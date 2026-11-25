"""Student profile model with membership-bound composite tenant integrity."""
from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import TenantScopedManager, TimeStampedModel


class StudentProfile(TimeStampedModel):
    """Institution-scoped student academic profile linked 1:1 to Membership."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="student_profiles",
    )
    membership = models.OneToOneField(
        "tenancy.Membership",
        on_delete=models.PROTECT,
        related_name="student_profile",
    )
    cohort = models.ForeignKey(
        "academics.Cohort",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students",
    )
    registration_no = models.CharField(max_length=80)
    admission_year = models.PositiveSmallIntegerField(null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    objects = TenantScopedManager()

    class Meta:
        db_table = "student_profiles"
        ordering = ["registration_no"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "registration_no"], name="uq_student_inst_regno"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_student_id_inst"),
        ]
        indexes = [
            models.Index(fields=["institution", "cohort"], name="idx_students_inst_cohort"),
            models.Index(fields=["institution", "registration_no"], name="idx_students_regno"),
        ]

    def clean(self):
        super().clean()
        if self.registration_no:
            self.registration_no = self.registration_no.strip().upper()
        if self.membership_id and self.institution_id and self.membership.institution_id != self.institution_id:
            raise ValidationError({"membership": "Membership must belong to the same institution."})
        if self.cohort_id and self.institution_id and self.cohort.institution_id != self.institution_id:
            raise ValidationError({"cohort": "Cohort must belong to the same institution."})

    def save(self, *args, **kwargs):
        if self.registration_no:
            self.registration_no = self.registration_no.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.registration_no} ({self.membership.user.full_name})"

