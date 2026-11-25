"""Audit logging, secret scrubbing, IP HMAC hashing, and tenant-scoped query tests."""
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from apps.accounts.models import PlatformRole, Role, User
from apps.accounts.rbac import (
    ROLE_INSTITUTION_ADMIN,
    ROLE_PLATFORM_SUPER_ADMIN,
    ROLE_STUDENT,
)
from apps.accounts.services import seed_roles_and_permissions
from apps.audit.services import log_audit_event, sanitize_audit_payload
from apps.tenancy.models import Institution, Membership, MembershipRole


class AuditLoggingTests(TestCase):
    """Verify audit payload scrubbing, IP hashing, and tenant-isolated listing."""

    @classmethod
    def setUpTestData(cls):
        seed_roles_and_permissions()
        cls.inst_a = Institution.objects.create(code="MITT", name="MIT Thandavapura")
        cls.inst_b = Institution.objects.create(code="DEMOB", name="Demo Institute B")

        cls.super_admin = User.objects.create_user(
            email="super@compass.test", password="StrongPass!123", first_name="Super"
        )
        PlatformRole.objects.create(
            user=cls.super_admin, role=Role.objects.get(code=ROLE_PLATFORM_SUPER_ADMIN)
        )

        cls.admin_a = User.objects.create_user(
            email="admin@mitt.test", password="StrongPass!123", first_name="AdminA"
        )
        m_a = Membership.objects.create(institution=cls.inst_a, user=cls.admin_a)
        MembershipRole.objects.create(membership=m_a, role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN))

        cls.student_a = User.objects.create_user(
            email="stu@mitt.test", password="StrongPass!123", first_name="StudentA"
        )
        m_s = Membership.objects.create(institution=cls.inst_a, user=cls.student_a)
        MembershipRole.objects.create(membership=m_s, role=Role.objects.get(code=ROLE_STUDENT))

    def setUp(self):
        self.client = APIClient()

    def test_sanitize_payload_scrubs_secrets_and_hashes_ip(self):
        cleaned = sanitize_audit_payload({
            "email": "user@test.edu",
            "password": "my-plaintext-password",
            "nested": {"reset_token": "secret-tok", "api_key": "abc", "safe": 42},
        })
        self.assertEqual(cleaned["password"], "[REDACTED]")
        self.assertEqual(cleaned["nested"]["reset_token"], "[REDACTED]")
        self.assertEqual(cleaned["nested"]["api_key"], "[REDACTED]")
        self.assertEqual(cleaned["nested"]["safe"], 42)

        rf = RequestFactory()
        req = rf.get("/", REMOTE_ADDR="192.168.1.50")
        ev = log_audit_event(
            action="TEST_ACTION",
            entity_type="Test",
            institution=self.inst_a,
            actor_user=self.admin_a,
            after={"password": "leak-me"},
            request=req,
        )
        self.assertEqual(ev.after_json["password"], "[REDACTED]")
        self.assertNotEqual(ev.ip_hash, "192.168.1.50")
        self.assertEqual(len(ev.ip_hash), 64)

    def test_audit_events_scoped_by_tenant_and_role(self):
        log_audit_event(action="INST_A_EVENT", entity_type="StudentProfile", institution=self.inst_a, actor_user=self.admin_a)
        log_audit_event(action="INST_B_EVENT", entity_type="StudentProfile", institution=self.inst_b)

        # Student denied
        self.client.post(
            "/api/v1/auth/login/",
            {"portal": "academic", "identifier": "stu@mitt.test", "password": "StrongPass!123", "institution_code": "MITT"},
            format="json",
        )
        self.assertEqual(self.client.get("/api/v1/audit-events/").status_code, 403)

        # Institution A admin sees only MITT events, even if passing ?institution_id=<inst_b>
        self.client.post(
            "/api/v1/auth/login/",
            {"portal": "admin", "identifier": "admin@mitt.test", "password": "StrongPass!123", "institution_code": "MITT"},
            format="json",
        )
        res_a = self.client.get(f"/api/v1/audit-events/?institution_id={self.inst_b.id}")
        self.assertEqual(res_a.status_code, 200)
        actions_a = {row["action"] for row in res_a.data["results"]}
        self.assertIn("INST_A_EVENT", actions_a)
        self.assertNotIn("INST_B_EVENT", actions_a)

        # Platform Super Admin sees both institutions
        self.client.post(
            "/api/v1/auth/login/",
            {"portal": "admin", "identifier": "super@compass.test", "password": "StrongPass!123"},
            format="json",
        )
        res_p = self.client.get("/api/v1/audit-events/")
        self.assertEqual(res_p.status_code, 200)
        actions_p = {row["action"] for row in res_p.data["results"]}
        self.assertIn("INST_A_EVENT", actions_p)
        self.assertIn("INST_B_EVENT", actions_p)

        # Append-only: POST/DELETE not allowed
        self.assertEqual(self.client.post("/api/v1/audit-events/", {}, format="json").status_code, 405)

