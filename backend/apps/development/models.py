"""Phase 5 models: LearningResource, DevelopmentPlan, DevelopmentActivity, ProgressRecord."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from apps.core.models import TenantScopedManager, TimeStampedModel, UUIDModel


class ResourceType(models.TextChoices):
    LEARNING_PATHWAY = "learning_pathway", "Learning Pathway"
    TRAINING = "training", "Training / Workshop"
    PROJECT = "project", "Hands-on Project"
    CERTIFICATION = "certification", "Certification"
    MILESTONE = "milestone", "Custom Milestone"


class LearningResource(TimeStampedModel):
    """Institution-configurable catalogue of pathways, training, projects, and certifications."""

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="learning_resources",
    )
    dimension_code = models.CharField(max_length=60, blank=True, default="")
    target_domain = models.CharField(max_length=120)
    resource_type = models.CharField(max_length=30, choices=ResourceType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=120, blank=True, default="")
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INTERMEDIATE)
    estimated_hours = models.PositiveIntegerField(default=10)
    resource_url = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    objects = TenantScopedManager()

    class Meta:
        db_table = "learning_resources"
        ordering = ["target_domain", "resource_type", "title"]
        constraints = [
            models.UniqueConstraint(fields=["id", "institution"], name="uq_learning_resource_id_inst"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.resource_type})"


class DevelopmentPlan(TimeStampedModel):
    """Personalized student development roadmap."""

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="development_plans",
    )
    student_profile = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.PROTECT,
        related_name="development_plans",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_development_plans",
    )
    title = models.CharField(max_length=200)
    target_domain = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "development_plans"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["id", "institution"], name="uq_dev_plan_id_inst"),
            models.CheckConstraint(
                condition=Q(target_date__isnull=True) | Q(start_date__isnull=True) | Q(target_date__gte=F("start_date")),
                name="chk_dev_plan_dates",
            ),
        ]

    def clean(self):
        super().clean()
        if self.student_profile_id and self.institution_id and self.student_profile.institution_id != self.institution_id:
            raise ValidationError({"student_profile": "Student must belong to the same institution."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DevelopmentActivity(TimeStampedModel):
    """Actionable training, project, certification, or pathway milestone in a plan."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="development_activities",
    )
    plan = models.ForeignKey(
        DevelopmentPlan,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    dimension = models.ForeignKey(
        "assessments.AssessmentDimension",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="development_activities",
    )
    resource = models.ForeignKey(
        LearningResource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="adopted_activities",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    activity_type = models.CharField(max_length=30, choices=ResourceType.choices, default=ResourceType.LEARNING_PATHWAY)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    evidence_url = models.CharField(max_length=500, blank=True, default="")

    objects = TenantScopedManager()

    class Meta:
        db_table = "development_activities"
        ordering = ["status", "due_date", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["id", "institution"], name="uq_dev_activity_id_inst"),
            models.CheckConstraint(condition=Q(progress_percent__lte=100), name="chk_dev_act_progress"),
        ]


class ProgressRecord(UUIDModel):
    """Progress update and reflection entry on a DevelopmentActivity."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="progress_records",
    )
    activity = models.ForeignKey(
        DevelopmentActivity,
        on_delete=models.CASCADE,
        related_name="progress_records",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_progress_updates",
    )
    progress_percent = models.PositiveSmallIntegerField()
    reflection = models.TextField(blank=True, default="")
    evidence_url = models.CharField(max_length=500, blank=True, default="")
    recorded_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "progress_records"
        ordering = ["-recorded_at"]
        constraints = [
            models.CheckConstraint(condition=Q(progress_percent__lte=100), name="chk_progress_pct_range"),
        ]

