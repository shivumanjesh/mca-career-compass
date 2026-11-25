"""Faculty management & cohort assignment services."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.academics.models import Cohort
from apps.accounts.models import Role, User
from apps.accounts.rbac import ROLE_FACULTY_HOD
from apps.accounts.services import build_password_reset_payload
from apps.audit.services import log_audit_event
from apps.faculty.models import CohortFaculty, FacultyProfile
from apps.tenancy.models import Institution, Membership, MembershipRole


@transaction.atomic
def create_faculty_profile(
    *,
    institution: Institution,
    email: str,
    first_name: str,
    last_name: str = "",
    employee_code: str | None = None,
    department: str = "",
    designation: str = "",
    status: str = FacultyProfile.Status.ACTIVE,
    password: str | None = None,
    actor_user=None,
    request=None,
) -> tuple[FacultyProfile, str | None]:
    norm_email = email.strip().lower()
    norm_emp = employee_code.strip().upper() if employee_code else None
    if norm_emp == "":
        norm_emp = None

    if norm_emp and FacultyProfile.objects.filter(institution=institution, employee_code__iexact=norm_emp).exists():
        raise ValidationError({"employee_code": f"Employee code '{norm_emp}' already exists in this institution."})

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
        if existing_membership and hasattr(existing_membership, "faculty_profile"):
            raise ValidationError({"email": "A faculty profile with this email already exists in this institution."})

    membership, _ = Membership.objects.get_or_create(
        institution=institution,
        user=user,
        defaults={
            "status": Membership.Status.ACTIVE if status == FacultyProfile.Status.ACTIVE else Membership.Status.INACTIVE,
        },
    )
    faculty_role = Role.objects.get(code=ROLE_FACULTY_HOD)
    MembershipRole.objects.get_or_create(
        membership=membership,
        role=faculty_role,
        defaults={"assigned_by": actor_user if getattr(actor_user, "is_authenticated", False) else None},
    )

    profile = FacultyProfile.objects.create(
        institution=institution,
        membership=membership,
        employee_code=norm_emp,
        department=department.strip(),
        designation=designation.strip(),
        status=status,
    )
    log_audit_event(
        action="FACULTY_CREATED",
        entity_type="FacultyProfile",
        entity_id=profile.id,
        institution=institution,
        actor_user=actor_user,
        after={
            "email": user.email,
            "employee_code": profile.employee_code,
            "department": profile.department,
            "designation": profile.designation,
        },
        request=request,
    )
    return profile, onboarding_link


@transaction.atomic
def update_faculty_profile(
    *,
    profile: FacultyProfile,
    data: dict,
    actor_user=None,
    request=None,
) -> FacultyProfile:
    user = profile.membership.user
    before = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "employee_code": profile.employee_code,
        "department": profile.department,
        "designation": profile.designation,
        "status": profile.status,
    }

    if "first_name" in data:
        user.first_name = data["first_name"].strip()
    if "last_name" in data:
        user.last_name = data["last_name"].strip()
    user.save(update_fields=["first_name", "last_name", "updated_at"])

    if "employee_code" in data:
        raw_code = data["employee_code"]
        new_code = raw_code.strip().upper() if raw_code else None
        if new_code == "":
            new_code = None
        if (
            new_code
            and FacultyProfile.objects.filter(institution=profile.institution)
            .exclude(id=profile.id)
            .filter(employee_code__iexact=new_code)
            .exists()
        ):
            raise ValidationError({"employee_code": f"Employee code '{new_code}' already exists in this institution."})
        profile.employee_code = new_code

    if "department" in data:
        profile.department = data["department"].strip()
    if "designation" in data:
        profile.designation = data["designation"].strip()
    if "status" in data:
        profile.status = data["status"]
        profile.membership.status = (
            Membership.Status.ACTIVE
            if data["status"] == FacultyProfile.Status.ACTIVE
            else Membership.Status.INACTIVE
        )
        profile.membership.save(update_fields=["status", "updated_at"])

    profile.save()
    after = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "employee_code": profile.employee_code,
        "department": profile.department,
        "designation": profile.designation,
        "status": profile.status,
    }
    action = "FACULTY_STATUS_CHANGED" if before["status"] != after["status"] else "FACULTY_UPDATED"
    log_audit_event(
        action=action,
        entity_type="FacultyProfile",
        entity_id=profile.id,
        institution=profile.institution,
        actor_user=actor_user,
        before=before,
        after=after,
        request=request,
    )
    return profile


@transaction.atomic
def assign_faculty_to_cohort(
    *,
    faculty_profile: FacultyProfile,
    cohort_id,
    assignment_type: str = CohortFaculty.AssignmentType.MENTOR,
    actor_user=None,
    request=None,
) -> CohortFaculty:
    cohort = Cohort.objects.filter(institution=faculty_profile.institution, id=cohort_id).first()
    if cohort is None:
        raise ValidationError({"cohort_id": "Cohort not found in the active institution."})

    if CohortFaculty.objects.filter(
        cohort=cohort,
        faculty_profile=faculty_profile,
        assignment_type=assignment_type,
    ).exists():
        raise ValidationError({"cohort_id": "This faculty member already holds this assignment type for the selected cohort."})

    assignment = CohortFaculty.objects.create(
        institution=faculty_profile.institution,
        cohort=cohort,
        faculty_profile=faculty_profile,
        assignment_type=assignment_type,
    )
    log_audit_event(
        action="FACULTY_COHORT_ASSIGNED",
        entity_type="CohortFaculty",
        entity_id=assignment.id,
        institution=faculty_profile.institution,
        actor_user=actor_user,
        after={
            "faculty_email": faculty_profile.membership.user.email,
            "cohort_id": str(cohort.id),
            "cohort": str(cohort),
            "assignment_type": assignment_type,
        },
        request=request,
    )
    return assignment


@transaction.atomic
def remove_faculty_cohort_assignment(
    *,
    assignment: CohortFaculty,
    actor_user=None,
    request=None,
) -> None:
    inst = assignment.institution
    before = {
        "faculty_email": assignment.faculty_profile.membership.user.email,
        "cohort_id": str(assignment.cohort_id),
        "assignment_type": assignment.assignment_type,
    }
    assignment_id = assignment.id
    assignment.delete()
    log_audit_event(
        action="FACULTY_COHORT_UNASSIGNED",
        entity_type="CohortFaculty",
        entity_id=assignment_id,
        institution=inst,
        actor_user=actor_user,
        before=before,
        request=request,
    )

