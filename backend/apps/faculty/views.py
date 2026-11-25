"""Faculty management and cohort assignment REST API views."""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasInstitutionPermission
from apps.core.pagination import StandardResultsSetPagination
from apps.faculty.models import CohortFaculty, FacultyProfile
from apps.faculty.serializers import (
    CohortAssignmentSerializer,
    FacultyCohortAssignSerializer,
    FacultyCreateSerializer,
    FacultyProfileSerializer,
    FacultyUpdateSerializer,
)
from apps.faculty.services import (
    assign_faculty_to_cohort,
    create_faculty_profile,
    remove_faculty_cohort_assignment,
    update_faculty_profile,
)
from apps.tenancy.mixins import require_active_institution, require_active_membership


class FacultyListCreateView(APIView):
    permission_classes = [HasInstitutionPermission("institution.faculty.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = (
            FacultyProfile.objects.for_institution(inst)
            .select_related("membership__user")
            .prefetch_related("cohort_assignments__cohort__programme")
            .order_by("membership__user__first_name", "employee_code")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(employee_code__icontains=search)
                | Q(department__icontains=search)
                | Q(designation__icontains=search)
                | Q(membership__user__email__icontains=search)
                | Q(membership__user__first_name__icontains=search)
                | Q(membership__user__last_name__icontains=search)
            )
        dept = request.query_params.get("department", "").strip()
        if dept:
            qs = qs.filter(department__iexact=dept)
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(FacultyProfileSerializer(page, many=True).data)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = FacultyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile, onboarding_link = create_faculty_profile(
            institution=inst,
            email=data["email"],
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
            employee_code=data.get("employee_code"),
            department=data.get("department", ""),
            designation=data.get("designation", ""),
            status=data["status"],
            password=data.get("password") or None,
            actor_user=request.user,
            request=request,
        )
        payload = FacultyProfileSerializer(profile).data
        if onboarding_link:
            payload["onboarding_reset_path"] = onboarding_link
        return Response(payload, status=status.HTTP_201_CREATED)


class FacultyDetailView(APIView):
    permission_classes = [HasInstitutionPermission("institution.faculty.manage")]

    def get(self, request, faculty_id):
        inst = require_active_institution(request)
        profile = get_object_or_404(
            FacultyProfile.objects.for_institution(inst)
            .select_related("membership__user")
            .prefetch_related("cohort_assignments__cohort__programme"),
            id=faculty_id,
        )
        return Response(FacultyProfileSerializer(profile).data)

    def patch(self, request, faculty_id):
        inst = require_active_institution(request)
        profile = get_object_or_404(
            FacultyProfile.objects.for_institution(inst).select_related("membership__user"),
            id=faculty_id,
        )
        serializer = FacultyUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_faculty_profile(
            profile=profile,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(FacultyProfileSerializer(updated).data)


class FacultyCohortAssignListCreateView(APIView):
    permission_classes = [HasInstitutionPermission("institution.faculty.manage")]

    def get(self, request, faculty_id):
        inst = require_active_institution(request)
        profile = get_object_or_404(FacultyProfile.objects.for_institution(inst), id=faculty_id)
        assignments = CohortFaculty.objects.for_institution(inst).filter(faculty_profile=profile).select_related("cohort__programme")
        return Response(CohortAssignmentSerializer(assignments, many=True).data)

    def post(self, request, faculty_id):
        inst = require_active_institution(request)
        profile = get_object_or_404(
            FacultyProfile.objects.for_institution(inst).select_related("membership__user"),
            id=faculty_id,
        )
        serializer = FacultyCohortAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = assign_faculty_to_cohort(
            faculty_profile=profile,
            cohort_id=serializer.validated_data["cohort_id"],
            assignment_type=serializer.validated_data["assignment_type"],
            actor_user=request.user,
            request=request,
        )
        return Response(CohortAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class FacultyCohortAssignDeleteView(APIView):
    permission_classes = [HasInstitutionPermission("institution.faculty.manage")]

    def delete(self, request, faculty_id, assignment_id):
        inst = require_active_institution(request)
        assignment = get_object_or_404(
            CohortFaculty.objects.for_institution(inst).select_related("faculty_profile__membership__user"),
            id=assignment_id,
            faculty_profile_id=faculty_id,
        )
        remove_faculty_cohort_assignment(
            assignment=assignment,
            actor_user=request.user,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class FacultySelfCohortsView(APIView):
    """Return cohorts assigned to the authenticated Faculty/HOD member."""

    permission_classes = [HasInstitutionPermission("student.assigned.view")]

    def get(self, request):
        membership = require_active_membership(request)
        assignments = (
            CohortFaculty.objects.for_institution(membership.institution)
            .filter(faculty_profile__membership=membership)
            .select_related("cohort__programme", "cohort__academic_year")
            .annotate(student_count=Count("cohort__students", distinct=True))
        )
        data = []
        for a in assignments:
            data.append(
                {
                    "id": str(a.id),
                    "cohort_id": str(a.cohort_id),
                    "cohort_label": str(a.cohort),
                    "programme_code": a.cohort.programme.code,
                    "batch_name": a.cohort.batch_name,
                    "semester": a.cohort.semester,
                    "section": a.cohort.section,
                    "assignment_type": a.assignment_type,
                    "student_count": a.student_count,
                }
            )
        return Response(data)

