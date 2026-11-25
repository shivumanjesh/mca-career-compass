"""Phase 5 CRUD & progress tracking services for development plans and learning resources."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.assessments.models import AssessmentDimension
from apps.audit.services import log_audit_event
from apps.development.models import (
    DevelopmentActivity,
    DevelopmentPlan,
    LearningResource,
    ProgressRecord,
    ResourceType,
)
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution


@transaction.atomic
def create_learning_resource(*, institution: Institution, data: dict, actor_user=None, request=None) -> LearningResource:
    res = LearningResource.objects.create(
        institution=institution,
        dimension_code=data.get("dimension_code", "").strip().upper(),
        target_domain=data["target_domain"].strip(),
        resource_type=data["resource_type"],
        title=data["title"].strip(),
        description=data.get("description", "").strip(),
        provider=data.get("provider", "").strip(),
        level=data.get("level", LearningResource.Level.INTERMEDIATE),
        estimated_hours=data.get("estimated_hours", 10),
        resource_url=data.get("resource_url", "").strip(),
    )
    log_audit_event(
        action="LEARNING_RESOURCE_CREATED",
        entity_type="LearningResource",
        entity_id=res.id,
        institution=institution,
        actor_user=actor_user,
        after={"title": res.title, "resource_type": res.resource_type, "target_domain": res.target_domain},
        request=request,
    )
    return res


@transaction.atomic
def update_learning_resource(*, resource: LearningResource, data: dict, actor_user=None, request=None) -> LearningResource:
    before = {"title": resource.title, "status": resource.status}
    for field in ("target_domain", "resource_type", "title", "description", "provider", "level", "estimated_hours", "resource_url", "status"):
        if field in data:
            val = data[field]
            setattr(resource, field, val.strip() if isinstance(val, str) else val)
    if "dimension_code" in data:
        resource.dimension_code = data["dimension_code"].strip().upper()
    resource.save()
    log_audit_event(
        action="LEARNING_RESOURCE_UPDATED",
        entity_type="LearningResource",
        entity_id=resource.id,
        institution=resource.institution,
        actor_user=actor_user,
        before=before,
        after={"title": resource.title, "status": resource.status},
        request=request,
    )
    return resource


@transaction.atomic
def create_development_plan(
    *,
    institution: Institution,
    student: StudentProfile,
    data: dict,
    actor_user,
    default_status: str = DevelopmentPlan.Status.ACTIVE,
    request=None,
) -> DevelopmentPlan:
    start_date = data.get("start_date")
    target_date = data.get("target_date")
    if start_date and target_date and target_date < start_date:
        raise ValidationError({"target_date": "Target date must be on or after start date."})

    plan = DevelopmentPlan.objects.create(
        institution=institution,
        student_profile=student,
        created_by=actor_user,
        title=data["title"].strip(),
        target_domain=data.get("target_domain", "").strip(),
        notes=data.get("notes", "").strip(),
        status=data.get("status", default_status),
        start_date=start_date,
        target_date=target_date,
    )
    log_audit_event(
        action="DEVELOPMENT_PLAN_CREATED",
        entity_type="DevelopmentPlan",
        entity_id=plan.id,
        institution=institution,
        actor_user=actor_user,
        after={"student_reg_no": student.registration_no, "title": plan.title, "status": plan.status},
        request=request,
    )
    return plan


@transaction.atomic
def update_development_plan(
    *,
    plan: DevelopmentPlan,
    data: dict,
    actor_user,
    request=None,
) -> DevelopmentPlan:
    before = {"title": plan.title, "status": plan.status, "target_domain": plan.target_domain}
    for field in ("title", "target_domain", "notes", "status", "start_date", "target_date"):
        if field in data:
            val = data[field]
            setattr(plan, field, val.strip() if isinstance(val, str) else val)

    if plan.start_date and plan.target_date and plan.target_date < plan.start_date:
        raise ValidationError({"target_date": "Target date must be on or after start date."})

    plan.save()
    log_audit_event(
        action="DEVELOPMENT_PLAN_UPDATED",
        entity_type="DevelopmentPlan",
        entity_id=plan.id,
        institution=plan.institution,
        actor_user=actor_user,
        before=before,
        after={"title": plan.title, "status": plan.status, "target_domain": plan.target_domain},
        request=request,
    )
    return plan


@transaction.atomic
def add_plan_activity(*, plan: DevelopmentPlan, data: dict, actor_user, request=None) -> DevelopmentActivity:
    institution = plan.institution
    resource = None
    if data.get("resource_id"):
        resource = LearningResource.objects.filter(institution=institution, id=data["resource_id"]).first()
        if resource is None:
            raise ValidationError({"resource_id": "Learning resource not found in active institution."})

    dimension = None
    if data.get("dimension_id"):
        dimension = AssessmentDimension.objects.filter(institution=institution, id=data["dimension_id"]).first()
        if dimension is None:
            raise ValidationError({"dimension_id": "Assessment dimension not found in active institution."})

    title = (data.get("title") or (resource.title if resource else "")).strip()
    if not title:
        raise ValidationError({"title": "Activity title is required."})

    activity = DevelopmentActivity.objects.create(
        institution=institution,
        plan=plan,
        dimension=dimension,
        resource=resource,
        title=title,
        description=(data.get("description") or (resource.description if resource else "")).strip(),
        activity_type=data.get("activity_type") or (resource.resource_type if resource else ResourceType.LEARNING_PATHWAY),
        due_date=data.get("due_date"),
        evidence_url=data.get("evidence_url", "").strip(),
    )
    log_audit_event(
        action="DEVELOPMENT_ACTIVITY_ADDED",
        entity_type="DevelopmentActivity",
        entity_id=activity.id,
        institution=institution,
        actor_user=actor_user,
        after={"plan_id": str(plan.id), "title": activity.title, "activity_type": activity.activity_type},
        request=request,
    )
    return activity


@transaction.atomic
def record_activity_progress(
    *,
    activity: DevelopmentActivity,
    progress_percent: int,
    reflection: str = "",
    evidence_url: str = "",
    actor_user,
    request=None,
) -> ProgressRecord:
    if not (0 <= progress_percent <= 100):
        raise ValidationError({"progress_percent": "Progress percent must be between 0 and 100."})

    record = ProgressRecord.objects.create(
        institution=activity.institution,
        activity=activity,
        recorded_by=actor_user,
        progress_percent=progress_percent,
        reflection=reflection.strip(),
        evidence_url=evidence_url.strip(),
    )

    activity.progress_percent = progress_percent
    if evidence_url.strip():
        activity.evidence_url = evidence_url.strip()
    if progress_percent == 0:
        activity.status = DevelopmentActivity.Status.NOT_STARTED
    elif progress_percent < 100:
        activity.status = DevelopmentActivity.Status.IN_PROGRESS
    else:
        activity.status = DevelopmentActivity.Status.COMPLETED
    activity.save(update_fields=["progress_percent", "status", "evidence_url", "updated_at"])

    # Auto-complete plan if all activities in plan are completed
    plan = activity.plan
    all_acts = list(plan.activities.all())
    if all_acts and all(a.status == DevelopmentActivity.Status.COMPLETED for a in all_acts):
        plan.status = DevelopmentPlan.Status.COMPLETED
        plan.save(update_fields=["status", "updated_at"])
    elif plan.status == DevelopmentPlan.Status.COMPLETED and progress_percent < 100:
        plan.status = DevelopmentPlan.Status.ACTIVE
        plan.save(update_fields=["status", "updated_at"])

    log_audit_event(
        action="DEVELOPMENT_PROGRESS_RECORDED",
        entity_type="ProgressRecord",
        entity_id=record.id,
        institution=activity.institution,
        actor_user=actor_user,
        after={"activity_id": str(activity.id), "progress_percent": progress_percent, "status": activity.status},
        request=request,
    )
    return record
