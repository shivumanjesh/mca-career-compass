"""Platform Super Admin and Institution Admin REST API views."""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import HasInstitutionPermission, HasPlatformPermission
from apps.accounts.rbac import ROLE_INSTITUTION_ADMIN
from apps.accounts.services import build_password_reset_payload
from apps.audit.services import log_audit_event
from apps.core.pagination import StandardResultsSetPagination
from apps.tenancy.mixins import require_active_institution
from apps.tenancy.models import Institution, Membership
from apps.tenancy.serializers import (
    InstitutionAdminCreateSerializer,
    InstitutionCreateSerializer,
    InstitutionProfileUpdateSerializer,
    InstitutionSerializer,
    InstitutionUpdateSerializer,
    InstitutionUserCreateSerializer,
    InstitutionUserUpdateSerializer,
    MembershipRolesUpdateSerializer,
    MembershipUserSerializer,
)
from apps.tenancy.services import (
    create_institution,
    provision_institution_admin,
    provision_institution_user,
    update_institution,
    update_institution_user,
    update_membership_roles,
)


def _paginate_queryset(queryset, request, serializer_class):
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = serializer_class(page, many=True)
    return paginator.get_paginated_response(serializer.data)


class PlatformInstitutionListCreateView(APIView):
    """List or create institutions (Platform Super Admin only)."""

    permission_classes = [HasPlatformPermission("platform.institution.manage")]

    def get(self, request):
        qs = Institution.objects.annotate(
            member_count=Count("memberships", distinct=True),
            admin_count=Count(
                "memberships",
                filter=Q(memberships__membership_roles__role__code=ROLE_INSTITUTION_ADMIN),
                distinct=True,
            ),
        ).order_by("name")

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))

        inst_status = request.query_params.get("status", "").strip()
        if inst_status:
            qs = qs.filter(status=inst_status)

        return _paginate_queryset(qs, request, InstitutionSerializer)

    def post(self, request):
        serializer = InstitutionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        inst = create_institution(
            code=data["code"],
            name=data["name"],
            status=data["status"],
            timezone=data["timezone"],
            settings_data=data.get("settings"),
            actor_user=request.user,
            request=request,
        )
        return Response(InstitutionSerializer(inst).data, status=status.HTTP_201_CREATED)


class PlatformInstitutionDetailView(APIView):
    """Retrieve or update an institution (Platform Super Admin only)."""

    permission_classes = [HasPlatformPermission("platform.institution.manage")]

    def get(self, request, institution_id):
        inst = get_object_or_404(
            Institution.objects.annotate(
                member_count=Count("memberships", distinct=True),
                admin_count=Count(
                    "memberships",
                    filter=Q(memberships__membership_roles__role__code=ROLE_INSTITUTION_ADMIN),
                    distinct=True,
                ),
            ),
            id=institution_id,
        )
        return Response(InstitutionSerializer(inst).data)

    def patch(self, request, institution_id):
        inst = get_object_or_404(Institution, id=institution_id)
        serializer = InstitutionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_institution(
            institution=inst,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
            allow_status_and_code=True,
        )
        return Response(InstitutionSerializer(updated).data)


class PlatformInstitutionAdminsView(APIView):
    """List or provision Institution Admins for a target institution (Platform Super Admin only)."""

    permission_classes = [HasPlatformPermission("platform.admin.manage")]

    def get(self, request, institution_id):
        inst = get_object_or_404(Institution, id=institution_id)
        qs = (
            Membership.objects.select_related("user")
            .prefetch_related("membership_roles__role")
            .filter(
                institution=inst,
                membership_roles__role__code=ROLE_INSTITUTION_ADMIN,
            )
            .distinct()
            .order_by("user__first_name", "user__email")
        )
        return _paginate_queryset(qs, request, MembershipUserSerializer)

    def post(self, request, institution_id):
        inst = get_object_or_404(Institution, id=institution_id)
        serializer = InstitutionAdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        membership, onboarding_link = provision_institution_admin(
            institution=inst,
            email=data["email"],
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
            password=data.get("password") or None,
            actor_user=request.user,
            request=request,
        )
        payload = MembershipUserSerializer(membership).data
        if onboarding_link:
            payload["onboarding_reset_path"] = onboarding_link
        return Response(payload, status=status.HTTP_201_CREATED)


class InstitutionProfileView(APIView):
    """View or update the active institution's own profile (tenant-scoped)."""

    permission_classes = [HasInstitutionPermission("institution.profile.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        annotated = Institution.objects.annotate(
            member_count=Count("memberships", distinct=True),
            admin_count=Count(
                "memberships",
                filter=Q(memberships__membership_roles__role__code=ROLE_INSTITUTION_ADMIN),
                distinct=True,
            ),
        ).get(id=inst.id)
        return Response(InstitutionSerializer(annotated).data)

    def patch(self, request):
        inst = require_active_institution(request)
        serializer = InstitutionProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_institution(
            institution=inst,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
            allow_status_and_code=False,
        )
        return Response(InstitutionSerializer(updated).data)


class InstitutionUserListCreateView(APIView):
    """List or create users/memberships scoped strictly to the active institution."""

    permission_classes = [HasInstitutionPermission("institution.user.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = (
            Membership.objects.select_related("user")
            .prefetch_related("membership_roles__role")
            .filter(institution=inst)
            .order_by("user__first_name", "user__email")
        )

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )

        member_status = request.query_params.get("status", "").strip()
        if member_status:
            qs = qs.filter(status=member_status)

        role_code = request.query_params.get("role", "").strip()
        if role_code:
            qs = qs.filter(membership_roles__role__code=role_code).distinct()

        return _paginate_queryset(qs, request, MembershipUserSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = InstitutionUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        membership, onboarding_link = provision_institution_user(
            institution=inst,
            email=data["email"],
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
            role_codes=data["role_codes"],
            password=data.get("password") or None,
            membership_status=data["status"],
            actor_user=request.user,
            request=request,
        )
        payload = MembershipUserSerializer(membership).data
        if onboarding_link:
            payload["onboarding_reset_path"] = onboarding_link
        return Response(payload, status=status.HTTP_201_CREATED)


class InstitutionUserDetailView(APIView):
    """Retrieve or update a membership scoped to the active institution."""

    permission_classes = [HasInstitutionPermission("institution.user.manage")]

    def get(self, request, membership_id):
        inst = require_active_institution(request)
        membership = get_object_or_404(
            Membership.objects.select_related("user").prefetch_related("membership_roles__role"),
            id=membership_id,
            institution=inst,
        )
        return Response(MembershipUserSerializer(membership).data)

    def patch(self, request, membership_id):
        inst = require_active_institution(request)
        membership = get_object_or_404(
            Membership.objects.select_related("user", "institution"),
            id=membership_id,
            institution=inst,
        )
        serializer = InstitutionUserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        updated = update_institution_user(
            membership=membership,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            status=data.get("status"),
            actor_user=request.user,
            request=request,
        )
        return Response(MembershipUserSerializer(updated).data)


class InstitutionUserRolesView(APIView):
    """Assign or revoke institution-scoped roles on a membership in the active institution."""

    permission_classes = [HasInstitutionPermission("institution.user.manage")]

    def patch(self, request, membership_id):
        inst = require_active_institution(request)
        membership = get_object_or_404(
            Membership.objects.select_related("user", "institution"),
            id=membership_id,
            institution=inst,
        )
        serializer = MembershipRolesUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_membership_roles(
            membership=membership,
            role_codes=serializer.validated_data["role_codes"],
            actor_user=request.user,
            request=request,
        )
        return Response(MembershipUserSerializer(updated).data)


class InstitutionUserResetLinkView(APIView):
    """Issue a one-time onboarding/reset path for an institution member (never stored)."""

    permission_classes = [HasInstitutionPermission("institution.user.manage")]

    def post(self, request, membership_id):
        inst = require_active_institution(request)
        membership = get_object_or_404(
            Membership.objects.select_related("user"),
            id=membership_id,
            institution=inst,
        )
        payload = build_password_reset_payload(membership.user)
        log_audit_event(
            action="INSTITUTION_USER_RESET_LINK_ISSUED",
            entity_type="Membership",
            entity_id=membership.id,
            institution=inst,
            actor_user=request.user,
            after={"email": membership.user.email},
            request=request,
        )
        return Response(
            {
                "onboarding_reset_path": f"/reset-password?uid={payload['uid']}&token={payload['token']}",
            },
            status=status.HTTP_200_OK,
        )

