"""Serializers for student profile endpoints."""
from rest_framework import serializers
from apps.students.models import StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    membership_id = serializers.UUIDField(source="membership.id", read_only=True)
    email = serializers.EmailField(source="membership.user.email", read_only=True)
    first_name = serializers.CharField(source="membership.user.first_name", read_only=True)
    last_name = serializers.CharField(source="membership.user.last_name", read_only=True)
    full_name = serializers.CharField(source="membership.user.full_name", read_only=True)
    cohort_label = serializers.SerializerMethodField()
    programme_code = serializers.SerializerMethodField()
    batch_name = serializers.SerializerMethodField()
    semester = serializers.SerializerMethodField()
    section = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "membership_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "registration_no",
            "cohort_id",
            "cohort_label",
            "programme_code",
            "batch_name",
            "semester",
            "section",
            "admission_year",
            "phone",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_cohort_label(self, obj: StudentProfile) -> str | None:
        return str(obj.cohort) if obj.cohort else None

    def get_programme_code(self, obj: StudentProfile) -> str | None:
        return obj.cohort.programme.code if obj.cohort else None

    def get_batch_name(self, obj: StudentProfile) -> str | None:
        return obj.cohort.batch_name if obj.cohort else None

    def get_semester(self, obj: StudentProfile) -> int | None:
        return obj.cohort.semester if obj.cohort else None

    def get_section(self, obj: StudentProfile) -> str | None:
        return obj.cohort.section if obj.cohort else None


class StudentCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    registration_no = serializers.CharField(max_length=80)
    cohort_id = serializers.UUIDField(required=False, allow_null=True)
    admission_year = serializers.IntegerField(min_value=1990, max_value=2100, required=False, allow_null=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=StudentProfile.Status.choices, required=False, default=StudentProfile.Status.ACTIVE)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=10)


class StudentUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    registration_no = serializers.CharField(max_length=80, required=False)
    cohort_id = serializers.UUIDField(required=False, allow_null=True)
    admission_year = serializers.IntegerField(min_value=1990, max_value=2100, required=False, allow_null=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=StudentProfile.Status.choices, required=False)

