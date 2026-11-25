"""Phase 3 tests: assignments, answer-key protection, autosave, timer, scoring, and evaluation."""
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Cohort, Programme
from apps.accounts.models import Role, User
from apps.accounts.rbac import (
    ROLE_ASSESSMENT_ADMIN,
    ROLE_FACULTY_HOD,
    ROLE_STUDENT,
)
from apps.accounts.services import seed_roles_and_permissions
from apps.assessments.models import (
    AssessmentDimension,
    MeasurementFamily,
)
from apps.assessments.services import (
    create_assessment_template,
    create_question,
    publish_assessment_version,
    seed_starter_catalogue,
    update_draft_version,
)
from apps.attempts.models import AssessmentAttempt, AssessmentResult, Evaluation
from apps.faculty.models import CohortFaculty, FacultyProfile
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership, MembershipRole


class AssessmentDeliveryAndEvaluationTests(TestCase):
    """Verify Phase 3 assignment constraints, test runner, scoring, and manual grading."""

    @classmethod
    def setUpTestData(cls):
        seed_roles_and_permissions()
        cls.inst_a = Institution.objects.create(code="MITT", name="MIT Thandavapura")
        cls.inst_b = Institution.objects.create(code="DEMOB", name="Demo Institute B")

        cls.assessor = User.objects.create_user(email="assessor@mitt.test", password="StrongPass!123", first_name="Assessor")
        m_ass = Membership.objects.create(institution=cls.inst_a, user=cls.assessor)
        MembershipRole.objects.create(membership=m_ass, role=Role.objects.get(code=ROLE_ASSESSMENT_ADMIN))

        cls.prog = Programme.objects.create(institution=cls.inst_a, code="MCA", name="MCA")
        cls.ay = AcademicYear.objects.create(institution=cls.inst_a, name="2025-26", start_date=date(2025, 8, 1), end_date=date(2026, 7, 31))
        cls.cohort_a = Cohort.objects.create(institution=cls.inst_a, programme=cls.prog, academic_year=cls.ay, batch_name="2025", semester=1, section="A")
        cls.cohort_b = Cohort.objects.create(institution=cls.inst_a, programme=cls.prog, academic_year=cls.ay, batch_name="2025", semester=1, section="B")

        # Students in cohort_a and cohort_b
        cls.stu_a_user = User.objects.create_user(email="stu.a@mitt.test", password="StrongPass!123", first_name="StuA")
        m_sa = Membership.objects.create(institution=cls.inst_a, user=cls.stu_a_user)
        MembershipRole.objects.create(membership=m_sa, role=Role.objects.get(code=ROLE_STUDENT))
        cls.stu_a = StudentProfile.objects.create(institution=cls.inst_a, membership=m_sa, cohort=cls.cohort_a, registration_no="4MT25MC001")

        cls.stu_b_user = User.objects.create_user(email="stu.b@mitt.test", password="StrongPass!123", first_name="StuB")
        m_sb = Membership.objects.create(institution=cls.inst_a, user=cls.stu_b_user)
        MembershipRole.objects.create(membership=m_sb, role=Role.objects.get(code=ROLE_STUDENT))
        cls.stu_b = StudentProfile.objects.create(institution=cls.inst_a, membership=m_sb, cohort=cls.cohort_b, registration_no="4MT25MC002")

        # Faculty assigned ONLY to cohort_a
        cls.fac_user = User.objects.create_user(email="fac.a@mitt.test", password="StrongPass!123", first_name="FacA")
        m_fa = Membership.objects.create(institution=cls.inst_a, user=cls.fac_user)
        MembershipRole.objects.create(membership=m_fa, role=Role.objects.get(code=ROLE_FACULTY_HOD))
        cls.fac_a = FacultyProfile.objects.create(institution=cls.inst_a, membership=m_fa, employee_code="FAC1")
        CohortFaculty.objects.create(institution=cls.inst_a, cohort=cls.cohort_a, faculty_profile=cls.fac_a)

        # Seed catalogue & questions across all 3 measurement families
        seed_starter_catalogue(institution=cls.inst_a, actor_user=cls.assessor)
        dim_prog = AssessmentDimension.objects.get(institution=cls.inst_a, code="PROG")
        dim_comm = AssessmentDimension.objects.get(institution=cls.inst_a, code="COMM")

        cls.q_mcq = create_question(
            institution=cls.inst_a,
            actor_user=cls.assessor,
            data={
                "question_code": "P3_MCQ",
                "question_type": "single_mcq",
                "prompt": "Time complexity of binary search?",
                "difficulty": "easy",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": Decimal("4.00"),
                "negative_marks": Decimal("1.00"),
                "options": [
                    {"option_key": "A", "option_text": "O(log n)", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "O(n^2)", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": dim_prog.id, "weight": Decimal("1.00")}],
            },
        )
        cls.q_num = create_question(
            institution=cls.inst_a,
            actor_user=cls.assessor,
            data={
                "question_code": "P3_NUM",
                "question_type": "numeric",
                "prompt": "2 + 2 * 3 = ?",
                "difficulty": "easy",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "tolerance",
                "max_marks": Decimal("2.00"),
                "negative_marks": Decimal("0.00"),
                "scoring_config": {"correct_value": 8, "tolerance": 0},
                "dimensions": [{"dimension_id": dim_prog.id, "weight": Decimal("1.00")}],
            },
        )
        cls.q_likert = create_question(
            institution=cls.inst_a,
            actor_user=cls.assessor,
            data={
                "question_code": "P3_LIK",
                "question_type": "likert",
                "prompt": "Confidence in technical presentations",
                "difficulty": "easy",
                "measurement_family": MeasurementFamily.SELF_REPORTED_PROFICIENCY,
                "scoring_method": "likert_scale",
                "max_marks": Decimal("5.00"),
                "negative_marks": Decimal("0.00"),
                "options": [
                    {"option_key": "1", "option_text": "Low", "display_order": 1},
                    {"option_key": "5", "option_text": "High", "display_order": 2},
                ],
                "dimensions": [{"dimension_id": dim_comm.id, "weight": Decimal("1.00")}],
            },
        )
        cls.q_desc = create_question(
            institution=cls.inst_a,
            actor_user=cls.assessor,
            data={
                "question_code": "P3_DESC",
                "question_type": "descriptive",
                "prompt": "Explain ACID properties.",
                "difficulty": "medium",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "rubric",
                "max_marks": Decimal("6.00"),
                "negative_marks": Decimal("0.00"),
                "rubric": {"rubric_json": {"criteria": ["Atomicity", "Isolation"]}, "max_marks": Decimal("6.00"), "evaluator_guidance": "Check all 4."},
                "dimensions": [{"dimension_id": dim_prog.id, "weight": Decimal("1.00")}],
            },
        )

        cls.tmpl = create_assessment_template(
            institution=cls.inst_a,
            name="Phase 3 Mixed Assessment",
            duration_minutes=30,
            max_attempts=1,
            actor_user=cls.assessor,
        )
        cls.draft_v1 = cls.tmpl.versions.first()
        cls.draft_v1 = update_draft_version(
            version=cls.draft_v1,
            data={
                "items": [
                    {"question_id": cls.q_mcq.id, "marks": Decimal("4.00"), "negative_marks": Decimal("1.00")},
                    {"question_id": cls.q_num.id, "marks": Decimal("2.00"), "negative_marks": Decimal("0.00")},
                    {"question_id": cls.q_likert.id, "marks": Decimal("5.00"), "negative_marks": Decimal("0.00")},
                    {"question_id": cls.q_desc.id, "marks": Decimal("6.00"), "negative_marks": Decimal("0.00")},
                ]
            },
            actor_user=cls.assessor,
        )
        cls.pub_v1 = publish_assessment_version(version=cls.draft_v1, actor_user=cls.assessor)

    def setUp(self):
        self.client = APIClient()

    def _login(self, portal: str, email: str, inst_code: str):
        res = self.client.post(
            "/api/v1/auth/login/",
            {"portal": portal, "identifier": email, "password": "StrongPass!123", "institution_code": inst_code},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    def test_assignment_constraints_and_full_delivery_evaluation_flow(self):
        self._login("admin", "assessor@mitt.test", "MITT")
        now = timezone.now()

        # Assessor with assessment.assign can read cohorts, students, and templates for assignment pickers, but cannot mutate students
        self.assertEqual(self.client.get("/api/v1/academics/cohorts/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/students/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/assessments/templates/").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/students/", {}, format="json").status_code, 403)

        # Cannot assign both cohort and student
        bad_target = self.client.post(
            "/api/v1/assessments/assignments/",
            {
                "assessment_version_id": str(self.pub_v1.id),
                "cohort_id": str(self.cohort_a.id),
                "student_profile_id": str(self.stu_a.id),
                "opens_at": (now - timedelta(minutes=5)).isoformat(),
                "closes_at": (now + timedelta(hours=2)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(bad_target.status_code, 400)

        # Assign to cohort_a (results NOT released initially)
        assign_a = self.client.post(
            "/api/v1/assessments/assignments/",
            {
                "assessment_version_id": str(self.pub_v1.id),
                "cohort_id": str(self.cohort_a.id),
                "opens_at": (now - timedelta(minutes=5)).isoformat(),
                "closes_at": (now + timedelta(hours=2)).isoformat(),
                "results_released": False,
            },
            format="json",
        )
        self.assertEqual(assign_a.status_code, 201)
        assign_a_id = assign_a.data["id"]

        # Assign also to student B directly to test faculty cohort isolation later
        assign_b = self.client.post(
            "/api/v1/assessments/assignments/",
            {
                "assessment_version_id": str(self.pub_v1.id),
                "student_profile_id": str(self.stu_b.id),
                "opens_at": (now - timedelta(minutes=5)).isoformat(),
                "closes_at": (now + timedelta(hours=2)).isoformat(),
                "results_released": True,
            },
            format="json",
        )
        self.assertEqual(assign_b.status_code, 201)
        assign_b_id = assign_b.data["id"]

        # Student A starts attempt
        self._login("academic", "stu.a@mitt.test", "MITT")
        my_list = self.client.get("/api/v1/attempts/my-assignments/")
        self.assertEqual(my_list.status_code, 200)
        self.assertEqual(len(my_list.data), 1)

        start_res = self.client.post(f"/api/v1/attempts/assignments/{assign_a_id}/start/")
        self.assertEqual(start_res.status_code, 200)
        attempt_id = start_res.data["attempt"]["id"]
        questions = start_res.data["questions"]
        self.assertEqual(len(questions), 4)

        # Security check: answer keys are stripped from student payload
        for q in questions:
            for opt in q["options"]:
                self.assertNotIn("is_correct", opt)
                self.assertNotIn("points_override", opt)

        vq_by_code = {q["question_code"]: q["version_question_id"] for q in questions}

        # Autosave answers
        save_res = self.client.put(
            f"/api/v1/attempts/{attempt_id}/responses/",
            {
                "items": [
                    {"version_question_id": vq_by_code["P3_MCQ"], "response_json": {"selected_keys": ["A"]}},
                    {"version_question_id": vq_by_code["P3_NUM"], "response_json": {"numeric_value": 8}},
                    {"version_question_id": vq_by_code["P3_LIK"], "response_json": {"selected_keys": ["5"]}},
                    {"version_question_id": vq_by_code["P3_DESC"], "response_json": {"text": "Atomicity, Consistency, Isolation, Durability"}},
                ]
            },
            format="json",
        )
        self.assertEqual(save_res.status_code, 200)

        # Submit idempotently (call twice)
        sub1 = self.client.post(f"/api/v1/attempts/{attempt_id}/submit/")
        self.assertEqual(sub1.status_code, 200)
        self.assertEqual(sub1.data["status"], AssessmentAttempt.Status.SUBMITTED)
        # Objective marks only: 4 + 2 = 6.00 (Likert 5.00 excluded from objective raw score!)
        self.assertEqual(sub1.data["total_awarded"], "6.00")

        sub2 = self.client.post(f"/api/v1/attempts/{attempt_id}/submit/")
        self.assertEqual(sub2.status_code, 200)
        self.assertEqual(AssessmentResult.objects.filter(attempt_id=attempt_id).count(), 1)

        # Autosave after submission is rejected
        self.assertEqual(
            self.client.put(
                f"/api/v1/attempts/{attempt_id}/responses/",
                {"items": [{"version_question_id": vq_by_code["P3_MCQ"], "response_json": {"selected_keys": ["B"]}}]},
                format="json",
            ).status_code,
            400,
        )

        # Result not released yet -> 403
        self.assertEqual(self.client.get(f"/api/v1/attempts/{attempt_id}/result/").status_code, 403)

        # Student B also submits an attempt
        self._login("academic", "stu.b@mitt.test", "MITT")
        b_start = self.client.post(f"/api/v1/attempts/assignments/{assign_b_id}/start/")
        b_att_id = b_start.data["attempt"]["id"]
        b_vqs = {q["question_code"]: q["version_question_id"] for q in b_start.data["questions"]}
        self.client.put(
            f"/api/v1/attempts/{b_att_id}/responses/",
            {"items": [{"version_question_id": b_vqs["P3_DESC"], "response_json": {"text": "Student B answer"}}]},
            format="json",
        )
        self.client.post(f"/api/v1/attempts/{b_att_id}/submit/")

        # Faculty A logs in: sees ONLY Student A's pending response (cohort_a), NOT Student B (cohort_b)
        self._login("academic", "fac.a@mitt.test", "MITT")
        queue = self.client.get("/api/v1/attempts/evaluations/queue/")
        self.assertEqual(queue.status_code, 200)
        self.assertEqual(queue.data["count"], 1)
        resp_a_id = queue.data["results"][0]["id"]

        # Evaluate Student A's descriptive response (v1 -> 5.00 marks, then revise v2 -> 6.00 marks)
        ev1 = self.client.post(
            f"/api/v1/attempts/evaluations/responses/{resp_a_id}/",
            {"awarded_marks": "5.00", "comments": "Good summary"},
            format="json",
        )
        self.assertEqual(ev1.status_code, 201)
        ev2 = self.client.post(
            f"/api/v1/attempts/evaluations/responses/{resp_a_id}/",
            {"awarded_marks": "6.00", "comments": "All 4 properties covered"},
            format="json",
        )
        self.assertEqual(ev2.status_code, 201)
        self.assertEqual(Evaluation.objects.filter(response_id=resp_a_id).count(), 2)

        # Assessor releases results on assignment A
        self._login("admin", "assessor@mitt.test", "MITT")
        self.client.patch(
            f"/api/v1/assessments/assignments/{assign_a_id}/",
            {"results_released": True},
            format="json",
        )

        # Student A views finalized result (4 + 2 + 6 = 12 / 12 = 100%, Likert stored separately!)
        self._login("academic", "stu.a@mitt.test", "MITT")
        res = self.client.get(f"/api/v1/attempts/{attempt_id}/result/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["raw_score"], "12.00")
        self.assertEqual(res.data["max_score"], "12.00")
        self.assertEqual(res.data["normalized_score"], "100.00")
        self.assertEqual(res.data["result_status"], "finalized")
        self.assertEqual(len(res.data["breakdown_json"]["demonstrated_performance"]), 1)
        self.assertEqual(res.data["breakdown_json"]["self_reported_proficiency"][0]["average_rating"], 5.0)

