"""Tenant scoping helpers for views and services."""
from rest_framework.exceptions import PermissionDenied


def require_active_institution(request):
    """Return server-derived active Institution or deny by default."""
    inst = getattr(request, "active_institution", None)
    if inst is None:
        raise PermissionDenied("Active institution context is required for this endpoint.")
    return inst


def require_active_membership(request):
    """Return server-derived active Membership or deny by default."""
    membership = getattr(request, "active_membership", None)
    if membership is None:
        raise PermissionDenied("Active institution membership is required for this endpoint.")
    return membership

