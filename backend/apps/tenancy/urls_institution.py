"""Institution Admin API URL routes."""
from django.urls import path
from apps.tenancy.views import (
    InstitutionProfileView,
    InstitutionUserDetailView,
    InstitutionUserListCreateView,
    InstitutionUserResetLinkView,
    InstitutionUserRolesView,
)

urlpatterns = [
    path("profile/", InstitutionProfileView.as_view(), name="institution-profile"),
    path("users/", InstitutionUserListCreateView.as_view(), name="institution-users"),
    path("users/<uuid:membership_id>/", InstitutionUserDetailView.as_view(), name="institution-user-detail"),
    path("users/<uuid:membership_id>/roles/", InstitutionUserRolesView.as_view(), name="institution-user-roles"),
    path("users/<uuid:membership_id>/reset-link/", InstitutionUserResetLinkView.as_view(), name="institution-user-reset-link"),
]

