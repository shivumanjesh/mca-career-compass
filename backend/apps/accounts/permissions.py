"""Granular DRF permission classes enforcing backend RBAC and tenant context."""
from rest_framework.permissions import BasePermission


def _is_active_user(request) -> bool:
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_active)


class HasPlatformPermission(BasePermission):
    """Require an explicit platform-scoped permission code."""

    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def __call__(self):
        return self

    def has_permission(self, request, view) -> bool:
        if not _is_active_user(request):
            return False
        perms = getattr(request, "platform_permissions", set())
        return self.permission_code in perms


class HasInstitutionPermission(BasePermission):
    """Require active institution membership AND an institution-scoped permission code."""

    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def __call__(self):
        return self

    def has_permission(self, request, view) -> bool:
        if not _is_active_user(request):
            return False
        if getattr(request, "active_institution", None) is None:
            return False
        if getattr(request, "active_membership", None) is None:
            return False
        perms = getattr(request, "institution_permissions", set())
        return self.permission_code in perms


class HasAnyPermission(BasePermission):
    """Require any one of the specified permission codes (checks tenant context for institution perms)."""

    def __init__(self, *permission_codes: str):
        self.permission_codes = set(permission_codes)

    def __call__(self):
        return self

    def has_permission(self, request, view) -> bool:
        if not _is_active_user(request):
            return False
        platform_perms = getattr(request, "platform_permissions", set())
        if self.permission_codes & platform_perms:
            return True
        if getattr(request, "active_institution", None) is None:
            return False
        inst_perms = getattr(request, "institution_permissions", set())
        return bool(self.permission_codes & inst_perms)

