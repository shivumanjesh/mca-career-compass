"""Business logic, transactions, and audit logging for tenancy & user management."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Role, RoleScope, User
from apps.accounts.rbac import ROLE_INSTITUTION_ADMIN
from apps.accounts.services import build_password_reset_payload
from apps.audit.services import log_audit_event
from apps.tenancy.models import Institution, Membership, MembershipRole


def _onboarding_reset_url(user: User) -> str:
    payload = build_password_reset_payload(user)
    return f"/reset-password?uid={payload['uid']}&token={payload['token']}"


@transaction.atomic
def create_institution(
    *,
    code: str,
    name: str,
    timezone: str = "Asia/Kolkata",
    status: str = Institution.Status.ACTIVE,
    settings_data: dict | None = None,
    actor_user=None,
    request=None,
) -> Institution:
    normalized_code = code.strip().upper()
    if Institution.objects.filter(code__iexact=normalized_code).exists():
        raise ValidationError({"code": "An institution with this code already exists."})

    institution = Institution.objects.create(
        code=normalized_code,
        name=name.strip(),
        timezone=timezone.strip() or "Asia/Kolkata",
        status=status,
        settings=settings_data or {},
    )
    log_audit_event(
        action="INSTITUTION_CREATED",
        entity_type="Institution",
        entity_id=institution.id,
        institution=institution,
        actor_user=actor_user,
        after={
            "code": institution.code,
            "name": institution.name,
            "status": institution.status,
            "timezone": institution.timezone,
        },
        request=request,
    )
    return institution


@transaction.atomic
def update_institution(
    *,
    institution: Institution,
    data: dict,
    actor_user=None,
    request=None,
    allow_status_and_code: bool = True,
) -> Institution:
    before = {
        "code": institution.code,
        "name": institution.name,
        "status": institution.status,
        "timezone": institution.timezone,
        "settings": institution.settings,
    }

    if allow_status_and_code and "code" in data:
        new_code = data["code"].strip().upper()
        if Institution.objects.exclude(id=institution.id).filter(code__iexact=new_code).exists():
            raise ValidationError({"code": "An institution with this code already exists."})
        institution.code = new_code

    if "name" in data:
        institution.name = data["name"].strip()
    if "timezone" in data:
        institution.timezone = data["timezone"].strip() or "Asia/Kolkata"
    if "settings" in data:
        institution.settings = data["settings"] or {}
    if allow_status_and_code and "status" in data:
        institution.status = data["status"]

    institution.save()

    after = {
        "code": institution.code,
        "name": institution.name,
        "status": institution.status,
        "timezone": institution.timezone,
        "settings": institution.settings,
    }
    action = (
        "INSTITUTION_STATUS_CHANGED"
        if before["status"] != after["status"]
        else "INSTITUTION_UPDATED"
    )
    log_audit_event(
        action=action,
        entity_type="Institution",
        entity_id=institution.id,
        institution=institution,
        actor_user=actor_user,
        before=before,
        after=after,
        request=request,
    )
    return institution


@transaction.atomic
def provision_institution_user(
    *,
    institution: Institution,
    email: str,
    first_name: str,
    last_name: str = "",
    role_codes: list[str],
    password: str | None = None,
    membership_status: str = Membership.Status.ACTIVE,
    actor_user=None,
    request=None,
) -> tuple[Membership, str | None]:
    """Create or link a user to an institution with explicit institution-scoped roles."""
    normalized_email = email.strip().lower()
    if not role_codes:
        raise ValidationError({"role_codes": "At least one institution role is required."})

    roles = list(Role.objects.filter(code__in=role_codes, scope=RoleScope.INSTITUTION))
    found_codes = {r.code for r in roles}
    invalid_codes = [c for c in role_codes if c not in found_codes]
    if invalid_codes:
        raise ValidationError({"role_codes": f"Invalid or non-institution roles: {', '.join(invalid_codes)}"})

    user = User.objects.filter(email__iexact=normalized_email).first()
    onboarding_link: str | None = None

    if user is None:
        user = User.objects.create_user(
            email=normalized_email,
            password=password or None,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            is_active=True,
            must_change_password=True,
        )
        if not password:
            onboarding_link = _onboarding_reset_url(user)
    else:
        if Membership.objects.filter(institution=institution, user=user).exists():
            raise ValidationError({"email": "This user already has a membership in this institution."})

    membership = Membership.objects.create(
        institution=institution,
        user=user,
        status=membership_status,
    )
    for role in roles:
        MembershipRole.objects.create(
            membership=membership,
            role=role,
            assigned_by=actor_user if getattr(actor_user, "is_authenticated", False) else None,
        )

    log_audit_event(
        action="INSTITUTION_USER_CREATED",
        entity_type="Membership",
        entity_id=membership.id,
        institution=institution,
        actor_user=actor_user,
        after={
            "email": user.email,
            "full_name": user.full_name,
            "membership_status": membership.status,
            "roles": sorted(found_codes),
        },
        request=request,
    )
    return membership, onboarding_link


@transaction.atomic
def provision_institution_admin(
    *,
    institution: Institution,
    email: str,
    first_name: str,
    last_name: str = "",
    password: str | None = None,
    actor_user=None,
    request=None,
) -> tuple[Membership, str | None]:
    """Create an Institution Admin for a specific institution (Platform Super Admin action)."""
    membership, onboarding_link = provision_institution_user(
        institution=institution,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role_codes=[ROLE_INSTITUTION_ADMIN],
        password=password,
        membership_status=Membership.Status.ACTIVE,
        actor_user=actor_user,
        request=request,
    )
    log_audit_event(
        action="INSTITUTION_ADMIN_PROVISIONED",
        entity_type="Membership",
        entity_id=membership.id,
        institution=institution,
        actor_user=actor_user,
        after={"email": membership.user.email, "institution_code": institution.code},
        request=request,
    )
    return membership, onboarding_link


@transaction.atomic
def update_institution_user(
    *,
    membership: Membership,
    first_name: str | None = None,
    last_name: str | None = None,
    status: str | None = None,
    actor_user=None,
    request=None,
) -> Membership:
    user = membership.user
    before = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "membership_status": membership.status,
    }

    if status == Membership.Status.INACTIVE and actor_user and actor_user.id == user.id:
        raise ValidationError({"status": "You cannot deactivate your own active membership."})

    if first_name is not None:
        user.first_name = first_name.strip()
    if last_name is not None:
        user.last_name = last_name.strip()
    user.save(update_fields=["first_name", "last_name", "updated_at"])

    if status is not None:
        membership.status = status
        membership.save(update_fields=["status", "updated_at"])

    after = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "membership_status": membership.status,
    }
    action = (
        "MEMBERSHIP_STATUS_CHANGED"
        if before["membership_status"] != after["membership_status"]
        else "INSTITUTION_USER_UPDATED"
    )
    log_audit_event(
        action=action,
        entity_type="Membership",
        entity_id=membership.id,
        institution=membership.institution,
        actor_user=actor_user,
        before=before,
        after=after,
        request=request,
    )
    return membership


@transaction.atomic
def update_membership_roles(
    *,
    membership: Membership,
    role_codes: list[str],
    actor_user=None,
    request=None,
) -> Membership:
    if not role_codes:
        raise ValidationError({"role_codes": "A membership must retain at least one role."})

    roles = list(Role.objects.filter(code__in=role_codes, scope=RoleScope.INSTITUTION))
    found_codes = {r.code for r in roles}
    invalid_codes = [c for c in role_codes if c not in found_codes]
    if invalid_codes:
        raise ValidationError({"role_codes": f"Invalid or non-institution roles: {', '.join(invalid_codes)}"})

    if (
        actor_user
        and actor_user.id == membership.user_id
        and ROLE_INSTITUTION_ADMIN not in found_codes
    ):
        raise ValidationError({"role_codes": "You cannot remove your own INSTITUTION_ADMIN role."})

    before_codes = sorted(
        membership.membership_roles.values_list("role__code", flat=True)
    )
    MembershipRole.objects.filter(membership=membership).delete()
    for role in roles:
        MembershipRole.objects.create(
            membership=membership,
            role=role,
            assigned_by=actor_user if getattr(actor_user, "is_authenticated", False) else None,
        )

    log_audit_event(
        action="MEMBERSHIP_ROLES_UPDATED",
        entity_type="Membership",
        entity_id=membership.id,
        institution=membership.institution,
        actor_user=actor_user,
        before={"roles": before_codes},
        after={"roles": sorted(found_codes)},
        request=request,
    )
    return membership

