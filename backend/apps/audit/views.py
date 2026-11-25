"""Restricted read-only audit event query views."""
from django.db.models import Q
from rest_framework.views import APIView

from apps.accounts.permissions import HasAnyPermission
from apps.audit.models import AuditEvent
from apps.audit.serializers import AuditEventSerializer
from apps.core.pagination import StandardResultsSetPagination
from apps.tenancy.mixins import require_active_institution


class AuditEventListView(APIView):
    """List audit events scoped to platform (Super Admin) or active institution."""

    permission_classes = [HasAnyPermission("audit.platform.view", "audit.institution.view")]

    def get(self, request):
        platform_perms = getattr(request, "platform_permissions", set())
        active_inst = getattr(request, "active_institution", None)

        qs = AuditEvent.objects.select_related("institution", "actor_user").order_by("-created_at")

        if "audit.platform.view" in platform_perms and active_inst is None:
            institution_id = request.query_params.get("institution_id", "").strip()
            if institution_id:
                qs = qs.filter(institution_id=institution_id)
        else:
            inst = require_active_institution(request)
            qs = qs.filter(institution=inst)

        action = request.query_params.get("action", "").strip()
        if action:
            qs = qs.filter(action__icontains=action)

        entity_type = request.query_params.get("entity_type", "").strip()
        if entity_type:
            qs = qs.filter(entity_type__iexact=entity_type)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(action__icontains=search)
                | Q(entity_type__icontains=search)
                | Q(actor_user__email__icontains=search)
                | Q(institution__code__icontains=search)
            )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(AuditEventSerializer(page, many=True).data)

