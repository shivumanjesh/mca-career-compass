"""Phase 3 services: assignments, attempt lifecycle, autosave, submission & manual evaluation."""
import random
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.academics.models import Cohort
from apps.assessments.models import AssessmentAssignment, AssessmentVersion
from apps.attempts.models import AssessmentAttempt, Evaluation, Response
from apps.attempts.scoring import recalculate_attempt_result, score_single_response
from apps.audit.services import log_audit_event
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership


def sanitize_question_snapshot_for_student(vq) -> dict[str, Any]:
    """Strip answer keys, feedback, and scoring secrets before serving to a student."""
    snap = vq.question_snapshot or {}
    safe_options = [
        {
            "option_key": o["option_key"],
            "option_text": o["option_text"],
            "display_order": o["display_order"],
        }
        for o in (snap.get("options") or [])
    ]
    return {
        "version_question_id": str(vq.id),
        "sequence": vq.sequence,
        "marks": str(vq.marks),
        "negative_marks": str(vq.negative_marks),
        "required": vq.required,
        "question_code": snap.get("question_code"),
        "question_type": snap.get("question_type"),
        "prompt": snap.get("prompt"),
        "difficulty": snap.get("difficulty"),
        "measurement_family": snap.get("measurement_family"),
        "options": safe_options,
    }


@transaction.atomic
def create_assessment_assignment(
    *,
    institution: Institution,
    assessment_version_id,
    cohort_id=None,
    student_profile_id=None,
    opens_at,
    closes_at,
    results_released: bool = False,
    actor_user,
    request=None,
) -> AssessmentAssignment:
    if bool(cohort_id) == bool(student_profile_id):
        raise ValidationError({"target": "Specify either cohort_id or student_profile_id, not both or neither."})
    if closes_at < opens_at:
        raise ValidationError({"closes_at": "Closing time must be on or after opening time."})

    version = AssessmentVersion.objects.filter(institution=institution, id=assessment_version_id).first()
    if version is None:
        raise ValidationError({"assessment_version_id": "Assessment version not found in active institution."})
    if version.status != AssessmentVersion.Status.PUBLISHED:
        raise ValidationError({"assessment_version_id": "Only published assessment versions can be assigned."})

    cohort = None
    if cohort_id:
        cohort = Cohort.objects.filter(institution=institution, id=cohort_id).first()
        if cohort is None:
            raise ValidationError({"cohort_id": "Cohort not found in active institution."})

    student = None
    if student_profile_id:
        student = StudentProfile.objects.filter(institution=institution, id=student_profile_id).first()
        if student is None:
            raise ValidationError({"student_profile_id": "Student not found in active institution."})

    assignment = AssessmentAssignment.objects.create(
        institution=institution,
        assessment_version=version,
        cohort=cohort,
        student_profile=student,
        opens_at=opens_at,
        closes_at=closes_at,
        results_released=results_released,
        created_by=actor_user,
    )
    log_audit_event(
        action="ASSESSMENT_ASSIGNED",
        entity_type="AssessmentAssignment",
        entity_id=assignment.id,
        institution=institution,
        actor_user=actor_user,
        after={
            "template": version.template.name,
            "version_no": version.version_no,
            "cohort_id": str(cohort.id) if cohort else None,
            "student_profile_id": str(student.id) if student else None,
            "opens_at": opens_at.isoformat(),
            "closes_at": closes_at.isoformat(),
        },
        request=request,
    )
    return assignment


def get_student_profile_for_membership(membership: Membership) -> StudentProfile:
    profile = StudentProfile.objects.for_institution(membership.institution).filter(membership=membership).first()
    if profile is None:
        raise PermissionDenied("No student profile is linked to your active membership.")
    return profile


def get_student_assignments_queryset(student: StudentProfile):
    return (
        AssessmentAssignment.objects.for_institution(student.institution)
        .filter(
            Q(student_profile=student)
            | (Q(cohort=student.cohort) if student.cohort_id else Q(pk__isnull=True)),
        )
        .exclude(status=AssessmentAssignment.Status.CANCELLED)
        .select_related("assessment_version__template", "cohort")
        .order_by("-opens_at")
    )


@transaction.atomic
def start_or_resume_attempt(*, assignment: AssessmentAssignment, student: StudentProfile, actor_user, request=None) -> AssessmentAttempt:
    now = timezone.now()
    if assignment.status != AssessmentAssignment.Status.ACTIVE:
        raise ValidationError({"assignment": "This assessment assignment is no longer active."})
    if now < assignment.opens_at:
        raise ValidationError({"assignment": "This assessment is not open yet."})
    if now > assignment.closes_at:
        raise ValidationError({"assignment": "The availability window for this assessment has closed."})

    # Resume existing in-progress attempt if still valid
    existing_in_progress = (
        AssessmentAttempt.objects.select_for_update()
        .filter(assignment=assignment, student_profile=student, status=AssessmentAttempt.Status.IN_PROGRESS)
        .first()
    )
    if existing_in_progress is not None:
        if now <= existing_in_progress.expires_at:
            return existing_in_progress
        # Expired attempt: auto-submit immediately before checking attempt limit
        submit_attempt(attempt=existing_in_progress, actor_user=actor_user, request=request, auto_expired=True)

    version = assignment.assessment_version
    attempts_count = AssessmentAttempt.objects.filter(assignment=assignment, student_profile=student).count()
    if attempts_count >= version.max_attempts:
        raise ValidationError({"attempts": f"Maximum allowed attempts ({version.max_attempts}) reached for this assessment."})

    vqs = list(version.version_questions.order_by("sequence"))
    if version.randomize_questions:
        rng = random.Random(f"{assignment.id}:{student.id}:{attempts_count + 1}")
        rng.shuffle(vqs)

    order_ids = [str(vq.id) for vq in vqs]
    expires_at = min(now + timedelta(minutes=version.duration_minutes), assignment.closes_at)

    attempt = AssessmentAttempt.objects.create(
        institution=assignment.institution,
        assignment=assignment,
        student_profile=student,
        attempt_no=attempts_count + 1,
        question_order=order_ids,
        expires_at=expires_at,
        max_marks=version.total_marks,
        status=AssessmentAttempt.Status.IN_PROGRESS,
    )
    log_audit_event(
        action="ASSESSMENT_ATTEMPT_STARTED",
        entity_type="AssessmentAttempt",
        entity_id=attempt.id,
        institution=assignment.institution,
        actor_user=actor_user,
        after={"assignment_id": str(assignment.id), "attempt_no": attempt.attempt_no},
        request=request,
    )
    return attempt


@transaction.atomic
def autosave_attempt_responses(*, attempt: AssessmentAttempt, items: list[dict[str, Any]], actor_user, request=None) -> AssessmentAttempt:
    locked_attempt = AssessmentAttempt.objects.select_for_update().get(id=attempt.id)
    if locked_attempt.status != AssessmentAttempt.Status.IN_PROGRESS:
        raise ValidationError({"attempt": "This attempt has already been submitted and cannot be modified."})

    now = timezone.now()
    if now > locked_attempt.expires_at + timedelta(seconds=15):
        submit_attempt(attempt=locked_attempt, actor_user=actor_user, request=request, auto_expired=True)
        raise ValidationError({"attempt": "Time expired. Your saved responses were automatically submitted."})

    valid_vq_map = {
        str(vq.id): vq
        for vq in locked_attempt.assignment.assessment_version.version_questions.all()
    }
    for item in items:
        vq_id = str(item["version_question_id"])
        vq = valid_vq_map.get(vq_id)
        if vq is None:
            raise ValidationError({"items": f"Question {vq_id} does not belong to this assessment version."})
        Response.objects.update_or_create(
            attempt=locked_attempt,
            version_question=vq,
            defaults={"response_json": item.get("response_json") or {}},
        )
    return locked_attempt


@transaction.atomic
def submit_attempt(*, attempt: AssessmentAttempt, actor_user, request=None, auto_expired: bool = False) -> AssessmentAttempt:
    locked_attempt = AssessmentAttempt.objects.select_for_update().get(id=attempt.id)
    # Idempotent submission guard
    if locked_attempt.status != AssessmentAttempt.Status.IN_PROGRESS:
        return locked_attempt

    now = timezone.now()
    vqs = list(
        locked_attempt.assignment.assessment_version.version_questions.select_related("question").all()
    )
    existing_responses = {r.version_question_id: r for r in locked_attempt.responses.all()}

    for vq in vqs:
        resp = existing_responses.get(vq.id)
        if resp is None:
            resp = Response.objects.create(
                attempt=locked_attempt,
                version_question=vq,
                response_json={},
            )
        awarded, scoring_status = score_single_response(vq, resp.response_json)
        resp.awarded_marks = awarded
        resp.scoring_status = scoring_status
        resp.submitted_at = now
        resp.save(update_fields=["awarded_marks", "scoring_status", "submitted_at"])

    locked_attempt.submitted_at = now
    locked_attempt.save(update_fields=["submitted_at", "updated_at"])

    recalculate_attempt_result(locked_attempt)

    log_audit_event(
        action="ASSESSMENT_ATTEMPT_SUBMITTED",
        entity_type="AssessmentAttempt",
        entity_id=locked_attempt.id,
        institution=locked_attempt.institution,
        actor_user=actor_user,
        after={
            "attempt_no": locked_attempt.attempt_no,
            "auto_expired": auto_expired,
            "status": locked_attempt.status,
            "total_awarded": str(locked_attempt.total_awarded),
        },
        request=request,
    )
    return locked_attempt


@transaction.atomic
def evaluate_manual_response(
    *,
    response: Response,
    awarded_marks: Decimal,
    comments: str = "",
    rubric_result: dict | None = None,
    evaluator_user,
    request=None,
) -> Evaluation:
    vq = response.version_question
    max_m = Decimal(str(vq.marks))
    if awarded_marks < 0 or awarded_marks > max_m:
        raise ValidationError({"awarded_marks": f"Awarded marks must be between 0 and {max_m}."})

    attempt = response.attempt
    if attempt.status == AssessmentAttempt.Status.IN_PROGRESS:
        raise ValidationError({"response": "Cannot evaluate an attempt that is still in progress."})

    next_ver = (response.evaluations.aggregate(m=Max("version_no"))["m"] or 0) + 1
    evaluation = Evaluation.objects.create(
        institution=attempt.institution,
        response=response,
        evaluator_user=evaluator_user,
        rubric_result=rubric_result or {},
        awarded_marks=awarded_marks,
        comments=comments.strip(),
        version_no=next_ver,
    )

    response.awarded_marks = awarded_marks
    response.scoring_status = Response.ScoringStatus.MANUALLY_EVALUATED
    response.save(update_fields=["awarded_marks", "scoring_status"])

    recalculate_attempt_result(attempt)

    log_audit_event(
        action="RESPONSE_MANUALLY_EVALUATED",
        entity_type="Evaluation",
        entity_id=evaluation.id,
        institution=attempt.institution,
        actor_user=evaluator_user,
        after={
            "attempt_id": str(attempt.id),
            "response_id": str(response.id),
            "awarded_marks": str(awarded_marks),
            "version_no": next_ver,
        },
        request=request,
    )
    return evaluation

