"""Phase 2 tests: RBAC, measurement-family separation, scoring, immutable versions, and isolation."""
from django.core.files.uploadedfile import SimpleUploadedFile
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

    def test_bulk_question_import_template_preview_commit_and_guardrails(self):
        self._login("admin", "assessor.a@mitt.test", "MITT")
        self.client.post("/api/v1/assessments/seed-catalogue/")

        # Template downloads work for xlsx & csv
        tpl_xlsx = self.client.get("/api/v1/assessments/questions/import-template/?export_format=xlsx")
        self.assertEqual(tpl_xlsx.status_code, 200)
        self.assertIn("spreadsheetml", tpl_xlsx["Content-Type"])
        self.assertTrue(tpl_xlsx.content.startswith(b"PK"))

        tpl_csv = self.client.get("/api/v1/assessments/questions/import-template/?export_format=csv")
        self.assertEqual(tpl_csv.status_code, 200)
        self.assertIn("question_code,question_type", tpl_csv.content.decode("utf-8"))

        # Mixed valid rows (MCQ, True/False, Numeric, Descriptive, Likert) + 1 invalid row (Likert as demonstrated)
        import csv as _csv
        import io as _io
        from apps.assessments.bulk_import import TEMPLATE_HEADERS

        buf = _io.StringIO()
        w = _csv.writer(buf)
        w.writerow(TEMPLATE_HEADERS)
        w.writerow(["BLK_MCQ", "single_mcq", "Which protocol is stateless?", "demonstrated_performance", "PROG", "2", "0.5", "easy", "exact", "HTTP", "FTP", "SMTP", "", "", "A", "", "", "", "web"])
        w.writerow(["BLK_TF", "true_false", "Stack is LIFO.", "demonstrated_performance", "DSA", "1", "0", "easy", "exact", "", "", "", "", "", "TRUE", "", "", "", "dsa"])
        w.writerow(["BLK_NUM", "numeric", "Binary of decimal 10?", "demonstrated_performance", "PROG", "2", "0", "medium", "tolerance", "", "", "", "", "", "", "1010", "0", "", "binary"])
        w.writerow(["BLK_DESC", "descriptive", "Explain ACID properties.", "demonstrated_performance", "DBMS", "5", "0", "medium", "rubric", "", "", "", "", "", "", "", "", "Award 1 mark per property", "dbms"])
        w.writerow(["BLK_INT", "likert", "Interest in SDE?", "stated_interest", "INT_SDE", "5", "0", "easy", "likert_scale", "", "", "", "", "", "", "", "", "", "interest"])
        w.writerow(["BLK_BAD", "likert", "Bad measurement family", "demonstrated_performance", "PROG", "5", "0", "easy", "likert_scale", "", "", "", "", "", "", "", "", "", "invalid"])
        csv_content = buf.getvalue().encode("utf-8")

        preview_res = self.client.post(
            "/api/v1/assessments/questions/bulk-import/preview/",
            {"file": SimpleUploadedFile("questions.csv", csv_content, content_type="text/csv")},
            format="multipart",
        )
        self.assertEqual(preview_res.status_code, 200)
        self.assertEqual(preview_res.data["summary"]["total_rows"], 6)
        self.assertEqual(preview_res.data["summary"]["valid_count"], 5)
        self.assertEqual(preview_res.data["summary"]["error_count"], 1)
        self.assertFalse(preview_res.data["rows"][5]["valid"])

        # all_or_nothing rejects when any error exists
        abort_res = self.client.post(
            "/api/v1/assessments/questions/bulk-import/commit/",
            {"file": SimpleUploadedFile("questions.csv", csv_content, content_type="text/csv"), "mode": "all_or_nothing"},
            format="multipart",
        )
        self.assertEqual(abort_res.status_code, 400)

        # skip_invalid commits all 5 valid questions & emits aggregate audit event
        commit_res = self.client.post(
            "/api/v1/assessments/questions/bulk-import/commit/",
            {"file": SimpleUploadedFile("questions.csv", csv_content, content_type="text/csv"), "mode": "skip_invalid"},
            format="multipart",
        )
        self.assertEqual(commit_res.status_code, 201)
        self.assertEqual(commit_res.data["created_count"], 5)
        self.assertEqual(commit_res.data["skipped_count"], 1)
        self.assertTrue(AuditEvent.objects.filter(institution=self.inst_a, action="QUESTION_BULK_IMPORTED").exists())

        # Invalid extension rejected
        bad_ext = self.client.post(
            "/api/v1/assessments/questions/bulk-import/preview/",
            {"file": SimpleUploadedFile("malware.exe", b"MZ", content_type="application/octet-stream")},
            format="multipart",
        )
        self.assertEqual(bad_ext.status_code, 400)

        # Student denied
        self._login("academic", "stu.a@mitt.test", "MITT")
        self.assertEqual(self.client.get("/api/v1/assessments/questions/import-template/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/assessments/questions/bulk-import/preview/",
                {"file": SimpleUploadedFile("q.csv", csv_content, content_type="text/csv")},
                format="multipart",
            ).status_code,
            403,
        )

