"""Platform Super Admin API URL routes."""
from django.urls import path
from apps.tenancy.views import (
    PlatformInstitutionAdminsView,
    PlatformInstitutionDetailView,
    PlatformInstitutionListCreateView,
)

urlpatterns = [
    path("institutions/", PlatformInstitutionListCreateView.as_view(), name="platform-institutions"),
    path("institutions/<uuid:institution_id>/", PlatformInstitutionDetailView.as_view(), name="platform-institution-detail"),
    path("institutions/<uuid:institution_id>/admins/", PlatformInstitutionAdminsView.as_view(), name="platform-institution-admins"),
]

