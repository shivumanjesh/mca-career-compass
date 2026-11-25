"""Phase 2 tests: RBAC, measurement-family separation, scoring, immutable versions, and isolation."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.rbac import (
    ROLE_ASSESSMENT_ADMIN,
    ROLE_INSTITUTION_ADMIN,
    ROLE_STUDENT,
)
from apps.accounts.services import seed_roles_and_permissions
from apps.assessments.models import AssessmentDimension, AssessmentVersion, MeasurementFamily
from apps.audit.models import AuditEvent
from apps.tenancy.models import Institution, Membership, MembershipRole


class AssessmentAdminPhase2Tests(TestCase):
    """Verify Phase 2 assessment administration, immutability, guardrails, and isolation."""

    @classmethod
    def setUpTestData(cls):
        seed_roles_and_permissions()
        cls.inst_a = Institution.objects.create(code="MITT", name="MIT Thandavapura")
        cls.inst_b = Institution.objects.create(code="DEMOB", name="Demo Institute B")

        cls.assessor_a = User.objects.create_user(
            email="assessor.a@mitt.test", password="StrongPass!123", first_name="Assessor", last_name="A"
        )
        m_a = Membership.objects.create(institution=cls.inst_a, user=cls.assessor_a)
        MembershipRole.objects.create(membership=m_a, role=Role.objects.get(code=ROLE_ASSESSMENT_ADMIN))

        cls.assessor_b = User.objects.create_user(
            email="assessor.b@demob.test", password="StrongPass!123", first_name="Assessor", last_name="B"
        )
        m_b = Membership.objects.create(institution=cls.inst_b, user=cls.assessor_b)
        MembershipRole.objects.create(membership=m_b, role=Role.objects.get(code=ROLE_ASSESSMENT_ADMIN))

        cls.inst_admin_a = User.objects.create_user(
            email="admin.a@mitt.test", password="StrongPass!123", first_name="InstAdmin", last_name="A"
        )
        m_ia = Membership.objects.create(institution=cls.inst_a, user=cls.inst_admin_a)
        MembershipRole.objects.create(membership=m_ia, role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN))

        cls.student_a = User.objects.create_user(
            email="stu.a@mitt.test", password="StrongPass!123", first_name="Student", last_name="A"
        )
        m_sa = Membership.objects.create(institution=cls.inst_a, user=cls.student_a)
        MembershipRole.objects.create(membership=m_sa, role=Role.objects.get(code=ROLE_STUDENT))

    def setUp(self):
        self.client = APIClient()

    def _login(self, portal: str, email: str, inst_code: str):
        res = self.client.post(
            "/api/v1/auth/login/",
            {"portal": portal, "identifier": email, "password": "StrongPass!123", "institution_code": inst_code},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    def test_rbac_denies_student_and_unassigned_institution_admin(self):
        self._login("academic", "stu.a@mitt.test", "MITT")
        self.assertEqual(self.client.get("/api/v1/assessments/dimensions/").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/assessments/seed-catalogue/").status_code, 403)

        self._login("admin", "admin.a@mitt.test", "MITT")
        self.assertEqual(self.client.get("/api/v1/assessments/questions/").status_code, 403)

    def test_measurement_family_guardrails_and_question_validation(self):
        self._login("admin", "assessor.a@mitt.test", "MITT")
        seed = self.client.post("/api/v1/assessments/seed-catalogue/")
        self.assertEqual(seed.status_code, 200)
        self.assertGreater(seed.data["created_dimensions"], 10)

        prog_dim = AssessmentDimension.objects.get(institution=self.inst_a, code="PROG")
        int_dim = AssessmentDimension.objects.get(institution=self.inst_a, code="INT_AIML")

        # Guardrail 1: Likert cannot be labeled demonstrated_performance
        bad_likert = self.client.post(
            "/api/v1/assessments/questions/",
            {
                "question_code": "Q_BAD_LIKERT",
                "question_type": "likert",
                "prompt": "Rate your confidence in Python",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "likert_scale",
                "max_marks": "5.00",
                "options": [
                    {"option_key": "1", "option_text": "Novice", "display_order": 1},
                    {"option_key": "5", "option_text": "Expert", "display_order": 2},
                ],
                "dimensions": [{"dimension_id": str(prog_dim.id), "weight": "1.00"}],
            },
            format="json",
        )
        self.assertEqual(bad_likert.status_code, 400)

        # Guardrail 2: Cannot link demonstrated_performance question to stated_interest dimension
        bad_mix = self.client.post(
            "/api/v1/assessments/questions/",
            {
                "question_code": "Q_BAD_MIX",
                "question_type": "single_mcq",
                "prompt": "What is O(log n)?",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": "2.00",
                "options": [
                    {"option_key": "A", "option_text": "Binary search", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "Linear scan", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": str(int_dim.id), "weight": "1.00"}],
            },
            format="json",
        )
        self.assertEqual(bad_mix.status_code, 400)

        # Guardrail 3: Single MCQ with 0 correct options rejected
        bad_mcq = self.client.post(
            "/api/v1/assessments/questions/",
            {
                "question_code": "Q_BAD_MCQ",
                "question_type": "single_mcq",
                "prompt": "Pick one",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": "2.00",
                "options": [
                    {"option_key": "A", "option_text": "One", "display_order": 1, "is_correct": False},
                    {"option_key": "B", "option_text": "Two", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": str(prog_dim.id), "weight": "1.00"}],
            },
            format="json",
        )
        self.assertEqual(bad_mcq.status_code, 400)

    def test_template_versioning_immutability_and_cross_tenant_isolation(self):
        self._login("admin", "assessor.a@mitt.test", "MITT")
        self.client.post("/api/v1/assessments/seed-catalogue/")
        prog_dim = AssessmentDimension.objects.get(institution=self.inst_a, code="PROG")

        q1 = self.client.post(
            "/api/v1/assessments/questions/",
            {
                "question_code": "PROG_001",
                "question_type": "single_mcq",
                "prompt": "Which data structure uses LIFO?",
                "difficulty": "easy",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": "4.00",
                "negative_marks": "1.00",
                "options": [
                    {"option_key": "A", "option_text": "Stack", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "Queue", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": str(prog_dim.id), "weight": "1.00"}],
            },
            format="json",
        )
        self.assertEqual(q1.status_code, 201)
        q1_id = q1.data["id"]

        # Create template (auto-creates draft v1)
        tmpl = self.client.post(
            "/api/v1/assessments/templates/",
            {"name": "MCA Sem 1 Baseline", "description": "Initial baseline", "duration_minutes": 45},
            format="json",
        )
        self.assertEqual(tmpl.status_code, 201)
        v1_id = tmpl.data["versions"][0]["id"]

        # Cannot publish empty draft
        self.assertEqual(self.client.post(f"/api/v1/assessments/versions/{v1_id}/publish/").status_code, 400)

        # Add question to draft v1
        upd = self.client.patch(
            f"/api/v1/assessments/versions/{v1_id}/",
            {"items": [{"question_id": q1_id, "marks": "5.00", "negative_marks": "1.00", "required": True}]},
            format="json",
        )
        self.assertEqual(upd.status_code, 200)
        self.assertEqual(upd.data["total_marks"], "5.00")

        # Publish v1
        pub = self.client.post(f"/api/v1/assessments/versions/{v1_id}/publish/")
        self.assertEqual(pub.status_code, 200)
        self.assertEqual(pub.data["status"], AssessmentVersion.Status.PUBLISHED)
        snapshot = pub.data["version_questions"][0]["question_snapshot"]
        self.assertEqual(snapshot["prompt"], "Which data structure uses LIFO?")

        # Published version is immutable
        mut_pub = self.client.patch(
            f"/api/v1/assessments/versions/{v1_id}/",
            {"duration_minutes": 90},
            format="json",
        )
        self.assertEqual(mut_pub.status_code, 400)

        # Editing Question bank item later does NOT alter published snapshot
        self.client.patch(
            f"/api/v1/assessments/questions/{q1_id}/",
            {"prompt": "UPDATED PROMPT AFTER PUBLISH"},
            format="json",
        )
        v1_check = self.client.get(f"/api/v1/assessments/versions/{v1_id}/")
        self.assertEqual(
            v1_check.data["version_questions"][0]["question_snapshot"]["prompt"],
            "Which data structure uses LIFO?",
        )

        # Clone published v1 to new draft v2
        cloned = self.client.post(f"/api/v1/assessments/versions/{v1_id}/clone/")
        self.assertEqual(cloned.status_code, 201)
        self.assertEqual(cloned.data["version_no"], 2)
        self.assertEqual(cloned.data["status"], AssessmentVersion.Status.DRAFT)
        self.assertTrue(AuditEvent.objects.filter(action="ASSESSMENT_VERSION_PUBLISHED").exists())

        # Cross-institution isolation: Assessor B cannot access Inst A template/version/question
        self._login("admin", "assessor.b@demob.test", "DEMOB")
        self.assertEqual(self.client.get(f"/api/v1/assessments/questions/{q1_id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/assessments/versions/{v1_id}/").status_code, 404)

