"""Core API routes."""
from django.urls import path
from apps.core.dashboard_views import DashboardSummaryView
from apps.core.views import HealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
]

