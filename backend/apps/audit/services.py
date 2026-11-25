"""Audit logging helper service with secret scrubbing and IP HMAC hashing."""
import hashlib
import hmac
import uuid
from typing import Any
from django.conf import settings
from apps.audit.models import AuditEvent

SENSITIVE_KEY_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "csrf",
    "authorization",
    "api_key",
    "private_key",
)


def sanitize_audit_payload(payload: Any) -> Any:
    """Recursively remove or redact sensitive keys from audit JSON payloads."""
    if payload is None:
        return None
    if isinstance(payload, dict):
        sanitized: dict[str, Any] = {}
        for key, value in payload.items():
            key_lower = str(key).lower()
            if any(marker in key_lower for marker in SENSITIVE_KEY_SUBSTRINGS):
                sanitized[str(key)] = "[REDACTED]"
            else:
                sanitized[str(key)] = sanitize_audit_payload(value)
        return sanitized
    if isinstance(payload, (list, tuple)):
        return [sanitize_audit_payload(item) for item in payload]
    if isinstance(payload, uuid.UUID):
        return str(payload)
    return payload


def compute_ip_hash(request) -> str:
    """Compute keyed HMAC-SHA256 hash of client IP address without storing raw IP."""
    if request is None:
        return ""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip_addr = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR", "")
    if not ip_addr:
        return ""
    key = str(getattr(settings, "AUDIT_IP_HMAC_KEY", settings.SECRET_KEY)).encode("utf-8")
    return hmac.new(key, ip_addr.encode("utf-8"), hashlib.sha256).hexdigest()


def log_audit_event(
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None = None,
    institution=None,
    actor_user=None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request=None,
) -> AuditEvent:
    """Create an append-only AuditEvent entry."""
    parsed_entity_id = None
    if entity_id:
        parsed_entity_id = uuid.UUID(str(entity_id))

    resolved_actor = actor_user if getattr(actor_user, "is_authenticated", False) else None
    if resolved_actor is None and actor_user is not None and getattr(actor_user, "id", None):
        resolved_actor = actor_user

    return AuditEvent.objects.create(
        institution=institution,
        actor_user=resolved_actor,
        action=action,
        entity_type=entity_type,
        entity_id=parsed_entity_id,
        before_json=sanitize_audit_payload(before),
        after_json=sanitize_audit_payload(after),
        ip_hash=compute_ip_hash(request),
    )

