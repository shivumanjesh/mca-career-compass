"""Academic structure, student, faculty cohort scoping, and isolation tests."""
from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Cohort, Programme
from apps.accounts.models import Role, User
from apps.accounts.rbac import ROLE_INSTITUTION_ADMIN
from apps.accounts.services import seed_roles_and_permissions
from apps.audit.models import AuditEvent
from apps.tenancy.models import Institution, Membership, MembershipRole


class AcademicsStudentsFacultyTests(TestCase):
    """Verify academic setup, student duplicate reg checks, faculty scoping, and tenant isolation."""

    @classmethod
    def setUpTestData(cls):
        seed_roles_and_permissions()
        cls.inst_a = Institution.objects.create(code="MITT", name="MIT Thandavapura")
        cls.inst_b = Institution.objects.create(code="DEMOB", name="Demo Institute B")

        cls.admin_a = User.objects.create_user(
            email="admin@mitt.test", password="StrongPass!123", first_name="Admin", last_name="A"
        )
        m_a = Membership.objects.create(institution=cls.inst_a, user=cls.admin_a)
        MembershipRole.objects.create(membership=m_a, role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN))

        cls.admin_b = User.objects.create_user(
            email="admin@demob.test", password="StrongPass!123", first_name="Admin", last_name="B"
        )
        m_b = Membership.objects.create(institution=cls.inst_b, user=cls.admin_b)
        MembershipRole.objects.create(membership=m_b, role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN))

        cls.prog_a = Programme.objects.create(institution=cls.inst_a, code="MCA", name="Master of Computer Applications")
        cls.ay_a = AcademicYear.objects.create(
            institution=cls.inst_a, name="2025-26", start_date=date(2025, 8, 1), end_date=date(2026, 7, 31)
        )
        cls.cohort_a1 = Cohort.objects.create(
            institution=cls.inst_a, programme=cls.prog_a, academic_year=cls.ay_a,
            batch_name="2025-2027", semester=1, section="A",
        )
        cls.cohort_a2 = Cohort.objects.create(
            institution=cls.inst_a, programme=cls.prog_a, academic_year=cls.ay_a,
            batch_name="2025-2027", semester=1, section="B",
        )

        cls.prog_b = Programme.objects.create(institution=cls.inst_b, code="MCA", name="MCA Demo B")
        cls.ay_b = AcademicYear.objects.create(
            institution=cls.inst_b, name="2025-26", start_date=date(2025, 8, 1), end_date=date(2026, 7, 31)
        )
        cls.cohort_b1 = Cohort.objects.create(
            institution=cls.inst_b, programme=cls.prog_b, academic_year=cls.ay_b,
            batch_name="2025-2027", semester=1, section="A",
        )

    def setUp(self):
        self.client = APIClient()

    def _login(self, portal: str, identifier: str, inst_code: str, password: str = "StrongPass!123"):
        res = self.client.post(
            "/api/v1/auth/login/",
            {"portal": portal, "identifier": identifier, "password": password, "institution_code": inst_code},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        return res

    def test_duplicate_registration_no_rejected_in_same_inst_but_allowed_across_inst(self):
        self._login("admin", "admin@mitt.test", "MITT")
        s1 = self.client.post(
            "/api/v1/students/",
            {
                "email": "stu1@mitt.test",
                "first_name": "Asha",
                "last_name": "K",
                "registration_no": "4MT25MC001",
                "cohort_id": str(self.cohort_a1.id),
                "admission_year": 2025,
                "password": "StudentPass!123",
            },
            format="json",
        )
        self.assertEqual(s1.status_code, 201)

        # Duplicate reg_no in MITT rejected
        dup = self.client.post(
            "/api/v1/students/",
            {
                "email": "stu2@mitt.test",
                "first_name": "Bala",
                "registration_no": "4mt25mc001",
                "cohort_id": str(self.cohort_a1.id),
            },
            format="json",
        )
        self.assertEqual(dup.status_code, 400)

        # Cross-institution cohort rejected
        bad_cohort = self.client.post(
            "/api/v1/students/",
            {
                "email": "stu3@mitt.test",
                "first_name": "Chitra",
                "registration_no": "4MT25MC003",
                "cohort_id": str(self.cohort_b1.id),
            },
            format="json",
        )
        self.assertEqual(bad_cohort.status_code, 400)

        # Same registration_no allowed in Institution B
        self._login("admin", "admin@demob.test", "DEMOB")
        s_b = self.client.post(
            "/api/v1/students/",
            {
                "email": "stu1@demob.test",
                "first_name": "Deepa",
                "registration_no": "4MT25MC001",
                "cohort_id": str(self.cohort_b1.id),
            },
            format="json",
        )
        self.assertEqual(s_b.status_code, 201)

    def test_student_login_by_registration_no_and_self_only_access(self):
        self._login("admin", "admin@mitt.test", "MITT")
        s1 = self.client.post(
            "/api/v1/students/",
            {
                "email": "ravi@mitt.test",
                "first_name": "Ravi",
                "registration_no": "4MT25MC010",
                "cohort_id": str(self.cohort_a1.id),
                "password": "StudentPass!123",
            },
            format="json",
        )
        self.assertEqual(s1.status_code, 201)
        s1_id = s1.data["id"]

        # Student logs in with registration number
        self._login("academic", "4MT25MC010", "MITT", password="StudentPass!123")
        me = self.client.get("/api/v1/students/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["registration_no"], "4MT25MC010")

        # Student cannot list all students or access /students/{id}/
        self.assertEqual(self.client.get("/api/v1/students/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/students/{s1_id}/").status_code, 403)

    def test_faculty_cohort_assignment_scopes_student_access(self):
        self._login("admin", "admin@mitt.test", "MITT")

        # Create 2 students in different cohorts
        s_a1 = self.client.post(
            "/api/v1/students/",
            {
                "email": "s_a1@mitt.test",
                "first_name": "Student",
                "last_name": "One",
                "registration_no": "4MT25MC101",
                "cohort_id": str(self.cohort_a1.id),
            },
            format="json",
        ).data
        s_a2 = self.client.post(
            "/api/v1/students/",
            {
                "email": "s_a2@mitt.test",
                "first_name": "Student",
                "last_name": "Two",
                "registration_no": "4MT25MC102",
                "cohort_id": str(self.cohort_a2.id),
            },
            format="json",
        ).data

        # Create faculty and assign ONLY to cohort_a1
        fac = self.client.post(
            "/api/v1/faculty/",
            {
                "email": "prof@mitt.test",
                "first_name": "Dr. Suma",
                "last_name": "N",
                "employee_code": "FAC001",
                "department": "MCA",
                "designation": "Associate Professor",
                "password": "FacultyPass!123",
            },
            format="json",
        )
        self.assertEqual(fac.status_code, 201)
        fac_id = fac.data["id"]

        assign = self.client.post(
            f"/api/v1/faculty/{fac_id}/cohorts/",
            {"cohort_id": str(self.cohort_a1.id), "assignment_type": "mentor"},
            format="json",
        )
        self.assertEqual(assign.status_code, 201)
        self.assertTrue(AuditEvent.objects.filter(action="FACULTY_COHORT_ASSIGNED").exists())

        # Log in as faculty
        self._login("academic", "prof@mitt.test", "MITT", password="FacultyPass!123")
        cohorts = self.client.get("/api/v1/faculty/me/cohorts/")
        self.assertEqual(cohorts.status_code, 200)
        self.assertEqual(len(cohorts.data), 1)
        self.assertEqual(cohorts.data[0]["student_count"], 1)

        visible_students = self.client.get("/api/v1/students/")
        self.assertEqual(visible_students.status_code, 200)
        reg_nos = [s["registration_no"] for s in visible_students.data["results"]]
        self.assertEqual(reg_nos, ["4MT25MC101"])

        # Cannot view student in unassigned cohort_a2
        self.assertEqual(self.client.get(f"/api/v1/students/{s_a2['id']}/").status_code, 404)
        # Cannot mutate student
        self.assertEqual(
            self.client.patch(f"/api/v1/students/{s_a1['id']}/", {"first_name": "Hacked"}, format="json").status_code,
            403,
        )

