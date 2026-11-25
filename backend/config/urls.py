"""Root URL routing for MCA Career Compass."""
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/platform/", include("apps.tenancy.urls_platform")),
    path("api/v1/institution/", include("apps.tenancy.urls_institution")),
    path("api/v1/academics/", include("apps.academics.urls")),
    path("api/v1/students/", include("apps.imports.urls")),
    path("api/v1/students/", include("apps.students.urls")),
    path("api/v1/faculty/", include("apps.faculty.urls")),
    path("api/v1/assessments/", include("apps.assessments.urls")),
    path("api/v1/attempts/", include("apps.attempts.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/development/", include("apps.development.urls")),
    path("api/v1/audit-events/", include("apps.audit.urls")),
]

