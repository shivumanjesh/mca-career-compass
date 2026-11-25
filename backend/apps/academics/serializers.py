"""Serializers for academics endpoints."""
from rest_framework import serializers
from apps.academics.models import AcademicYear, ActiveStatus, Cohort, Programme


class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
        fields = ["id", "code", "name", "level", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProgrammeWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)
    name = serializers.CharField(max_length=160)
    level = serializers.CharField(max_length=40, required=False, default="PG")
    status = serializers.ChoiceField(choices=ActiveStatus.choices, required=False, default=ActiveStatus.ACTIVE)


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["id", "name", "start_date", "end_date", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AcademicYearWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=40)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    status = serializers.ChoiceField(choices=ActiveStatus.choices, required=False, default=ActiveStatus.ACTIVE)


class CohortSerializer(serializers.ModelSerializer):
    programme_code = serializers.CharField(source="programme.code", read_only=True)
    programme_name = serializers.CharField(source="programme.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    student_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Cohort
        fields = [
            "id",
            "programme_id",
            "programme_code",
            "programme_name",
            "academic_year_id",
            "academic_year_name",
            "batch_name",
            "semester",
            "section",
            "status",
            "student_count",
            "created_at",
            "updated_at",
        ]


class CohortWriteSerializer(serializers.Serializer):
    programme_id = serializers.UUIDField()
    academic_year_id = serializers.UUIDField()
    batch_name = serializers.CharField(max_length=100)
    semester = serializers.IntegerField(min_value=1, max_value=8)
    section = serializers.CharField(max_length=30, required=False, default="A")
    status = serializers.ChoiceField(choices=ActiveStatus.choices, required=False, default=ActiveStatus.ACTIVE)

