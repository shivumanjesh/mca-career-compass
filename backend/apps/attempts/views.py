"""Phase 3 REST API views: student assignments, test runner, autosave, submit, and manual evaluation."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response as DRFResponse
from rest_framework.views import APIView

from apps.accounts.permissions import HasInstitutionPermission
from apps.attempts.models import AssessmentAttempt, AssessmentResult, Response
from apps.attempts.serializers import (
    AssessmentAttemptSummarySerializer,
    AssessmentResultSerializer,
    AutosaveRequestSerializer,
    EvaluationCreateSerializer,
    EvaluationSerializer,
    PendingEvaluationResponseSerializer,
)
from apps.attempts.services import (
    autosave_attempt_responses,
    evaluate_manual_response,
    get_student_assignments_queryset,
    get_student_profile_for_membership,
    sanitize_question_snapshot_for_student,
    start_or_resume_attempt,
    submit_attempt,
)
from apps.core.pagination import StandardResultsSetPagination
from apps.tenancy.mixins import require_active_institution, require_active_membership


def _build_attempt_runner_payload(attempt: AssessmentAttempt) -> dict:
    version = attempt.assignment.assessment_version
    vqs_by_id = {
        str(vq.id): vq for vq in version.version_questions.all()
    }
    ordered_ids = attempt.question_order or [str(vq.id) for vq in version.version_questions.order_by("sequence")]
    questions = [
        sanitize_question_snapshot_for_student(vqs_by_id[vq_id])
        for vq_id in ordered_ids
        if vq_id in vqs_by_id
    ]
    saved_responses = {
        str(r.version_question_id): r.response_json
        for r in attempt.responses.all()
    }
    now = timezone.now()
    remaining_seconds = max(0, int((attempt.expires_at - now).total_seconds()))

    return {
        "attempt": AssessmentAttemptSummarySerializer(attempt).data,
        "instructions": version.instructions,
        "duration_minutes": version.duration_minutes,
        "server_time": now.isoformat(),
        "remaining_seconds": remaining_seconds,
        "questions": questions,
        "saved_responses": saved_responses,
    }


class StudentMyAssignmentsView(APIView):
    """List assignments targeted to the authenticated student or their cohort."""

    permission_classes = [HasInstitutionPermission("assessment.attempt.take")]

    def get(self, request):
        membership = require_active_membership(request)
        student = get_student_profile_for_membership(membership)
        assignments = list(get_student_assignments_queryset(student))
        attempts_by_assign: dict = {}
        for att in AssessmentAttempt.objects.filter(
            institution=membership.institution,
            student_profile=student,
        ).order_by("-attempt_no"):
            attempts_by_assign.setdefault(att.assignment_id, []).append(att)

        now = timezone.now()
        results = []
        for a in assignments:
            atts = attempts_by_assign.get(a.id, [])
            latest = atts[0] if atts else None
            in_window = a.status == "active" and a.opens_at <= now <= a.closes_at
            can_start = in_window and (
                (latest and latest.status == AssessmentAttempt.Status.IN_PROGRESS)
                or len(atts) < a.assessment_version.max_attempts
            )
            results.append(
                {
                    "id": str(a.id),
                    "template_name": a.assessment_version.template.name,
                    "version_no": a.assessment_version.version_no,
                    "duration_minutes": a.assessment_version.duration_minutes,
                    "max_attempts": a.assessment_version.max_attempts,
                    "total_marks": str(a.assessment_version.total_marks),
                    "opens_at": a.opens_at.isoformat(),
                    "closes_at": a.closes_at.isoformat(),
                    "status": a.status,
                    "results_released": a.results_released,
                    "attempts_used": len(atts),
                    "can_start_or_resume": bool(can_start),
                    "latest_attempt": AssessmentAttemptSummarySerializer(latest).data if latest else None,
                }
            )
        return DRFResponse(results)


class StudentStartAttemptView(APIView):
    """Start or resume an attempt for an assigned assessment."""

    permission_classes = [HasInstitutionPermission("assessment.attempt.take")]

    def post(self, request, assignment_id):
        membership = require_active_membership(request)
        student = get_student_profile_for_membership(membership)
        assignment = get_object_or_404(get_student_assignments_queryset(student), id=assignment_id)
        attempt = start_or_resume_attempt(
            assignment=assignment,
            student=student,
            actor_user=request.user,
            request=request,
        )
        return DRFResponse(_build_attempt_runner_payload(attempt), status=status.HTTP_200_OK)


class StudentAttemptDetailView(APIView):
    """Fetch current attempt runner payload for own attempt."""

    permission_classes = [HasInstitutionPermission("assessment.attempt.take")]

    def get(self, request, attempt_id):
        membership = require_active_membership(request)
        student = get_student_profile_for_membership(membership)
        attempt = get_object_or_404(
            AssessmentAttempt.objects.for_institution(membership.institution).select_related(
                "assignment__assessment_version__template"
            ),
            id=attempt_id,
            student_profile=student,
        )
        return DRFResponse(_build_attempt_runner_payload(attempt))


class StudentAutosaveResponsesView(APIView):
    """Idempotently persist responses while attempt is in progress and within server timer."""

    permission_classes = [HasInstitutionPermission("assessment.attempt.take")]

    def put(self, request, attempt_id):
        membership = require_active_membership(request)
        student = get_student_profile_for_membership(membership)
        attempt = get_object_or_404(
            AssessmentAttempt.objects.for_institution(membership.institution),
            id=attempt_id,
            student_profile=student,
        )
        serializer = AutosaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        autosave_attempt_responses(
            attempt=attempt,
            items=serializer.validated_data["items"],
            actor_user=request.user,
            request=request,
        )
        return DRFResponse({"status": "saved", "saved_at": timezone.now().isoformat()})


class StudentSubmitAttemptView(APIView):
    """Idempotently submit attempt and score objective items from immutable snapshot."""

    permission_classes = [HasInstitutionPermission("assessment.attempt.take")]

    def post(self, request, attempt_id):
        membership = require_active_membership(request)
        student = get_student_profile_for_membership(membership)
        attempt = get_object_or_404(
            AssessmentAttempt.objects.for_institution(membership.institution),
            id=attempt_id,
            student_profile=student,
        )
        submitted = submit_attempt(attempt=attempt, actor_user=request.user, request=request)
        return DRFResponse(AssessmentAttemptSummarySerializer(submitted).data, status=status.HTTP_200_OK)


class StudentAttemptResultView(APIView):
    """View own released attempt result (strictly gated by results_released)."""

    permission_classes = [HasInstitutionPermission("results.self.view")]

    def get(self, request, attempt_id):
        membership = require_active_membership(request)
        student = get_student_profile_for_membership(membership)
        attempt = get_object_or_404(
            AssessmentAttempt.objects.for_institution(membership.institution).select_related(
                "assignment__assessment_version__template"
            ),
            id=attempt_id,
            student_profile=student,
        )
        if not attempt.assignment.results_released:
            raise PermissionDenied("Results for this assessment have not been released yet.")
        result = get_object_or_404(AssessmentResult, attempt=attempt)
        return DRFResponse(AssessmentResultSerializer(result).data)


class EvaluationQueueListView(APIView):
    """List responses requiring or having manual evaluation, scoped to Faculty cohorts or Admin."""

    permission_classes = [HasInstitutionPermission("assessment.response.evaluate")]

    def get(self, request):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())

        qs = (
            Response.objects.filter(
                attempt__institution=inst,
                scoring_status__in=[
                    Response.ScoringStatus.PENDING_MANUAL,
                    Response.ScoringStatus.MANUALLY_EVALUATED,
                ],
            )
            .select_related(
                "attempt__student_profile__membership__user",
                "attempt__assignment__assessment_version__template",
                "version_question",
            )
            .prefetch_related("evaluations__evaluator_user")
            .order_by("scoring_status", "-submitted_at")
        )

        # Faculty/HOD without institution-wide assign/manage scope sees only assigned cohorts
        if "assessment.assign" not in perms:
            qs = qs.filter(
                attempt__student_profile__cohort__faculty_assignments__faculty_profile__membership=membership
            ).distinct()

        status_filter = request.query_params.get("scoring_status", "").strip()
        if status_filter:
            qs = qs.filter(scoring_status=status_filter)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(PendingEvaluationResponseSerializer(page, many=True).data)


class EvaluateResponseView(APIView):
    """Submit a manual rubric evaluation for an eligible response."""

    permission_classes = [HasInstitutionPermission("assessment.response.evaluate")]

    def post(self, request, response_id):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())

        qs = Response.objects.filter(attempt__institution=inst).select_related(
            "attempt__student_profile__cohort",
            "version_question",
        )
        if "assessment.assign" not in perms:
            qs = qs.filter(
                attempt__student_profile__cohort__faculty_assignments__faculty_profile__membership=membership
            ).distinct()

        resp_obj = get_object_or_404(qs, id=response_id)
        serializer = EvaluationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        evaluation = evaluate_manual_response(
            response=resp_obj,
            awarded_marks=data["awarded_marks"],
            comments=data.get("comments", ""),
            rubric_result=data.get("rubric_result"),
            evaluator_user=request.user,
            request=request,
        )
        return DRFResponse(EvaluationSerializer(evaluation).data, status=status.HTTP_201_CREATED)

