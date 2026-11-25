"""Faculty profile and cohort assignment models."""
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from apps.core.models import TenantScopedManager, TimeStampedModel


class FacultyProfile(TimeStampedModel):
    """Institution-scoped faculty profile linked 1:1 to Membership."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="faculty_profiles",
    )
    membership = models.OneToOneField(
        "tenancy.Membership",
        on_delete=models.PROTECT,
        related_name="faculty_profile",
    )
    employee_code = models.CharField(max_length=80, null=True, blank=True)
    department = models.CharField(max_length=120, blank=True, default="")
    designation = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    objects = TenantScopedManager()

    class Meta:
        db_table = "faculty_profiles"
        ordering = ["membership__user__first_name", "employee_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "employee_code"],
                condition=Q(employee_code__isnull=False),
                name="uq_faculty_inst_empcode",
            ),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_faculty_id_inst"),
        ]
        indexes = [
            models.Index(fields=["institution", "department"], name="idx_faculty_inst_dept"),
        ]

    def clean(self):
        super().clean()
        if self.employee_code is not None:
            cleaned = self.employee_code.strip().upper()
            self.employee_code = cleaned or None
        if self.membership_id and self.institution_id and self.membership.institution_id != self.institution_id:
            raise ValidationError({"membership": "Membership must belong to the same institution."})

    def save(self, *args, **kwargs):
        if self.employee_code is not None:
            cleaned = self.employee_code.strip().upper()
            self.employee_code = cleaned or None
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.membership.user.full_name} ({self.designation or 'Faculty'})"


class CohortFaculty(TimeStampedModel):
    """Explicit assignment of Faculty / HOD to a Cohort for scoped student access."""

    class AssignmentType(models.TextChoices):
        MENTOR = "mentor", "Mentor"
        HOD = "hod", "HOD"
        FACULTY = "faculty", "Faculty"
        COORDINATOR = "coordinator", "Coordinator"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="cohort_faculty_assignments",
    )
    cohort = models.ForeignKey(
        "academics.Cohort",
        on_delete=models.PROTECT,
        related_name="faculty_assignments",
    )
    faculty_profile = models.ForeignKey(
        FacultyProfile,
        on_delete=models.PROTECT,
        related_name="cohort_assignments",
    )
    assignment_type = models.CharField(
        max_length=40,
        choices=AssignmentType.choices,
        default=AssignmentType.MENTOR,
    )

    objects = TenantScopedManager()

    class Meta:
        db_table = "cohort_faculty"
        constraints = [
            models.UniqueConstraint(
                fields=["cohort", "faculty_profile", "assignment_type"],
                name="uq_cohort_faculty_type",
            ),
        ]

    def clean(self):
        super().clean()
        if self.cohort_id and self.institution_id and self.cohort.institution_id != self.institution_id:
            raise ValidationError({"cohort": "Cohort must belong to the same institution."})
        if self.faculty_profile_id and self.institution_id and self.faculty_profile.institution_id != self.institution_id:
            raise ValidationError({"faculty_profile": "Faculty profile must belong to the same institution."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

