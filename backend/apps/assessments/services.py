"""Phase 2 services: categories, dimensions, question bank, scoring, versioning & publishing."""
from decimal import Decimal
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.assessments.models import (
    AssessmentCategory,
    AssessmentDimension,
    AssessmentTemplate,
    AssessmentVersion,
    DimensionSkillTag,
    LifecycleStatus,
    MeasurementFamily,
    Question,
    QuestionDimension,
    QuestionOption,
    QuestionRubric,
    SkillTag,
    VersionQuestion,
)
from apps.audit.services import log_audit_event
from apps.tenancy.models import Institution

STARTER_CATALOGUE = [
    (
        "Technical Competency",
        "Core software engineering, computing, and systems disciplines.",
        MeasurementFamily.DEMONSTRATED_PERFORMANCE,
        [
            ("PROG", "Programming & Computational Thinking"),
            ("DSA", "Data Structures & Algorithms"),
            ("DBMS", "Database & Data Engineering"),
            ("AIML", "AI & Data Science"),
            ("CLOUDSEC", "Networks, Cloud & Cybersecurity"),
            ("SE_TEST", "Software Engineering & Testing"),
            ("WEBMOB", "Web & Mobile Development"),
        ],
    ),
    (
        "Cognitive & Problem Solving",
        "Analytical, logical, numerical, and debugging reasoning.",
        MeasurementFamily.DEMONSTRATED_PERFORMANCE,
        [
            ("LOGIC", "Logical Reasoning"),
            ("ANALYTICAL", "Analytical Reasoning"),
            ("NUMERICAL", "Numerical Ability"),
            ("DEBUG", "Problem Solving & Debugging"),
        ],
    ),
    (
        "Professional & Soft Skills",
        "Self-reported proficiency and behavioural communication dimensions.",
        MeasurementFamily.SELF_REPORTED_PROFICIENCY,
        [
            ("COMM", "Communication"),
            ("TEAM", "Teamwork & Collaboration"),
            ("LEAD", "Leadership & Initiative"),
            ("ADAPT", "Adaptability & Time Management"),
            ("ETHICS", "Professional Ethics"),
        ],
    ),
    (
        "Career Interests",
        "Stated domain preferences for career and learning pathway alignment.",
        MeasurementFamily.STATED_INTEREST,
        [
            ("INT_SDE", "Software Development"),
            ("INT_AIML", "AI / ML Engineering"),
            ("INT_DATA", "Data Analytics"),
            ("INT_CYBER", "Cybersecurity"),
            ("INT_CLOUD", "Cloud / DevOps"),
            ("INT_UIUX", "UI / UX & Product"),
            ("INT_RES", "Research & Academia"),
        ],
    ),
]


@transaction.atomic
def seed_starter_catalogue(*, institution: Institution, actor_user=None, request=None) -> dict:
    created_categories = 0
    created_dimensions = 0
    for cat_idx, (cat_name, cat_desc, family, dims) in enumerate(STARTER_CATALOGUE, start=1):
        cat, cat_created = AssessmentCategory.objects.get_or_create(
            institution=institution,
            name=cat_name,
            defaults={"description": cat_desc, "sort_order": cat_idx},
        )
        if cat_created:
            created_categories += 1
        for dim_idx, (code, name) in enumerate(dims, start=1):
            _, dim_created = AssessmentDimension.objects.get_or_create(
                institution=institution,
                code=code,
                defaults={
                    "category": cat,
                    "name": name,
                    "measurement_family": family,
                    "sort_order": dim_idx,
                },
            )
            if dim_created:
                created_dimensions += 1

    log_audit_event(
        action="ASSESSMENT_STARTER_CATALOGUE_SEEDED",
        entity_type="Institution",
        entity_id=institution.id,
        institution=institution,
        actor_user=actor_user,
        after={"created_categories": created_categories, "created_dimensions": created_dimensions},
        request=request,
    )
    return {"created_categories": created_categories, "created_dimensions": created_dimensions}


@transaction.atomic
def create_category(*, institution: Institution, name: str, description: str = "", sort_order: int = 0, actor_user=None, request=None) -> AssessmentCategory:
    if AssessmentCategory.objects.filter(institution=institution, name__iexact=name.strip()).exists():
        raise ValidationError({"name": "An assessment category with this name already exists."})
    cat = AssessmentCategory.objects.create(
        institution=institution,
        name=name.strip(),
        description=description.strip(),
        sort_order=sort_order,
    )
    log_audit_event(
        action="ASSESSMENT_CATEGORY_CREATED",
        entity_type="AssessmentCategory",
        entity_id=cat.id,
        institution=institution,
        actor_user=actor_user,
        after={"name": cat.name, "sort_order": cat.sort_order},
        request=request,
    )
    return cat


@transaction.atomic
def update_category(*, category: AssessmentCategory, data: dict, actor_user=None, request=None) -> AssessmentCategory:
    before = {"name": category.name, "status": category.status, "sort_order": category.sort_order}
    if "name" in data:
        new_name = data["name"].strip()
        if AssessmentCategory.objects.filter(institution=category.institution).exclude(id=category.id).filter(name__iexact=new_name).exists():
            raise ValidationError({"name": "An assessment category with this name already exists."})
        category.name = new_name
    if "description" in data:
        category.description = data["description"].strip()
    if "sort_order" in data:
        category.sort_order = data["sort_order"]
    if "status" in data:
        category.status = data["status"]
    category.save()
    log_audit_event(
        action="ASSESSMENT_CATEGORY_UPDATED",
        entity_type="AssessmentCategory",
        entity_id=category.id,
        institution=category.institution,
        actor_user=actor_user,
        before=before,
        after={"name": category.name, "status": category.status, "sort_order": category.sort_order},
        request=request,
    )
    return category


def _sync_dimension_tags(dimension: AssessmentDimension, skill_tag_names: list[str] | None) -> None:
    if skill_tag_names is None:
        return
    DimensionSkillTag.objects.filter(dimension=dimension).delete()
    seen: set[str] = set()
    for raw_name in skill_tag_names:
        cleaned = raw_name.strip()
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        tag, _ = SkillTag.objects.get_or_create(
            institution=dimension.institution,
            name=cleaned,
        )
        DimensionSkillTag.objects.create(dimension=dimension, skill_tag=tag)


@transaction.atomic
def create_dimension(
    *,
    institution: Institution,
    category_id,
    code: str,
    name: str,
    description: str = "",
    measurement_family: str = MeasurementFamily.DEMONSTRATED_PERFORMANCE,
    interpretation_guidance: str = "",
    sort_order: int = 0,
    skill_tags: list[str] | None = None,
    actor_user=None,
    request=None,
) -> AssessmentDimension:
    category = AssessmentCategory.objects.filter(institution=institution, id=category_id).first()
    if category is None:
        raise ValidationError({"category_id": "Assessment category not found in active institution."})
    norm_code = code.strip().upper()
    if AssessmentDimension.objects.filter(institution=institution, code__iexact=norm_code).exists():
        raise ValidationError({"code": f"Dimension code '{norm_code}' already exists in this institution."})

    dim = AssessmentDimension.objects.create(
        institution=institution,
        category=category,
        code=norm_code,
        name=name.strip(),
        description=description.strip(),
        measurement_family=measurement_family,
        interpretation_guidance=interpretation_guidance.strip(),
        sort_order=sort_order,
    )
    _sync_dimension_tags(dim, skill_tags)
    log_audit_event(
        action="ASSESSMENT_DIMENSION_CREATED",
        entity_type="AssessmentDimension",
        entity_id=dim.id,
        institution=institution,
        actor_user=actor_user,
        after={"code": dim.code, "name": dim.name, "measurement_family": dim.measurement_family},
        request=request,
    )
    return dim


@transaction.atomic
def update_dimension(*, dimension: AssessmentDimension, data: dict, actor_user=None, request=None) -> AssessmentDimension:
    before = {
        "code": dimension.code,
        "name": dimension.name,
        "measurement_family": dimension.measurement_family,
        "status": dimension.status,
    }
    if "category_id" in data:
        cat = AssessmentCategory.objects.filter(institution=dimension.institution, id=data["category_id"]).first()
        if cat is None:
            raise ValidationError({"category_id": "Assessment category not found in active institution."})
        dimension.category = cat
    if "code" in data:
        new_code = data["code"].strip().upper()
        if AssessmentDimension.objects.filter(institution=dimension.institution).exclude(id=dimension.id).filter(code__iexact=new_code).exists():
            raise ValidationError({"code": f"Dimension code '{new_code}' already exists in this institution."})
        dimension.code = new_code
    if "name" in data:
        dimension.name = data["name"].strip()
    if "description" in data:
        dimension.description = data["description"].strip()
    if "measurement_family" in data:
        dimension.measurement_family = data["measurement_family"]
    if "interpretation_guidance" in data:
        dimension.interpretation_guidance = data["interpretation_guidance"].strip()
    if "sort_order" in data:
        dimension.sort_order = data["sort_order"]
    if "status" in data:
        dimension.status = data["status"]
    dimension.save()

    if "skill_tags" in data:
        _sync_dimension_tags(dimension, data["skill_tags"])

    log_audit_event(
        action="ASSESSMENT_DIMENSION_UPDATED",
        entity_type="AssessmentDimension",
        entity_id=dimension.id,
        institution=dimension.institution,
        actor_user=actor_user,
        before=before,
        after={
            "code": dimension.code,
            "name": dimension.name,
            "measurement_family": dimension.measurement_family,
            "status": dimension.status,
        },
        request=request,
    )
    return dimension


def _validate_question_scoring_and_dimensions(
    *,
    institution: Institution,
    question_type: str,
    measurement_family: str,
    scoring_method: str,
    max_marks: Decimal,
    negative_marks: Decimal,
    scoring_config: dict,
    options: list[dict],
    rubric: dict | None,
    dimension_links: list[dict],
) -> list[tuple[AssessmentDimension, Decimal]]:
    max_marks = Decimal(str(max_marks))
    negative_marks = Decimal(str(negative_marks))
    if max_marks < 0 or negative_marks < 0:
        raise ValidationError({"max_marks": "Marks and negative marks cannot be negative."})

    # Guardrail: Never label Likert / Self-Rating items as objective demonstrated performance
    if question_type in (Question.QuestionType.LIKERT, Question.QuestionType.SELF_RATING):
        if measurement_family == MeasurementFamily.DEMONSTRATED_PERFORMANCE:
            raise ValidationError({
                "measurement_family": "Likert and Self-Rating items cannot be classified as Demonstrated Performance. Use Self-Reported Proficiency or Stated Career Interest."
            })

    if question_type in (Question.QuestionType.SINGLE_MCQ, Question.QuestionType.TRUE_FALSE):
        if len(options) < 2:
            raise ValidationError({"options": "At least 2 options are required."})
        correct_count = sum(1 for o in options if o.get("is_correct"))
        if correct_count != 1:
            raise ValidationError({"options": "Single-choice MCQ and True/False items must have exactly 1 correct option."})

    elif question_type == Question.QuestionType.MULTIPLE_MCQ:
        if len(options) < 2:
            raise ValidationError({"options": "At least 2 options are required."})
        correct_count = sum(1 for o in options if o.get("is_correct"))
        if correct_count < 1:
            raise ValidationError({"options": "Multiple-choice MCQ items must have at least 1 correct option."})

    elif question_type in (
        Question.QuestionType.LIKERT,
        Question.QuestionType.SELF_RATING,
        Question.QuestionType.SITUATIONAL_JUDGEMENT,
    ):
        if len(options) < 2:
            raise ValidationError({"options": "Scale/judgement items require at least 2 answer options."})

    elif question_type == Question.QuestionType.NUMERIC:
        if "correct_value" not in scoring_config:
            raise ValidationError({"scoring_config": "Numeric questions require 'correct_value' in scoring_config."})
        try:
            float(scoring_config["correct_value"])
        except (TypeError, ValueError):
            raise ValidationError({"scoring_config": "'correct_value' must be numeric."})

    elif question_type in (Question.QuestionType.DESCRIPTIVE, Question.QuestionType.CODING):
        if scoring_method == Question.ScoringMethod.RUBRIC and not rubric:
            raise ValidationError({"rubric": "Rubric-scored descriptive/coding questions require rubric details."})

    if not dimension_links:
        raise ValidationError({"dimensions": "Link the question to at least one Assessment Dimension."})

    resolved_dims: list[tuple[AssessmentDimension, Decimal]] = []
    seen_dim_ids: set = set()
    for item in dimension_links:
        dim = AssessmentDimension.objects.filter(institution=institution, id=item["dimension_id"]).first()
        if dim is None:
            raise ValidationError({"dimensions": "One or more dimensions were not found in the active institution."})
        if dim.id in seen_dim_ids:
            raise ValidationError({"dimensions": "Duplicate dimension in question dimension links."})
        if dim.measurement_family != measurement_family:
            raise ValidationError({
                "dimensions": f"Measurement family mismatch: question is '{measurement_family}' while dimension '{dim.code}' is '{dim.measurement_family}'."
            })
        weight = Decimal(str(item.get("weight", "1.00")))
        if weight <= 0:
            raise ValidationError({"dimensions": "Dimension weight must be greater than 0."})
        seen_dim_ids.add(dim.id)
        resolved_dims.append((dim, weight))

    return resolved_dims


@transaction.atomic
def create_question(*, institution: Institution, data: dict, actor_user, request=None) -> Question:
    norm_code = data["question_code"].strip().upper()
    if Question.objects.filter(institution=institution, question_code__iexact=norm_code).exists():
        raise ValidationError({"question_code": f"Question code '{norm_code}' already exists in this institution."})

    options_data = data.get("options", [])
    rubric_data = data.get("rubric")
    dim_links = data.get("dimensions", [])

    resolved_dims = _validate_question_scoring_and_dimensions(
        institution=institution,
        question_type=data["question_type"],
        measurement_family=data["measurement_family"],
        scoring_method=data["scoring_method"],
        max_marks=data["max_marks"],
        negative_marks=data["negative_marks"],
        scoring_config=data.get("scoring_config") or {},
        options=options_data,
        rubric=rubric_data,
        dimension_links=dim_links,
    )

    q = Question.objects.create(
        institution=institution,
        question_code=norm_code,
        question_type=data["question_type"],
        prompt=data["prompt"].strip(),
        difficulty=data["difficulty"],
        measurement_family=data["measurement_family"],
        scoring_method=data["scoring_method"],
        max_marks=data["max_marks"],
        negative_marks=data["negative_marks"],
        scoring_config=data.get("scoring_config") or {},
        tags=data.get("tags") or [],
        status=data.get("status", LifecycleStatus.ACTIVE),
        created_by=actor_user,
    )

    for idx, opt in enumerate(options_data, start=1):
        QuestionOption.objects.create(
            question=q,
            option_key=opt["option_key"].strip().upper(),
            option_text=opt["option_text"].strip(),
            display_order=opt.get("display_order", idx),
            is_correct=bool(opt.get("is_correct", False)),
            points_override=opt.get("points_override"),
            feedback=opt.get("feedback", ""),
        )

    if rubric_data:
        QuestionRubric.objects.create(
            question=q,
            rubric_json=rubric_data.get("rubric_json") or {},
            max_marks=rubric_data.get("max_marks", q.max_marks),
            evaluator_guidance=rubric_data.get("evaluator_guidance", ""),
        )

    for dim, weight in resolved_dims:
        QuestionDimension.objects.create(question=q, dimension=dim, weight=weight)

    log_audit_event(
        action="QUESTION_CREATED",
        entity_type="Question",
        entity_id=q.id,
        institution=institution,
        actor_user=actor_user,
        after={
            "question_code": q.question_code,
            "question_type": q.question_type,
            "measurement_family": q.measurement_family,
            "max_marks": str(q.max_marks),
        },
        request=request,
    )
    return q


@transaction.atomic
def update_question(*, question: Question, data: dict, actor_user=None, request=None) -> Question:
    before = {
        "question_code": question.question_code,
        "status": question.status,
        "max_marks": str(question.max_marks),
    }

    if "question_code" in data:
        new_code = data["question_code"].strip().upper()
        if Question.objects.filter(institution=question.institution).exclude(id=question.id).filter(question_code__iexact=new_code).exists():
            raise ValidationError({"question_code": f"Question code '{new_code}' already exists in this institution."})
        question.question_code = new_code

    q_type = data.get("question_type", question.question_type)
    m_family = data.get("measurement_family", question.measurement_family)
    s_method = data.get("scoring_method", question.scoring_method)
    max_m = data.get("max_marks", question.max_marks)
    neg_m = data.get("negative_marks", question.negative_marks)
    s_conf = data.get("scoring_config", question.scoring_config)

    options_data = data.get("options")
    if options_data is None:
        options_data = [
            {
                "option_key": o.option_key,
                "option_text": o.option_text,
                "display_order": o.display_order,
                "is_correct": o.is_correct,
                "points_override": o.points_override,
                "feedback": o.feedback,
            }
            for o in question.options.all()
        ]

    rubric_data = data.get("rubric")
    if rubric_data is None and hasattr(question, "rubric"):
        rubric_data = {
            "rubric_json": question.rubric.rubric_json,
            "max_marks": question.rubric.max_marks,
            "evaluator_guidance": question.rubric.evaluator_guidance,
        }

    dim_links = data.get("dimensions")
    if dim_links is None:
        dim_links = [
            {"dimension_id": qd.dimension_id, "weight": qd.weight}
            for qd in question.question_dimensions.all()
        ]

    resolved_dims = _validate_question_scoring_and_dimensions(
        institution=question.institution,
        question_type=q_type,
        measurement_family=m_family,
        scoring_method=s_method,
        max_marks=max_m,
        negative_marks=neg_m,
        scoring_config=s_conf or {},
        options=options_data,
        rubric=rubric_data,
        dimension_links=dim_links,
    )

    question.question_type = q_type
    question.measurement_family = m_family
    question.scoring_method = s_method
    question.max_marks = max_m
    question.negative_marks = neg_m
    question.scoring_config = s_conf or {}
    if "prompt" in data:
        question.prompt = data["prompt"].strip()
    if "difficulty" in data:
        question.difficulty = data["difficulty"]
    if "tags" in data:
        question.tags = data["tags"] or []
    if "status" in data:
        question.status = data["status"]
    question.save()

    if "options" in data:
        QuestionOption.objects.filter(question=question).delete()
        for idx, opt in enumerate(options_data, start=1):
            QuestionOption.objects.create(
                question=question,
                option_key=opt["option_key"].strip().upper(),
                option_text=opt["option_text"].strip(),
                display_order=opt.get("display_order", idx),
                is_correct=bool(opt.get("is_correct", False)),
                points_override=opt.get("points_override"),
                feedback=opt.get("feedback", ""),
            )

    if "rubric" in data:
        QuestionRubric.objects.filter(question=question).delete()
        if rubric_data:
            QuestionRubric.objects.create(
                question=question,
                rubric_json=rubric_data.get("rubric_json") or {},
                max_marks=rubric_data.get("max_marks", question.max_marks),
                evaluator_guidance=rubric_data.get("evaluator_guidance", ""),
            )

    if "dimensions" in data:
        QuestionDimension.objects.filter(question=question).delete()
        for dim, weight in resolved_dims:
            QuestionDimension.objects.create(question=question, dimension=dim, weight=weight)

    log_audit_event(
        action="QUESTION_UPDATED",
        entity_type="Question",
        entity_id=question.id,
        institution=question.institution,
        actor_user=actor_user,
        before=before,
        after={"question_code": question.question_code, "status": question.status, "max_marks": str(question.max_marks)},
        request=request,
    )
    return question


@transaction.atomic
def create_assessment_template(
    *,
    institution: Institution,
    name: str,
    description: str = "",
    duration_minutes: int = 60,
    max_attempts: int = 1,
    instructions: str = "",
    actor_user,
    request=None,
) -> AssessmentTemplate:
    if AssessmentTemplate.objects.filter(institution=institution, name__iexact=name.strip()).exists():
        raise ValidationError({"name": "An assessment template with this name already exists."})

    template = AssessmentTemplate.objects.create(
        institution=institution,
        name=name.strip(),
        description=description.strip(),
        created_by=actor_user,
    )
    v1 = AssessmentVersion.objects.create(
        institution=institution,
        template=template,
        version_no=1,
        duration_minutes=duration_minutes,
        max_attempts=max_attempts,
        instructions=instructions.strip(),
        status=AssessmentVersion.Status.DRAFT,
    )
    log_audit_event(
        action="ASSESSMENT_TEMPLATE_CREATED",
        entity_type="AssessmentTemplate",
        entity_id=template.id,
        institution=institution,
        actor_user=actor_user,
        after={"name": template.name, "initial_version_id": str(v1.id)},
        request=request,
    )
    return template


def _build_question_snapshot(question: Question) -> dict:
    """Create immutable snapshot dictionary of question, options, rubric, and dimension links."""
    return {
        "question_id": str(question.id),
        "question_code": question.question_code,
        "question_type": question.question_type,
        "prompt": question.prompt,
        "difficulty": question.difficulty,
        "measurement_family": question.measurement_family,
        "scoring_method": question.scoring_method,
        "scoring_config": question.scoring_config,
        "tags": question.tags,
        "options": [
            {
                "id": str(o.id),
                "option_key": o.option_key,
                "option_text": o.option_text,
                "display_order": o.display_order,
                "is_correct": o.is_correct,
                "points_override": str(o.points_override) if o.points_override is not None else None,
                "feedback": o.feedback,
            }
            for o in question.options.all()
        ],
        "rubric": (
            {
                "rubric_json": question.rubric.rubric_json,
                "max_marks": str(question.rubric.max_marks),
                "evaluator_guidance": question.rubric.evaluator_guidance,
            }
            if hasattr(question, "rubric")
            else None
        ),
        "dimensions": [
            {
                "dimension_id": str(qd.dimension_id),
                "code": qd.dimension.code,
                "name": qd.dimension.name,
                "measurement_family": qd.dimension.measurement_family,
                "weight": str(qd.weight),
            }
            for qd in question.question_dimensions.select_related("dimension").all()
        ],
    }


@transaction.atomic
def update_draft_version(
    *,
    version: AssessmentVersion,
    data: dict,
    actor_user=None,
    request=None,
) -> AssessmentVersion:
    if version.status != AssessmentVersion.Status.DRAFT:
        raise ValidationError({
            "status": "Published or archived assessment versions are immutable. Create a new draft version to make changes."
        })

    for field in ("duration_minutes", "max_attempts", "instructions", "scoring_config", "randomize_questions", "randomize_options"):
        if field in data:
            setattr(version, field, data[field])

    if "items" in data:
        items = data["items"]
        seen_q_ids: set = set()
        VersionQuestion.objects.filter(assessment_version=version).delete()
        total_marks = Decimal("0.00")
        for idx, item in enumerate(items, start=1):
            q = Question.objects.filter(
                institution=version.institution,
                id=item["question_id"],
                status=LifecycleStatus.ACTIVE,
            ).first()
            if q is None:
                raise ValidationError({"items": "Active question not found in the active institution."})
            if q.id in seen_q_ids:
                raise ValidationError({"items": f"Duplicate question '{q.question_code}' in assessment version."})
            seen_q_ids.add(q.id)

            marks = Decimal(str(item.get("marks", q.max_marks)))
            neg_marks = Decimal(str(item.get("negative_marks", q.negative_marks)))
            if marks < 0 or neg_marks < 0:
                raise ValidationError({"items": "Marks and negative marks must be non-negative."})
            VersionQuestion.objects.create(
                assessment_version=version,
                question=q,
                marks=marks,
                negative_marks=neg_marks,
                sequence=idx,
                required=bool(item.get("required", True)),
            )
            total_marks += marks
        version.total_marks = total_marks

    version.save()
    log_audit_event(
        action="ASSESSMENT_VERSION_DRAFT_UPDATED",
        entity_type="AssessmentVersion",
        entity_id=version.id,
        institution=version.institution,
        actor_user=actor_user,
        after={
            "template": version.template.name,
            "version_no": version.version_no,
            "total_marks": str(version.total_marks),
            "question_count": version.version_questions.count(),
        },
        request=request,
    )
    return version


@transaction.atomic
def publish_assessment_version(*, version: AssessmentVersion, actor_user=None, request=None) -> AssessmentVersion:
    if version.status != AssessmentVersion.Status.DRAFT:
        raise ValidationError({"status": "Only draft assessment versions can be published."})

    vqs = list(
        version.version_questions.select_related("question")
        .prefetch_related("question__options", "question__question_dimensions__dimension")
        .order_by("sequence")
    )
    if not vqs:
        raise ValidationError({"items": "Add at least one question before publishing an assessment version."})

    total_marks = Decimal("0.00")
    for vq in vqs:
        vq.question_snapshot = _build_question_snapshot(vq.question)
        vq.save(update_fields=["question_snapshot"])
        total_marks += vq.marks

    version.total_marks = total_marks
    version.status = AssessmentVersion.Status.PUBLISHED
    version.published_at = timezone.now()
    version.save()

    log_audit_event(
        action="ASSESSMENT_VERSION_PUBLISHED",
        entity_type="AssessmentVersion",
        entity_id=version.id,
        institution=version.institution,
        actor_user=actor_user,
        after={
            "template": version.template.name,
            "version_no": version.version_no,
            "total_marks": str(version.total_marks),
            "question_count": len(vqs),
        },
        request=request,
    )
    return version


@transaction.atomic
def clone_version_to_draft(*, source_version: AssessmentVersion, actor_user=None, request=None) -> AssessmentVersion:
    template = source_version.template
    max_ver = template.versions.aggregate(m=Max("version_no"))["m"] or 0
    next_ver = AssessmentVersion.objects.create(
        institution=source_version.institution,
        template=template,
        version_no=max_ver + 1,
        duration_minutes=source_version.duration_minutes,
        max_attempts=source_version.max_attempts,
        instructions=source_version.instructions,
        scoring_config=source_version.scoring_config,
        randomize_questions=source_version.randomize_questions,
        randomize_options=source_version.randomize_options,
        total_marks=source_version.total_marks,
        status=AssessmentVersion.Status.DRAFT,
    )
    for vq in source_version.version_questions.order_by("sequence"):
        VersionQuestion.objects.create(
            assessment_version=next_ver,
            question=vq.question,
            marks=vq.marks,
            negative_marks=vq.negative_marks,
            sequence=vq.sequence,
            required=vq.required,
        )

    log_audit_event(
        action="ASSESSMENT_VERSION_CLONED",
        entity_type="AssessmentVersion",
        entity_id=next_ver.id,
        institution=source_version.institution,
        actor_user=actor_user,
        after={
            "template": template.name,
            "source_version_no": source_version.version_no,
            "new_version_no": next_ver.version_no,
        },
        request=request,
    )
    return next_ver

