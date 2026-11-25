"""Staged Excel/CSV import job and row-level error models."""
from django.conf import settings
from django.db import models
from apps.core.models import TenantScopedManager, TimeStampedModel, UUIDModel


class ImportJob(TimeStampedModel):
    """Tracks staged bulk import upload, validation preview, and transactional commit."""

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        VALIDATED = "validated", "Validated"
        COMMITTED = "committed", "Committed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    institution = models.ForeignKey(
        "tenancy.Institution",
        on_delete=models.PROTECT,
        related_name="import_jobs",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="import_jobs",
    )
    file_name = models.CharField(max_length=255)
    stored_file_path = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    total_rows = models.PositiveIntegerField(default=0)
    success_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    summary_json = models.JSONField(default=dict, blank=True)

    objects = TenantScopedManager()

    class Meta:
        db_table = "import_jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["institution", "-created_at"], name="idx_import_jobs_tenant_created"),
        ]

    def __str__(self) -> str:
        return f"{self.file_name} ({self.status})"


class ImportRowError(UUIDModel):
    """Row-level validation or duplicate detection feedback for an ImportJob."""

    import_job = models.ForeignKey(
        ImportJob,
        on_delete=models.CASCADE,
        related_name="row_errors",
    )
    row_number = models.PositiveIntegerField()
    field_name = models.CharField(max_length=100, blank=True, default="")
    error_code = models.CharField(max_length=80)
    message = models.TextField()
    row_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_row_errors"
        ordering = ["row_number", "id"]
        indexes = [
            models.Index(fields=["import_job", "row_number"], name="idx_import_errors_job_row"),
        ]

