"""Serializers for staged Excel/CSV import endpoints."""
from rest_framework import serializers
from apps.imports.models import ImportJob, ImportRowError


class ImportRowErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRowError
        fields = [
            "id",
            "row_number",
            "field_name",
            "error_code",
            "message",
            "row_data",
            "created_at",
        ]


class ImportJobSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "file_name",
            "status",
            "total_rows",
            "success_rows",
            "error_rows",
            "summary_json",
            "created_by_email",
            "created_by_name",
            "created_at",
            "updated_at",
        ]


class ImportValidateSerializer(serializers.Serializer):
    column_mapping = serializers.DictField(child=serializers.CharField(allow_blank=True))
    sheet_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    default_cohort_id = serializers.UUIDField(required=False, allow_null=True)


class ImportCommitSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(
        choices=["skip_invalid", "all_or_nothing"],
        default="skip_invalid",
    )

