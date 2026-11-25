"""Server-side active institution and permission context middleware."""
from apps.accounts.models import PlatformRole, RolePermission
from apps.tenancy.models import Institution, Membership, MembershipRole


def populate_request_context(request) -> None:
    """Resolve active institution, membership, roles, and permissions from session."""
    request.active_institution = None
    request.active_membership = None
    request.platform_role_codes = set()
    request.institution_role_codes = set()
    request.platform_permissions = set()
    request.institution_permissions = set()
    request.all_permissions = set()

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_active:
        return

    platform_assignments = list(
        PlatformRole.objects.filter(user=user).select_related("role")
    )
    platform_role_ids = [pr.role_id for pr in platform_assignments]
    request.platform_role_codes = {pr.role.code for pr in platform_assignments}

    if platform_role_ids:
        request.platform_permissions = set(
            RolePermission.objects.filter(role_id__in=platform_role_ids)
            .values_list("permission__code", flat=True)
        )

    active_inst_id = request.session.get("active_institution_id")
    if active_inst_id:
        membership = (
            Membership.objects.select_related("institution")
            .filter(
                user=user,
                institution_id=active_inst_id,
                status=Membership.Status.ACTIVE,
                institution__status=Institution.Status.ACTIVE,
            )
            .first()
        )
        if membership is None:
            # Membership or institution became inactive/revoked: clear stale session context immediately.
            request.session.pop("active_institution_id", None)
        else:
            request.active_membership = membership
            request.active_institution = membership.institution
            membership_roles = list(
                MembershipRole.objects.filter(membership=membership).select_related("role")
            )
            inst_role_ids = [mr.role_id for mr in membership_roles]
            request.institution_role_codes = {mr.role.code for mr in membership_roles}
            if inst_role_ids:
                request.institution_permissions = set(
                    RolePermission.objects.filter(role_id__in=inst_role_ids)
                    .values_list("permission__code", flat=True)
                )

    request.all_permissions = request.platform_permissions | request.institution_permissions


class TenantContextMiddleware:
    """Attach verified server-side tenant context to every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        populate_request_context(request)
        return self.get_response(request)

