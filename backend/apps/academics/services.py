"""Academic structure services with tenant validation and audit logging."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.academics.models import AcademicYear, ActiveStatus, Cohort, Programme
from apps.audit.services import log_audit_event
from apps.tenancy.models import Institution


@transaction.atomic
def create_programme(*, institution: Institution, code: str, name: str, level: str = "PG", status: str = ActiveStatus.ACTIVE, actor_user=None, request=None) -> Programme:
    norm_code = code.strip().upper()
    if Programme.objects.filter(institution=institution, code__iexact=norm_code).exists():
        raise ValidationError({"code": "A programme with this code already exists in your institution."})
    programme = Programme.objects.create(
        institution=institution,
        code=norm_code,
        name=name.strip(),
        level=level.strip() or "PG",
        status=status,
    )
    log_audit_event(
        action="PROGRAMME_CREATED",
        entity_type="Programme",
        entity_id=programme.id,
        institution=institution,
        actor_user=actor_user,
        after={"code": programme.code, "name": programme.name, "level": programme.level},
        request=request,
    )
    return programme


@transaction.atomic
def update_programme(*, programme: Programme, data: dict, actor_user=None, request=None) -> Programme:
    before = {"code": programme.code, "name": programme.name, "level": programme.level, "status": programme.status}
    if "code" in data:
        new_code = data["code"].strip().upper()
        if Programme.objects.filter(institution=programme.institution).exclude(id=programme.id).filter(code__iexact=new_code).exists():
            raise ValidationError({"code": "A programme with this code already exists in your institution."})
        programme.code = new_code
    if "name" in data:
        programme.name = data["name"].strip()
    if "level" in data:
        programme.level = data["level"].strip() or "PG"
    if "status" in data:
        programme.status = data["status"]
    programme.save()

    after = {"code": programme.code, "name": programme.name, "level": programme.level, "status": programme.status}
    log_audit_event(
        action="PROGRAMME_UPDATED",
        entity_type="Programme",
        entity_id=programme.id,
        institution=programme.institution,
        actor_user=actor_user,
        before=before,
        after=after,
        request=request,
    )
    return programme


@transaction.atomic
def create_academic_year(*, institution: Institution, name: str, start_date, end_date, status: str = ActiveStatus.ACTIVE, actor_user=None, request=None) -> AcademicYear:
    if end_date < start_date:
        raise ValidationError({"end_date": "End date must be on or after start date."})
    if AcademicYear.objects.filter(institution=institution, name__iexact=name.strip()).exists():
        raise ValidationError({"name": "An academic year with this name already exists."})
    ay = AcademicYear.objects.create(
        institution=institution,
        name=name.strip(),
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    log_audit_event(
        action="ACADEMIC_YEAR_CREATED",
        entity_type="AcademicYear",
        entity_id=ay.id,
        institution=institution,
        actor_user=actor_user,
        after={"name": ay.name, "start_date": str(ay.start_date), "end_date": str(ay.end_date)},
        request=request,
    )
    return ay


@transaction.atomic
def update_academic_year(*, academic_year: AcademicYear, data: dict, actor_user=None, request=None) -> AcademicYear:
    before = {
        "name": academic_year.name,
        "start_date": str(academic_year.start_date),
        "end_date": str(academic_year.end_date),
        "status": academic_year.status,
    }
    if "name" in data:
        new_name = data["name"].strip()
        if AcademicYear.objects.filter(institution=academic_year.institution).exclude(id=academic_year.id).filter(name__iexact=new_name).exists():
            raise ValidationError({"name": "An academic year with this name already exists."})
        academic_year.name = new_name
    if "start_date" in data:
        academic_year.start_date = data["start_date"]
    if "end_date" in data:
        academic_year.end_date = data["end_date"]
    if academic_year.end_date < academic_year.start_date:
        raise ValidationError({"end_date": "End date must be on or after start date."})
    if "status" in data:
        academic_year.status = data["status"]
    academic_year.save()

    after = {
        "name": academic_year.name,
        "start_date": str(academic_year.start_date),
        "end_date": str(academic_year.end_date),
        "status": academic_year.status,
    }
    log_audit_event(
        action="ACADEMIC_YEAR_UPDATED",
        entity_type="AcademicYear",
        entity_id=academic_year.id,
        institution=academic_year.institution,
        actor_user=actor_user,
        before=before,
        after=after,
        request=request,
    )
    return academic_year


@transaction.atomic
def create_cohort(
    *,
    institution: Institution,
    programme_id,
    academic_year_id,
    batch_name: str,
    semester: int,
    section: str = "A",
    status: str = ActiveStatus.ACTIVE,
    actor_user=None,
    request=None,
) -> Cohort:
    programme = Programme.objects.filter(institution=institution, id=programme_id).first()
    if programme is None:
        raise ValidationError({"programme_id": "Programme not found in active institution."})
    academic_year = AcademicYear.objects.filter(institution=institution, id=academic_year_id).first()
    if academic_year is None:
        raise ValidationError({"academic_year_id": "Academic year not found in active institution."})

    norm_batch = batch_name.strip()
    norm_section = section.strip().upper() or "A"

    if Cohort.objects.filter(
        institution=institution,
        programme=programme,
        academic_year=academic_year,
        batch_name__iexact=norm_batch,
        semester=semester,
        section=norm_section,
    ).exists():
        raise ValidationError({"batch_name": "This cohort (programme, academic year, batch, semester, section) already exists."})

    cohort = Cohort.objects.create(
        institution=institution,
        programme=programme,
        academic_year=academic_year,
        batch_name=norm_batch,
        semester=semester,
        section=norm_section,
        status=status,
    )
    log_audit_event(
        action="COHORT_CREATED",
        entity_type="Cohort",
        entity_id=cohort.id,
        institution=institution,
        actor_user=actor_user,
        after={
            "programme_code": programme.code,
            "academic_year": academic_year.name,
            "batch_name": cohort.batch_name,
            "semester": cohort.semester,
            "section": cohort.section,
        },
        request=request,
    )
    return cohort


@transaction.atomic
def update_cohort(*, cohort: Cohort, data: dict, actor_user=None, request=None) -> Cohort:
    before = {
        "batch_name": cohort.batch_name,
        "semester": cohort.semester,
        "section": cohort.section,
        "status": cohort.status,
    }
    if "programme_id" in data:
        prog = Programme.objects.filter(institution=cohort.institution, id=data["programme_id"]).first()
        if prog is None:
            raise ValidationError({"programme_id": "Programme not found in active institution."})
        cohort.programme = prog
    if "academic_year_id" in data:
        ay = AcademicYear.objects.filter(institution=cohort.institution, id=data["academic_year_id"]).first()
        if ay is None:
            raise ValidationError({"academic_year_id": "Academic year not found in active institution."})
        cohort.academic_year = ay
    if "batch_name" in data:
        cohort.batch_name = data["batch_name"].strip()
    if "semester" in data:
        cohort.semester = data["semester"]
    if "section" in data:
        cohort.section = data["section"].strip().upper() or "A"
    if "status" in data:
        cohort.status = data["status"]

    if (
        Cohort.objects.filter(
            institution=cohort.institution,
            programme=cohort.programme,
            academic_year=cohort.academic_year,
            batch_name__iexact=cohort.batch_name,
            semester=cohort.semester,
            section=cohort.section,
        )
        .exclude(id=cohort.id)
        .exists()
    ):
        raise ValidationError({"batch_name": "Another cohort with the same programme, year, batch, semester, and section already exists."})

    cohort.save()
    after = {
        "batch_name": cohort.batch_name,
        "semester": cohort.semester,
        "section": cohort.section,
        "status": cohort.status,
    }
    log_audit_event(
        action="COHORT_UPDATED",
        entity_type="Cohort",
        entity_id=cohort.id,
        institution=cohort.institution,
        actor_user=actor_user,
        before=before,
        after=after,
        request=request,
    )
    return cohort

