"""Serializers for authentication endpoints."""
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    portal = serializers.ChoiceField(choices=["admin", "academic"])
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    institution_code = serializers.CharField(max_length=40, required=False, allow_blank=True, allow_null=True)


class SwitchInstitutionSerializer(serializers.Serializer):
    institution_id = serializers.UUIDField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=False, allow_blank=True, default="", trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

