"""Academic structure REST API views (tenant-scoped)."""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import AcademicYear, Cohort, Programme
from apps.academics.serializers import (
    AcademicYearSerializer,
    AcademicYearWriteSerializer,
    CohortSerializer,
    CohortWriteSerializer,
    ProgrammeSerializer,
    ProgrammeWriteSerializer,
)
from apps.academics.services import (
    create_academic_year,
    create_cohort,
    create_programme,
    update_academic_year,
    update_cohort,
    update_programme,
)
from apps.accounts.permissions import HasAnyPermission, HasInstitutionPermission
from apps.core.pagination import StandardResultsSetPagination
from apps.tenancy.mixins import require_active_institution


def _paginate(qs, request, serializer_cls):
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(serializer_cls(page, many=True).data)


class ProgrammeListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [
                HasAnyPermission(
                    "academics.cohort.manage",
                    "institution.student.manage",
                    "institution.faculty.manage",
                    "student.assigned.view",
                )
            ]
        return [HasInstitutionPermission("academics.cohort.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = Programme.objects.for_institution(inst).order_by("code")
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        return _paginate(qs, request, ProgrammeSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = ProgrammeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prog = create_programme(
            institution=inst,
            actor_user=request.user,
            request=request,
            **serializer.validated_data,
        )
        return Response(ProgrammeSerializer(prog).data, status=status.HTTP_201_CREATED)


class ProgrammeDetailView(APIView):
    permission_classes = [HasInstitutionPermission("academics.cohort.manage")]

    def patch(self, request, programme_id):
        inst = require_active_institution(request)
        prog = get_object_or_404(Programme.objects.for_institution(inst), id=programme_id)
        serializer = ProgrammeWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_programme(
            programme=prog,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(ProgrammeSerializer(updated).data)


class AcademicYearListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [
                HasAnyPermission(
                    "academics.cohort.manage",
                    "institution.student.manage",
                    "institution.faculty.manage",
                    "student.assigned.view",
                )
            ]
        return [HasInstitutionPermission("academics.cohort.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = AcademicYear.objects.for_institution(inst).order_by("-start_date", "name")
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        return _paginate(qs, request, AcademicYearSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = AcademicYearWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ay = create_academic_year(
            institution=inst,
            actor_user=request.user,
            request=request,
            **serializer.validated_data,
        )
        return Response(AcademicYearSerializer(ay).data, status=status.HTTP_201_CREATED)


class AcademicYearDetailView(APIView):
    permission_classes = [HasInstitutionPermission("academics.cohort.manage")]

    def patch(self, request, academic_year_id):
        inst = require_active_institution(request)
        ay = get_object_or_404(AcademicYear.objects.for_institution(inst), id=academic_year_id)
        serializer = AcademicYearWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_academic_year(
            academic_year=ay,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(AcademicYearSerializer(updated).data)


class CohortListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [
                HasAnyPermission(
                    "academics.cohort.manage",
                    "institution.student.manage",
                    "institution.student.import",
                    "institution.faculty.manage",
                    "student.assigned.view",
                    "assessment.assign",
                )
            ]
        return [HasInstitutionPermission("academics.cohort.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = (
            Cohort.objects.for_institution(inst)
            .select_related("programme", "academic_year")
            .annotate(student_count=Count("students", distinct=True))
            .order_by("-academic_year__start_date", "batch_name", "semester", "section")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(batch_name__icontains=search)
                | Q(programme__code__icontains=search)
                | Q(section__icontains=search)
            )
        programme_id = request.query_params.get("programme_id", "").strip()
        if programme_id:
            qs = qs.filter(programme_id=programme_id)
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        return _paginate(qs, request, CohortSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = CohortWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cohort = create_cohort(
            institution=inst,
            actor_user=request.user,
            request=request,
            **serializer.validated_data,
        )
        return Response(CohortSerializer(cohort).data, status=status.HTTP_201_CREATED)


class CohortDetailView(APIView):
    permission_classes = [HasInstitutionPermission("academics.cohort.manage")]

    def patch(self, request, cohort_id):
        inst = require_active_institution(request)
        cohort = get_object_or_404(Cohort.objects.for_institution(inst), id=cohort_id)
        serializer = CohortWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_cohort(
            cohort=cohort,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(CohortSerializer(updated).data)

