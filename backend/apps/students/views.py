"""Student management and scoped student-view REST APIs."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasAnyPermission, HasInstitutionPermission
from apps.core.pagination import StandardResultsSetPagination
from apps.students.models import StudentProfile
from apps.students.serializers import (
    StudentCreateSerializer,
    StudentProfileSerializer,
    StudentUpdateSerializer,
)
from apps.students.services import create_student_profile, update_student_profile
from apps.tenancy.mixins import require_active_institution, require_active_membership


def _scoped_student_queryset(request):
    inst = require_active_institution(request)
    qs = StudentProfile.objects.for_institution(inst).select_related(
        "membership__user",
        "cohort__programme",
        "cohort__academic_year",
    )
    perms = getattr(request, "institution_permissions", set())
    if "institution.student.manage" in perms or "assessment.assign" in perms:
        return qs
    if "student.assigned.view" in perms:
        membership = require_active_membership(request)
        return qs.filter(cohort__faculty_assignments__faculty_profile__membership=membership).distinct()
    return qs.none()


class StudentListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [HasAnyPermission("institution.student.manage", "student.assigned.view", "assessment.assign")]
        return [HasInstitutionPermission("institution.student.manage")]

    def get(self, request):
        qs = _scoped_student_queryset(request).order_by("registration_no")

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(registration_no__icontains=search)
                | Q(membership__user__email__icontains=search)
                | Q(membership__user__first_name__icontains=search)
                | Q(membership__user__last_name__icontains=search)
            )

        cohort_id = request.query_params.get("cohort_id", "").strip()
        if cohort_id:
            qs = qs.filter(cohort_id=cohort_id)

        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(StudentProfileSerializer(page, many=True).data)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = StudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile, onboarding_link = create_student_profile(
            institution=inst,
            email=data["email"],
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
            registration_no=data["registration_no"],
            cohort_id=data.get("cohort_id"),
            admission_year=data.get("admission_year"),
            phone=data.get("phone", ""),
            status=data["status"],
            password=data.get("password") or None,
            actor_user=request.user,
            request=request,
        )
        payload = StudentProfileSerializer(profile).data
        if onboarding_link:
            payload["onboarding_reset_path"] = onboarding_link
        return Response(payload, status=status.HTTP_201_CREATED)


class StudentDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [HasAnyPermission("institution.student.manage", "student.assigned.view")]
        return [HasInstitutionPermission("institution.student.manage")]

    def get(self, request, student_id):
        qs = _scoped_student_queryset(request)
        profile = get_object_or_404(qs, id=student_id)
        return Response(StudentProfileSerializer(profile).data)

    def patch(self, request, student_id):
        inst = require_active_institution(request)
        profile = get_object_or_404(
            StudentProfile.objects.for_institution(inst).select_related("membership__user", "cohort"),
            id=student_id,
        )
        serializer = StudentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_student_profile(
            profile=profile,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(StudentProfileSerializer(updated).data)


class StudentSelfProfileView(APIView):
    """Derive StudentProfile exclusively from authenticated active_membership."""

    permission_classes = [HasInstitutionPermission("student.self.view")]

    def get(self, request):
        membership = require_active_membership(request)
        profile = (
            StudentProfile.objects.for_institution(membership.institution)
            .select_related("membership__user", "cohort__programme", "cohort__academic_year")
            .filter(membership=membership)
            .first()
        )
        if profile is None:
            raise PermissionDenied("No student profile is linked to your active membership.")
        return Response(StudentProfileSerializer(profile).data)

