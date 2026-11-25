"""Authentication, RBAC seeding, and credential lifecycle services."""
from django.apps import apps
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError

from apps.accounts.models import Permission, PlatformRole, Role, RolePermission, User
from apps.accounts.rbac import (
    ACADEMIC_PORTAL_ROLES,
    ADMIN_PORTAL_ROLES,
    CANONICAL_PERMISSIONS,
    CANONICAL_ROLES,
    ROLE_PERMISSION_MAP,
)
from apps.audit.services import log_audit_event
from apps.tenancy.middleware import populate_request_context
from apps.tenancy.models import Institution, Membership


def seed_roles_and_permissions() -> None:
    """Idempotently ensure canonical roles, permissions, and mappings exist."""
    role_map: dict[str, Role] = {}
    for code, name, scope in CANONICAL_ROLES:
        role, _ = Role.objects.update_or_create(
            code=code,
            defaults={"name": name, "scope": scope},
        )
        role_map[code] = role

    perm_map: dict[str, Permission] = {}
    for code, name, scope, description in CANONICAL_PERMISSIONS:
        perm, _ = Permission.objects.update_or_create(
            code=code,
            defaults={"name": name, "scope": scope, "description": description},
        )
        perm_map[code] = perm

    for role_code, perm_codes in ROLE_PERMISSION_MAP.items():
        role = role_map[role_code]
        for perm_code in perm_codes:
            RolePermission.objects.get_or_create(
                role=role,
                permission=perm_map[perm_code],
            )


def _resolve_user_by_identifier(identifier: str, portal: str, institution_code: str | None) -> User | None:
    cleaned = identifier.strip()
    user = User.objects.filter(email__iexact=cleaned).first()
    if user is not None:
        return user

    if portal == "academic" and institution_code and apps.is_installed("apps.students"):
        StudentProfile = apps.get_model("students", "StudentProfile")
        profile = (
            StudentProfile.objects.select_related("membership__user", "institution")
            .filter(
                institution__code__iexact=institution_code.strip(),
                registration_no__iexact=cleaned,
            )
            .first()
        )
        if profile is not None:
            return profile.membership.user
    return None


def authenticate_portal_login(
    *,
    request,
    portal: str,
    identifier: str,
    password: str,
    institution_code: str | None = None,
) -> tuple[User, Membership | None]:
    """Authenticate a user for either 'admin' or 'academic' portal with strict scope checks."""
    if portal not in ("admin", "academic"):
        raise ValidationError({"portal": "Invalid login portal specified."})

    cleaned_inst_code = institution_code.strip().upper() if institution_code else None
    user = _resolve_user_by_identifier(identifier, portal, cleaned_inst_code)

    if user is None or not user.check_password(password) or not user.is_active:
        log_audit_event(
            action="AUTH_LOGIN_FAILED",
            entity_type="User",
            entity_id=user.id if user else None,
            actor_user=None,
            after={"portal": portal, "identifier": identifier.strip().lower(), "institution_code": cleaned_inst_code},
            request=request,
        )
        raise AuthenticationFailed("Invalid credentials or inactive account.")

    has_platform_admin = PlatformRole.objects.filter(
        user=user,
        role__code__in=ADMIN_PORTAL_ROLES,
    ).exists()

    selected_membership: Membership | None = None

    if portal == "admin":
        if has_platform_admin and not cleaned_inst_code:
            selected_membership = None
        else:
            qs = Membership.objects.select_related("institution").filter(
                user=user,
                status=Membership.Status.ACTIVE,
                institution__status=Institution.Status.ACTIVE,
                membership_roles__role__code__in=ADMIN_PORTAL_ROLES,
            ).distinct()
            if cleaned_inst_code:
                qs = qs.filter(institution__code__iexact=cleaned_inst_code)
            memberships = list(qs)
            if not memberships:
                if has_platform_admin and cleaned_inst_code:
                    raise PermissionDenied("Platform admin does not hold an administrative membership in that institution.")
                raise PermissionDenied("Your account is not authorized for the administrative portal or the institution is inactive.")
            if len(memberships) > 1:
                raise ValidationError({"institution_code": "Multiple active institutions found. Please specify your Institution Code."})
            selected_membership = memberships[0]
    else:
        qs = Membership.objects.select_related("institution").filter(
            user=user,
            status=Membership.Status.ACTIVE,
            institution__status=Institution.Status.ACTIVE,
            membership_roles__role__code__in=ACADEMIC_PORTAL_ROLES,
        ).distinct()
        if cleaned_inst_code:
            qs = qs.filter(institution__code__iexact=cleaned_inst_code)
        memberships = list(qs)
        if not memberships:
            raise PermissionDenied("No active Faculty or Student membership found for the specified institution.")
        if len(memberships) > 1:
            raise ValidationError({"institution_code": "Multiple active institutions found. Please specify your Institution Code."})
        selected_membership = memberships[0]

    login(request, user)
    if selected_membership is not None:
        request.session["active_institution_id"] = str(selected_membership.institution_id)
    else:
        request.session.pop("active_institution_id", None)

    populate_request_context(request)

    log_audit_event(
        action="AUTH_LOGIN_SUCCESS",
        entity_type="User",
        entity_id=user.id,
        institution=selected_membership.institution if selected_membership else None,
        actor_user=user,
        after={"portal": portal, "institution_code": selected_membership.institution.code if selected_membership else None},
        request=request,
    )
    return user, selected_membership


def logout_current_user(*, request) -> None:
    """Terminate authenticated session and record audit event."""
    user = request.user if request.user.is_authenticated else None
    inst = getattr(request, "active_institution", None)
    if user:
        log_audit_event(
            action="AUTH_LOGOUT",
            entity_type="User",
            entity_id=user.id,
            institution=inst,
            actor_user=user,
            request=request,
        )
    logout(request)


def switch_active_institution(*, request, institution_id: str) -> Membership:
    """Switch active institution in server session only after verifying active Membership."""
    membership = (
        Membership.objects.select_related("institution")
        .filter(
            user=request.user,
            institution_id=institution_id,
            status=Membership.Status.ACTIVE,
            institution__status=Institution.Status.ACTIVE,
        )
        .first()
    )
    if membership is None:
        raise PermissionDenied("You do not have an active membership in the requested institution.")

    previous_inst = getattr(request, "active_institution", None)
    request.session["active_institution_id"] = str(membership.institution_id)
    populate_request_context(request)

    log_audit_event(
        action="AUTH_SWITCH_INSTITUTION",
        entity_type="Membership",
        entity_id=membership.id,
        institution=membership.institution,
        actor_user=request.user,
        before={"institution_code": previous_inst.code if previous_inst else None},
        after={"institution_code": membership.institution.code},
        request=request,
    )
    return membership


def change_user_password(*, request, old_password: str, new_password: str) -> None:
    """Validate and update authenticated user's password."""
    user = request.user
    if user.has_usable_password() and not user.check_password(old_password):
        raise ValidationError({"old_password": "Current password is incorrect."})

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"new_password": list(exc.messages)})

    with transaction.atomic():
        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        update_session_auth_hash(request, user)
        log_audit_event(
            action="AUTH_PASSWORD_CHANGED",
            entity_type="User",
            entity_id=user.id,
            institution=getattr(request, "active_institution", None),
            actor_user=user,
            request=request,
        )


def build_password_reset_payload(user: User) -> dict[str, str]:
    """Generate uidb64 and one-time Django password reset token."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return {"uid": uid, "token": token}


def request_password_reset(*, email: str, request=None) -> None:
    """Dispatch password reset instructions via configured Django email backend without leaking existence."""
    user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
    if user is None:
        return
    payload = build_password_reset_payload(user)
    reset_path = f"/reset-password?uid={payload['uid']}&token={payload['token']}"
    send_mail(
        subject="MCA Career Compass — Password Setup / Reset",
        message=(
            f"Hello {user.full_name},\n\n"
            f"Use the following secure link to set or reset your password:\n"
            f"http://localhost:5173{reset_path}\n\n"
            "If you did not request this, you can safely ignore this message."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    log_audit_event(
        action="AUTH_PASSWORD_RESET_REQUESTED",
        entity_type="User",
        entity_id=user.id,
        actor_user=user,
        request=request,
    )


def confirm_password_reset(*, uid: str, token: str, new_password: str, request=None) -> None:
    """Verify reset token and set new password."""
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id, is_active=True)
    except Exception:
        raise ValidationError({"token": "Invalid or expired password reset link."})

    if not default_token_generator.check_token(user, token):
        raise ValidationError({"token": "Invalid or expired password reset link."})

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"new_password": list(exc.messages)})

    with transaction.atomic():
        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        log_audit_event(
            action="AUTH_PASSWORD_RESET_CONFIRMED",
            entity_type="User",
            entity_id=user.id,
            actor_user=user,
            request=request,
        )


def serialize_auth_me(request) -> dict:
    """Build current user, memberships, active institution, roles, and permissions payload."""
    user = request.user
    memberships_qs = (
        Membership.objects.select_related("institution")
        .prefetch_related("membership_roles__role")
        .filter(
            user=user,
            status=Membership.Status.ACTIVE,
            institution__status=Institution.Status.ACTIVE,
        )
        .order_by("institution__name")
    )
    memberships_data = []
    for m in memberships_qs:
        memberships_data.append(
            {
                "id": str(m.id),
                "institution_id": str(m.institution_id),
                "institution_code": m.institution.code,
                "institution_name": m.institution.name,
                "status": m.status,
                "roles": [mr.role.code for mr in m.membership_roles.all()],
            }
        )

    active_inst = getattr(request, "active_institution", None)
    active_membership = getattr(request, "active_membership", None)

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "must_change_password": user.must_change_password,
        },
        "platform_roles": sorted(getattr(request, "platform_role_codes", set())),
        "active_institution": (
            {
                "id": str(active_inst.id),
                "code": active_inst.code,
                "name": active_inst.name,
                "status": active_inst.status,
                "timezone": active_inst.timezone,
            }
            if active_inst
            else None
        ),
        "active_membership_id": str(active_membership.id) if active_membership else None,
        "active_roles": sorted(getattr(request, "institution_role_codes", set())),
        "permissions": sorted(getattr(request, "all_permissions", set())),
        "memberships": memberships_data,
    }

