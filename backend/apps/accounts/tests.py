"""Authentication, tenancy context, RBAC, and audit tests."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import PlatformRole, Role, User
from apps.accounts.rbac import (
    ROLE_INSTITUTION_ADMIN,
    ROLE_PLATFORM_SUPER_ADMIN,
    ROLE_STUDENT,
)
from apps.accounts.services import build_password_reset_payload, seed_roles_and_permissions
from apps.audit.models import AuditEvent
from apps.tenancy.models import Institution, Membership, MembershipRole


class AuthAndRbacTests(TestCase):
    """Verify portal logins, session tenant derivation, revocation, and password reset."""

    @classmethod
    def setUpTestData(cls):
        seed_roles_and_permissions()
        cls.inst_a = Institution.objects.create(code="MITT", name="MIT Thandavapura")
        cls.inst_b = Institution.objects.create(code="DEMOB", name="Demo Institute B")

        cls.super_admin = User.objects.create_user(
            email="superadmin@compass.test",
            password="StrongPass!123",
            first_name="Super",
            last_name="Admin",
        )
        PlatformRole.objects.create(
            user=cls.super_admin,
            role=Role.objects.get(code=ROLE_PLATFORM_SUPER_ADMIN),
        )

        cls.inst_admin = User.objects.create_user(
            email="admin@mitt.test",
            password="StrongPass!123",
            first_name="Inst",
            last_name="Admin",
        )
        cls.admin_membership_a = Membership.objects.create(
            institution=cls.inst_a, user=cls.inst_admin
        )
        MembershipRole.objects.create(
            membership=cls.admin_membership_a,
            role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN),
        )

        cls.student_user = User.objects.create_user(
            email="student1@mitt.test",
            password="StrongPass!123",
            first_name="Asha",
            last_name="Rao",
        )
        cls.student_membership_a = Membership.objects.create(
            institution=cls.inst_a, user=cls.student_user
        )
        MembershipRole.objects.create(
            membership=cls.student_membership_a,
            role=Role.objects.get(code=ROLE_STUDENT),
        )
        # Also give student_user membership in inst_b to test institution switching
        cls.student_membership_b = Membership.objects.create(
            institution=cls.inst_b, user=cls.student_user
        )
        MembershipRole.objects.create(
            membership=cls.student_membership_b,
            role=Role.objects.get(code=ROLE_STUDENT),
        )

    def setUp(self):
        self.client = APIClient()

    def test_super_admin_login_on_admin_portal(self):
        res = self.client.post(
            "/api/v1/auth/login/",
            {"portal": "admin", "identifier": "superadmin@compass.test", "password": "StrongPass!123"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(ROLE_PLATFORM_SUPER_ADMIN, res.data["platform_roles"])
        self.assertIsNone(res.data["active_institution"])
        self.assertTrue(
            AuditEvent.objects.filter(action="AUTH_LOGIN_SUCCESS", actor_user=self.super_admin).exists()
        )

    def test_student_denied_on_admin_portal(self):
        res = self.client.post(
            "/api/v1/auth/login/",
            {
                "portal": "admin",
                "identifier": "student1@mitt.test",
                "password": "StrongPass!123",
                "institution_code": "MITT",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_institution_admin_denied_on_academic_portal(self):
        res = self.client.post(
            "/api/v1/auth/login/",
            {
                "portal": "academic",
                "identifier": "admin@mitt.test",
                "password": "StrongPass!123",
                "institution_code": "MITT",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_inactive_user_cannot_login(self):
        self.inst_admin.is_active = False
        self.inst_admin.save()
        res = self.client.post(
            "/api/v1/auth/login/",
            {
                "portal": "admin",
                "identifier": "admin@mitt.test",
                "password": "StrongPass!123",
                "institution_code": "MITT",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 401)
        # Ensure audit failed event does not store password
        ev = AuditEvent.objects.filter(action="AUTH_LOGIN_FAILED").first()
        self.assertIsNotNone(ev)
        self.assertNotIn("StrongPass!123", str(ev.after_json))

    def test_inactive_institution_blocks_login_and_clears_session_context(self):
        res = self.client.post(
            "/api/v1/auth/login/",
            {
                "portal": "admin",
                "identifier": "admin@mitt.test",
                "password": "StrongPass!123",
                "institution_code": "MITT",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["active_institution"]["code"], "MITT")

        self.inst_a.status = Institution.Status.INACTIVE
        self.inst_a.save()

        me = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertIsNone(me.data["active_institution"])
        self.assertEqual(me.data["permissions"], [])

    def test_role_removal_takes_effect_on_next_request(self):
        self.client.post(
            "/api/v1/auth/login/",
            {
                "portal": "admin",
                "identifier": "admin@mitt.test",
                "password": "StrongPass!123",
                "institution_code": "MITT",
            },
            format="json",
        )
        me_before = self.client.get("/api/v1/auth/me/")
        self.assertIn("institution.student.manage", me_before.data["permissions"])

        MembershipRole.objects.filter(membership=self.admin_membership_a).delete()

        me_after = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_after.data["active_roles"], [])
        self.assertEqual(me_after.data["permissions"], [])

    def test_multi_institution_switch_verifies_membership(self):
        self.client.post(
            "/api/v1/auth/login/",
            {
                "portal": "academic",
                "identifier": "student1@mitt.test",
                "password": "StrongPass!123",
                "institution_code": "MITT",
            },
            format="json",
        )
        switch_ok = self.client.post(
            "/api/v1/auth/switch-institution/",
            {"institution_id": str(self.inst_b.id)},
            format="json",
        )
        self.assertEqual(switch_ok.status_code, 200)
        self.assertEqual(switch_ok.data["active_institution"]["code"], "DEMOB")

        # Switching to an institution where user has NO membership is denied
        inst_c = Institution.objects.create(code="INSTC", name="Unauthorized College")
        switch_denied = self.client.post(
            "/api/v1/auth/switch-institution/",
            {"institution_id": str(inst_c.id)},
            format="json",
        )
        self.assertEqual(switch_denied.status_code, 403)

    def test_password_reset_confirm_updates_password(self):
        payload = build_password_reset_payload(self.student_user)
        res = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": payload["uid"],
                "token": payload["token"],
                "new_password": "NewSecurePassword!99",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        login_res = self.client.post(
            "/api/v1/auth/login/",
            {
                "portal": "academic",
                "identifier": "student1@mitt.test",
                "password": "NewSecurePassword!99",
                "institution_code": "MITT",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, 200)

