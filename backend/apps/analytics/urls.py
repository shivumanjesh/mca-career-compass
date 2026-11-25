"""Phase 4 analytics & report export URL routes."""
from django.urls import path
from apps.analytics.views import (
    AnalyticsCohortListView,
    AnalyticsTemplateListView,
    CohortAnalyticsDetailView,
    ExecutiveReportExportView,
    ExecutiveReportView,
    FacultyIntelligenceView,
    PrePostComparisonView,
    ReportExportView,
    StudentIndividualReportView,
    StudentMyReportView,
)

urlpatterns = [
    path("cohorts/", AnalyticsCohortListView.as_view(), name="analytics-cohorts"),
    path("cohorts/<uuid:cohort_id>/", CohortAnalyticsDetailView.as_view(), name="analytics-cohort-detail"),
    path("templates/", AnalyticsTemplateListView.as_view(), name="analytics-templates"),
    path("intelligence/", FacultyIntelligenceView.as_view(), name="analytics-intelligence"),
    path("pre-post/", PrePostComparisonView.as_view(), name="analytics-pre-post"),
    path("executive/", ExecutiveReportView.as_view(), name="analytics-executive"),
    path("executive/export/", ExecutiveReportExportView.as_view(), name="analytics-executive-export"),
    path("students/<uuid:student_id>/", StudentIndividualReportView.as_view(), name="analytics-student-report"),
    path("my-reports/", StudentMyReportView.as_view(), name="analytics-my-reports"),
    path("exports/", ReportExportView.as_view(), name="analytics-exports"),
]

