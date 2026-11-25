"""Append-only audit event model."""
from django.conf import settings
from django.db import models
from apps.core.models import UUIDModel


class AuditEvent(UUIDModel):
    """Immutable administrative and security audit trail."""

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField(null=True, blank=True)
    before_json = models.JSONField(null=True, blank=True)
    after_json = models.JSONField(null=True, blank=True)
    ip_hash = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["institution", "-created_at"], name="idx_audit_tenant_created"),
            models.Index(fields=["action", "-created_at"], name="idx_audit_action_created"),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.action} {self.entity_type}"

