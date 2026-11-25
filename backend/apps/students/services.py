"""Student management business logic with duplicate detection and audit logging."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.academics.models import Cohort
from apps.accounts.models import Role, User
from apps.accounts.rbac import ROLE_STUDENT
from apps.accounts.services import build_password_reset_payload
from apps.audit.services import log_audit_event
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership, MembershipRole


@transaction.atomic
def create_student_profile(
    *,
    institution: Institution,
    email: str,
    first_name: str,
    last_name: str = "",
    registration_no: str,
    cohort_id=None,
    admission_year: int | None = None,
    phone: str = "",
    status: str = StudentProfile.Status.ACTIVE,
    password: str | None = None,
    actor_user=None,
    request=None,
) -> tuple[StudentProfile, str | None]:
    norm_email = email.strip().lower()
    norm_reg = registration_no.strip().upper()

    if not norm_reg:
        raise ValidationError({"registration_no": "Registration number is required."})

    if StudentProfile.objects.filter(institution=institution, registration_no__iexact=norm_reg).exists():
        raise ValidationError({"registration_no": f"Registration number '{norm_reg}' already exists in this institution."})

    cohort = None
    if cohort_id:
        cohort = Cohort.objects.filter(institution=institution, id=cohort_id).first()
        if cohort is None:
            raise ValidationError({"cohort_id": "Selected cohort was not found in the active institution."})

    user = User.objects.filter(email__iexact=norm_email).first()
    onboarding_link: str | None = None
    if user is None:
        user = User.objects.create_user(
            email=norm_email,
            password=password or None,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            is_active=True,
            must_change_password=True,
        )
        if not password:
            payload = build_password_reset_payload(user)
            onboarding_link = f"/reset-password?uid={payload['uid']}&token={payload['token']}"
    else:
        existing_membership = Membership.objects.filter(institution=institution, user=user).first()
        if existing_membership and hasattr(existing_membership, "student_profile"):
            raise ValidationError({"email": "A student profile with this email already exists in this institution."})

    membership, _ = Membership.objects.get_or_create(
        institution=institution,
        user=user,
        defaults={
            "status": Membership.Status.ACTIVE if status == StudentProfile.Status.ACTIVE else Membership.Status.INACTIVE,
        },
    )
    student_role = Role.objects.get(code=ROLE_STUDENT)
    MembershipRole.objects.get_or_create(
        membership=membership,
        role=student_role,
        defaults={"assigned_by": actor_user if getattr(actor_user, "is_authenticated", False) else None},
    )

    profile = StudentProfile.objects.create(
        institution=institution,
        membership=membership,
        cohort=cohort,
        registration_no=norm_reg,
        admission_year=admission_year,
        phone=phone.strip(),
        status=status,
    )

    log_audit_event(
        action="STUDENT_CREATED",
        entity_type="StudentProfile",
        entity_id=profile.id,
        institution=institution,
        actor_user=actor_user,
        after={
            "registration_no": profile.registration_no,
            "email": user.email,
            "cohort_id": str(cohort.id) if cohort else None,
            "status": profile.status,
        },
        request=request,
    )
    return profile, onboarding_link


@transaction.atomic
def update_student_profile(
    *,
    profile: StudentProfile,
    data: dict,
    actor_user=None,
    request=None,
) -> StudentProfile:
    user = profile.membership.user
    before = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "registration_no": profile.registration_no,
        "cohort_id": str(profile.cohort_id) if profile.cohort_id else None,
        "admission_year": profile.admission_year,
        "phone": profile.phone,
        "status": profile.status,
    }

    if "first_name" in data:
        user.first_name = data["first_name"].strip()
    if "last_name" in data:
        user.last_name = data["last_name"].strip()
    user.save(update_fields=["first_name", "last_name", "updated_at"])

    if "registration_no" in data:
        new_reg = data["registration_no"].strip().upper()
        if (
            StudentProfile.objects.filter(institution=profile.institution)
            .exclude(id=profile.id)
            .filter(registration_no__iexact=new_reg)
            .exists()
        ):
            raise ValidationError({"registration_no": f"Registration number '{new_reg}' already exists in this institution."})
        profile.registration_no = new_reg

    if "cohort_id" in data:
        cid = data["cohort_id"]
        if cid is None:
            profile.cohort = None
        else:
            cohort = Cohort.objects.filter(institution=profile.institution, id=cid).first()
            if cohort is None:
                raise ValidationError({"cohort_id": "Selected cohort was not found in the active institution."})
            profile.cohort = cohort

    if "admission_year" in data:
        profile.admission_year = data["admission_year"]
    if "phone" in data:
        profile.phone = data["phone"].strip()
    if "status" in data:
        profile.status = data["status"]
        profile.membership.status = (
            Membership.Status.ACTIVE
            if data["status"] == StudentProfile.Status.ACTIVE
            else Membership.Status.INACTIVE
        )
        profile.membership.save(update_fields=["status", "updated_at"])

    profile.save()

    after = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "registration_no": profile.registration_no,
        "cohort_id": str(profile.cohort_id) if profile.cohort_id else None,
        "admission_year": profile.admission_year,
        "phone": profile.phone,
        "status": profile.status,
    }
    action = "STUDENT_STATUS_CHANGED" if before["status"] != after["status"] else "STUDENT_UPDATED"
    log_audit_event(
        action=action,
        entity_type="StudentProfile",
        entity_id=profile.id,
        institution=profile.institution,
        actor_user=actor_user,
        before=before,
        after=after,
        request=request,
    )
    return profile

