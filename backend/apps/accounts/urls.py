"""Authentication and RBAC URL routes."""
from django.urls import path
from apps.accounts.views import (
    ChangePasswordView,
    CsrfTokenView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SwitchInstitutionView,
)

urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("switch-institution/", SwitchInstitutionView.as_view(), name="auth-switch-institution"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="auth-password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
]

