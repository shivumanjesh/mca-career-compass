"""Abstract base models and tenant-aware queryset helpers."""
import uuid
from django.db import models


class UUIDModel(models.Model):
    """Abstract base model using UUID v4 primary keys."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(UUIDModel):
    """Abstract base model with UUID PK and UTC created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedQuerySet(models.QuerySet):
    """QuerySet helper enforcing explicit institution scoping."""

    def for_institution(self, institution):
        institution_id = getattr(institution, "id", institution)
        if not institution_id:
            return self.none()
        return self.filter(institution_id=institution_id)


class TenantScopedManager(models.Manager):
    """Manager exposing tenant-scoped filtering helpers."""

    def get_queryset(self) -> TenantScopedQuerySet:
        return TenantScopedQuerySet(self.model, using=self._db)

    def for_institution(self, institution) -> TenantScopedQuerySet:
        return self.get_queryset().for_institution(institution)

