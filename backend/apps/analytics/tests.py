"""Phase 4 tests: domain analytics, measurement separation, scoping, and CSV/XLSX/PDF exports."""
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Cohort, Programme
from apps.accounts.models import Role, User
from apps.accounts.rbac import ROLE_ASSESSMENT_ADMIN, ROLE_FACULTY_HOD, ROLE_STUDENT
from apps.accounts.services import seed_roles_and_permissions
from apps.assessments.models import AssessmentDimension, MeasurementFamily
from apps.assessments.services import (
    create_assessment_template,
    create_question,
    publish_assessment_version,
    seed_starter_catalogue,
    update_draft_version,
)
from apps.attempts.services import (
    autosave_attempt_responses,
    create_assessment_assignment,
    start_or_resume_attempt,
    submit_attempt,
)
from apps.audit.models import AuditEvent
from apps.faculty.models import CohortFaculty, FacultyProfile
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership, MembershipRole


class AnalyticsAndExportsPhase4Tests(TestCase):
    """Verify cohort analytics, student comparison, individual reports, scoping, and exports."""

    @classmethod
    def setUpTestData(cls):
        seed_roles_and_permissions()
        cls.inst = Institution.objects.create(code="MITT", name="MIT Thandavapura")

        cls.assessor = User.objects.create_user(email="assessor@mitt.test", password="StrongPass!123", first_name="Assessor")
        m_ass = Membership.objects.create(institution=cls.inst, user=cls.assessor)
        MembershipRole.objects.create(membership=m_ass, role=Role.objects.get(code=ROLE_ASSESSMENT_ADMIN))

        cls.prog = Programme.objects.create(institution=cls.inst, code="MCA", name="MCA")
        cls.ay = AcademicYear.objects.create(institution=cls.inst, name="2025-26", start_date=date(2025, 8, 1), end_date=date(2026, 7, 31))
        cls.cohort_a = Cohort.objects.create(institution=cls.inst, programme=cls.prog, academic_year=cls.ay, batch_name="2025", semester=1, section="A")
        cls.cohort_b = Cohort.objects.create(institution=cls.inst, programme=cls.prog, academic_year=cls.ay, batch_name="2025", semester=1, section="B")

        # Student A in Cohort A, Student B in Cohort B
        cls.stu_a_user = User.objects.create_user(email="stu.a@mitt.test", password="StrongPass!123", first_name="Aarav", last_name="S")
        m_sa = Membership.objects.create(institution=cls.inst, user=cls.stu_a_user)
        MembershipRole.objects.create(membership=m_sa, role=Role.objects.get(code=ROLE_STUDENT))
        cls.stu_a = StudentProfile.objects.create(institution=cls.inst, membership=m_sa, cohort=cls.cohort_a, registration_no="4MT25MC001")

        cls.stu_b_user = User.objects.create_user(email="stu.b@mitt.test", password="StrongPass!123", first_name="Divya", last_name="R")
        m_sb = Membership.objects.create(institution=cls.inst, user=cls.stu_b_user)
        MembershipRole.objects.create(membership=m_sb, role=Role.objects.get(code=ROLE_STUDENT))
        cls.stu_b = StudentProfile.objects.create(institution=cls.inst, membership=m_sb, cohort=cls.cohort_b, registration_no="4MT25MC002")

        # Faculty assigned ONLY to Cohort A
        cls.fac_user = User.objects.create_user(email="fac@mitt.test", password="StrongPass!123", first_name="Dr. Kavitha")
        m_fa = Membership.objects.create(institution=cls.inst, user=cls.fac_user)
        MembershipRole.objects.create(membership=m_fa, role=Role.objects.get(code=ROLE_FACULTY_HOD))
        cls.fac = FacultyProfile.objects.create(institution=cls.inst, membership=m_fa, employee_code="FAC01")
        CohortFaculty.objects.create(institution=cls.inst, cohort=cls.cohort_a, faculty_profile=cls.fac)

        seed_starter_catalogue(institution=cls.inst, actor_user=cls.assessor)
        dim_prog = AssessmentDimension.objects.get(institution=cls.inst, code="PROG")
        dim_dsa = AssessmentDimension.objects.get(institution=cls.inst, code="DSA")
        dim_int = AssessmentDimension.objects.get(institution=cls.inst, code="INT_AIML")

        q1 = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "A_PROG",
                "question_type": "single_mcq",
                "prompt": "Python list append complexity?",
                "difficulty": "easy",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": Decimal("10.00"),
                "negative_marks": Decimal("0.00"),
                "options": [
                    {"option_key": "A", "option_text": "O(1) amortized", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "O(n)", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": dim_prog.id, "weight": Decimal("1.00")}],
            },
        )
        q2 = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "A_DSA",
                "question_type": "single_mcq",
                "prompt": "Worst case quicksort?",
                "difficulty": "medium",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": Decimal("10.00"),
                "negative_marks": Decimal("0.00"),
                "options": [
                    {"option_key": "A", "option_text": "O(n^2)", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "O(n log n)", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": dim_dsa.id, "weight": Decimal("1.00")}],
            },
        )
        q3 = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "A_INT",
                "question_type": "likert",
                "prompt": "Interest in AI/ML projects",
                "difficulty": "easy",
                "measurement_family": MeasurementFamily.STATED_INTEREST,
                "scoring_method": "likert_scale",
                "max_marks": Decimal("5.00"),
                "negative_marks": Decimal("0.00"),
                "options": [
                    {"option_key": "1", "option_text": "Low", "display_order": 1},
                    {"option_key": "5", "option_text": "High", "display_order": 2},
                ],
                "dimensions": [{"dimension_id": dim_int.id, "weight": Decimal("1.00")}],
            },
        )

        tmpl = create_assessment_template(institution=cls.inst, name="Phase 4 Baseline", actor_user=cls.assessor)
        v1 = update_draft_version(
            version=tmpl.versions.first(),
            data={"items": [{"question_id": q1.id}, {"question_id": q2.id}, {"question_id": q3.id}]},
            actor_user=cls.assessor,
        )
        pub = publish_assessment_version(version=v1, actor_user=cls.assessor)

        now = timezone.now()
        cls.assign_a = create_assessment_assignment(
            institution=cls.inst,
            assessment_version_id=pub.id,
            cohort_id=cls.cohort_a.id,
            opens_at=now - timedelta(minutes=5),
            closes_at=now + timedelta(hours=2),
            results_released=True,
            actor_user=cls.assessor,
        )
        att = start_or_resume_attempt(assignment=cls.assign_a, student=cls.stu_a, actor_user=cls.stu_a_user)
        vqs = {vq.question.question_code: vq.id for vq in pub.version_questions.all()}
        autosave_attempt_responses(
            attempt=att,
            items=[
                {"version_question_id": vqs["A_PROG"], "response_json": {"selected_keys": ["A"]}},  # 10/10 = 100%
                {"version_question_id": vqs["A_DSA"], "response_json": {"selected_keys": ["B"]}},   # 0/10 = 0%
                {"version_question_id": vqs["A_INT"], "response_json": {"selected_keys": ["5"]}},   # Interest 5
            ],
            actor_user=cls.stu_a_user,
        )
        submit_attempt(attempt=att, actor_user=cls.stu_a_user)

    def setUp(self):
        self.client = APIClient()

    def _login(self, portal: str, email: str):
        res = self.client.post(
            "/api/v1/auth/login/",
            {"portal": portal, "identifier": email, "password": "StrongPass!123", "institution_code": "MITT"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    def test_faculty_cohort_scoping_and_analytics_strength_gap_separation(self):
        self._login("academic", "fac@mitt.test")

        cohorts_res = self.client.get("/api/v1/analytics/cohorts/")
        self.assertEqual(cohorts_res.status_code, 200)
        self.assertEqual([c["id"] for c in cohorts_res.data], [str(self.cohort_a.id)])

        # Denied Cohort B analytics & Student B individual report
        self.assertEqual(self.client.get(f"/api/v1/analytics/cohorts/{self.cohort_b.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/analytics/students/{self.stu_b.id}/").status_code, 404)

        # Cohort A analytics
        ca_res = self.client.get(f"/api/v1/analytics/cohorts/{self.cohort_a.id}/")
        self.assertEqual(ca_res.status_code, 200)
        self.assertEqual(ca_res.data["summary"]["cohort_average_percentage"], 50.0)
        self.assertEqual(ca_res.data["summary"]["students_needing_training"], 1)
        self.assertEqual(ca_res.data["cohort_strengths"][0]["code"], "PROG")
        self.assertEqual(ca_res.data["cohort_gaps"][0]["code"], "DSA")
        self.assertEqual(ca_res.data["stated_interest_domains"][0]["code"], "INT_AIML")

        # Individual report
        ind_res = self.client.get(f"/api/v1/analytics/students/{self.stu_a.id}/")
        self.assertEqual(ind_res.status_code, 200)
        self.assertEqual(ind_res.data["demonstrated_performance"]["strengths"][0]["code"], "PROG")
        self.assertEqual(ind_res.data["demonstrated_performance"]["gaps"][0]["code"], "DSA")
        self.assertEqual(ind_res.data["stated_interest"][0]["average_rating"], 5.0)

    def test_student_my_reports_and_denied_cohort_exports(self):
        self._login("academic", "stu.a@mitt.test")
        my_res = self.client.get("/api/v1/analytics/my-reports/")
        self.assertEqual(my_res.status_code, 200)
        self.assertEqual(my_res.data["summary"]["overall_demonstrated_percentage"], 50.0)
        self.assertEqual(my_res.data["summary"]["cohort_benchmark_percentage"], 50.0)

        # Student denied cohort analytics, other student report, and exports
        self.assertEqual(self.client.get(f"/api/v1/analytics/cohorts/{self.cohort_a.id}/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/analytics/students/{self.stu_b.id}/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/analytics/exports/?export_format=csv&cohort_id={self.cohort_a.id}").status_code, 403)

    def test_csv_xlsx_and_pdf_exports_with_audit_events(self):
        self._login("academic", "fac@mitt.test")
        for fmt, expected_ct in [
            ("csv", "text/csv"),
            ("xlsx", "spreadsheetml"),
            ("pdf", "application/pdf"),
        ]:
            res = self.client.get(f"/api/v1/analytics/exports/?export_format={fmt}&cohort_id={self.cohort_a.id}")
            self.assertEqual(res.status_code, 200)
            self.assertIn(expected_ct, res["Content-Type"])
            if fmt == "pdf":
                self.assertTrue(res.content.startswith(b"%PDF-1.4"))

        stu_pdf = self.client.get(f"/api/v1/analytics/exports/?export_format=pdf&student_id={self.stu_a.id}")
        self.assertEqual(stu_pdf.status_code, 200)
        self.assertTrue(stu_pdf.content.startswith(b"%PDF-1.4"))
        self.assertEqual(AuditEvent.objects.filter(action="REPORT_EXPORTED").count(), 4)

