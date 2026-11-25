"""Serializers for faculty and cohort assignment endpoints."""
from rest_framework import serializers
from apps.faculty.models import CohortFaculty, FacultyProfile


class CohortAssignmentSerializer(serializers.ModelSerializer):
    cohort_label = serializers.SerializerMethodField()
    programme_code = serializers.CharField(source="cohort.programme.code", read_only=True)
    batch_name = serializers.CharField(source="cohort.batch_name", read_only=True)
    semester = serializers.IntegerField(source="cohort.semester", read_only=True)
    section = serializers.CharField(source="cohort.section", read_only=True)

    class Meta:
        model = CohortFaculty
        fields = [
            "id",
            "cohort_id",
            "cohort_label",
            "programme_code",
            "batch_name",
            "semester",
            "section",
            "assignment_type",
            "created_at",
        ]

    def get_cohort_label(self, obj: CohortFaculty) -> str:
        return str(obj.cohort)


class FacultyProfileSerializer(serializers.ModelSerializer):
    membership_id = serializers.UUIDField(source="membership.id", read_only=True)
    email = serializers.EmailField(source="membership.user.email", read_only=True)
    first_name = serializers.CharField(source="membership.user.first_name", read_only=True)
    last_name = serializers.CharField(source="membership.user.last_name", read_only=True)
    full_name = serializers.CharField(source="membership.user.full_name", read_only=True)
    cohort_assignments = CohortAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = FacultyProfile
        fields = [
            "id",
            "membership_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "employee_code",
            "department",
            "designation",
            "status",
            "cohort_assignments",
            "created_at",
            "updated_at",
        ]


class FacultyCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    employee_code = serializers.CharField(max_length=80, required=False, allow_blank=True, allow_null=True)
    department = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    designation = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=FacultyProfile.Status.choices, required=False, default=FacultyProfile.Status.ACTIVE)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=10)


class FacultyUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    employee_code = serializers.CharField(max_length=80, required=False, allow_blank=True, allow_null=True)
    department = serializers.CharField(max_length=120, required=False, allow_blank=True)
    designation = serializers.CharField(max_length=120, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=FacultyProfile.Status.choices, required=False)


class FacultyCohortAssignSerializer(serializers.Serializer):
    cohort_id = serializers.UUIDField()
    assignment_type = serializers.ChoiceField(
        choices=CohortFaculty.AssignmentType.choices,
        default=CohortFaculty.AssignmentType.MENTOR,
    )

