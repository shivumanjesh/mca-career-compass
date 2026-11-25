"""Serializers for Phase 2 assessment administration APIs."""
from decimal import Decimal
from rest_framework import serializers
from apps.assessments.models import (
    AssessmentAssignment,
    AssessmentCategory,
    AssessmentDimension,
    AssessmentTemplate,
    AssessmentVersion,
    LifecycleStatus,
    MeasurementFamily,
    Question,
    QuestionOption,
    QuestionRubric,
    VersionQuestion,
)


class AssessmentCategorySerializer(serializers.ModelSerializer):
    dimension_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = AssessmentCategory
        fields = ["id", "name", "description", "sort_order", "status", "dimension_count", "created_at", "updated_at"]


class AssessmentCategoryWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    sort_order = serializers.IntegerField(min_value=0, required=False, default=0)
    status = serializers.ChoiceField(choices=LifecycleStatus.choices, required=False, default=LifecycleStatus.ACTIVE)


class AssessmentDimensionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    skill_tags = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentDimension
        fields = [
            "id",
            "category_id",
            "category_name",
            "code",
            "name",
            "description",
            "measurement_family",
            "interpretation_guidance",
            "sort_order",
            "status",
            "skill_tags",
            "created_at",
            "updated_at",
        ]

    def get_skill_tags(self, obj: AssessmentDimension) -> list[str]:
        return [dt.skill_tag.name for dt in obj.dimension_tags.all()]


class AssessmentDimensionWriteSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    code = serializers.CharField(max_length=60)
    name = serializers.CharField(max_length=160)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    measurement_family = serializers.ChoiceField(
        choices=MeasurementFamily.choices,
        default=MeasurementFamily.DEMONSTRATED_PERFORMANCE,
    )
    interpretation_guidance = serializers.CharField(required=False, allow_blank=True, default="")
    sort_order = serializers.IntegerField(min_value=0, required=False, default=0)
    status = serializers.ChoiceField(choices=LifecycleStatus.choices, required=False, default=LifecycleStatus.ACTIVE)
    skill_tags = serializers.ListField(child=serializers.CharField(max_length=80), required=False)


class QuestionOptionInputSerializer(serializers.Serializer):
    option_key = serializers.CharField(max_length=20)
    option_text = serializers.CharField()
    display_order = serializers.IntegerField(min_value=1, required=False, default=1)
    is_correct = serializers.BooleanField(required=False, default=False)
    points_override = serializers.DecimalField(max_digits=7, decimal_places=2, required=False, allow_null=True)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")


class QuestionRubricInputSerializer(serializers.Serializer):
    rubric_json = serializers.JSONField(default=dict)
    max_marks = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0)
    evaluator_guidance = serializers.CharField(required=False, allow_blank=True, default="")


class QuestionDimensionLinkInputSerializer(serializers.Serializer):
    dimension_id = serializers.UUIDField()
    weight = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=Decimal("1.00"))


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "option_key", "option_text", "display_order", "is_correct", "points_override", "feedback"]


class QuestionRubricSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionRubric
        fields = ["id", "rubric_json", "max_marks", "evaluator_guidance"]


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    rubric = QuestionRubricSerializer(read_only=True)
    dimensions = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "question_code",
            "question_type",
            "prompt",
            "difficulty",
            "measurement_family",
            "scoring_method",
            "max_marks",
            "negative_marks",
            "scoring_config",
            "tags",
            "status",
            "options",
            "rubric",
            "dimensions",
            "created_by_email",
            "created_at",
            "updated_at",
        ]

    def get_dimensions(self, obj: Question) -> list[dict]:
        return [
            {
                "dimension_id": str(qd.dimension_id),
                "code": qd.dimension.code,
                "name": qd.dimension.name,
                "measurement_family": qd.dimension.measurement_family,
                "weight": str(qd.weight),
            }
            for qd in obj.question_dimensions.all()
        ]


class QuestionWriteSerializer(serializers.Serializer):
    question_code = serializers.CharField(max_length=60)
    question_type = serializers.ChoiceField(choices=Question.QuestionType.choices)
    prompt = serializers.CharField()
    difficulty = serializers.ChoiceField(choices=Question.Difficulty.choices, default=Question.Difficulty.MEDIUM)
    measurement_family = serializers.ChoiceField(
        choices=MeasurementFamily.choices,
        default=MeasurementFamily.DEMONSTRATED_PERFORMANCE,
    )
    scoring_method = serializers.ChoiceField(
        choices=Question.ScoringMethod.choices,
        default=Question.ScoringMethod.EXACT,
    )
    max_marks = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0, default=Decimal("1.00"))
    negative_marks = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0, default=Decimal("0.00"))
    scoring_config = serializers.JSONField(required=False, default=dict)
    tags = serializers.ListField(child=serializers.CharField(max_length=60), required=False, default=list)
    status = serializers.ChoiceField(choices=LifecycleStatus.choices, required=False, default=LifecycleStatus.ACTIVE)
    options = QuestionOptionInputSerializer(many=True, required=False, default=list)
    rubric = QuestionRubricInputSerializer(required=False, allow_null=True)
    dimensions = QuestionDimensionLinkInputSerializer(many=True, min_length=1)


class VersionQuestionSerializer(serializers.ModelSerializer):
    question_code = serializers.CharField(source="question.question_code", read_only=True)
    question_type = serializers.CharField(source="question.question_type", read_only=True)
    prompt = serializers.CharField(source="question.prompt", read_only=True)
    measurement_family = serializers.CharField(source="question.measurement_family", read_only=True)

    class Meta:
        model = VersionQuestion
        fields = [
            "id",
            "question_id",
            "question_code",
            "question_type",
            "prompt",
            "measurement_family",
            "marks",
            "negative_marks",
            "sequence",
            "required",
            "question_snapshot",
        ]


class AssessmentVersionSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    question_count = serializers.SerializerMethodField()
    version_questions = VersionQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = AssessmentVersion
        fields = [
            "id",
            "template_id",
            "template_name",
            "version_no",
            "duration_minutes",
            "max_attempts",
            "instructions",
            "scoring_config",
            "randomize_questions",
            "randomize_options",
            "total_marks",
            "status",
            "published_at",
            "question_count",
            "version_questions",
            "created_at",
            "updated_at",
        ]

    def get_question_count(self, obj: AssessmentVersion) -> int:
        return obj.version_questions.count()


class AssessmentTemplateSerializer(serializers.ModelSerializer):
    versions = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentTemplate
        fields = ["id", "name", "description", "status", "versions", "created_at", "updated_at"]

    def get_versions(self, obj: AssessmentTemplate) -> list[dict]:
        return [
            {
                "id": str(v.id),
                "version_no": v.version_no,
                "status": v.status,
                "duration_minutes": v.duration_minutes,
                "max_attempts": v.max_attempts,
                "total_marks": str(v.total_marks),
                "question_count": v.version_questions.count(),
                "published_at": v.published_at.isoformat() if v.published_at else None,
            }
            for v in obj.versions.all().order_by("-version_no")
        ]


class AssessmentTemplateCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    duration_minutes = serializers.IntegerField(min_value=1, max_value=600, required=False, default=60)
    max_attempts = serializers.IntegerField(min_value=1, max_value=20, required=False, default=1)
    instructions = serializers.CharField(required=False, allow_blank=True, default="")


class AssessmentTemplateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=LifecycleStatus.choices, required=False)


class VersionQuestionItemInputSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    marks = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0, required=False)
    negative_marks = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0, required=False)
    required = serializers.BooleanField(required=False, default=True)


class AssessmentVersionDraftUpdateSerializer(serializers.Serializer):
    duration_minutes = serializers.IntegerField(min_value=1, max_value=600, required=False)
    max_attempts = serializers.IntegerField(min_value=1, max_value=20, required=False)
    instructions = serializers.CharField(required=False, allow_blank=True)
    scoring_config = serializers.JSONField(required=False)
    randomize_questions = serializers.BooleanField(required=False)
    randomize_options = serializers.BooleanField(required=False)
    items = VersionQuestionItemInputSerializer(many=True, required=False)


class AssessmentAssignmentSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="assessment_version.template.name", read_only=True)
    version_no = serializers.IntegerField(source="assessment_version.version_no", read_only=True)
    duration_minutes = serializers.IntegerField(source="assessment_version.duration_minutes", read_only=True)
    total_marks = serializers.DecimalField(
        source="assessment_version.total_marks", max_digits=9, decimal_places=2, read_only=True
    )
    cohort_label = serializers.SerializerMethodField()
    student_label = serializers.SerializerMethodField()
    attempt_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = AssessmentAssignment
        fields = [
            "id",
            "assessment_version_id",
            "template_name",
            "version_no",
            "duration_minutes",
            "total_marks",
            "cohort_id",
            "cohort_label",
            "student_profile_id",
            "student_label",
            "opens_at",
            "closes_at",
            "results_released",
            "status",
            "attempt_count",
            "created_at",
        ]

    def get_cohort_label(self, obj: AssessmentAssignment) -> str | None:
        return str(obj.cohort) if obj.cohort else None

    def get_student_label(self, obj: AssessmentAssignment) -> str | None:
        return str(obj.student_profile) if obj.student_profile else None


class AssessmentAssignmentCreateSerializer(serializers.Serializer):
    assessment_version_id = serializers.UUIDField()
    cohort_id = serializers.UUIDField(required=False, allow_null=True)
    student_profile_id = serializers.UUIDField(required=False, allow_null=True)
    opens_at = serializers.DateTimeField()
    closes_at = serializers.DateTimeField()
    results_released = serializers.BooleanField(required=False, default=False)


class AssessmentAssignmentUpdateSerializer(serializers.Serializer):
    opens_at = serializers.DateTimeField(required=False)
    closes_at = serializers.DateTimeField(required=False)
    results_released = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(choices=AssessmentAssignment.Status.choices, required=False)

