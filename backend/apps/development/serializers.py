"""DRF serializers for Phase 5 Student Empowerment (catalogue, plans, activities, progress)."""
from rest_framework import serializers

from apps.development.models import (
    DevelopmentActivity,
    DevelopmentPlan,
    LearningResource,
    ProgressRecord,
    ResourceType,
)


class LearningResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = [
            "id",
            "dimension_code",
            "target_domain",
            "resource_type",
            "title",
            "description",
            "provider",
            "level",
            "estimated_hours",
            "resource_url",
            "status",
            "created_at",
            "updated_at",
        ]


class LearningResourceCreateSerializer(serializers.Serializer):
    dimension_code = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    target_domain = serializers.CharField(max_length=120)
    resource_type = serializers.ChoiceField(choices=ResourceType.choices)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    provider = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    level = serializers.ChoiceField(choices=LearningResource.Level.choices, required=False, default=LearningResource.Level.INTERMEDIATE)
    estimated_hours = serializers.IntegerField(min_value=1, max_value=2000, required=False, default=10)
    resource_url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class LearningResourceUpdateSerializer(serializers.Serializer):
    dimension_code = serializers.CharField(max_length=60, required=False, allow_blank=True)
    target_domain = serializers.CharField(max_length=120, required=False)
    resource_type = serializers.ChoiceField(choices=ResourceType.choices, required=False)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    provider = serializers.CharField(max_length=120, required=False, allow_blank=True)
    level = serializers.ChoiceField(choices=LearningResource.Level.choices, required=False)
    estimated_hours = serializers.IntegerField(min_value=1, max_value=2000, required=False)
    resource_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=LearningResource.Status.choices, required=False)


class ProgressRecordSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source="recorded_by.full_name", read_only=True)
    recorded_by_email = serializers.EmailField(source="recorded_by.email", read_only=True)

    class Meta:
        model = ProgressRecord
        fields = [
            "id",
            "activity_id",
            "progress_percent",
            "reflection",
            "evidence_url",
            "recorded_by_name",
            "recorded_by_email",
            "recorded_at",
        ]


class ProgressRecordCreateSerializer(serializers.Serializer):
    progress_percent = serializers.IntegerField(min_value=0, max_value=100)
    reflection = serializers.CharField(required=False, allow_blank=True, default="")
    evidence_url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class DevelopmentActivitySerializer(serializers.ModelSerializer):
    dimension_code = serializers.SerializerMethodField()
    dimension_name = serializers.SerializerMethodField()
    resource_title = serializers.SerializerMethodField()
    resource_url = serializers.SerializerMethodField()
    progress_records = ProgressRecordSerializer(many=True, read_only=True)

    class Meta:
        model = DevelopmentActivity
        fields = [
            "id",
            "plan_id",
            "resource_id",
            "resource_title",
            "resource_url",
            "dimension_id",
            "dimension_code",
            "dimension_name",
            "title",
            "description",
            "activity_type",
            "due_date",
            "status",
            "progress_percent",
            "evidence_url",
            "progress_records",
            "created_at",
            "updated_at",
        ]

    def get_dimension_code(self, obj: DevelopmentActivity) -> str | None:
        return obj.dimension.code if obj.dimension else None

    def get_dimension_name(self, obj: DevelopmentActivity) -> str | None:
        return obj.dimension.name if obj.dimension else None

    def get_resource_title(self, obj: DevelopmentActivity) -> str | None:
        return obj.resource.title if obj.resource else None

    def get_resource_url(self, obj: DevelopmentActivity) -> str | None:
        return obj.resource.resource_url if obj.resource else None


class DevelopmentActivityCreateSerializer(serializers.Serializer):
    resource_id = serializers.UUIDField(required=False, allow_null=True)
    dimension_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    activity_type = serializers.ChoiceField(choices=ResourceType.choices, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    evidence_url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class DevelopmentPlanSerializer(serializers.ModelSerializer):
    student_id = serializers.UUIDField(source="student_profile.id", read_only=True)
    student_registration_no = serializers.CharField(source="student_profile.registration_no", read_only=True)
    student_name = serializers.CharField(source="student_profile.membership.user.full_name", read_only=True)
    student_cohort_label = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    activities = DevelopmentActivitySerializer(many=True, read_only=True)
    overall_progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = DevelopmentPlan
        fields = [
            "id",
            "student_id",
            "student_registration_no",
            "student_name",
            "student_cohort_label",
            "created_by_name",
            "title",
            "target_domain",
            "notes",
            "status",
            "start_date",
            "target_date",
            "overall_progress_percent",
            "activities",
            "created_at",
            "updated_at",
        ]

    def get_student_cohort_label(self, obj: DevelopmentPlan) -> str | None:
        return str(obj.student_profile.cohort) if obj.student_profile.cohort else None

    def get_overall_progress_percent(self, obj: DevelopmentPlan) -> int:
        acts = list(obj.activities.all())
        if not acts:
            return 0
        return round(sum(a.progress_percent for a in acts) / len(acts))


class DevelopmentPlanCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField(required=False)
    title = serializers.CharField(max_length=200)
    target_domain = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=DevelopmentPlan.Status.choices, required=False)
    start_date = serializers.DateField(required=False, allow_null=True)
    target_date = serializers.DateField(required=False, allow_null=True)


class DevelopmentPlanUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    target_domain = serializers.CharField(max_length=120, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=DevelopmentPlan.Status.choices, required=False)
    start_date = serializers.DateField(required=False, allow_null=True)
    target_date = serializers.DateField(required=False, allow_null=True)

