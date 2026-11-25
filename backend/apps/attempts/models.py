"""Phase 3 models: AssessmentAttempt, Response, Evaluation, and AssessmentResult."""
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from apps.core.models import TenantScopedManager, TimeStampedModel, UUIDModel


class AssessmentAttempt(TimeStampedModel):
    """A student's attempt on a specific AssessmentAssignment."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        PARTIALLY_EVALUATED = "partially_evaluated", "Partially Evaluated"
        EVALUATED = "evaluated", "Evaluated"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="assessment_attempts",
    )
    assignment = models.ForeignKey(
        "assessments.AssessmentAssignment",
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    student_profile = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    attempt_no = models.PositiveSmallIntegerField(default=1)
    question_order = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.IN_PROGRESS)
    total_awarded = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))
    max_marks = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))

    objects = TenantScopedManager()

    class Meta:
        db_table = "assessment_attempts"
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student_profile", "attempt_no"],
                name="uq_attempt_assignment_student_no",
            ),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_attempt_id_inst"),
        ]
        indexes = [
            models.Index(fields=["institution", "student_profile", "status"], name="idx_attempt_stu_status"),
        ]

    def clean(self):
        super().clean()
        if self.assignment_id and self.institution_id and self.assignment.institution_id != self.institution_id:
            raise ValidationError({"assignment": "Assignment must belong to the same institution."})
        if self.student_profile_id and self.institution_id and self.student_profile.institution_id != self.institution_id:
            raise ValidationError({"student_profile": "Student must belong to the same institution."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Response(UUIDModel):
    """Persisted student answer to a specific VersionQuestion inside an attempt."""

    class ScoringStatus(models.TextChoices):
        UNANSWERED = "unanswered", "Unanswered"
        AUTO_SCORED = "auto_scored", "Auto Scored"
        PENDING_MANUAL = "pending_manual", "Pending Manual Evaluation"
        MANUALLY_EVALUATED = "manually_evaluated", "Manually Evaluated"
        NON_SCORED_SURVEY = "non_scored_survey", "Self-Report / Interest Recorded"

    attempt = models.ForeignKey(
        AssessmentAttempt,
        on_delete=models.PROTECT,
        related_name="responses",
    )
    version_question = models.ForeignKey(
        "assessments.VersionQuestion",
        on_delete=models.PROTECT,
        related_name="responses",
    )
    response_json = models.JSONField(default=dict, blank=True)
    saved_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    awarded_marks = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    scoring_status = models.CharField(
        max_length=30,
        choices=ScoringStatus.choices,
        default=ScoringStatus.UNANSWERED,
    )

    class Meta:
        db_table = "responses"
        constraints = [
            models.UniqueConstraint(fields=["attempt", "version_question"], name="uq_response_attempt_vq"),
        ]


class Evaluation(UUIDModel):
    """Append-only manual grading record retaining evaluation history."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    response = models.ForeignKey(
        Response,
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    evaluator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evaluations_performed",
    )
    rubric_result = models.JSONField(default=dict, blank=True)
    awarded_marks = models.DecimalField(max_digits=7, decimal_places=2)
    comments = models.TextField(blank=True, default="")
    evaluated_at = models.DateTimeField(auto_now_add=True)
    version_no = models.PositiveIntegerField(default=1)

    objects = TenantScopedManager()

    class Meta:
        db_table = "evaluations"
        ordering = ["-version_no", "-evaluated_at"]
        constraints = [
            models.CheckConstraint(condition=Q(awarded_marks__gte=0), name="chk_eval_marks_nonneg"),
            models.UniqueConstraint(fields=["response", "version_no"], name="uq_eval_response_ver"),
        ]


class AssessmentResult(TimeStampedModel):
    """Calculated result snapshot separating demonstrated, self-report, and interest families."""

    class ResultStatus(models.TextChoices):
        PENDING_MANUAL = "pending_manual", "Pending Manual Evaluation"
        FINALIZED = "finalized", "Finalized"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="assessment_results",
    )
    attempt = models.OneToOneField(
        AssessmentAttempt,
        on_delete=models.PROTECT,
        related_name="result",
    )
    raw_score = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))
    max_score = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))
    normalized_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    breakdown_json = models.JSONField(default=dict, blank=True)
    result_status = models.CharField(
        max_length=30,
        choices=ResultStatus.choices,
        default=ResultStatus.FINALIZED,
    )
    calculated_at = models.DateTimeField(auto_now=True)
    algorithm_version = models.CharField(max_length=40, default="v1.0")

    objects = TenantScopedManager()

    class Meta:
        db_table = "assessment_results"

