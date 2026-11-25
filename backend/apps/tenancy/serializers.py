"""Serializers for Platform and Institution Admin tenancy APIs."""
from rest_framework import serializers
from apps.accounts.rbac import ROLE_INSTITUTION_ADMIN
from apps.tenancy.models import Institution, Membership


class InstitutionSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, default=0)
    admin_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Institution
        fields = [
            "id",
            "code",
            "name",
            "status",
            "timezone",
            "settings",
            "member_count",
            "admin_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "member_count", "admin_count"]


class InstitutionCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)
    name = serializers.CharField(max_length=200)
    status = serializers.ChoiceField(
        choices=Institution.Status.choices, default=Institution.Status.ACTIVE
    )
    timezone = serializers.CharField(max_length=64, default="Asia/Kolkata")
    settings = serializers.JSONField(required=False, default=dict)


class InstitutionUpdateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40, required=False)
    name = serializers.CharField(max_length=200, required=False)
    status = serializers.ChoiceField(choices=Institution.Status.choices, required=False)
    timezone = serializers.CharField(max_length=64, required=False)
    settings = serializers.JSONField(required=False)


class InstitutionProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    timezone = serializers.CharField(max_length=64, required=False)
    settings = serializers.JSONField(required=False)


class InstitutionAdminCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=10)


class MembershipUserSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    must_change_password = serializers.BooleanField(source="user.must_change_password", read_only=True)
    last_login = serializers.DateTimeField(source="user.last_login", read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "id",
            "user_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "status",
            "user_is_active",
            "must_change_password",
            "last_login",
            "roles",
            "created_at",
            "updated_at",
        ]

    def get_roles(self, obj: Membership) -> list[str]:
        return sorted(mr.role.code for mr in obj.membership_roles.all())


class InstitutionUserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    role_codes = serializers.ListField(
        child=serializers.CharField(max_length=60),
        min_length=1,
    )
    status = serializers.ChoiceField(
        choices=Membership.Status.choices, default=Membership.Status.ACTIVE
    )
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=10)


class InstitutionUserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Membership.Status.choices, required=False)


class MembershipRolesUpdateSerializer(serializers.Serializer):
    role_codes = serializers.ListField(
        child=serializers.CharField(max_length=60),
        min_length=1,
    )

