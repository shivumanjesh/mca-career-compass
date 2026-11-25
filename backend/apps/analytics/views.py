"""Phase 4 REST API views for cohort analytics, student reports, and exports."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasAnyPermission, HasInstitutionPermission
from apps.analytics.exports import (
    export_cohort_csv,
    export_cohort_pdf,
    export_cohort_xlsx,
    export_executive_csv,
    export_executive_pdf,
    export_executive_xlsx,
    export_student_csv,
    export_student_pdf,
    export_student_xlsx,
)
from apps.analytics.intelligence import (
    build_executive_report,
    build_faculty_intelligence,
    build_pre_post_comparison,
)
from apps.analytics.services import (
    build_cohort_analytics,
    build_student_report,
    get_authorized_cohorts_queryset,
    get_authorized_students_queryset,
)
from apps.assessments.models import AssessmentTemplate
from apps.attempts.services import get_student_profile_for_membership
from apps.audit.services import log_audit_event
from apps.tenancy.mixins import require_active_institution, require_active_membership


class AnalyticsCohortListView(APIView):
    """List cohorts the caller is authorized to analyze."""

    permission_classes = [HasAnyPermission("analytics.cohort.view", "results.cohort.view")]

    def get(self, request):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())
        cohorts = get_authorized_cohorts_queryset(inst, membership, perms).order_by(
            "-academic_year__start_date", "batch_name", "semester", "section"
        )
        return Response([{"id": str(c.id), "label": str(c)} for c in cohorts])


class CohortAnalyticsDetailView(APIView):
    """Return cohort analytics, domain breakdown, and student comparison."""

    permission_classes = [HasAnyPermission("analytics.cohort.view", "results.cohort.view")]

    def get(self, request, cohort_id):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())
        cohort = get_object_or_404(get_authorized_cohorts_queryset(inst, membership, perms), id=cohort_id)
        template_id = request.query_params.get("template_id", "").strip() or None
        return Response(build_cohort_analytics(inst, cohort, template_id=template_id))


class StudentIndividualReportView(APIView):
    """Return individual student domain report for authorized Faculty/HOD or Admin."""

    permission_classes = [HasInstitutionPermission("results.cohort.view")]

    def get(self, request, student_id):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())
        student = get_object_or_404(get_authorized_students_queryset(inst, membership, perms), id=student_id)
        return Response(build_student_report(student, released_only=False))


class StudentMyReportView(APIView):
    """Return authenticated student's own released individual domain report."""

    permission_classes = [HasInstitutionPermission("results.self.view")]

    def get(self, request):
        membership = require_active_membership(request)
        student = get_student_profile_for_membership(membership)
        return Response(build_student_report(student, released_only=True))


class ReportExportView(APIView):
    """Export authorized cohort or individual student report to CSV, XLSX, or PDF."""

    permission_classes = [HasInstitutionPermission("reports.export")]

    def get(self, request):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())

        fmt = request.query_params.get("export_format", "csv").strip().lower()
        if fmt not in {"csv", "xlsx", "pdf"}:
            raise ValidationError({"export_format": "Format must be one of: csv, xlsx, pdf."})

        cohort_id = request.query_params.get("cohort_id", "").strip()
        student_id = request.query_params.get("student_id", "").strip()
        if bool(cohort_id) == bool(student_id):
            raise ValidationError({"target": "Specify either cohort_id or student_id."})

        if cohort_id:
            cohort = get_object_or_404(get_authorized_cohorts_queryset(inst, membership, perms), id=cohort_id)
            template_id = request.query_params.get("template_id", "").strip() or None
            data = build_cohort_analytics(inst, cohort, template_id=template_id)
            filename_base = f"cohort_{cohort.programme.code}_sem{cohort.semester}_{cohort.section}"
            log_audit_event(
                action="REPORT_EXPORTED",
                entity_type="Cohort",
                entity_id=cohort.id,
                institution=inst,
                actor_user=request.user,
                after={"format": fmt, "cohort": str(cohort)},
                request=request,
            )
            if fmt == "csv":
                resp = HttpResponse(export_cohort_csv(data), content_type="text/csv; charset=utf-8")
                resp["Content-Disposition"] = f'attachment; filename="{filename_base}.csv"'
                return resp
            if fmt == "xlsx":
                resp = HttpResponse(
                    export_cohort_xlsx(data),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                resp["Content-Disposition"] = f'attachment; filename="{filename_base}.xlsx"'
                return resp
            resp = HttpResponse(export_cohort_pdf(data), content_type="application/pdf")
            resp["Content-Disposition"] = f'attachment; filename="{filename_base}.pdf"'
            return resp

        student = get_object_or_404(get_authorized_students_queryset(inst, membership, perms), id=student_id)
        data = build_student_report(student, released_only=False)
        filename_base = f"student_{student.registration_no}_report"
        log_audit_event(
            action="REPORT_EXPORTED",
            entity_type="StudentProfile",
            entity_id=student.id,
            institution=inst,
            actor_user=request.user,
            after={"format": fmt, "registration_no": student.registration_no},
            request=request,
        )
        if fmt == "csv":
            resp = HttpResponse(export_student_csv(data), content_type="text/csv; charset=utf-8")
            resp["Content-Disposition"] = f'attachment; filename="{filename_base}.csv"'
            return resp
        if fmt == "xlsx":
            resp = HttpResponse(
                export_student_xlsx(data),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            resp["Content-Disposition"] = f'attachment; filename="{filename_base}.xlsx"'
            return resp
        resp = HttpResponse(export_student_pdf(data), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename_base}.pdf"'
        return resp


class AnalyticsTemplateListView(APIView):
    """List assessment templates in active institution for pre/post comparison selectors."""

    permission_classes = [HasAnyPermission("intelligence.faculty.view", "analytics.cohort.view", "analytics.executive.view")]

    def get(self, request):
        inst = require_active_institution(request)
        templates = AssessmentTemplate.objects.for_institution(inst).order_by("name")
        return Response([{"id": str(t.id), "name": t.name} for t in templates])


class FacultyIntelligenceView(APIView):
    """Cohort-scoped Faculty / HOD intelligence, placement readiness & mentoring dashboard."""

    permission_classes = [HasInstitutionPermission("intelligence.faculty.view")]

    def get(self, request):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())
        cohort_id = request.query_params.get("cohort_id", "").strip() or None
        if cohort_id:
            get_object_or_404(get_authorized_cohorts_queryset(inst, membership, perms), id=cohort_id)
        return Response(build_faculty_intelligence(inst, membership, perms, cohort_id=cohort_id))


class PrePostComparisonView(APIView):
    """Compare baseline (Pre) vs follow-up (Post) assessment outcomes within authorized scope."""

    permission_classes = [HasAnyPermission("intelligence.faculty.view", "analytics.executive.view")]

    def get(self, request):
        inst = require_active_institution(request)
        membership = require_active_membership(request)
        perms = getattr(request, "institution_permissions", set())
        cohort_id = request.query_params.get("cohort_id", "").strip() or None
        if cohort_id:
            get_object_or_404(get_authorized_cohorts_queryset(inst, membership, perms), id=cohort_id)
        pre_template_id = request.query_params.get("pre_template_id", "").strip() or None
        post_template_id = request.query_params.get("post_template_id", "").strip() or None
        return Response(
            build_pre_post_comparison(
                inst,
                membership,
                perms,
                pre_template_id=pre_template_id,
                post_template_id=post_template_id,
                cohort_id=cohort_id,
            )
        )


class ExecutiveReportView(APIView):
    """Institution-wide executive dashboard across all programmes and cohorts."""

    permission_classes = [HasInstitutionPermission("analytics.executive.view")]

    def get(self, request):
        inst = require_active_institution(request)
        return Response(build_executive_report(inst))


class ExecutiveReportExportView(APIView):
    """Export institution executive report to CSV, XLSX, or PDF."""

    permission_classes = [HasInstitutionPermission("analytics.executive.view")]

    def get(self, request):
        inst = require_active_institution(request)
        perms = getattr(request, "institution_permissions", set())
        if "reports.export" not in perms:
            self.permission_denied(request, message="Export permission is required.")

        fmt = request.query_params.get("export_format", "csv").strip().lower()
        if fmt not in {"csv", "xlsx", "pdf"}:
            raise ValidationError({"export_format": "Format must be one of: csv, xlsx, pdf."})

        data = build_executive_report(inst)
        filename_base = f"executive_report_{inst.code.lower()}"
        log_audit_event(
            action="EXECUTIVE_REPORT_EXPORTED",
            entity_type="Institution",
            entity_id=inst.id,
            institution=inst,
            actor_user=request.user,
            after={"format": fmt, "institution_code": inst.code},
            request=request,
        )
        if fmt == "csv":
            resp = HttpResponse(export_executive_csv(data), content_type="text/csv; charset=utf-8")
            resp["Content-Disposition"] = f'attachment; filename="{filename_base}.csv"'
            return resp
        if fmt == "xlsx":
            resp = HttpResponse(
                export_executive_xlsx(data),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            resp["Content-Disposition"] = f'attachment; filename="{filename_base}.xlsx"'
            return resp
        resp = HttpResponse(export_executive_pdf(data), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename_base}.pdf"'
        return resp

