"""Phase 6 tests: Faculty/HOD intelligence, placement readiness, pre/post comparison & executive reports."""
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Cohort, Programme
from apps.accounts.models import Role, User
from apps.accounts.rbac import ROLE_ASSESSMENT_ADMIN, ROLE_FACULTY_HOD, ROLE_INSTITUTION_ADMIN, ROLE_STUDENT
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
from apps.development.services import add_plan_activity, create_development_plan, record_activity_progress
from apps.faculty.models import CohortFaculty, FacultyProfile
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership, MembershipRole


class InstitutionalIntelligencePhase6Tests(TestCase):
    """Verify Faculty intelligence, placement readiness, pre/post deltas, executive reports & exports."""

    @classmethod
    def setUpTestData(cls):
        seed_roles_and_permissions()
        cls.inst = Institution.objects.create(code="MITT", name="MIT Thandavapura")
        cls.other_inst = Institution.objects.create(code="DEMOB", name="Demo B Institution")

        cls.assessor = User.objects.create_user(email="assessor@mitt.test", password="StrongPass!123", first_name="Assessor")
        m_ass = Membership.objects.create(institution=cls.inst, user=cls.assessor)
        MembershipRole.objects.create(membership=m_ass, role=Role.objects.get(code=ROLE_ASSESSMENT_ADMIN))

        cls.other_admin = User.objects.create_user(email="admin@demob.test", password="StrongPass!123", first_name="OtherAdmin")
        m_other = Membership.objects.create(institution=cls.other_inst, user=cls.other_admin)
        MembershipRole.objects.create(membership=m_other, role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN))

        cls.prog = Programme.objects.create(institution=cls.inst, code="MCA", name="MCA")
        cls.ay = AcademicYear.objects.create(institution=cls.inst, name="2025-26", start_date=date(2025, 8, 1), end_date=date(2026, 7, 31))
        cls.cohort_a = Cohort.objects.create(institution=cls.inst, programme=cls.prog, academic_year=cls.ay, batch_name="2025", semester=1, section="A")
        cls.cohort_b = Cohort.objects.create(institution=cls.inst, programme=cls.prog, academic_year=cls.ay, batch_name="2025", semester=1, section="B")

        # Cohort A: Student A (Placement Ready after Post) & Student C (Needs Support)
        cls.stu_a_user = User.objects.create_user(email="stu.a@mitt.test", password="StrongPass!123", first_name="Aarav", last_name="S")
        m_sa = Membership.objects.create(institution=cls.inst, user=cls.stu_a_user)
        MembershipRole.objects.create(membership=m_sa, role=Role.objects.get(code=ROLE_STUDENT))
        cls.stu_a = StudentProfile.objects.create(institution=cls.inst, membership=m_sa, cohort=cls.cohort_a, registration_no="4MT25MC001")

        cls.stu_c_user = User.objects.create_user(email="stu.c@mitt.test", password="StrongPass!123", first_name="Kiran", last_name="M")
        m_sc = Membership.objects.create(institution=cls.inst, user=cls.stu_c_user)
        MembershipRole.objects.create(membership=m_sc, role=Role.objects.get(code=ROLE_STUDENT))
        cls.stu_c = StudentProfile.objects.create(institution=cls.inst, membership=m_sc, cohort=cls.cohort_a, registration_no="4MT25MC003")

        # Cohort B: Student B
        cls.stu_b_user = User.objects.create_user(email="stu.b@mitt.test", password="StrongPass!123", first_name="Divya", last_name="R")
        m_sb = Membership.objects.create(institution=cls.inst, user=cls.stu_b_user)
        MembershipRole.objects.create(membership=m_sb, role=Role.objects.get(code=ROLE_STUDENT))
        cls.stu_b = StudentProfile.objects.create(institution=cls.inst, membership=m_sb, cohort=cls.cohort_b, registration_no="4MT25MC002")

        # Faculty assigned strictly to Cohort A
        cls.fac_user = User.objects.create_user(email="fac@mitt.test", password="StrongPass!123", first_name="Dr. Kavitha")
        m_fa = Membership.objects.create(institution=cls.inst, user=cls.fac_user)
        MembershipRole.objects.create(membership=m_fa, role=Role.objects.get(code=ROLE_FACULTY_HOD))
        cls.fac = FacultyProfile.objects.create(institution=cls.inst, membership=m_fa, employee_code="FAC01")
        CohortFaculty.objects.create(institution=cls.inst, cohort=cls.cohort_a, faculty_profile=cls.fac)

        seed_starter_catalogue(institution=cls.inst, actor_user=cls.assessor)
        dim_prog = AssessmentDimension.objects.get(institution=cls.inst, code="PROG")
        dim_dsa = AssessmentDimension.objects.get(institution=cls.inst, code="DSA")
        dim_int = AssessmentDimension.objects.get(institution=cls.inst, code="INT_SDE")

        q_prog = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "P6_PROG",
                "question_type": "single_mcq",
                "prompt": "Python generator keyword?",
                "difficulty": "easy",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": Decimal("10.00"),
                "negative_marks": Decimal("0.00"),
                "options": [
                    {"option_key": "A", "option_text": "yield", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "emit", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": dim_prog.id, "weight": Decimal("1.00")}],
            },
        )
        q_dsa = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "P6_DSA",
                "question_type": "single_mcq",
                "prompt": "Binary search time complexity?",
                "difficulty": "medium",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": Decimal("10.00"),
                "negative_marks": Decimal("0.00"),
                "options": [
                    {"option_key": "A", "option_text": "O(log n)", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "O(n^2)", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": dim_dsa.id, "weight": Decimal("1.00")}],
            },
        )
        q_int = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "P6_INT",
                "question_type": "likert",
                "prompt": "Interest in SDE",
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

        cls.pre_tmpl = create_assessment_template(institution=cls.inst, name="Baseline Entry Test", actor_user=cls.assessor)
        pre_v1 = update_draft_version(
            version=cls.pre_tmpl.versions.first(),
            data={"items": [{"question_id": q_prog.id}, {"question_id": q_dsa.id}, {"question_id": q_int.id}]},
            actor_user=cls.assessor,
        )
        pre_pub = publish_assessment_version(version=pre_v1, actor_user=cls.assessor)

        cls.post_tmpl = create_assessment_template(institution=cls.inst, name="Post Training Evaluation", actor_user=cls.assessor)
        post_v1 = update_draft_version(
            version=cls.post_tmpl.versions.first(),
            data={"items": [{"question_id": q_prog.id}, {"question_id": q_dsa.id}]},
            actor_user=cls.assessor,
        )
        post_pub = publish_assessment_version(version=post_v1, actor_user=cls.assessor)

        now = timezone.now()
        pre_assign_a = create_assessment_assignment(
            institution=cls.inst,
            assessment_version_id=pre_pub.id,
            cohort_id=cls.cohort_a.id,
            opens_at=now - timedelta(minutes=10),
            closes_at=now + timedelta(hours=2),
            results_released=True,
            actor_user=cls.assessor,
        )
        post_assign_a = create_assessment_assignment(
            institution=cls.inst,
            assessment_version_id=post_pub.id,
            cohort_id=cls.cohort_a.id,
            opens_at=now - timedelta(minutes=5),
            closes_at=now + timedelta(hours=2),
            results_released=True,
            actor_user=cls.assessor,
        )

        # Student A: Pre = 50% (PROG A, DSA B), Post = 100% (PROG A, DSA A) -> avg 75% => Placement Ready!
        pre_vqs = {vq.question.question_code: vq.id for vq in pre_pub.version_questions.all()}
        post_vqs = {vq.question.question_code: vq.id for vq in post_pub.version_questions.all()}

        att_a_pre = start_or_resume_attempt(assignment=pre_assign_a, student=cls.stu_a, actor_user=cls.stu_a_user)
        autosave_attempt_responses(
            attempt=att_a_pre,
            items=[
                {"version_question_id": pre_vqs["P6_PROG"], "response_json": {"selected_keys": ["A"]}},
                {"version_question_id": pre_vqs["P6_DSA"], "response_json": {"selected_keys": ["B"]}},
                {"version_question_id": pre_vqs["P6_INT"], "response_json": {"selected_keys": ["5"]}},
            ],
            actor_user=cls.stu_a_user,
        )
        submit_attempt(attempt=att_a_pre, actor_user=cls.stu_a_user)

        att_a_post = start_or_resume_attempt(assignment=post_assign_a, student=cls.stu_a, actor_user=cls.stu_a_user)
        autosave_attempt_responses(
            attempt=att_a_post,
            items=[
                {"version_question_id": post_vqs["P6_PROG"], "response_json": {"selected_keys": ["A"]}},
                {"version_question_id": post_vqs["P6_DSA"], "response_json": {"selected_keys": ["A"]}},
            ],
            actor_user=cls.stu_a_user,
        )
        submit_attempt(attempt=att_a_post, actor_user=cls.stu_a_user)

        # Student C: Pre = 0% -> Needs Support
        att_c_pre = start_or_resume_attempt(assignment=pre_assign_a, student=cls.stu_c, actor_user=cls.stu_c_user)
        autosave_attempt_responses(
            attempt=att_c_pre,
            items=[
                {"version_question_id": pre_vqs["P6_PROG"], "response_json": {"selected_keys": ["B"]}},
                {"version_question_id": pre_vqs["P6_DSA"], "response_json": {"selected_keys": ["B"]}},
            ],
            actor_user=cls.stu_c_user,
        )
        submit_attempt(attempt=att_c_pre, actor_user=cls.stu_c_user)

        # Student A development plan with 100% progress
        plan = create_development_plan(
            institution=cls.inst,
            student=cls.stu_a,
            data={"title": "DSA Mastery", "target_domain": "Software Development"},
            actor_user=cls.fac_user,
        )
        act = add_plan_activity(plan=plan, data={"title": "Complete Binary Search Lab"}, actor_user=cls.fac_user)
        record_activity_progress(activity=act, progress_percent=100, reflection="Mastered", actor_user=cls.stu_a_user)

    def _login(self, portal: str, email: str, inst_code: str = "MITT") -> APIClient:
        client = APIClient()
        res = client.post(
            "/api/v1/auth/login/",
            {"portal": portal, "identifier": email, "password": "StrongPass!123", "institution_code": inst_code},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        return client

    def test_faculty_intelligence_scoping_readiness_and_pre_post_deltas(self):
        fac = self._login("academic", "fac@mitt.test")

        intel_res = fac.get("/api/v1/analytics/intelligence/")
        self.assertEqual(intel_res.status_code, 200)
        self.assertEqual(intel_res.data["summary"]["authorized_cohorts"], 1)
        self.assertEqual(intel_res.data["summary"]["total_students"], 2)
        self.assertEqual(intel_res.data["summary"]["placement_ready_count"], 1)
        self.assertEqual(intel_res.data["summary"]["needs_support_count"], 1)
        self.assertEqual(intel_res.data["summary"]["avg_plan_completion_percent"], 100)
        self.assertIn("Mentor", intel_res.data["cohort_rollups"][0]["assigned_mentors"][0])

        # Cohort B is off-limits to Cohort A faculty -> 404; Executive report -> 403
        self.assertEqual(fac.get(f"/api/v1/analytics/intelligence/?cohort_id={self.cohort_b.id}").status_code, 404)
        self.assertEqual(fac.get("/api/v1/analytics/executive/").status_code, 403)

        # Pre/Post comparison between Baseline Entry Test & Post Training Evaluation
        pp_res = fac.get(
            f"/api/v1/analytics/pre-post/?pre_template_id={self.pre_tmpl.id}&post_template_id={self.post_tmpl.id}"
        )
        self.assertEqual(pp_res.status_code, 200)
        self.assertEqual(pp_res.data["summary"]["comparable_students"], 1)
        self.assertEqual(pp_res.data["summary"]["pre_average_percentage"], 50.0)
        self.assertEqual(pp_res.data["summary"]["post_average_percentage"], 100.0)
        self.assertEqual(pp_res.data["summary"]["average_delta"], 50.0)
        self.assertEqual(pp_res.data["summary"]["improved_students_count"], 1)

        dsa_delta = next(d for d in pp_res.data["dimension_deltas"] if d["code"] == "DSA")
        self.assertEqual(dsa_delta["pre_percentage"], 0.0)
        self.assertEqual(dsa_delta["post_percentage"], 100.0)
        self.assertEqual(dsa_delta["delta_percentage"], 100.0)

    def test_executive_report_exports_student_denial_and_cross_tenant_isolation(self):
        admin = self._login("admin", "assessor@mitt.test")

        exec_res = admin.get("/api/v1/analytics/executive/")
        self.assertEqual(exec_res.status_code, 200)
        self.assertEqual(exec_res.data["summary"]["total_cohorts"], 2)
        self.assertEqual(exec_res.data["summary"]["total_students"], 3)
        self.assertEqual(exec_res.data["summary"]["placement_ready_count"], 1)
        self.assertEqual(exec_res.data["stated_interest_domains"][0]["code"], "INT_SDE")

        for fmt, expected_ct in [
            ("csv", "text/csv"),
            ("xlsx", "spreadsheetml"),
            ("pdf", "application/pdf"),
        ]:
            exp = admin.get(f"/api/v1/analytics/executive/export/?export_format={fmt}")
            self.assertEqual(exp.status_code, 200)
            self.assertIn(expected_ct, exp["Content-Type"])
            if fmt == "pdf":
                self.assertTrue(exp.content.startswith(b"%PDF-1.4"))

        self.assertEqual(AuditEvent.objects.filter(institution=self.inst, action="EXECUTIVE_REPORT_EXPORTED").count(), 3)

        # Student is denied all Phase 6 endpoints
        stu = self._login("academic", "stu.a@mitt.test")
        self.assertEqual(stu.get("/api/v1/analytics/intelligence/").status_code, 403)
        self.assertEqual(stu.get("/api/v1/analytics/pre-post/").status_code, 403)
        self.assertEqual(stu.get("/api/v1/analytics/executive/").status_code, 403)
        self.assertEqual(stu.get("/api/v1/analytics/executive/export/?export_format=csv").status_code, 403)

        # Cross-tenant isolation: DEMOB admin sees 0 cohorts/students in DEMOB executive report
        other = self._login("admin", "admin@demob.test", "DEMOB")
        other_exec = other.get("/api/v1/analytics/executive/")
        self.assertEqual(other_exec.status_code, 200)
        self.assertEqual(other_exec.data["summary"]["total_cohorts"], 0)
        self.assertEqual(other_exec.data["summary"]["total_students"], 0)

