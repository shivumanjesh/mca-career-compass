"""Live role-scoped dashboard summary endpoint (zero hardcoded statistics)."""
from django.apps import apps
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.rbac import ROLE_FACULTY_HOD, ROLE_PLATFORM_SUPER_ADMIN, ROLE_STUDENT
from apps.audit.models import AuditEvent
from apps.tenancy.models import Institution, Membership, MembershipRole


class DashboardSummaryView(APIView):
    """Return live PostgreSQL counts scoped to the authenticated role & institution."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        platform_roles = getattr(request, "platform_role_codes", set())
        inst_roles = getattr(request, "institution_role_codes", set())
        inst_perms = getattr(request, "institution_permissions", set())
        active_inst = getattr(request, "active_institution", None)
        active_membership = getattr(request, "active_membership", None)

        if ROLE_PLATFORM_SUPER_ADMIN in platform_roles and active_inst is None:
            total_inst = Institution.objects.count()
            active_inst_count = Institution.objects.filter(status=Institution.Status.ACTIVE).count()
            inactive_inst_count = total_inst - active_inst_count
            total_users = User.objects.count()
            total_audit_events = AuditEvent.objects.count()
            recent_institutions = list(
                Institution.objects.order_by("-created_at")
                .values("id", "code", "name", "status", "timezone", "created_at")[:5]
            )
            return Response(
                {
                    "scope": "platform",
                    "metrics": {
                        "total_institutions": total_inst,
                        "active_institutions": active_inst_count,
                        "inactive_institutions": inactive_inst_count,
                        "total_users": total_users,
                        "total_audit_events": total_audit_events,
                    },
                    "recent_institutions": recent_institutions,
                }
            )

        if active_inst is None or active_membership is None:
            return Response({"scope": "unassigned", "metrics": {}})

        # Student-only view
        if inst_roles == {ROLE_STUDENT} and "institution.user.manage" not in inst_perms:
            StudentProfile = apps.get_model("students", "StudentProfile")
            from apps.attempts.services import get_student_assignments_queryset
            from apps.attempts.models import AssessmentAttempt

            profile = (
                StudentProfile.objects.for_institution(active_inst)
                .select_related("cohort__programme", "cohort__academic_year")
                .filter(membership=active_membership)
                .first()
            )
            assigned_count = get_student_assignments_queryset(profile).count() if profile else 0
            completed_count = (
                AssessmentAttempt.objects.for_institution(active_inst)
                .filter(student_profile=profile)
                .exclude(status=AssessmentAttempt.Status.IN_PROGRESS)
                .count()
                if profile
                else 0
            )
            return Response(
                {
                    "scope": "student",
                    "institution": {
                        "id": str(active_inst.id),
                        "code": active_inst.code,
                        "name": active_inst.name,
                    },
                    "metrics": {
                        "assigned_assessments": assigned_count,
                        "completed_attempts": completed_count,
                    },
                    "student_profile": (
                        {
                            "registration_no": profile.registration_no,
                            "admission_year": profile.admission_year,
                            "status": profile.status,
                            "cohort": str(profile.cohort) if profile.cohort else None,
                            "programme": profile.cohort.programme.name if profile.cohort else None,
                            "semester": profile.cohort.semester if profile.cohort else None,
                            "section": profile.cohort.section if profile.cohort else None,
                        }
                        if profile
                        else None
                    ),
                }
            )

        # Faculty/HOD-only view
        if ROLE_FACULTY_HOD in inst_roles and "institution.user.manage" not in inst_perms:
            CohortFaculty = apps.get_model("faculty", "CohortFaculty")
            StudentProfile = apps.get_model("students", "StudentProfile")
            AttemptResponse = apps.get_model("attempts", "Response")
            assignments = list(
                CohortFaculty.objects.for_institution(active_inst)
                .filter(faculty_profile__membership=active_membership)
                .select_related("cohort__programme")
                .annotate(student_count=Count("cohort__students", distinct=True))
            )
            assigned_cohort_ids = [a.cohort_id for a in assignments]
            assigned_students_count = StudentProfile.objects.for_institution(active_inst).filter(
                cohort_id__in=assigned_cohort_ids
            ).count()
            pending_evaluations = AttemptResponse.objects.filter(
                attempt__institution=active_inst,
                attempt__student_profile__cohort_id__in=assigned_cohort_ids,
                scoring_status="pending_manual",
            ).count()
            return Response(
                {
                    "scope": "faculty",
                    "institution": {
                        "id": str(active_inst.id),
                        "code": active_inst.code,
                        "name": active_inst.name,
                    },
                    "metrics": {
                        "assigned_cohorts": len(assignments),
                        "assigned_students": assigned_students_count,
                        "pending_evaluations": pending_evaluations,
                    },
                    "cohorts": [
                        {
                            "cohort_id": str(a.cohort_id),
                            "cohort_label": str(a.cohort),
                            "assignment_type": a.assignment_type,
                            "student_count": a.student_count,
                        }
                        for a in assignments
                    ],
                }
            )

        # Institution Admin / Assessment Admin view
        memberships_qs = Membership.objects.filter(institution=active_inst)
        total_members = memberships_qs.count()
        active_members = memberships_qs.filter(status=Membership.Status.ACTIVE).count()
        role_counts = {
            row["role__code"]: row["total"]
            for row in MembershipRole.objects.filter(membership__institution=active_inst)
            .values("role__code")
            .annotate(total=Count("id"))
        }

        StudentProfile = apps.get_model("students", "StudentProfile")
        FacultyProfile = apps.get_model("faculty", "FacultyProfile")
        Cohort = apps.get_model("academics", "Cohort")
        AssessmentDimension = apps.get_model("assessments", "AssessmentDimension")
        Question = apps.get_model("assessments", "Question")
        AssessmentTemplate = apps.get_model("assessments", "AssessmentTemplate")
        AssessmentVersion = apps.get_model("assessments", "AssessmentVersion")

        return Response(
            {
                "scope": "institution",
                "institution": {
                    "id": str(active_inst.id),
                    "code": active_inst.code,
                    "name": active_inst.name,
                    "status": active_inst.status,
                    "timezone": active_inst.timezone,
                },
                "metrics": {
                    "total_members": total_members,
                    "active_members": active_members,
                    "student_count": StudentProfile.objects.filter(institution=active_inst).count(),
                    "faculty_count": FacultyProfile.objects.filter(institution=active_inst).count(),
                    "cohort_count": Cohort.objects.filter(institution=active_inst).count(),
                    "dimension_count": AssessmentDimension.objects.filter(institution=active_inst, status="active").count(),
                    "question_count": Question.objects.filter(institution=active_inst, status="active").count(),
                    "template_count": AssessmentTemplate.objects.filter(institution=active_inst, status="active").count(),
                    "published_version_count": AssessmentVersion.objects.filter(institution=active_inst, status="published").count(),
                    "audit_events_count": AuditEvent.objects.filter(institution=active_inst).count(),
                },
                "role_breakdown": role_counts,
            }
        )
