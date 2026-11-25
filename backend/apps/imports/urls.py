"""Import API routes mounted under /api/v1/students/."""
from django.urls import path
from apps.imports.views import (
    StudentImportCommitView,
    StudentImportErrorExportView,
    StudentImportJobDetailView,
    StudentImportJobListView,
    StudentImportTemplateView,
    StudentImportUploadView,
    StudentImportValidateView,
)

urlpatterns = [
    path("import/template/", StudentImportTemplateView.as_view(), name="student-import-template"),
    path("import/upload/", StudentImportUploadView.as_view(), name="student-import-upload"),
    path("import/<uuid:job_id>/validate/", StudentImportValidateView.as_view(), name="student-import-validate"),
    path("import/<uuid:job_id>/commit/", StudentImportCommitView.as_view(), name="student-import-commit"),
    path("import-jobs/", StudentImportJobListView.as_view(), name="student-import-jobs"),
    path("import-jobs/<uuid:job_id>/", StudentImportJobDetailView.as_view(), name="student-import-job-detail"),
    path("import-jobs/<uuid:job_id>/errors/export/", StudentImportErrorExportView.as_view(), name="student-import-errors-export"),
]

