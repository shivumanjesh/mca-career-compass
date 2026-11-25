"""Platform Super Admin, Institution Admin, and cross-tenant isolation tests."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import PlatformRole, Role, User
from apps.accounts.rbac import (
    ROLE_ASSESSMENT_ADMIN,
    ROLE_FACULTY_HOD,
    ROLE_INSTITUTION_ADMIN,
    ROLE_PLATFORM_SUPER_ADMIN,
    ROLE_STUDENT,
)
from apps.accounts.services import seed_roles_and_permissions
from apps.audit.models import AuditEvent
from apps.tenancy.models import Institution, Membership, MembershipRole


class PlatformAndTenantIsolationTests(TestCase):
    """Verify Platform Super Admin, Institution Admin, and strict cross-tenant isolation."""

    @classmethod
    def setUpTestData(cls):
        seed_roles_and_permissions()
        cls.super_admin = User.objects.create_user(
            email="super@compass.test",
            password="StrongPass!123",
            first_name="Platform",
            last_name="Super",
        )
        PlatformRole.objects.create(
            user=cls.super_admin,
            role=Role.objects.get(code=ROLE_PLATFORM_SUPER_ADMIN),
        )

        cls.inst_a = Institution.objects.create(code="MITT", name="MIT Thandavapura")
        cls.inst_b = Institution.objects.create(code="DEMOB", name="Demo Institute B")

        cls.admin_a = User.objects.create_user(
            email="admin.a@mitt.test",
            password="StrongPass!123",
            first_name="Admin",
            last_name="A",
        )
        cls.mem_admin_a = Membership.objects.create(institution=cls.inst_a, user=cls.admin_a)
        MembershipRole.objects.create(
            membership=cls.mem_admin_a,
            role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN),
        )

        cls.admin_b = User.objects.create_user(
            email="admin.b@demob.test",
            password="StrongPass!123",
            first_name="Admin",
            last_name="B",
        )
        cls.mem_admin_b = Membership.objects.create(institution=cls.inst_b, user=cls.admin_b)
        MembershipRole.objects.create(
            membership=cls.mem_admin_b,
            role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN),
        )

        cls.user_b = User.objects.create_user(
            email="faculty.b@demob.test",
            password="StrongPass!123",
            first_name="Faculty",
            last_name="B",
        )
        cls.mem_user_b = Membership.objects.create(institution=cls.inst_b, user=cls.user_b)
        MembershipRole.objects.create(
            membership=cls.mem_user_b,
            role=Role.objects.get(code=ROLE_FACULTY_HOD),
        )

    def setUp(self):
        self.client = APIClient()

    def _login(self, portal: str, email: str, inst_code: str | None = None):
        payload = {"portal": portal, "identifier": email, "password": "StrongPass!123"}
        if inst_code:
            payload["institution_code"] = inst_code
        res = self.client.post("/api/v1/auth/login/", payload, format="json")
        self.assertEqual(res.status_code, 200)
        return res

    def test_super_admin_creates_institution_and_provisions_admin(self):
        self._login("admin", "super@compass.test")

        create_res = self.client.post(
            "/api/v1/platform/institutions/",
            {"code": "NEWINST", "name": "New Engineering College", "timezone": "Asia/Kolkata"},
            format="json",
        )
        self.assertEqual(create_res.status_code, 201)
        inst_id = create_res.data["id"]

        admin_res = self.client.post(
            f"/api/v1/platform/institutions/{inst_id}/admins/",
            {"email": "head@newinst.test", "first_name": "Meera", "last_name": "K"},
            format="json",
        )
        self.assertEqual(admin_res.status_code, 201)
        self.assertIn("onboarding_reset_path", admin_res.data)
        self.assertIn(ROLE_INSTITUTION_ADMIN, admin_res.data["roles"])

        # Verify audit events recorded without secret tokens
        ev = AuditEvent.objects.filter(action="INSTITUTION_ADMIN_PROVISIONED").first()
        self.assertIsNotNone(ev)
        self.assertNotIn("token", str(ev.after_json))

        # Deactivate institution
        patch_res = self.client.patch(
            f"/api/v1/platform/institutions/{inst_id}/",
            {"status": "inactive"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.data["status"], "inactive")

    def test_institution_admin_denied_on_platform_endpoints(self):
        self._login("admin", "admin.a@mitt.test", "MITT")
        res = self.client.get("/api/v1/platform/institutions/")
        self.assertEqual(res.status_code, 403)

    def test_cross_institution_user_isolation(self):
        self._login("admin", "admin.a@mitt.test", "MITT")

        # Listing users only returns MITT users, never DEMOB users
        list_res = self.client.get(f"/api/v1/institution/users/?institution_id={self.inst_b.id}")
        self.assertEqual(list_res.status_code, 200)
        emails = {row["email"] for row in list_res.data["results"]}
        self.assertIn("admin.a@mitt.test", emails)
        self.assertNotIn("faculty.b@demob.test", emails)

        # Direct access/update to Institution B membership_id is denied (404)
        get_b = self.client.get(f"/api/v1/institution/users/{self.mem_user_b.id}/")
        self.assertEqual(get_b.status_code, 404)

        patch_b = self.client.patch(
            f"/api/v1/institution/users/{self.mem_user_b.id}/roles/",
            {"role_codes": [ROLE_STUDENT]},
            format="json",
        )
        self.assertEqual(patch_b.status_code, 404)

    def test_institution_admin_manages_own_users_and_roles(self):
        self._login("admin", "admin.a@mitt.test", "MITT")

        create_user = self.client.post(
            "/api/v1/institution/users/",
            {
                "email": "assessor@mitt.test",
                "first_name": "Kiran",
                "last_name": "Desai",
                "role_codes": [ROLE_ASSESSMENT_ADMIN],
            },
            format="json",
        )
        self.assertEqual(create_user.status_code, 201)
        membership_id = create_user.data["id"]

        # Update roles
        role_res = self.client.patch(
            f"/api/v1/institution/users/{membership_id}/roles/",
            {"role_codes": [ROLE_ASSESSMENT_ADMIN, ROLE_FACULTY_HOD]},
            format="json",
        )
        self.assertEqual(role_res.status_code, 200)
        self.assertEqual(set(role_res.data["roles"]), {ROLE_ASSESSMENT_ADMIN, ROLE_FACULTY_HOD})

        # Prevent removing own INSTITUTION_ADMIN role
        self_role = self.client.patch(
            f"/api/v1/institution/users/{self.mem_admin_a.id}/roles/",
            {"role_codes": [ROLE_FACULTY_HOD]},
            format="json",
        )
        self.assertEqual(self_role.status_code, 400)

        # Deactivate user membership
        deact = self.client.patch(
            f"/api/v1/institution/users/{membership_id}/",
            {"status": "inactive"},
            format="json",
        )
        self.assertEqual(deact.status_code, 200)
        self.assertEqual(deact.data["status"], "inactive")

    def test_dashboard_summary_live_counts(self):
        self._login("admin", "super@compass.test")
        plat_res = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(plat_res.status_code, 200)
        self.assertEqual(plat_res.data["scope"], "platform")
        self.assertEqual(plat_res.data["metrics"]["total_institutions"], 2)

        self._login("admin", "admin.a@mitt.test", "MITT")
        inst_res = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(inst_res.status_code, 200)
        self.assertEqual(inst_res.data["scope"], "institution")
        self.assertEqual(inst_res.data["institution"]["code"], "MITT")
        self.assertEqual(inst_res.data["metrics"]["total_members"], 1)

