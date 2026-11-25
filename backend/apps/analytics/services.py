"""Phase 4 analytics aggregation: individual reports, cohort analytics, comparison & gap analysis."""
from collections import defaultdict
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied

from apps.academics.models import Cohort
from apps.attempts.models import AssessmentResult
from apps.faculty.models import CohortFaculty
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership

NON_CLINICAL_NOTICE = (
    "Educational capability and interest mapping only; not a clinical or validated psychological diagnosis."
)


def get_authorized_cohorts_queryset(institution: Institution, membership: Membership, perms: set[str]) -> QuerySet[Cohort]:
    qs = Cohort.objects.for_institution(institution).select_related("programme", "academic_year")
    if "institution.user.manage" in perms or "assessment.assign" in perms or "academics.cohort.manage" in perms:
        return qs
    if "analytics.cohort.view" in perms or "results.cohort.view" in perms:
        assigned_ids = CohortFaculty.objects.for_institution(institution).filter(
            faculty_profile__membership=membership
        ).values_list("cohort_id", flat=True)
        return qs.filter(id__in=assigned_ids)
    return qs.none()


def get_authorized_students_queryset(institution: Institution, membership: Membership, perms: set[str]) -> QuerySet[StudentProfile]:
    qs = StudentProfile.objects.for_institution(institution).select_related(
        "membership__user", "cohort__programme", "cohort__academic_year"
    )
    if "institution.user.manage" in perms or "assessment.assign" in perms or "institution.student.manage" in perms:
        return qs
    if "results.cohort.view" in perms or "analytics.cohort.view" in perms:
        assigned_ids = CohortFaculty.objects.for_institution(institution).filter(
            faculty_profile__membership=membership
        ).values_list("cohort_id", flat=True)
        return qs.filter(cohort_id__in=assigned_ids)
    return qs.none()


def build_student_report(
    student: StudentProfile,
    *,
    released_only: bool = False,
) -> dict[str, Any]:
    """Build domain-wise individual report separating all three measurement families."""
    qs = (
        AssessmentResult.objects.for_institution(student.institution)
        .filter(attempt__student_profile=student)
        .select_related(
            "attempt__assignment__assessment_version__template",
            "attempt__assignment",
        )
        .order_by("attempt__submitted_at", "created_at")
    )
    if released_only:
        qs = qs.filter(attempt__assignment__results_released=True)

    results = list(qs)

    demo_agg: dict[str, dict[str, Any]] = {}
    self_agg: dict[str, dict[str, Any]] = {}
    interest_agg: dict[str, dict[str, Any]] = {}
    assessment_history: list[dict[str, Any]] = []

    for r in results:
        att = r.attempt
        ver = att.assignment.assessment_version
        assessment_history.append(
            {
                "result_id": str(r.id),
                "attempt_id": str(att.id),
                "template_id": str(ver.template_id),
                "template_name": ver.template.name,
                "version_no": ver.version_no,
                "attempt_no": att.attempt_no,
                "submitted_at": att.submitted_at.isoformat() if att.submitted_at else None,
                "raw_score": str(r.raw_score),
                "max_score": str(r.max_score),
                "normalized_score": float(r.normalized_score) if r.normalized_score is not None else None,
                "result_status": r.result_status,
                "breakdown": r.breakdown_json,
            }
        )

        breakdown = r.breakdown_json or {}
        for item in breakdown.get("demonstrated_performance", []):
            code = item["code"]
            bucket = demo_agg.setdefault(
                code,
                {
                    "dimension_id": item["dimension_id"],
                    "code": code,
                    "name": item["name"],
                    "awarded_marks": Decimal("0.00"),
                    "max_marks": Decimal("0.00"),
                    "scored_entries": 0,
                },
            )
            if item.get("status") != "insufficient_data":
                bucket["awarded_marks"] += Decimal(str(item.get("awarded_marks", "0")))
                bucket["max_marks"] += Decimal(str(item.get("max_marks", "0")))
                bucket["scored_entries"] += 1

        for item in breakdown.get("self_reported_proficiency", []):
            code = item["code"]
            bucket = self_agg.setdefault(
                code,
                {
                    "dimension_id": item["dimension_id"],
                    "code": code,
                    "name": item["name"],
                    "ratings": [],
                    "responses_count": 0,
                },
            )
            if item.get("average_rating") is not None:
                bucket["ratings"].append(float(item["average_rating"]))
            bucket["responses_count"] += int(item.get("responses_count", 0))

        for item in breakdown.get("stated_interest", []):
            code = item["code"]
            bucket = interest_agg.setdefault(
                code,
                {
                    "dimension_id": item["dimension_id"],
                    "code": code,
                    "name": item["name"],
                    "ratings": [],
                    "responses_count": 0,
                },
            )
            if item.get("average_rating") is not None:
                bucket["ratings"].append(float(item["average_rating"]))
            bucket["responses_count"] += int(item.get("responses_count", 0))

    demonstrated_dimensions: list[dict[str, Any]] = []
    strengths: list[dict[str, Any]] = []
    moderate: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    insufficient_data: list[dict[str, Any]] = []

    for item in demo_agg.values():
        max_m = item["max_marks"]
        raw_m = item["awarded_marks"]
        if item["scored_entries"] == 0 or max_m <= 0:
            entry = {
                "dimension_id": item["dimension_id"],
                "code": item["code"],
                "name": item["name"],
                "awarded_marks": str(raw_m),
                "max_marks": str(max_m),
                "percentage": None,
                "status": "insufficient_data",
            }
            demonstrated_dimensions.append(entry)
            insufficient_data.append(entry)
        else:
            pct = round(float(raw_m / max_m * Decimal("100")), 2)
            entry = {
                "dimension_id": item["dimension_id"],
                "code": item["code"],
                "name": item["name"],
                "awarded_marks": str(raw_m),
                "max_marks": str(max_m),
                "percentage": pct,
                "status": "scored",
            }
            demonstrated_dimensions.append(entry)
            if pct >= 70.0:
                strengths.append(entry)
            elif pct >= 50.0:
                moderate.append(entry)
            else:
                gaps.append(entry)

    strengths.sort(key=lambda x: x["percentage"], reverse=True)
    gaps.sort(key=lambda x: x["percentage"])

    self_reported_dimensions = [
        {
            "dimension_id": item["dimension_id"],
            "code": item["code"],
            "name": item["name"],
            "responses_count": item["responses_count"],
            "average_rating": round(sum(item["ratings"]) / len(item["ratings"]), 2) if item["ratings"] else None,
            "status": "insufficient_data" if item["responses_count"] == 0 else "recorded",
        }
        for item in self_agg.values()
    ]

    stated_interest_dimensions = sorted(
        [
            {
                "dimension_id": item["dimension_id"],
                "code": item["code"],
                "name": item["name"],
                "responses_count": item["responses_count"],
                "average_rating": round(sum(item["ratings"]) / len(item["ratings"]), 2) if item["ratings"] else None,
                "status": "insufficient_data" if item["responses_count"] == 0 else "recorded",
            }
            for item in interest_agg.values()
        ],
        key=lambda x: (x["average_rating"] is not None, x["average_rating"] or 0),
        reverse=True,
    )

    scored_pcts = [float(r.normalized_score) for r in results if r.normalized_score is not None]
    overall_pct = round(sum(scored_pcts) / len(scored_pcts), 2) if scored_pcts else None

    cohort_avg_pct = None
    if student.cohort_id:
        cohort_qs = AssessmentResult.objects.for_institution(student.institution).filter(
            attempt__student_profile__cohort_id=student.cohort_id,
            normalized_score__isnull=False,
        )
        if released_only:
            cohort_qs = cohort_qs.filter(attempt__assignment__results_released=True)
        c_scores = [float(v) for v in cohort_qs.values_list("normalized_score", flat=True)]
        if c_scores:
            cohort_avg_pct = round(sum(c_scores) / len(c_scores), 2)

    return {
        "notice": NON_CLINICAL_NOTICE,
        "student": {
            "id": str(student.id),
            "registration_no": student.registration_no,
            "full_name": student.membership.user.full_name,
            "email": student.membership.user.email,
            "cohort_id": str(student.cohort_id) if student.cohort_id else None,
            "cohort_label": str(student.cohort) if student.cohort else None,
        },
        "summary": {
            "assessments_count": len(results),
            "overall_demonstrated_percentage": overall_pct,
            "cohort_benchmark_percentage": cohort_avg_pct,
            "needs_additional_training": bool(gaps) or (overall_pct is not None and overall_pct < 50.0),
        },
        "demonstrated_performance": {
            "dimensions": demonstrated_dimensions,
            "strengths": strengths,
            "moderate": moderate,
            "gaps": gaps,
            "insufficient_data": insufficient_data,
        },
        "self_reported_proficiency": self_reported_dimensions,
        "stated_interest": stated_interest_dimensions,
        "assessment_history": assessment_history,
    }


def build_cohort_analytics(
    institution: Institution,
    cohort: Cohort,
    *,
    template_id: str | None = None,
) -> dict[str, Any]:
    """Build cohort domain averages, score distribution, strengths/gaps & student comparison."""
    students = list(
        StudentProfile.objects.for_institution(institution)
        .filter(cohort=cohort, status=StudentProfile.Status.ACTIVE)
        .select_related("membership__user")
        .order_by("registration_no")
    )

    results_qs = (
        AssessmentResult.objects.for_institution(institution)
        .filter(attempt__student_profile__cohort=cohort)
        .select_related("attempt__student_profile", "attempt__assignment__assessment_version__template")
    )
    if template_id:
        results_qs = results_qs.filter(attempt__assignment__assessment_version__template_id=template_id)

    results = list(results_qs)

    results_by_student: dict[str, list[AssessmentResult]] = defaultdict(list)
    for r in results:
        results_by_student[str(r.attempt.student_profile_id)].append(r)

    # Score distribution buckets
    buckets = [
        {"label": "0-39%", "min": 0.0, "max": 39.99, "count": 0},
        {"label": "40-54%", "min": 40.0, "max": 54.99, "count": 0},
        {"label": "55-69%", "min": 55.0, "max": 69.99, "count": 0},
        {"label": "70-84%", "min": 70.0, "max": 84.99, "count": 0},
        {"label": "85-100%", "min": 85.0, "max": 100.0, "count": 0},
    ]

    demo_dim_totals: dict[str, dict[str, Any]] = {}
    self_dim_totals: dict[str, dict[str, Any]] = {}
    interest_dim_totals: dict[str, dict[str, Any]] = {}

    student_comparison: list[dict[str, Any]] = []

    for stu in students:
        stu_results = results_by_student.get(str(stu.id), [])
        stu_pcts = [float(r.normalized_score) for r in stu_results if r.normalized_score is not None]
        avg_pct = round(sum(stu_pcts) / len(stu_pcts), 2) if stu_pcts else None

        if avg_pct is not None:
            for b in buckets:
                if b["min"] <= avg_pct <= b["max"] or (avg_pct > 100.0 and b["max"] == 100.0):
                    b["count"] += 1
                    break

        stu_dim_raw: dict[str, list[Decimal]] = defaultdict(lambda: [Decimal("0.00"), Decimal("0.00")])
        for r in stu_results:
            bd = r.breakdown_json or {}
            for item in bd.get("demonstrated_performance", []):
                code = item["code"]
                d_bucket = demo_dim_totals.setdefault(
                    code,
                    {"code": code, "name": item["name"], "awarded": Decimal("0.00"), "max": Decimal("0.00"), "entries": 0},
                )
                if item.get("status") != "insufficient_data":
                    a = Decimal(str(item.get("awarded_marks", "0")))
                    m = Decimal(str(item.get("max_marks", "0")))
                    d_bucket["awarded"] += a
                    d_bucket["max"] += m
                    d_bucket["entries"] += 1
                    stu_dim_raw[code][0] += a
                    stu_dim_raw[code][1] += m

            for item in bd.get("self_reported_proficiency", []):
                code = item["code"]
                s_bucket = self_dim_totals.setdefault(
                    code,
                    {"code": code, "name": item["name"], "ratings": [], "responses": 0},
                )
                if item.get("average_rating") is not None:
                    s_bucket["ratings"].append(float(item["average_rating"]))
                s_bucket["responses"] += int(item.get("responses_count", 0))

            for item in bd.get("stated_interest", []):
                code = item["code"]
                i_bucket = interest_dim_totals.setdefault(
                    code,
                    {"code": code, "name": item["name"], "ratings": [], "responses": 0},
                )
                if item.get("average_rating") is not None:
                    i_bucket["ratings"].append(float(item["average_rating"]))
                i_bucket["responses"] += int(item.get("responses_count", 0))

        stu_dim_pcts: dict[str, float | None] = {}
        for code, (a, m) in stu_dim_raw.items():
            stu_dim_pcts[code] = round(float(a / m * Decimal("100")), 2) if m > 0 else None

        scored_dims = [(c, p) for c, p in stu_dim_pcts.items() if p is not None]
        top_strength = max(scored_dims, key=lambda x: x[1])[0] if scored_dims else None
        primary_gap = min(scored_dims, key=lambda x: x[1])[0] if scored_dims else None
        needs_support = (avg_pct is not None and avg_pct < 50.0) or any(p < 50.0 for _, p in scored_dims)

        student_comparison.append(
            {
                "student_id": str(stu.id),
                "registration_no": stu.registration_no,
                "full_name": stu.membership.user.full_name,
                "attempts_count": len(stu_results),
                "average_percentage": avg_pct,
                "top_strength": top_strength,
                "primary_gap": primary_gap,
                "needs_additional_training": needs_support,
                "dimension_scores": stu_dim_pcts,
            }
        )

    demo_domain_avgs = []
    cohort_strengths = []
    cohort_gaps = []
    for d in demo_dim_totals.values():
        pct = round(float(d["awarded"] / d["max"] * Decimal("100")), 2) if d["max"] > 0 and d["entries"] > 0 else None
        entry = {
            "code": d["code"],
            "name": d["name"],
            "average_percentage": pct,
            "status": "insufficient_data" if pct is None else "scored",
        }
        demo_domain_avgs.append(entry)
        if pct is not None:
            if pct >= 70.0:
                cohort_strengths.append(entry)
            elif pct < 50.0:
                cohort_gaps.append(entry)

    self_domain_avgs = [
        {
            "code": s["code"],
            "name": s["name"],
            "average_rating": round(sum(s["ratings"]) / len(s["ratings"]), 2) if s["ratings"] else None,
            "responses_count": s["responses"],
        }
        for s in self_dim_totals.values()
    ]

    interest_domain_avgs = sorted(
        [
            {
                "code": i["code"],
                "name": i["name"],
                "average_rating": round(sum(i["ratings"]) / len(i["ratings"]), 2) if i["ratings"] else None,
                "responses_count": i["responses"],
            }
            for i in interest_dim_totals.values()
        ],
        key=lambda x: (x["average_rating"] is not None, x["average_rating"] or 0),
        reverse=True,
    )

    all_student_avgs = [s["average_percentage"] for s in student_comparison if s["average_percentage"] is not None]
    cohort_overall_avg = round(sum(all_student_avgs) / len(all_student_avgs), 2) if all_student_avgs else None

    return {
        "notice": NON_CLINICAL_NOTICE,
        "cohort": {
            "id": str(cohort.id),
            "label": str(cohort),
            "programme_code": cohort.programme.code,
            "batch_name": cohort.batch_name,
            "semester": cohort.semester,
            "section": cohort.section,
        },
        "summary": {
            "total_students": len(students),
            "assessed_students": sum(1 for s in student_comparison if s["attempts_count"] > 0),
            "total_results": len(results),
            "finalized_results": sum(1 for r in results if r.result_status == AssessmentResult.ResultStatus.FINALIZED),
            "pending_manual_results": sum(1 for r in results if r.result_status == AssessmentResult.ResultStatus.PENDING_MANUAL),
            "cohort_average_percentage": cohort_overall_avg,
            "students_needing_training": sum(1 for s in student_comparison if s["needs_additional_training"]),
        },
        "score_distribution": [{"label": b["label"], "count": b["count"]} for b in buckets],
        "demonstrated_performance_domains": demo_domain_avgs,
        "cohort_strengths": sorted(cohort_strengths, key=lambda x: x["average_percentage"], reverse=True),
        "cohort_gaps": sorted(cohort_gaps, key=lambda x: x["average_percentage"]),
        "self_reported_proficiency_domains": self_domain_avgs,
        "stated_interest_domains": interest_domain_avgs,
        "student_comparison": student_comparison,
    }

