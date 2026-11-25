"""Phase 5 REST API views for recommendations, learning catalogue, development plans, and progress."""
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasAnyPermission, HasInstitutionPermission
from apps.analytics.services import get_authorized_students_queryset
from apps.attempts.services import get_student_profile_for_membership
from apps.core.pagination import StandardResultsSetPagination
from apps.development.models import (
    DevelopmentActivity,
    DevelopmentPlan,
    LearningResource,
    ProgressRecord,
)
from apps.development.recommendations import (
    generate_student_recommendations,
    seed_starter_learning_catalogue,
)
from apps.development.serializers import (
    DevelopmentActivityCreateSerializer,
    DevelopmentActivitySerializer,
    DevelopmentPlanCreateSerializer,
    DevelopmentPlanSerializer,
    DevelopmentPlanUpdateSerializer,
    LearningResourceCreateSerializer,
    LearningResourceSerializer,
    LearningResourceUpdateSerializer,
    ProgressRecordCreateSerializer,
    ProgressRecordSerializer,
)
from apps.development.services import (
    add_plan_activity,
    create_development_plan,
    create_learning_resource,
    record_activity_progress,
    update_development_plan,
    update_learning_resource,
)
from apps.tenancy.mixins import require_active_institution, require_active_membership


def _paginate(qs, request, serializer_cls):
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(serializer_cls(page, many=True).data)


def _plan_base_queryset(institution):
    return (
        DevelopmentPlan.objects.for_institution(institution)
        .select_related(
            "student_profile",
            "student_profile__membership__user",
            "student_profile__cohort",
            "student_profile__cohort__programme",
            "student_profile__cohort__academic_year",
            "created_by",
        )
        .prefetch_related(
            Prefetch(
                "activities",
                queryset=DevelopmentActivity.objects.select_related("dimension", "resource")
                .prefetch_related(
                    Prefetch(
                        "progress_records",
                        queryset=ProgressRecord.objects.select_related("recorded_by").order_by("-recorded_at"),
                    )
                )
                .order_by("status", "due_date", "created_at"),
            )
        )
    )


def _get_authorized_plan(request, plan_id):
    inst = require_active_institution(request)
    membership = require_active_membership(request)
    perms = getattr(request, "institution_permissions", set())
    base_qs = _plan_base_queryset(inst)
    if "development.plan.manage" in perms:
        auth_students = get_authorized_students_queryset(inst, membership, perms)
        return get_object_or_404(base_qs.filter(student_profile__in=auth_students), id=plan_id)

    student = get_student_profile_for_membership(membership)
    return get_object_or_404(base_qs.filter(student_profile=student), id=plan_id)


def _get_authorized_activity(request, activity_id):
    inst = require_active_institution(request)
    membership = require_active_membership(request)
    perms = getattr(request, "institution_permissions", set())
    base_qs = DevelopmentActivity.objects.for_institution(inst).select_related(
        "plan",
        "plan__student_profile",
        "institution",
        "dimension",
        "resource",
    )
    if "development.plan.manage" in perms:
        auth_students = get_authorized_students_queryset(inst, membership, perms)
        return get_object_or_404(base_qs.filter(plan__student_profile__in=auth_students), id=activity_id)

    student = get_student_profile_for_membership(membership)
    return get_object_or_404(base_qs.filter(plan__student_profile=student), id=activity_id)


class SeedLearningCatalogueView(APIView):
    """Seed starter MCA learning pathways, trainings, projects, and certifications."""

    permission_classes = [HasInstitutionPermission("development.catalogue.manage")]

    def post(self, request):
        inst = require_active_institution(request)
        res = seed_starter_learning_catalogue(institution=inst, actor_user=request.user, request=request)
        return Response(res, status=status.HTTP_200_OK)


class LearningResourceListCreateView(APIView):
    """List institutional learning catalogue or create a new resource."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasInstitutionPermission("development.catalogue.manage")]
        return [HasAnyPermission("development.catalogue.manage", "development.plan.manage", "development.self.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        perms = getattr(request, "institution_permissions", set())
        qs = LearningResource.objects.for_institution(inst).order_by("target_domain", "resource_type", "title")

        status_val = request.query_params.get("status", "").strip()
        if "development.catalogue.manage" in perms:
            if status_val:
                qs = qs.filter(status=status_val)
        else:
            qs = qs.filter(status=LearningResource.Status.ACTIVE)

        resource_type = request.query_params.get("resource_type", "").strip()
        if resource_type:
            qs = qs.filter(resource_type=resource_type)

        target_domain = request.query_params.get("target_domain", "").strip()
        if target_domain:
            qs = qs.filter(target_domain__icontains=target_domain)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(provider__icontains=search)
                | Q(dimension_code__icontains=search)
                | Q(target_domain__icontains=search)
            )
        return _paginate(qs, request, LearningResourceSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        ser = LearningResourceCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        resource = create_learning_resource(
            institution=inst,
            data=ser.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(LearningResourceSerializer(resource).data, status=status.HTTP_201_CREATED)


class LearningResourceDetailView(APIView):
    """Update or archive an institutional learning resource."""

    permission_classes = [HasInstitutionPermission("development.catalogue.manage")]

    def patch(self, request, resource_id):
        inst = require_active_institution(request)
        resource = get_object_or_404(LearningResource.objects.for_institution(inst), id=resource_id)
        ser = LearningResourceUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        updated = update_learning_resource(
            resource=resource,
            data=ser.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(LearningResourceSerializer(updated).data)


class MyRecommendationsView(APIView):
    """Explainable recommendations for the authenticated student based on released results."""

    permission_classes = [HasInstitutionPermission("development.self.manage")]

    def get(self, request):
        membership = require_active_membership(request)
        student = get_student_profile_for_membership(membership)
        return Response(generate_student_recommendations(student, released_only=True))


class DevelopmentStudentListView(APIView):
    """List students in cohorts authorized for faculty/admin mentorship & planning."""

    permission_classes = [HasInstitutionPermission("development.plan.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())
        qs = (
            get_authorized_students_queryset(inst, membership, perms)
            .select_related("membership__user", "cohort", "cohort__programme", "cohort__academic_year")
            .order_by("registration_no")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(registration_no__icontains=search)
                | Q(membership__user__first_name__icontains=search)
                | Q(membership__user__last_name__icontains=search)
                | Q(membership__user__email__icontains=search)
            )
        cohort_id = request.query_params.get("cohort_id", "").strip()
        if cohort_id:
            qs = qs.filter(cohort_id=cohort_id)

        rows = [
            {
                "id": str(s.id),
                "registration_no": s.registration_no,
                "full_name": s.membership.user.full_name,
                "email": s.membership.user.email,
                "cohort_id": str(s.cohort_id) if s.cohort_id else None,
                "cohort_label": str(s.cohort) if s.cohort else None,
            }
            for s in qs[:100]
        ]
        return Response(rows)


class StudentRecommendationsView(APIView):
    """Explainable recommendations for a specific cohort-authorized student (Faculty/Admin)."""

    permission_classes = [HasInstitutionPermission("development.plan.manage")]

    def get(self, request, student_id):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())
        student = get_object_or_404(get_authorized_students_queryset(inst, membership, perms), id=student_id)
        return Response(generate_student_recommendations(student, released_only=False))


class DevelopmentPlanListCreateView(APIView):
    """List or create development plans scoped strictly by role & active institution."""

    permission_classes = [HasAnyPermission("development.plan.manage", "development.self.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())
        qs = _plan_base_queryset(inst)

        if "development.plan.manage" in perms:
            auth_students = get_authorized_students_queryset(inst, membership, perms)
            qs = qs.filter(student_profile__in=auth_students)
            student_id = request.query_params.get("student_id", "").strip()
            if student_id:
                qs = qs.filter(student_profile_id=student_id)
        else:
            student = get_student_profile_for_membership(membership)
            qs = qs.filter(student_profile=student)

        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(target_domain__icontains=search)
                | Q(student_profile__registration_no__icontains=search)
                | Q(student_profile__membership__user__first_name__icontains=search)
                | Q(student_profile__membership__user__last_name__icontains=search)
            )

        return _paginate(qs, request, DevelopmentPlanSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())

        ser = DevelopmentPlanCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)

        if "development.plan.manage" in perms:
            student_id = data.pop("student_id", None)
            if not student_id:
                raise ValidationError({"student_id": "student_id is required when creating a student development plan."})
            student = get_object_or_404(get_authorized_students_queryset(inst, membership, perms), id=student_id)
            default_status = DevelopmentPlan.Status.ACTIVE
        else:
            if data.get("student_id"):
                raise PermissionDenied("Students can only create development plans for themselves.")
            data.pop("student_id", None)
            student = get_student_profile_for_membership(membership)
            default_status = DevelopmentPlan.Status.PROPOSED
            if data.get("status") not in (None, DevelopmentPlan.Status.PROPOSED, DevelopmentPlan.Status.ACTIVE):
                raise PermissionDenied("Students may only create plans in proposed or active status.")

        plan = create_development_plan(
            institution=inst,
            student=student,
            data=data,
            actor_user=request.user,
            default_status=default_status,
            request=request,
        )
        hydrated = _plan_base_queryset(inst).get(id=plan.id)
        return Response(DevelopmentPlanSerializer(hydrated).data, status=status.HTTP_201_CREATED)


class DevelopmentPlanDetailView(APIView):
    """Retrieve or update an authorized development plan."""

    permission_classes = [HasAnyPermission("development.plan.manage", "development.self.manage")]

    def get(self, request, plan_id):
        plan = _get_authorized_plan(request, plan_id)
        return Response(DevelopmentPlanSerializer(plan).data)

    def patch(self, request, plan_id):
        plan = _get_authorized_plan(request, plan_id)
        ser = DevelopmentPlanUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        perms = getattr(request, "institution_permissions", set())
        if "development.plan.manage" not in perms and data.get("status") == DevelopmentPlan.Status.ACTIVE and plan.status == DevelopmentPlan.Status.PROPOSED:
            # Students can keep proposed or archive their own plan; faculty activates/approves mentored plans
            raise PermissionDenied("Only faculty or administrators may approve a proposed plan to active.")

        updated = update_development_plan(
            plan=plan,
            data=data,
            actor_user=request.user,
            request=request,
        )
        hydrated = _plan_base_queryset(plan.institution).get(id=updated.id)
        return Response(DevelopmentPlanSerializer(hydrated).data)


class PlanActivityCreateView(APIView):
    """Add a recommended learning resource or custom milestone to a development plan."""

    permission_classes = [HasAnyPermission("development.plan.manage", "development.self.manage")]

    def post(self, request, plan_id):
        plan = _get_authorized_plan(request, plan_id)
        ser = DevelopmentActivityCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        activity = add_plan_activity(
            plan=plan,
            data=ser.validated_data,
            actor_user=request.user,
            request=request,
        )
        hydrated = (
            DevelopmentActivity.objects.select_related("dimension", "resource")
            .prefetch_related("progress_records__recorded_by")
            .get(id=activity.id)
        )
        return Response(DevelopmentActivitySerializer(hydrated).data, status=status.HTTP_201_CREATED)


class ActivityProgressCreateView(APIView):
    """Record a progress update (0-100%), reflection, and optional evidence URL on an activity."""

    permission_classes = [HasAnyPermission("development.plan.manage", "development.self.manage")]

    def post(self, request, activity_id):
        activity = _get_authorized_activity(request, activity_id)
        ser = ProgressRecordCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        record = record_activity_progress(
            activity=activity,
            progress_percent=ser.validated_data["progress_percent"],
            reflection=ser.validated_data.get("reflection", ""),
            evidence_url=ser.validated_data.get("evidence_url", ""),
            actor_user=request.user,
            request=request,
        )
        activity.refresh_from_db()
        plan_status = activity.plan.status
        return Response(
            {
                "record": ProgressRecordSerializer(record).data,
                "activity_status": activity.status,
                "activity_progress_percent": activity.progress_percent,
                "plan_status": plan_status,
            },
            status=status.HTTP_201_CREATED,
        )

