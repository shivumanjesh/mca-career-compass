"""Staged Excel/CSV import tests: template, mapping, duplicates, rollback, export, and isolation."""
import io
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from openpyxl import Workbook
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Cohort, Programme
from apps.accounts.models import Role, User
from apps.accounts.rbac import ROLE_INSTITUTION_ADMIN, ROLE_STUDENT
from apps.accounts.services import seed_roles_and_permissions
from apps.audit.models import AuditEvent
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership, MembershipRole


@override_settings(MEDIA_ROOT="d:\\MITT\\SkillBridge\\MCA Career compass\\backend\\media_test")
class StudentBulkImportTests(TestCase):
    """Verify staged XLSX/CSV import workflow and tenant isolation."""

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

        cls.prog_a = Programme.objects.create(institution=cls.inst_a, code="MCA", name="MCA")
        cls.ay_a = AcademicYear.objects.create(
            institution=cls.inst_a, name="2025-26", start_date=date(2025, 8, 1), end_date=date(2026, 7, 31)
        )
        cls.cohort_a = Cohort.objects.create(
            institution=cls.inst_a,
            programme=cls.prog_a,
            academic_year=cls.ay_a,
            batch_name="2025-2027",
            semester=1,
            section="A",
        )

        # Existing student in DB to trigger duplicate detection
        u_existing = User.objects.create_user(email="existing@mitt.test", first_name="Existing")
        m_existing = Membership.objects.create(institution=cls.inst_a, user=u_existing)
        MembershipRole.objects.create(membership=m_existing, role=Role.objects.get(code=ROLE_STUDENT))
        StudentProfile.objects.create(
            institution=cls.inst_a,
            membership=m_existing,
            cohort=cls.cohort_a,
            registration_no="4MT25MC000",
        )

    def setUp(self):
        self.client = APIClient()

    def _login(self, email: str, inst_code: str):
        res = self.client.post(
            "/api/v1/auth/login/",
            {"portal": "admin", "identifier": email, "password": "StrongPass!123", "institution_code": inst_code},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    def test_template_download_and_invalid_extension_rejected(self):
        self._login("admin@mitt.test", "MITT")
        tmpl = self.client.get("/api/v1/students/import/template/")
        self.assertEqual(tmpl.status_code, 200)
        self.assertIn("spreadsheetml", tmpl["Content-Type"])

        bad_file = SimpleUploadedFile("bad.txt", b"hello", content_type="text/plain")
        res = self.client.post("/api/v1/students/import/upload/", {"file": bad_file}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_xlsx_staged_import_preview_commit_and_error_export(self):
        self._login("admin@mitt.test", "MITT")

        wb = Workbook()
        ws = wb.active
        ws.append(["USN", "Email Address", "First Name", "Last Name", "Programme", "Batch", "Sem", "Sec"])
        # Valid row 2
        ws.append(["4MT25MC001", "asha@mitt.test", "Asha", "Rao", "MCA", "2025-2027", 1, "A"])
        # Duplicate in-file reg_no row 3
        ws.append(["4MT25MC001", "asha2@mitt.test", "Asha2", "Rao", "MCA", "2025-2027", 1, "A"])
        # Duplicate DB reg_no row 4
        ws.append(["4MT25MC000", "dupdb@mitt.test", "Dup", "DB", "MCA", "2025-2027", 1, "A"])
        # Invalid email + risky leading '+' string row 5
        ws.append(["4MT25MC009", "not-an-email", "+TestFormula", "Test", "MCA", "2025-2027", 1, "A"])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        upload_file = SimpleUploadedFile(
            "students.xlsx",
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        upload_res = self.client.post("/api/v1/students/import/upload/", {"file": upload_file}, format="multipart")
        self.assertEqual(upload_res.status_code, 201)
        job_id = upload_res.data["id"]

        suggested = upload_res.data["summary_json"]["suggested_mapping"]
        self.assertEqual(suggested["registration_no"], "USN")
        self.assertEqual(suggested["email"], "Email Address")

        val_res = self.client.post(
            f"/api/v1/students/import/{job_id}/validate/",
            {"column_mapping": suggested},
            format="json",
        )
        self.assertEqual(val_res.status_code, 200)
        self.assertEqual(val_res.data["job"]["total_rows"], 4)
        self.assertEqual(val_res.data["job"]["success_rows"], 1)
        self.assertEqual(val_res.data["job"]["error_rows"], 3)

        # No students created before commit
        self.assertFalse(StudentProfile.objects.filter(institution=self.inst_a, registration_no="4MT25MC001").exists())

        # All-or-nothing mode aborts commit cleanly
        abort_res = self.client.post(
            f"/api/v1/students/import/{job_id}/commit/",
            {"mode": "all_or_nothing"},
            format="json",
        )
        self.assertEqual(abort_res.status_code, 400)
        self.assertFalse(StudentProfile.objects.filter(institution=self.inst_a, registration_no="4MT25MC001").exists())

        # Skip-invalid mode commits valid row atomically
        commit_res = self.client.post(
            f"/api/v1/students/import/{job_id}/commit/",
            {"mode": "skip_invalid"},
            format="json",
        )
        self.assertEqual(commit_res.status_code, 200)
        self.assertEqual(commit_res.data["status"], "committed")
        self.assertEqual(commit_res.data["success_rows"], 1)
        self.assertEqual(commit_res.data["error_rows"], 3)

        created_student = StudentProfile.objects.get(institution=self.inst_a, registration_no="4MT25MC001")
        self.assertEqual(created_student.cohort_id, self.cohort_a.id)
        self.assertFalse(created_student.membership.user.has_usable_password())

        # Download error CSV report (sanitized & password-free)
        export_res = self.client.get(f"/api/v1/students/import-jobs/{job_id}/errors/export/")
        self.assertEqual(export_res.status_code, 200)
        csv_text = export_res.content.decode("utf-8")
        self.assertIn("'+TestFormula", csv_text)
        self.assertNotIn("password", csv_text.lower())

        # Cross-institution isolation: Admin B cannot access job
        self._login("admin@demob.test", "DEMOB")
        self.assertEqual(self.client.get(f"/api/v1/students/import-jobs/{job_id}/").status_code, 404)
        self.assertTrue(AuditEvent.objects.filter(action="IMPORT_JOB_COMMITTED").exists())

    def test_csv_import_and_formula_injection_sanitization(self):
        self._login("admin@mitt.test", "MITT")
        csv_bytes = (
            "registration_no,email,first_name,last_name\n"
            "4MT25MC050,valid.csv@mitt.test,Priya,S\n"
            "4MT25MC051,bad-email,=CMD(),Risk\n"
        ).encode("utf-8")
        upload_file = SimpleUploadedFile("students.csv", csv_bytes, content_type="text/csv")

        up = self.client.post("/api/v1/students/import/upload/", {"file": upload_file}, format="multipart")
        self.assertEqual(up.status_code, 201)
        job_id = up.data["id"]

        val = self.client.post(
            f"/api/v1/students/import/{job_id}/validate/",
            {"column_mapping": up.data["summary_json"]["suggested_mapping"], "default_cohort_id": str(self.cohort_a.id)},
            format="json",
        )
        self.assertEqual(val.status_code, 200)
        self.assertEqual(val.data["job"]["success_rows"], 1)
        self.assertEqual(val.data["job"]["error_rows"], 1)

        export_res = self.client.get(f"/api/v1/students/import-jobs/{job_id}/errors/export/")
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("'=CMD()", export_res.content.decode("utf-8"))

