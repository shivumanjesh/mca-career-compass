"""Authentication API views."""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SwitchInstitutionSerializer,
)
from apps.accounts.services import (
    authenticate_portal_login,
    change_user_password,
    confirm_password_reset,
    logout_current_user,
    request_password_reset,
    serialize_auth_me,
    switch_active_institution,
)


class CsrfTokenView(APIView):
    """Issue a CSRF cookie for the SPA prior to login/mutations."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"status": "csrf_cookie_set"})


class LoginView(APIView):
    """Authenticate user for /admin/login or /login portal."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get_authenticate_header(self, request) -> str:
        return "Session"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        authenticate_portal_login(
            request=request,
            portal=data["portal"],
            identifier=data["identifier"],
            password=data["password"],
            institution_code=data.get("institution_code") or None,
        )
        return Response(serialize_auth_me(request), status=status.HTTP_200_OK)


class LogoutView(APIView):
    """End current authenticated session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout_current_user(request=request)
        return Response({"detail": "Signed out successfully."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """Return authenticated user, active institution context, roles, and permissions."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_active:
            return Response(
                {"code": "inactive_user", "message": "Account is inactive.", "details": None},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(serialize_auth_me(request), status=status.HTTP_200_OK)


class SwitchInstitutionView(APIView):
    """Switch active institution in session after verifying active Membership."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SwitchInstitutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        switch_active_institution(
            request=request,
            institution_id=str(serializer.validated_data["institution_id"]),
        )
        return Response(serialize_auth_me(request), status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """Change password for authenticated user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_user_password(
            request=request,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
        )
        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    """Request a password reset email/link."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(email=serializer.validated_data["email"], request=request)
        return Response(
            {"detail": "If an active account matches that email, password reset instructions have been issued."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset using uid and token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        confirm_password_reset(
            uid=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
            request=request,
        )
        return Response({"detail": "Password has been reset. You may now sign in."}, status=status.HTTP_200_OK)

