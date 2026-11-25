"""Phase 6 Institutional Intelligence, Pre/Post Comparison, Placement Readiness & Executive Reports."""
from collections import defaultdict
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q

from apps.academics.models import AcademicYear, Cohort, Programme
from apps.analytics.services import (
    NON_CLINICAL_NOTICE,
    get_authorized_cohorts_queryset,
    get_authorized_students_queryset,
)
from apps.assessments.models import AssessmentTemplate
from apps.attempts.models import AssessmentResult, Response
from apps.development.models import DevelopmentPlan
from apps.faculty.models import CohortFaculty, FacultyProfile
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution, Membership

CORE_TECHNICAL_CODES = {"PROG", "DSA", "DBMS", "SE_TEST", "WEBMOB", "AIML", "CLOUDSEC"}

READINESS_LABELS = {
    "placement_ready": "Placement Ready",
    "near_ready": "Near Ready",
    "needs_support": "Foundational Support Needed",
    "insufficient_data": "Insufficient Assessment Data",
}


def _extract_student_demo_dims(results: list[AssessmentResult]) -> dict[str, dict[str, Any]]:
    dims: dict[str, dict[str, Any]] = {}
    for res in results:
        bd = res.breakdown_json or {}
        for item in bd.get("demonstrated_performance", []):
            code = item["code"]
            bucket = dims.setdefault(
                code,
                {"code": code, "name": item["name"], "awarded": Decimal("0.00"), "max": Decimal("0.00"), "entries": 0},
            )
            if item.get("status") != "insufficient_data":
                bucket["awarded"] += Decimal(str(item.get("awarded_marks", "0")))
                bucket["max"] += Decimal(str(item.get("max_marks", "0")))
                bucket["entries"] += 1
    out: dict[str, dict[str, Any]] = {}
    for code, b in dims.items():
        pct = round(float(b["awarded"] / b["max"] * Decimal("100")), 2) if b["max"] > 0 and b["entries"] > 0 else None
        out[code] = {
            "code": code,
            "name": b["name"],
            "awarded": b["awarded"],
            "max": b["max"],
            "percentage": pct,
        }
    return out


def _classify_student_readiness(
    student: StudentProfile,
    results: list[AssessmentResult],
    plans: list[DevelopmentPlan],
    pending_manual_count: int,
) -> dict[str, Any]:
    pcts = [float(r.normalized_score) for r in results if r.normalized_score is not None]
    overall_pct = round(sum(pcts) / len(pcts), 2) if pcts else None
    dims = _extract_student_demo_dims(results)

    core_awarded = sum((d["awarded"] for c, d in dims.items() if c in CORE_TECHNICAL_CODES and d["percentage"] is not None), Decimal("0.00"))
    core_max = sum((d["max"] for c, d in dims.items() if c in CORE_TECHNICAL_CODES and d["percentage"] is not None), Decimal("0.00"))
    core_tech_pct = round(float(core_awarded / core_max * Decimal("100")), 2) if core_max > 0 else None

    scored_dims = [(c, d["percentage"]) for c, d in dims.items() if d["percentage"] is not None]
    top_strength = max(scored_dims, key=lambda x: x[1])[0] if scored_dims else None
    primary_gap_pair = min(scored_dims, key=lambda x: x[1]) if scored_dims else None
    primary_gap = primary_gap_pair[0] if primary_gap_pair else None
    lowest_pct = primary_gap_pair[1] if primary_gap_pair else None

    plan_act_pcts: list[int] = []
    for p in plans:
        acts = list(p.activities.all())
        if acts:
            plan_act_pcts.append(round(sum(a.progress_percent for a in acts) / len(acts)))
    plan_completion_pct = round(sum(plan_act_pcts) / len(plan_act_pcts)) if plan_act_pcts else 0

    if overall_pct is None:
        band = "insufficient_data"
        explanation = "No scored demonstrated assessments completed yet."
    elif (
        overall_pct >= 75.0
        and (core_tech_pct is None or core_tech_pct >= 65.0)
        and (lowest_pct is None or lowest_pct >= 50.0)
    ):
        band = "placement_ready"
        explanation = f"Demonstrated avg {overall_pct}%" + (
            f", Core Tech {core_tech_pct}%" if core_tech_pct is not None else ""
        ) + f", lowest domain {lowest_pct}%."
    elif overall_pct >= 55.0 and (core_tech_pct is None or core_tech_pct >= 50.0):
        band = "near_ready"
        explanation = f"Demonstrated avg {overall_pct}%; strengthen {primary_gap or 'target gaps'} (Plan {plan_completion_pct}%)."
    else:
        band = "needs_support"
        explanation = f"Demonstrated avg {overall_pct}%" + (
            f" with gap in {primary_gap} ({lowest_pct}%)" if primary_gap and lowest_pct is not None else ""
        ) + "."

    return {
        "student_id": str(student.id),
        "registration_no": student.registration_no,
        "full_name": student.membership.user.full_name,
        "cohort_id": str(student.cohort_id) if student.cohort_id else None,
        "cohort_label": str(student.cohort) if student.cohort else "Unassigned",
        "attempts_count": len(results),
        "overall_demonstrated_percentage": overall_pct,
        "core_technical_percentage": core_tech_pct,
        "top_strength": top_strength,
        "primary_gap": primary_gap,
        "plans_count": len(plans),
        "plan_completion_percent": plan_completion_pct,
        "pending_manual_count": pending_manual_count,
        "readiness_band": band,
        "readiness_label": READINESS_LABELS[band],
        "evidence_summary": explanation,
    }


def _collect_domain_rollups(results: list[AssessmentResult]) -> tuple[list[dict], list[dict], list[dict]]:
    demo_totals: dict[str, dict[str, Any]] = {}
    self_totals: dict[str, dict[str, Any]] = {}
    interest_totals: dict[str, dict[str, Any]] = {}

    for res in results:
        bd = res.breakdown_json or {}
        for item in bd.get("demonstrated_performance", []):
            code = item["code"]
            b = demo_totals.setdefault(code, {"code": code, "name": item["name"], "awarded": Decimal("0.00"), "max": Decimal("0.00"), "entries": 0})
            if item.get("status") != "insufficient_data":
                b["awarded"] += Decimal(str(item.get("awarded_marks", "0")))
                b["max"] += Decimal(str(item.get("max_marks", "0")))
                b["entries"] += 1
        for item in bd.get("self_reported_proficiency", []):
            code = item["code"]
            b = self_totals.setdefault(code, {"code": code, "name": item["name"], "ratings": [], "responses": 0})
            if item.get("average_rating") is not None:
                b["ratings"].append(float(item["average_rating"]))
            b["responses"] += int(item.get("responses_count", 0))
        for item in bd.get("stated_interest", []):
            code = item["code"]
            b = interest_totals.setdefault(code, {"code": code, "name": item["name"], "ratings": [], "responses": 0})
            if item.get("average_rating") is not None:
                b["ratings"].append(float(item["average_rating"]))
            b["responses"] += int(item.get("responses_count", 0))

    demo_domains = [
        {
            "code": b["code"],
            "name": b["name"],
            "average_percentage": round(float(b["awarded"] / b["max"] * Decimal("100")), 2) if b["max"] > 0 and b["entries"] > 0 else None,
            "status": "scored" if b["max"] > 0 and b["entries"] > 0 else "insufficient_data",
        }
        for b in demo_totals.values()
    ]
    self_domains = [
        {
            "code": b["code"],
            "name": b["name"],
            "average_rating": round(sum(b["ratings"]) / len(b["ratings"]), 2) if b["ratings"] else None,
            "responses_count": b["responses"],
        }
        for b in self_totals.values()
    ]
    interest_domains = sorted(
        [
            {
                "code": b["code"],
                "name": b["name"],
                "average_rating": round(sum(b["ratings"]) / len(b["ratings"]), 2) if b["ratings"] else None,
                "responses_count": b["responses"],
            }
            for b in interest_totals.values()
        ],
        key=lambda x: (x["average_rating"] is not None, x["average_rating"] or 0),
        reverse=True,
    )
    return demo_domains, self_domains, interest_domains


def _compute_cohort_intelligence(
    institution: Institution,
    cohorts: list[Cohort],
    students: list[StudentProfile],
) -> dict[str, Any]:
    student_ids = [s.id for s in students]
    cohort_ids = [c.id for c in cohorts]

    results = list(
        AssessmentResult.objects.for_institution(institution)
        .filter(attempt__student_profile_id__in=student_ids)
        .select_related("attempt__student_profile", "attempt__assignment__assessment_version__template")
        .order_by("attempt__submitted_at", "created_at")
    )
    plans = list(
        DevelopmentPlan.objects.for_institution(institution)
        .filter(student_profile_id__in=student_ids)
        .prefetch_related("activities")
    )
    pending_counts_rows = (
        Response.objects.filter(
            attempt__institution=institution,
            attempt__student_profile_id__in=student_ids,
            scoring_status=Response.ScoringStatus.PENDING_MANUAL,
        )
        .values("attempt__student_profile_id")
        .annotate(cnt=Count("id"))
    )
    pending_by_stu = {str(r["attempt__student_profile_id"]): r["cnt"] for r in pending_counts_rows}

    mentor_assignments = list(
        CohortFaculty.objects.for_institution(institution)
        .filter(cohort_id__in=cohort_ids)
        .select_related("faculty_profile__membership__user")
    )
    mentors_by_cohort: dict[str, list[str]] = defaultdict(list)
    for cf in mentor_assignments:
        mentors_by_cohort[str(cf.cohort_id)].append(
            f"{cf.faculty_profile.membership.user.full_name} ({cf.get_assignment_type_display()})"
        )

    results_by_stu: dict[str, list[AssessmentResult]] = defaultdict(list)
    for r in results:
        results_by_stu[str(r.attempt.student_profile_id)].append(r)

    plans_by_stu: dict[str, list[DevelopmentPlan]] = defaultdict(list)
    for p in plans:
        plans_by_stu[str(p.student_profile_id)].append(p)

    student_readiness = [
        _classify_student_readiness(
            s,
            results_by_stu.get(str(s.id), []),
            plans_by_stu.get(str(s.id), []),
            pending_by_stu.get(str(s.id), 0),
        )
        for s in students
    ]

    band_counts = {k: 0 for k in READINESS_LABELS}
    rows_by_cohort: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in student_readiness:
        band_counts[row["readiness_band"]] += 1
        if row["cohort_id"]:
            rows_by_cohort[row["cohort_id"]].append(row)

    cohort_rollups: list[dict[str, Any]] = []
    for c in cohorts:
        c_rows = rows_by_cohort.get(str(c.id), [])
        avgs = [r["overall_demonstrated_percentage"] for r in c_rows if r["overall_demonstrated_percentage"] is not None]
        with_plans = sum(1 for r in c_rows if r["plans_count"] > 0)
        plan_pcts = [r["plan_completion_percent"] for r in c_rows if r["plans_count"] > 0]
        cohort_rollups.append({
            "cohort_id": str(c.id),
            "cohort_label": str(c),
            "programme_code": c.programme.code,
            "batch_name": c.batch_name,
            "semester": c.semester,
            "section": c.section,
            "assigned_mentors": mentors_by_cohort.get(str(c.id), []),
            "total_students": len(c_rows),
            "assessed_students": sum(1 for r in c_rows if r["attempts_count"] > 0),
            "average_demonstrated_percentage": round(sum(avgs) / len(avgs), 2) if avgs else None,
            "placement_ready_count": sum(1 for r in c_rows if r["readiness_band"] == "placement_ready"),
            "near_ready_count": sum(1 for r in c_rows if r["readiness_band"] == "near_ready"),
            "needs_support_count": sum(1 for r in c_rows if r["readiness_band"] == "needs_support"),
            "pending_manual_evaluations": sum(r["pending_manual_count"] for r in c_rows),
            "plan_adoption_rate": round((with_plans / len(c_rows)) * 100, 1) if c_rows else 0.0,
            "avg_plan_completion_percent": round(sum(plan_pcts) / len(plan_pcts)) if plan_pcts else 0,
        })

    demo_domains, self_domains, interest_domains = _collect_domain_rollups(results)
    all_stu_avgs = [r["overall_demonstrated_percentage"] for r in student_readiness if r["overall_demonstrated_percentage"] is not None]
    plan_pcts_all = [r["plan_completion_percent"] for r in student_readiness if r["plans_count"] > 0]

    return {
        "readiness_distribution": [
            {"band": band, "label": label, "count": band_counts[band]}
            for band, label in READINESS_LABELS.items()
        ],
        "cohort_rollups": cohort_rollups,
        "student_readiness": student_readiness,
        "demonstrated_domains": demo_domains,
        "self_reported_domains": self_domains,
        "stated_interest_domains": interest_domains,
        "summary_stats": {
            "authorized_cohorts": len(cohorts),
            "total_students": len(students),
            "assessed_students": sum(1 for r in student_readiness if r["attempts_count"] > 0),
            "placement_ready_count": band_counts["placement_ready"],
            "near_ready_count": band_counts["near_ready"],
            "needs_support_count": band_counts["needs_support"],
            "insufficient_data_count": band_counts["insufficient_data"],
            "average_demonstrated_percentage": round(sum(all_stu_avgs) / len(all_stu_avgs), 2) if all_stu_avgs else None,
            "pending_manual_evaluations": sum(r["pending_manual_count"] for r in student_readiness),
            "students_with_plans": sum(1 for r in student_readiness if r["plans_count"] > 0),
            "active_or_completed_plans": sum(1 for p in plans if p.status in (DevelopmentPlan.Status.ACTIVE, DevelopmentPlan.Status.COMPLETED)),
            "avg_plan_completion_percent": round(sum(plan_pcts_all) / len(plan_pcts_all)) if plan_pcts_all else 0,
        },
    }


def build_faculty_intelligence(
    institution: Institution,
    membership: Membership,
    perms: set[str],
    *,
    cohort_id: str | None = None,
) -> dict[str, Any]:
    """Cohort-scoped Faculty / HOD intelligence dashboard with placement readiness & mentoring metrics."""
    cohorts_qs = get_authorized_cohorts_queryset(institution, membership, perms).order_by(
        "-academic_year__start_date", "batch_name", "semester", "section"
    )
    if cohort_id:
        cohorts_qs = cohorts_qs.filter(id=cohort_id)
    cohorts = list(cohorts_qs)

    students_qs = get_authorized_students_queryset(institution, membership, perms).filter(
        status=StudentProfile.Status.ACTIVE
    )
    if cohort_id:
        students_qs = students_qs.filter(cohort_id=cohort_id)
    students = list(students_qs.order_by("registration_no"))

    computed = _compute_cohort_intelligence(institution, cohorts, students)
    return {
        "notice": NON_CLINICAL_NOTICE,
        "summary": computed["summary_stats"],
        "readiness_distribution": computed["readiness_distribution"],
        "cohort_rollups": computed["cohort_rollups"],
        "domain_hotspots": computed["demonstrated_domains"],
        "self_reported_domains": computed["self_reported_domains"],
        "stated_interest_domains": computed["stated_interest_domains"],
        "student_readiness": computed["student_readiness"],
    }


def build_pre_post_comparison(
    institution: Institution,
    membership: Membership,
    perms: set[str],
    *,
    pre_template_id: str | None = None,
    post_template_id: str | None = None,
    cohort_id: str | None = None,
) -> dict[str, Any]:
    """Compare baseline (Pre) vs follow-up (Post) demonstrated assessment results across cohorts/students."""
    students_qs = get_authorized_students_queryset(institution, membership, perms).filter(
        status=StudentProfile.Status.ACTIVE
    )
    if cohort_id:
        students_qs = students_qs.filter(cohort_id=cohort_id)
    students = list(students_qs.order_by("registration_no"))
    student_ids = [s.id for s in students]

    results = list(
        AssessmentResult.objects.for_institution(institution)
        .filter(attempt__student_profile_id__in=student_ids)
        .select_related("attempt__assignment__assessment_version__template")
        .order_by("attempt__submitted_at", "created_at")
    )
    by_stu: dict[str, list[AssessmentResult]] = defaultdict(list)
    for r in results:
        by_stu[str(r.attempt.student_profile_id)].append(r)

    use_template_pair = bool(pre_template_id and post_template_id)
    pre_label = "Earliest Assessment"
    post_label = "Latest Assessment"
    if use_template_pair:
        tmpl_map = {
            str(t.id): t.name
            for t in AssessmentTemplate.objects.for_institution(institution).filter(id__in=[pre_template_id, post_template_id])
        }
        pre_label = tmpl_map.get(str(pre_template_id), "Baseline Template")
        post_label = tmpl_map.get(str(post_template_id), "Follow-Up Template")

    trajectories: list[dict[str, Any]] = []
    pre_dim_agg: dict[str, dict[str, Any]] = {}
    post_dim_agg: dict[str, dict[str, Any]] = {}

    for stu in students:
        stu_res = by_stu.get(str(stu.id), [])
        pre_res: AssessmentResult | None = None
        post_res: AssessmentResult | None = None

        if use_template_pair:
            if pre_template_id == post_template_id:
                matching = [r for r in stu_res if str(r.attempt.assignment.assessment_version.template_id) == str(pre_template_id)]
                if len(matching) >= 2:
                    pre_res, post_res = matching[0], matching[-1]
            else:
                pre_matches = [r for r in stu_res if str(r.attempt.assignment.assessment_version.template_id) == str(pre_template_id)]
                post_matches = [r for r in stu_res if str(r.attempt.assignment.assessment_version.template_id) == str(post_template_id)]
                if pre_matches and post_matches:
                    pre_res, post_res = pre_matches[-1], post_matches[-1]
        elif len(stu_res) >= 2:
            pre_res, post_res = stu_res[0], stu_res[-1]

        if not (pre_res and post_res and pre_res.normalized_score is not None and post_res.normalized_score is not None):
            continue

        pre_score = float(pre_res.normalized_score)
        post_score = float(post_res.normalized_score)
        delta = round(post_score - pre_score, 2)
        trend = "improved" if delta > 0 else ("declined" if delta < 0 else "unchanged")

        trajectories.append({
            "student_id": str(stu.id),
            "registration_no": stu.registration_no,
            "full_name": stu.membership.user.full_name,
            "cohort_label": str(stu.cohort) if stu.cohort else "Unassigned",
            "pre_template": pre_res.attempt.assignment.assessment_version.template.name,
            "post_template": post_res.attempt.assignment.assessment_version.template.name,
            "pre_score": pre_score,
            "post_score": post_score,
            "delta": delta,
            "trend": trend,
        })

        for res, target_agg in ((pre_res, pre_dim_agg), (post_res, post_dim_agg)):
            for item in (res.breakdown_json or {}).get("demonstrated_performance", []):
                if item.get("status") == "insufficient_data":
                    continue
                code = item["code"]
                b = target_agg.setdefault(
                    code,
                    {"code": code, "name": item["name"], "awarded": Decimal("0.00"), "max": Decimal("0.00"), "matched": 0},
                )
                b["awarded"] += Decimal(str(item.get("awarded_marks", "0")))
                b["max"] += Decimal(str(item.get("max_marks", "0")))
                b["matched"] += 1

    all_dim_codes = sorted(set(pre_dim_agg.keys()) | set(post_dim_agg.keys()))
    dimension_deltas: list[dict[str, Any]] = []
    for code in all_dim_codes:
        pb = pre_dim_agg.get(code)
        qb = post_dim_agg.get(code)
        pre_pct = round(float(pb["awarded"] / pb["max"] * Decimal("100")), 2) if pb and pb["max"] > 0 else None
        post_pct = round(float(qb["awarded"] / qb["max"] * Decimal("100")), 2) if qb and qb["max"] > 0 else None
        delta_pct = round(post_pct - pre_pct, 2) if pre_pct is not None and post_pct is not None else None
        dimension_deltas.append({
            "code": code,
            "name": (qb or pb)["name"],
            "pre_percentage": pre_pct,
            "post_percentage": post_pct,
            "delta_percentage": delta_pct,
            "matched_students": min(pb["matched"] if pb else 0, qb["matched"] if qb else 0),
        })

    pre_avg = round(sum(t["pre_score"] for t in trajectories) / len(trajectories), 2) if trajectories else None
    post_avg = round(sum(t["post_score"] for t in trajectories) / len(trajectories), 2) if trajectories else None
    avg_delta = round(post_avg - pre_avg, 2) if pre_avg is not None and post_avg is not None else None

    return {
        "notice": NON_CLINICAL_NOTICE,
        "mode": "template_pair" if use_template_pair else "earliest_vs_latest",
        "pre_label": pre_label,
        "post_label": post_label,
        "summary": {
            "comparable_students": len(trajectories),
            "pre_average_percentage": pre_avg,
            "post_average_percentage": post_avg,
            "average_delta": avg_delta,
            "improved_students_count": sum(1 for t in trajectories if t["trend"] == "improved"),
            "declined_students_count": sum(1 for t in trajectories if t["trend"] == "declined"),
            "unchanged_students_count": sum(1 for t in trajectories if t["trend"] == "unchanged"),
        },
        "dimension_deltas": dimension_deltas,
        "student_trajectories": trajectories,
    }


def build_executive_report(institution: Institution) -> dict[str, Any]:
    """Build institution-wide executive summary, cohort comparison, readiness & empowerment rollup."""
    cohorts = list(
        Cohort.objects.for_institution(institution)
        .select_related("programme", "academic_year")
        .order_by("-academic_year__start_date", "batch_name", "semester", "section")
    )
    students = list(
        StudentProfile.objects.for_institution(institution)
        .filter(status=StudentProfile.Status.ACTIVE)
        .select_related("membership__user", "cohort__programme", "cohort__academic_year")
        .order_by("registration_no")
    )
    computed = _compute_cohort_intelligence(institution, cohorts, students)
    stats = computed["summary_stats"]

    total_stu = stats["total_students"]
    participation_rate = round((stats["assessed_students"] / total_stu) * 100, 1) if total_stu else 0.0
    ready_rate = round((stats["placement_ready_count"] / total_stu) * 100, 1) if total_stu else 0.0

    scored_demo = [d for d in computed["demonstrated_domains"] if d["average_percentage"] is not None]
    strengths = sorted([d for d in scored_demo if d["average_percentage"] >= 70.0], key=lambda x: x["average_percentage"], reverse=True)
    gaps = sorted([d for d in scored_demo if d["average_percentage"] < 55.0], key=lambda x: x["average_percentage"])

    return {
        "notice": NON_CLINICAL_NOTICE,
        "institution": {
            "id": str(institution.id),
            "code": institution.code,
            "name": institution.name,
        },
        "summary": {
            "total_programmes": Programme.objects.for_institution(institution).filter(status="active").count(),
            "total_academic_years": AcademicYear.objects.for_institution(institution).filter(status="active").count(),
            "total_cohorts": len(cohorts),
            "active_faculty_count": FacultyProfile.objects.for_institution(institution).filter(status=FacultyProfile.Status.ACTIVE).count(),
            "total_students": total_stu,
            "assessed_students": stats["assessed_students"],
            "participation_rate": participation_rate,
            "overall_demonstrated_percentage": stats["average_demonstrated_percentage"],
            "placement_ready_count": stats["placement_ready_count"],
            "placement_ready_rate": ready_rate,
            "near_ready_count": stats["near_ready_count"],
            "needs_support_count": stats["needs_support_count"],
            "active_or_completed_plans": stats["active_or_completed_plans"],
            "avg_plan_completion_percent": stats["avg_plan_completion_percent"],
            "pending_manual_evaluations": stats["pending_manual_evaluations"],
        },
        "readiness_distribution": computed["readiness_distribution"],
        "cohort_rollups": computed["cohort_rollups"],
        "demonstrated_domains": computed["demonstrated_domains"],
        "demonstrated_strengths": strengths,
        "demonstrated_gaps": gaps,
        "self_reported_domains": computed["self_reported_domains"],
        "stated_interest_domains": computed["stated_interest_domains"],
    }

