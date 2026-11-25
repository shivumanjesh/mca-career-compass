"""Phase 5 tests: starter learning catalogue, explainable recommendations, plans, progress, scoping & audit."""
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
from apps.development.models import DevelopmentActivity, DevelopmentPlan
from apps.faculty.models import CohortFaculty, FacultyProfile
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership, MembershipRole


class EmpowermentPhase5Tests(TestCase):
    """Verify learning catalogue, evidence-cited recommendations, development plans, scoping, and audit logs."""

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

        cls.stu_a_user = User.objects.create_user(email="stu.a@mitt.test", password="StrongPass!123", first_name="Aarav", last_name="S")
        m_sa = Membership.objects.create(institution=cls.inst, user=cls.stu_a_user)
        MembershipRole.objects.create(membership=m_sa, role=Role.objects.get(code=ROLE_STUDENT))
        cls.stu_a = StudentProfile.objects.create(institution=cls.inst, membership=m_sa, cohort=cls.cohort_a, registration_no="4MT25MC001")

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
        dim_int = AssessmentDimension.objects.get(institution=cls.inst, code="INT_AIML")

        q1 = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "P5_PROG",
                "question_type": "single_mcq",
                "prompt": "Python dict lookup average complexity?",
                "difficulty": "easy",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": Decimal("10.00"),
                "negative_marks": Decimal("0.00"),
                "options": [
                    {"option_key": "A", "option_text": "O(1)", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "O(n)", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": dim_prog.id, "weight": Decimal("1.00")}],
            },
        )
        q2 = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "P5_DSA",
                "question_type": "single_mcq",
                "prompt": "BFS uses which data structure?",
                "difficulty": "medium",
                "measurement_family": MeasurementFamily.DEMONSTRATED_PERFORMANCE,
                "scoring_method": "exact",
                "max_marks": Decimal("10.00"),
                "negative_marks": Decimal("0.00"),
                "options": [
                    {"option_key": "A", "option_text": "Queue", "display_order": 1, "is_correct": True},
                    {"option_key": "B", "option_text": "Stack", "display_order": 2, "is_correct": False},
                ],
                "dimensions": [{"dimension_id": dim_dsa.id, "weight": Decimal("1.00")}],
            },
        )
        q3 = create_question(
            institution=cls.inst,
            actor_user=cls.assessor,
            data={
                "question_code": "P5_INT",
                "question_type": "likert",
                "prompt": "Interest in AI/ML systems",
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

        tmpl = create_assessment_template(institution=cls.inst, name="Phase 5 Baseline", actor_user=cls.assessor)
        v1 = update_draft_version(
            version=tmpl.versions.first(),
            data={"items": [{"question_id": q1.id}, {"question_id": q2.id}, {"question_id": q3.id}]},
            actor_user=cls.assessor,
        )
        pub = publish_assessment_version(version=v1, actor_user=cls.assessor)

        now = timezone.now()
        assign_a = create_assessment_assignment(
            institution=cls.inst,
            assessment_version_id=pub.id,
            cohort_id=cls.cohort_a.id,
            opens_at=now - timedelta(minutes=5),
            closes_at=now + timedelta(hours=2),
            results_released=True,
            actor_user=cls.assessor,
        )
        att = start_or_resume_attempt(assignment=assign_a, student=cls.stu_a, actor_user=cls.stu_a_user)
        vqs = {vq.question.question_code: vq.id for vq in pub.version_questions.all()}
        autosave_attempt_responses(
            attempt=att,
            items=[
                {"version_question_id": vqs["P5_PROG"], "response_json": {"selected_keys": ["A"]}},  # 100%
                {"version_question_id": vqs["P5_DSA"], "response_json": {"selected_keys": ["B"]}},   # 0% gap
                {"version_question_id": vqs["P5_INT"], "response_json": {"selected_keys": ["5"]}},   # 5/5 interest
            ],
            actor_user=cls.stu_a_user,
        )
        submit_attempt(attempt=att, actor_user=cls.stu_a_user)

    def _login_client(self, portal: str, email: str, institution_code: str = "MITT") -> APIClient:
        client = APIClient()
        res = client.post(
            "/api/v1/auth/login/",
            {
                "portal": portal,
                "identifier": email,
                "password": "StrongPass!123",
                "institution_code": institution_code,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        return client

    def test_catalogue_seed_crud_and_student_rbac(self):
        client = self._login_client("admin", "assessor@mitt.test", "MITT")

        seed_res = client.post("/api/v1/development/catalogue/seed/")
        self.assertEqual(seed_res.status_code, 200)
        self.assertGreaterEqual(seed_res.data["created_resources"], 10)

        create_res = client.post(
            "/api/v1/development/catalogue/",
            {
                "dimension_code": "DSA",
                "target_domain": "Software Development",
                "resource_type": "project",
                "title": "Graph Pathfinding Visualizer",
                "provider": "MCA Dept",
                "level": "intermediate",
                "estimated_hours": 18,
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, 201)
        res_id = create_res.data["id"]

        patch_res = client.patch(
            f"/api/v1/development/catalogue/{res_id}/",
            {"status": "archived"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.data["status"], "archived")

        # Student cannot create or archive catalogue entries
        stu_client = self._login_client("academic", "stu.a@mitt.test", "MITT")
        denied = stu_client.post(
            "/api/v1/development/catalogue/",
            {"target_domain": "Software Development", "resource_type": "training", "title": "Unauthorized"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(AuditEvent.objects.filter(institution=self.inst, action="LEARNING_CATALOGUE_SEEDED").exists())
        self.assertTrue(AuditEvent.objects.filter(institution=self.inst, action="LEARNING_RESOURCE_CREATED").exists())

    def test_explainable_recommendations_and_student_self_plan_progress(self):
        assessor_client = self._login_client("admin", "assessor@mitt.test", "MITT")
        assessor_client.post("/api/v1/development/catalogue/seed/")

        stu_client = self._login_client("academic", "stu.a@mitt.test", "MITT")

        rec_res = stu_client.get("/api/v1/development/my-recommendations/")
        self.assertEqual(rec_res.status_code, 200)
        self.assertIn("not a clinical", rec_res.data["notice"].lower())
        aiml_dom = next(d for d in rec_res.data["domain_recommendations"] if d["domain"] == "AI / ML Engineering")
        self.assertEqual(aiml_dom["interest_rating"], 5.0)
        self.assertIn("Demonstrated evidence:", aiml_dom["explanation"])
        self.assertIn("Stated career interest:", aiml_dom["explanation"])

        # Top training recommendation should cite DSA gap (0.0%)
        top_training = rec_res.data["training_recommendations"][0]
        self.assertEqual(top_training["dimension_code"], "DSA")
        self.assertIn("Addresses skill gap in DSA", top_training["reason"])

        # Student proposes a plan and adopts recommended training
        plan_res = stu_client.post(
            "/api/v1/development/plans/",
            {"title": "Sem 1 DSA & AI Prep", "target_domain": "AI / ML Engineering", "notes": "Focus on DSA basics"},
            format="json",
        )
        self.assertEqual(plan_res.status_code, 201)
        self.assertEqual(plan_res.data["status"], DevelopmentPlan.Status.PROPOSED)
        plan_id = plan_res.data["id"]

        # Student cannot self-approve a proposed plan to active
        approve_denied = stu_client.patch(f"/api/v1/development/plans/{plan_id}/", {"status": "active"}, format="json")
        self.assertEqual(approve_denied.status_code, 403)

        act_res = stu_client.post(
            f"/api/v1/development/plans/{plan_id}/activities/",
            {"resource_id": top_training["resource_id"]},
            format="json",
        )
        self.assertEqual(act_res.status_code, 201)
        act_id = act_res.data["id"]

        # Partial progress -> in_progress
        p1 = stu_client.post(
            f"/api/v1/development/activities/{act_id}/progress/",
            {"progress_percent": 50, "reflection": "Completed arrays & recursion modules."},
            format="json",
        )
        self.assertEqual(p1.status_code, 201)
        self.assertEqual(p1.data["activity_status"], DevelopmentActivity.Status.IN_PROGRESS)

        # Full completion -> activity completed AND plan auto-completed
        p2 = stu_client.post(
            f"/api/v1/development/activities/{act_id}/progress/",
            {"progress_percent": 100, "reflection": "Solved 20 graph problems.", "evidence_url": "https://example.test/cert"},
            format="json",
        )
        self.assertEqual(p2.status_code, 201)
        self.assertEqual(p2.data["activity_status"], DevelopmentActivity.Status.COMPLETED)
        self.assertEqual(p2.data["plan_status"], DevelopmentPlan.Status.COMPLETED)

        self.assertTrue(AuditEvent.objects.filter(institution=self.inst, action="DEVELOPMENT_PLAN_CREATED").exists())
        self.assertTrue(AuditEvent.objects.filter(institution=self.inst, action="DEVELOPMENT_ACTIVITY_ADDED").exists())
        self.assertTrue(AuditEvent.objects.filter(institution=self.inst, action="DEVELOPMENT_PROGRESS_RECORDED").exists())

    def test_faculty_cohort_student_and_cross_tenant_isolation(self):
        assessor_client = self._login_client("admin", "assessor@mitt.test", "MITT")
        assessor_client.post("/api/v1/development/catalogue/seed/")

        fac_client = self._login_client("academic", "fac@mitt.test", "MITT")

        # Faculty CAN view Student A (Cohort A) and create mentored plan
        rec_a = fac_client.get(f"/api/v1/development/students/{self.stu_a.id}/recommendations/")
        self.assertEqual(rec_a.status_code, 200)
        plan_a = fac_client.post(
            "/api/v1/development/plans/",
            {"student_id": str(self.stu_a.id), "title": "Faculty Mentored DSA Track", "target_domain": "Software Development"},
            format="json",
        )
        self.assertEqual(plan_a.status_code, 201)
        self.assertEqual(plan_a.data["status"], DevelopmentPlan.Status.ACTIVE)

        # Faculty CANNOT access Student B (unassigned Cohort B)
        rec_b = fac_client.get(f"/api/v1/development/students/{self.stu_b.id}/recommendations/")
        self.assertEqual(rec_b.status_code, 404)
        plan_b_denied = fac_client.post(
            "/api/v1/development/plans/",
            {"student_id": str(self.stu_b.id), "title": "Out of Scope Plan"},
            format="json",
        )
        self.assertEqual(plan_b_denied.status_code, 404)

        # Student B isolation checks
        stu_b_client = self._login_client("academic", "stu.b@mitt.test", "MITT")
        self.assertEqual(stu_b_client.get(f"/api/v1/development/students/{self.stu_a.id}/recommendations/").status_code, 403)
        self.assertEqual(stu_b_client.get(f"/api/v1/development/plans/{plan_a.data['id']}/").status_code, 404)
        self.assertEqual(
            stu_b_client.post("/api/v1/development/plans/", {"student_id": str(self.stu_a.id), "title": "Spoofed"}, format="json").status_code,
            403,
        )

        # Cross-tenant isolation: DEMOB admin sees 0 MITT resources & 404 on MITT plan/student
        other_client = self._login_client("admin", "admin@demob.test", "DEMOB")
        cat_other = other_client.get("/api/v1/development/catalogue/")
        self.assertEqual(cat_other.status_code, 200)
        self.assertEqual(cat_other.data["count"], 0)
        self.assertEqual(other_client.get(f"/api/v1/development/plans/{plan_a.data['id']}/").status_code, 404)
        self.assertEqual(other_client.get(f"/api/v1/development/students/{self.stu_a.id}/recommendations/").status_code, 404)

