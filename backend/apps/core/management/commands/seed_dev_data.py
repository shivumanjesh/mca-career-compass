"""Idempotent synthetic development dataset seeder for local testing."""
import os
from datetime import date
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.crypto import get_random_string

from apps.academics.models import AcademicYear, Cohort, Programme
from apps.accounts.models import PlatformRole, Role, User
from apps.accounts.rbac import (
    ROLE_ASSESSMENT_ADMIN,
    ROLE_FACULTY_HOD,
    ROLE_INSTITUTION_ADMIN,
    ROLE_PLATFORM_SUPER_ADMIN,
    ROLE_STUDENT,
)
from apps.accounts.services import seed_roles_and_permissions
from apps.faculty.models import CohortFaculty, FacultyProfile
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership, MembershipRole


class Command(BaseCommand):
    help = "Seed synthetic development tenants (MITT and DEMOB) without hardcoded credentials."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help="Optional dev password for synthetic seed accounts (otherwise reads SEED_DEV_PASSWORD or generates a one-time random password).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_dev_data can only be executed when DJANGO_DEBUG=True.")

        seed_roles_and_permissions()

        dev_password = options.get("password") or os.environ.get("SEED_DEV_PASSWORD")
        generated = False
        if not dev_password:
            dev_password = f"Dev#{get_random_string(12)}!"
            generated = True

        def ensure_user(email: str, first_name: str, last_name: str, is_superuser: bool = False) -> User:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": True,
                    "is_staff": is_superuser,
                    "is_superuser": is_superuser,
                },
            )
            if created:
                user.set_password(dev_password)
                user.save()
            return user

        # 1. Platform Super Admin
        super_user = ensure_user("superadmin@compass.local", "Platform", "SuperAdmin", is_superuser=True)
        PlatformRole.objects.get_or_create(
            user=super_user, role=Role.objects.get(code=ROLE_PLATFORM_SUPER_ADMIN)
        )

        # 2. Institution A: MIT Thandavapura (MITT)
        mitt, _ = Institution.objects.get_or_create(
            code="MITT",
            defaults={
                "name": "Maharaja Institute of Technology Thandavapura",
                "timezone": "Asia/Kolkata",
                "settings": {"city": "Thandavapura, Mysuru", "contact_email": "mca-office@mitt.local"},
            },
        )
        mitt_admin = ensure_user("admin@mitt.local", "MITT", "Admin")
        m_mitt_admin, _ = Membership.objects.get_or_create(institution=mitt, user=mitt_admin)
        MembershipRole.objects.get_or_create(
            membership=m_mitt_admin, role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN)
        )

        mitt_assessor = ensure_user("assessment@mitt.local", "Assessment", "Coordinator")
        m_mitt_assessor, _ = Membership.objects.get_or_create(institution=mitt, user=mitt_assessor)
        MembershipRole.objects.get_or_create(
            membership=m_mitt_assessor, role=Role.objects.get(code=ROLE_ASSESSMENT_ADMIN)
        )

        prog_mitt, _ = Programme.objects.get_or_create(
            institution=mitt,
            code="MCA",
            defaults={"name": "Master of Computer Applications", "level": "PG"},
        )
        ay_mitt, _ = AcademicYear.objects.get_or_create(
            institution=mitt,
            name="2025-26",
            defaults={"start_date": date(2025, 8, 1), "end_date": date(2026, 7, 31)},
        )
        cohort_mitt_a, _ = Cohort.objects.get_or_create(
            institution=mitt,
            programme=prog_mitt,
            academic_year=ay_mitt,
            batch_name="2025-2027",
            semester=1,
            section="A",
        )
        cohort_mitt_b, _ = Cohort.objects.get_or_create(
            institution=mitt,
            programme=prog_mitt,
            academic_year=ay_mitt,
            batch_name="2025-2027",
            semester=1,
            section="B",
        )

        fac1_user = ensure_user("kavitha.faculty@mitt.local", "Dr. Kavitha", "S")
        m_fac1, _ = Membership.objects.get_or_create(institution=mitt, user=fac1_user)
        MembershipRole.objects.get_or_create(membership=m_fac1, role=Role.objects.get(code=ROLE_FACULTY_HOD))
        fac1, _ = FacultyProfile.objects.get_or_create(
            institution=mitt,
            membership=m_fac1,
            defaults={"employee_code": "MITTFAC01", "department": "MCA", "designation": "HOD & Professor"},
        )
        CohortFaculty.objects.get_or_create(
            institution=mitt, cohort=cohort_mitt_a, faculty_profile=fac1, assignment_type=CohortFaculty.AssignmentType.HOD
        )

        fac2_user = ensure_user("rajesh.faculty@mitt.local", "Prof. Rajesh", "M")
        m_fac2, _ = Membership.objects.get_or_create(institution=mitt, user=fac2_user)
        MembershipRole.objects.get_or_create(membership=m_fac2, role=Role.objects.get(code=ROLE_FACULTY_HOD))
        fac2, _ = FacultyProfile.objects.get_or_create(
            institution=mitt,
            membership=m_fac2,
            defaults={"employee_code": "MITTFAC02", "department": "MCA", "designation": "Assistant Professor"},
        )
        CohortFaculty.objects.get_or_create(
            institution=mitt, cohort=cohort_mitt_b, faculty_profile=fac2, assignment_type=CohortFaculty.AssignmentType.MENTOR
        )

        synthetic_mitt_students = [
            ("4MT25MC001", "aarav.sharma@mitt.local", "Aarav", "Sharma", cohort_mitt_a),
            ("4MT25MC002", "bhavana.nair@mitt.local", "Bhavana", "Nair", cohort_mitt_a),
            ("4MT25MC003", "chetan.patil@mitt.local", "Chetan", "Patil", cohort_mitt_a),
            ("4MT25MC004", "divya.rao@mitt.local", "Divya", "Rao", cohort_mitt_b),
            ("4MT25MC005", "eshan.verma@mitt.local", "Eshan", "Verma", cohort_mitt_b),
        ]
        for reg, email, fn, ln, cohort in synthetic_mitt_students:
            su = ensure_user(email, fn, ln)
            sm, _ = Membership.objects.get_or_create(institution=mitt, user=su)
            MembershipRole.objects.get_or_create(membership=sm, role=Role.objects.get(code=ROLE_STUDENT))
            StudentProfile.objects.get_or_create(
                institution=mitt,
                membership=sm,
                defaults={"registration_no": reg, "cohort": cohort, "admission_year": 2025},
            )

        # 3. Institution B: Demo Institute B (DEMOB)
        demob, _ = Institution.objects.get_or_create(
            code="DEMOB",
            defaults={
                "name": "Demo Institute B",
                "timezone": "Asia/Kolkata",
                "settings": {"city": "Bengaluru", "contact_email": "office@demob.local"},
            },
        )
        demob_admin = ensure_user("admin@demob.local", "DemoB", "Admin")
        m_demob_admin, _ = Membership.objects.get_or_create(institution=demob, user=demob_admin)
        MembershipRole.objects.get_or_create(
            membership=m_demob_admin, role=Role.objects.get(code=ROLE_INSTITUTION_ADMIN)
        )
        prog_b, _ = Programme.objects.get_or_create(
            institution=demob, code="MCA", defaults={"name": "Master of Computer Applications", "level": "PG"}
        )
        ay_b, _ = AcademicYear.objects.get_or_create(
            institution=demob, name="2025-26", defaults={"start_date": date(2025, 8, 1), "end_date": date(2026, 7, 31)}
        )
        cohort_b, _ = Cohort.objects.get_or_create(
            institution=demob, programme=prog_b, academic_year=ay_b,
            batch_name="2025-2027", semester=1, section="A",
        )
        for reg, email, fn, ln in [
            ("4DB25MC001", "kiran.b@demob.local", "Kiran", "Bhat"),
            ("4DB25MC002", "meera.b@demob.local", "Meera", "Menon"),
        ]:
            su = ensure_user(email, fn, ln)
            sm, _ = Membership.objects.get_or_create(institution=demob, user=su)
            MembershipRole.objects.get_or_create(membership=sm, role=Role.objects.get(code=ROLE_STUDENT))
            StudentProfile.objects.get_or_create(
                institution=demob,
                membership=sm,
                defaults={"registration_no": reg, "cohort": cohort_b, "admission_year": 2025},
            )

        self.stdout.write(self.style.SUCCESS("Synthetic seed complete for MITT and DEMOB."))
        if generated:
            self.stdout.write(
                self.style.WARNING(
                    f"Generated one-time dev password for newly created synthetic accounts: {dev_password}"
                )
            )

