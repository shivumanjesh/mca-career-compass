"""Academic structure models: Programme, AcademicYear, Cohort."""
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from apps.core.models import TenantScopedManager, TimeStampedModel


class ActiveStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class Programme(TimeStampedModel):
    """Academic programme within an institution (e.g., MCA)."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="programmes",
    )
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    level = models.CharField(max_length=40, default="PG")
    status = models.CharField(max_length=20, choices=ActiveStatus.choices, default=ActiveStatus.ACTIVE)

    objects = TenantScopedManager()

    class Meta:
        db_table = "programmes"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "code"], name="uq_programme_inst_code"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_programme_id_inst"),
        ]

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.strip().upper()

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class AcademicYear(TimeStampedModel):
    """Academic year period within an institution."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="academic_years",
    )
    name = models.CharField(max_length=40)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=ActiveStatus.choices, default=ActiveStatus.ACTIVE)

    objects = TenantScopedManager()

    class Meta:
        db_table = "academic_years"
        ordering = ["-start_date", "name"]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")), name="chk_ay_end_after_start"),
            models.UniqueConstraint(fields=["institution", "name"], name="uq_ay_inst_name"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_ay_id_inst"),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})

    def __str__(self) -> str:
        return self.name


class Cohort(TimeStampedModel):
    """Batch / semester / section grouping of students within an institution."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="cohorts",
    )
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="cohorts")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="cohorts")
    batch_name = models.CharField(max_length=100)
    semester = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=30, default="A")
    status = models.CharField(max_length=20, choices=ActiveStatus.choices, default=ActiveStatus.ACTIVE)

    objects = TenantScopedManager()

    class Meta:
        db_table = "cohorts"
        ordering = ["-academic_year__start_date", "batch_name", "semester", "section"]
        constraints = [
            models.CheckConstraint(
                condition=Q(semester__gte=1, semester__lte=8),
                name="chk_cohort_semester_range",
            ),
            models.UniqueConstraint(
                fields=["institution", "programme", "academic_year", "batch_name", "semester", "section"],
                name="uq_cohort_unique_slice",
            ),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_cohort_id_inst"),
        ]
        indexes = [
            models.Index(fields=["institution", "programme"], name="idx_cohorts_inst_programme"),
        ]

    def clean(self):
        super().clean()
        if self.programme_id and self.institution_id and self.programme.institution_id != self.institution_id:
            raise ValidationError({"programme": "Programme must belong to the same institution."})
        if self.academic_year_id and self.institution_id and self.academic_year.institution_id != self.institution_id:
            raise ValidationError({"academic_year": "Academic year must belong to the same institution."})
        if self.section:
            self.section = self.section.strip().upper()

    def save(self, *args, **kwargs):
        if self.section:
            self.section = self.section.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.programme.code} {self.batch_name} Sem-{self.semester} ({self.section})"

