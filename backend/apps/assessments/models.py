"""Phase 2 models: categories, dimensions, skill tags, question bank, templates, and immutable versions."""
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from apps.core.models import TenantScopedManager, TimeStampedModel, UUIDModel


class MeasurementFamily(models.TextChoices):
    """Strictly separated measurement families per product guardrails."""

    DEMONSTRATED_PERFORMANCE = "demonstrated_performance", "Demonstrated Performance"
    SELF_REPORTED_PROFICIENCY = "self_reported_proficiency", "Self-Reported Proficiency"
    STATED_INTEREST = "stated_interest", "Stated Career Interest"


class LifecycleStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class AssessmentCategory(TimeStampedModel):
    """High-level assessment category (Technical, Cognitive, Soft Skills, Career Interest)."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="assessment_categories",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.ACTIVE)

    objects = TenantScopedManager()

    class Meta:
        db_table = "assessment_categories"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "name"], name="uq_assessment_cat_inst_name"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_assessment_cat_id_inst"),
        ]

    def __str__(self) -> str:
        return self.name


class AssessmentDimension(TimeStampedModel):
    """Configurable assessment dimension (e.g., Programming, Logical Reasoning, Communication)."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="assessment_dimensions",
    )
    category = models.ForeignKey(
        AssessmentCategory,
        on_delete=models.PROTECT,
        related_name="dimensions",
    )
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    measurement_family = models.CharField(
        max_length=40,
        choices=MeasurementFamily.choices,
        default=MeasurementFamily.DEMONSTRATED_PERFORMANCE,
    )
    interpretation_guidance = models.TextField(blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.ACTIVE)

    objects = TenantScopedManager()

    class Meta:
        db_table = "assessment_dimensions"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "code"], name="uq_dimension_inst_code"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_dimension_id_inst"),
        ]

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.strip().upper()
        if self.category_id and self.institution_id and self.category.institution_id != self.institution_id:
            raise ValidationError({"category": "Category must belong to the same institution."})

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class SkillTag(TimeStampedModel):
    """Reusable skill tag within an institution."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="skill_tags",
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, default="")

    objects = TenantScopedManager()

    class Meta:
        db_table = "skill_tags"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "name"], name="uq_skill_tag_inst_name"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_skill_tag_id_inst"),
        ]

    def __str__(self) -> str:
        return self.name


class DimensionSkillTag(models.Model):
    """Many-to-many link between AssessmentDimension and SkillTag."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dimension = models.ForeignKey(AssessmentDimension, on_delete=models.CASCADE, related_name="dimension_tags")
    skill_tag = models.ForeignKey(SkillTag, on_delete=models.CASCADE, related_name="dimension_tags")

    class Meta:
        db_table = "dimension_skill_tags"
        constraints = [
            models.UniqueConstraint(fields=["dimension", "skill_tag"], name="uq_dimension_skill_tag"),
        ]


class Question(TimeStampedModel):
    """Reusable institution-scoped question bank item."""

    class QuestionType(models.TextChoices):
        SINGLE_MCQ = "single_mcq", "Single Choice MCQ"
        MULTIPLE_MCQ = "multiple_mcq", "Multiple Choice MCQ"
        TRUE_FALSE = "true_false", "True / False"
        NUMERIC = "numeric", "Numeric Response"
        LIKERT = "likert", "Likert Scale"
        SELF_RATING = "self_rating", "Self-Rating"
        SITUATIONAL_JUDGEMENT = "situational_judgement", "Situational Judgement"
        DESCRIPTIVE = "descriptive", "Descriptive"
        CODING = "coding", "Coding Task"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class ScoringMethod(models.TextChoices):
        EXACT = "exact", "Exact Match"
        PARTIAL_CREDIT = "partial_credit", "Partial Credit"
        TOLERANCE = "tolerance", "Numeric Tolerance"
        LIKERT_SCALE = "likert_scale", "Likert / Scale Mapping"
        RUBRIC = "rubric", "Evaluator Rubric"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="questions",
    )
    question_code = models.CharField(max_length=60)
    question_type = models.CharField(max_length=40, choices=QuestionType.choices)
    prompt = models.TextField()
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    measurement_family = models.CharField(
        max_length=40,
        choices=MeasurementFamily.choices,
        default=MeasurementFamily.DEMONSTRATED_PERFORMANCE,
    )
    scoring_method = models.CharField(
        max_length=30,
        choices=ScoringMethod.choices,
        default=ScoringMethod.EXACT,
    )
    max_marks = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("1.00"))
    negative_marks = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    scoring_config = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_questions",
    )

    objects = TenantScopedManager()

    class Meta:
        db_table = "questions"
        ordering = ["-created_at", "question_code"]
        constraints = [
            models.CheckConstraint(condition=Q(max_marks__gte=0), name="chk_question_max_marks_nonneg"),
            models.CheckConstraint(condition=Q(negative_marks__gte=0), name="chk_question_neg_marks_nonneg"),
            models.UniqueConstraint(fields=["institution", "question_code"], name="uq_question_inst_code"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_question_id_inst"),
        ]
        indexes = [
            models.Index(fields=["institution", "question_type", "status"], name="idx_questions_inst_type_status"),
        ]

    def clean(self):
        super().clean()
        if self.question_code:
            self.question_code = self.question_code.strip().upper()
        if self.max_marks is not None and self.max_marks < 0:
            raise ValidationError({"max_marks": "Max marks must be non-negative."})
        if self.negative_marks is not None and self.negative_marks < 0:
            raise ValidationError({"negative_marks": "Negative marks must be non-negative."})

    def save(self, *args, **kwargs):
        if self.question_code:
            self.question_code = self.question_code.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)


class QuestionDimension(models.Model):
    """Links a Question to one or more AssessmentDimensions with relative weights."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="question_dimensions")
    dimension = models.ForeignKey(AssessmentDimension, on_delete=models.PROTECT, related_name="question_links")
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.00"))

    class Meta:
        db_table = "question_dimensions"
        constraints = [
            models.UniqueConstraint(fields=["question", "dimension"], name="uq_question_dimension"),
            models.CheckConstraint(condition=Q(weight__gt=0), name="chk_qdim_weight_pos"),
        ]


class QuestionOption(UUIDModel):
    """Answer option for MCQ, True/False, Likert, Self-Rating, or Situational Judgement items."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    option_key = models.CharField(max_length=20)
    option_text = models.TextField()
    display_order = models.PositiveSmallIntegerField(default=1)
    is_correct = models.BooleanField(default=False)
    points_override = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True, default="")

    class Meta:
        db_table = "question_options"
        ordering = ["display_order", "option_key"]
        constraints = [
            models.UniqueConstraint(fields=["question", "option_key"], name="uq_question_option_key"),
        ]


class QuestionRubric(TimeStampedModel):
    """Rubric definition for descriptive, coding, or judgement items."""

    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name="rubric")
    rubric_json = models.JSONField(default=dict)
    max_marks = models.DecimalField(max_digits=7, decimal_places=2)
    evaluator_guidance = models.TextField(blank=True, default="")

    class Meta:
        db_table = "question_rubrics"
        constraints = [
            models.CheckConstraint(condition=Q(max_marks__gte=0), name="chk_rubric_max_marks_nonneg"),
        ]


class AssessmentTemplate(TimeStampedModel):
    """Reusable assessment blueprint containing versioned snapshots."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="assessment_templates",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_assessment_templates",
    )

    objects = TenantScopedManager()

    class Meta:
        db_table = "assessment_templates"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "name"], name="uq_template_inst_name"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_template_id_inst"),
        ]

    def __str__(self) -> str:
        return self.name


class AssessmentVersion(TimeStampedModel):
    """Draft or immutable published version of an AssessmentTemplate."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="assessment_versions",
    )
    template = models.ForeignKey(
        AssessmentTemplate,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_no = models.PositiveIntegerField(default=1)
    duration_minutes = models.PositiveIntegerField(default=60)
    max_attempts = models.PositiveSmallIntegerField(default=1)
    instructions = models.TextField(blank=True, default="")
    scoring_config = models.JSONField(default=dict, blank=True)
    randomize_questions = models.BooleanField(default=False)
    randomize_options = models.BooleanField(default=False)
    total_marks = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "assessment_versions"
        ordering = ["-version_no"]
        constraints = [
            models.UniqueConstraint(fields=["template", "version_no"], name="uq_assessment_version_no"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_assessment_version_id_inst"),
            models.CheckConstraint(condition=Q(duration_minutes__gte=1), name="chk_version_duration_pos"),
            models.CheckConstraint(condition=Q(max_attempts__gte=1), name="chk_version_attempts_pos"),
        ]

    def clean(self):
        super().clean()
        if self.template_id and self.institution_id and self.template.institution_id != self.institution_id:
            raise ValidationError({"template": "Template must belong to the same institution."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class VersionQuestion(UUIDModel):
    """Question included in an AssessmentVersion with an immutable snapshot once published."""

    assessment_version = models.ForeignKey(
        AssessmentVersion,
        on_delete=models.CASCADE,
        related_name="version_questions",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="version_usages",
    )
    question_snapshot = models.JSONField(default=dict, blank=True)
    marks = models.DecimalField(max_digits=7, decimal_places=2)
    negative_marks = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    sequence = models.PositiveIntegerField()
    required = models.BooleanField(default=True)

    class Meta:
        db_table = "version_questions"
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(fields=["assessment_version", "sequence"], name="uq_version_question_seq"),
            models.UniqueConstraint(fields=["assessment_version", "question"], name="uq_version_question_unique"),
            models.CheckConstraint(condition=Q(marks__gte=0), name="chk_vq_marks_nonneg"),
            models.CheckConstraint(condition=Q(negative_marks__gte=0), name="chk_vq_neg_marks_nonneg"),
        ]


class AssessmentAssignment(TimeStampedModel):
    """Scheduled assignment of a published AssessmentVersion to either a Cohort or a Student."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="assessment_assignments",
    )
    assessment_version = models.ForeignKey(
        AssessmentVersion,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    cohort = models.ForeignKey(
        "academics.Cohort",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assessment_assignments",
    )
    student_profile = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assessment_assignments",
    )
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    results_released = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_assessment_assignments",
    )

    objects = TenantScopedManager()

    class Meta:
        db_table = "assessment_assignments"
        ordering = ["-opens_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(cohort__isnull=False, student_profile__isnull=True)
                    | Q(cohort__isnull=True, student_profile__isnull=False)
                ),
                name="chk_assignment_single_target",
            ),
            models.CheckConstraint(condition=Q(closes_at__gte=F("opens_at")), name="chk_assignment_window"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_assignment_id_inst"),
        ]
        indexes = [
            models.Index(fields=["institution", "status", "opens_at"], name="idx_assign_inst_status"),
        ]

    def clean(self):
        super().clean()
        if bool(self.cohort_id) == bool(self.student_profile_id):
            raise ValidationError("Assignment must target either a cohort or an individual student, not both or neither.")
        if self.opens_at and self.closes_at and self.closes_at < self.opens_at:
            raise ValidationError({"closes_at": "Closing time must be on or after opening time."})
        if self.assessment_version_id and self.institution_id:
            if self.assessment_version.institution_id != self.institution_id:
                raise ValidationError({"assessment_version": "Assessment version must belong to the same institution."})
            if self.assessment_version.status != AssessmentVersion.Status.PUBLISHED:
                raise ValidationError({"assessment_version": "Only published assessment versions can be assigned."})
        if self.cohort_id and self.institution_id and self.cohort.institution_id != self.institution_id:
            raise ValidationError({"cohort": "Cohort must belong to the same institution."})
        if self.student_profile_id and self.institution_id and self.student_profile.institution_id != self.institution_id:
            raise ValidationError({"student_profile": "Student must belong to the same institution."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

