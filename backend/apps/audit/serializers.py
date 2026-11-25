"""Serializers for append-only audit log endpoints."""
from rest_framework import serializers
from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    institution_code = serializers.SerializerMethodField()
    actor_email = serializers.SerializerMethodField()
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "institution_id",
            "institution_code",
            "actor_user_id",
            "actor_email",
            "actor_name",
            "action",
            "entity_type",
            "entity_id",
            "before_json",
            "after_json",
            "ip_hash",
            "created_at",
        ]

    def get_institution_code(self, obj: AuditEvent) -> str | None:
        return obj.institution.code if obj.institution else None

    def get_actor_email(self, obj: AuditEvent) -> str | None:
        return obj.actor_user.email if obj.actor_user else None

    def get_actor_name(self, obj: AuditEvent) -> str | None:
        return obj.actor_user.full_name if obj.actor_user else None

