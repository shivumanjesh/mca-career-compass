"""Multi-institution tenant root, memberships, and institution-scoped roles."""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.accounts.models import Role, RoleScope
from apps.core.models import TimeStampedModel


class Institution(TimeStampedModel):
    """Tenant root representing a participating educational institution."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "institutions"
        ordering = ["name"]

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


class Membership(TimeStampedModel):
    """Explicit link between a global User and an Institution."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        PENDING = "pending", "Pending"

    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "memberships"
        constraints = [
            models.UniqueConstraint(fields=["institution", "user"], name="uq_membership_institution_user"),
            models.UniqueConstraint(fields=["id", "institution"], name="uq_membership_id_institution"),
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_memberships_user_status"),
            models.Index(fields=["institution", "status"], name="idx_memberships_inst_status"),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.institution.code} ({self.status})"


class MembershipRole(models.Model):
    """Institution-scoped role assigned to a specific Membership."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="membership_roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="membership_assignments")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_membership_roles",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "membership_roles"
        constraints = [
            models.UniqueConstraint(fields=["membership", "role"], name="uq_membership_role"),
        ]

    def clean(self):
        if self.role_id and self.role.scope != RoleScope.INSTITUTION:
            raise ValidationError("Only institution-scoped roles can be assigned in MembershipRole.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.membership} -> {self.role.code}"

