"""Staged Excel/CSV student import REST API views."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasInstitutionPermission
from apps.core.pagination import StandardResultsSetPagination
from apps.imports.models import ImportJob
from apps.imports.serializers import (
    ImportCommitSerializer,
    ImportJobSerializer,
    ImportRowErrorSerializer,
    ImportValidateSerializer,
)
from apps.imports.services import (
    commit_import_job,
    create_import_upload,
    export_import_errors_csv,
    generate_student_template_workbook,
    validate_import_job,
)
from apps.tenancy.mixins import require_active_institution


class StudentImportTemplateView(APIView):
    """Download standard .xlsx student import template."""

    permission_classes = [HasInstitutionPermission("institution.student.import")]

    def get(self, request):
        content = generate_student_template_workbook()
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="mca_career_compass_student_import_template.xlsx"'
        return response


class StudentImportUploadView(APIView):
    """Upload .xlsx or .csv file and inspect headers & sample rows."""

    permission_classes = [HasInstitutionPermission("institution.student.import")]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        inst = require_active_institution(request)
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return Response(
                {"code": "missing_file", "message": "Please select an .xlsx or .csv file to upload.", "details": None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job = create_import_upload(
            institution=inst,
            user=request.user,
            uploaded_file=uploaded,
            request=request,
        )
        return Response(ImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class StudentImportValidateView(APIView):
    """Apply column mapping and validate all rows (no DB student creation)."""

    permission_classes = [HasInstitutionPermission("institution.student.import")]

    def post(self, request, job_id):
        inst = require_active_institution(request)
        job = get_object_or_404(ImportJob.objects.for_institution(inst), id=job_id)
        serializer = ImportValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = validate_import_job(
            import_job=job,
            column_mapping=data["column_mapping"],
            sheet_name=data.get("sheet_name") or None,
            default_cohort_id=data.get("default_cohort_id"),
            actor_user=request.user,
            request=request,
        )
        return Response(
            {
                "job": ImportJobSerializer(result["job"]).data,
                "preview_rows": result["preview_rows"],
            },
            status=status.HTTP_200_OK,
        )


class StudentImportCommitView(APIView):
    """Transactionally commit validated import rows."""

    permission_classes = [HasInstitutionPermission("institution.student.import")]

    def post(self, request, job_id):
        inst = require_active_institution(request)
        job = get_object_or_404(ImportJob.objects.for_institution(inst), id=job_id)
        serializer = ImportCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        committed = commit_import_job(
            import_job=job,
            mode=serializer.validated_data["mode"],
            actor_user=request.user,
            request=request,
        )
        return Response(ImportJobSerializer(committed).data, status=status.HTTP_200_OK)


class StudentImportJobListView(APIView):
    """List past import jobs for the active institution."""

    permission_classes = [HasInstitutionPermission("institution.student.import")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = ImportJob.objects.for_institution(inst).select_related("created_by").order_by("-created_at")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ImportJobSerializer(page, many=True).data)


class StudentImportJobDetailView(APIView):
    """Retrieve import job summary and row-level errors."""

    permission_classes = [HasInstitutionPermission("institution.student.import")]

    def get(self, request, job_id):
        inst = require_active_institution(request)
        job = get_object_or_404(ImportJob.objects.for_institution(inst).select_related("created_by"), id=job_id)
        errors = job.row_errors.all()[:500]
        return Response(
            {
                "job": ImportJobSerializer(job).data,
                "errors": ImportRowErrorSerializer(errors, many=True).data,
            }
        )


class StudentImportErrorExportView(APIView):
    """Download sanitized CSV error report without passwords."""

    permission_classes = [HasInstitutionPermission("institution.student.import")]

    def get(self, request, job_id):
        inst = require_active_institution(request)
        job = get_object_or_404(ImportJob.objects.for_institution(inst), id=job_id)
        csv_content = export_import_errors_csv(job)
        response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="import_errors_{job.id}.csv"'
        return response

