"""Explainable, evidence-cited domain & learning recommendation engine (Phase 5)."""
from typing import Any
from django.db import transaction

from apps.analytics.services import NON_CLINICAL_NOTICE, build_student_report
from apps.audit.services import log_audit_event
from apps.development.models import LearningResource, ResourceType
from apps.students.models import StudentProfile
from apps.tenancy.models import Institution

DOMAIN_DEFINITIONS = [
    {
        "domain": "Software Development",
        "demo_dims": ["PROG", "DSA", "DBMS", "SE_TEST", "WEBMOB"],
        "interest_dims": ["INT_SDE"],
    },
    {
        "domain": "AI / ML Engineering",
        "demo_dims": ["AIML", "PROG", "DSA", "ANALYTICAL"],
        "interest_dims": ["INT_AIML"],
    },
    {
        "domain": "Data Analytics",
        "demo_dims": ["DBMS", "AIML", "NUMERICAL", "ANALYTICAL"],
        "interest_dims": ["INT_DATA"],
    },
    {
        "domain": "Cloud / DevOps",
        "demo_dims": ["CLOUDSEC", "SE_TEST", "PROG"],
        "interest_dims": ["INT_CLOUD"],
    },
    {
        "domain": "Cybersecurity",
        "demo_dims": ["CLOUDSEC", "LOGIC", "DEBUG"],
        "interest_dims": ["INT_CYBER"],
    },
    {
        "domain": "UI / UX & Web Engineering",
        "demo_dims": ["WEBMOB", "SE_TEST", "COMM"],
        "interest_dims": ["INT_UIUX"],
    },
]

STARTER_RESOURCES = [
    # Learning Pathways
    ("PROG", "Software Development", ResourceType.LEARNING_PATHWAY, "Clean Python & Object-Oriented Design Pathway", "Structured modular track covering clean functions, OOP patterns, and unit testing.", "Institutional Track", "beginner", 24),
    ("DSA", "Software Development", ResourceType.LEARNING_PATHWAY, "Algorithmic Problem Solving & Complexity Mastery", "Step-by-step mastery of trees, graphs, dynamic programming, and complexity analysis.", "Institutional Track", "intermediate", 36),
    ("AIML", "AI / ML Engineering", ResourceType.LEARNING_PATHWAY, "Applied Machine Learning & Model Evaluation Pathway", "Covers supervised/unsupervised pipelines, feature engineering, and validation metrics.", "Institutional Track", "intermediate", 40),
    ("DBMS", "Data Analytics", ResourceType.LEARNING_PATHWAY, "SQL Query Optimization & Relational Modelling Pathway", "Deep dive into indexing, normalization, window functions, and analytical queries.", "Institutional Track", "intermediate", 20),
    ("CLOUDSEC", "Cloud / DevOps", ResourceType.LEARNING_PATHWAY, "Linux, Containers & Cloud Infrastructure Foundations", "Hands-on pathway covering Docker, CI/CD, networking, and IAM security basics.", "Institutional Track", "beginner", 28),
    # Trainings
    ("DSA", "Software Development", ResourceType.TRAINING, "DSA Intensive Boot Camp (Arrays, Recursion & Graphs)", "Targeted remedial workshop strengthening core data structures and dry-run tracing.", "MCA Skill Lab", "beginner", 16),
    ("DEBUG", "Software Development", ResourceType.TRAINING, "Systematic Debugging & Problem Decomposition Clinic", "Practical exercises on reading stack traces, edge-case testing, and root-cause isolation.", "MCA Skill Lab", "beginner", 12),
    ("COMM", "UI / UX & Web Engineering", ResourceType.TRAINING, "Technical Communication & Design Review Workshop", "Practice articulating architectural decisions and structured technical documentation.", "Placement Cell", "beginner", 10),
    # Projects
    ("WEBMOB", "Software Development", ResourceType.PROJECT, "Full-Stack Multi-Tenant Academic Portal Capstone", "Build a PostgreSQL + REST API + React TypeScript application with automated tests.", "MCA Project Bank", "intermediate", 45),
    ("AIML", "AI / ML Engineering", ResourceType.PROJECT, "Explainable Student Risk & Study-Path Recommender Prototype", "Design an interpretable ML pipeline with clear baseline metrics and error analysis.", "MCA Project Bank", "advanced", 50),
    ("DBMS", "Data Analytics", ResourceType.PROJECT, "Institutional Placement & Cohort Trends Warehouse", "Design normalized schemas, analytical views, and interactive visual dashboards.", "MCA Project Bank", "intermediate", 35),
    ("CLOUDSEC", "Cybersecurity", ResourceType.PROJECT, "Web Application Security Audit & Hardening Lab", "Perform OWASP Top-10 threat modelling, CSRF/RBAC testing, and remediation.", "MCA Cyber Lab", "intermediate", 30),
    # Certifications
    ("PROG", "Software Development", ResourceType.CERTIFICATION, "Python Institute PCEP / PCAP Readiness", "Industry-recognized Python programming credential.", "Python Institute", "beginner", 30),
    ("CLOUDSEC", "Cloud / DevOps", ResourceType.CERTIFICATION, "AWS Certified Cloud Practitioner / Azure Fundamentals", "Foundational cloud architecture, security, and deployment certification.", "Cloud Provider", "beginner", 25),
    ("AIML", "AI / ML Engineering", ResourceType.CERTIFICATION, "TensorFlow / Applied Data Science Professional Certificate", "End-to-end ML workflow certification.", "Coursera / DeepLearning.AI", "intermediate", 45),
    ("CLOUDSEC", "Cybersecurity", ResourceType.CERTIFICATION, "CompTIA Security+ / ISC2 Certified in Cybersecurity (CC)", "Core network security, access control, and risk management credential.", "ISC2 / CompTIA", "intermediate", 40),
]


@transaction.atomic
def seed_starter_learning_catalogue(*, institution: Institution, actor_user=None, request=None) -> dict[str, int]:
    created_count = 0
    for dim_code, domain, r_type, title, desc, provider, level, hours in STARTER_RESOURCES:
        _, created = LearningResource.objects.get_or_create(
            institution=institution,
            title=title,
            defaults={
                "dimension_code": dim_code,
                "target_domain": domain,
                "resource_type": r_type,
                "description": desc,
                "provider": provider,
                "level": level,
                "estimated_hours": hours,
            },
        )
        if created:
            created_count += 1

    log_audit_event(
        action="LEARNING_CATALOGUE_SEEDED",
        entity_type="Institution",
        entity_id=institution.id,
        institution=institution,
        actor_user=actor_user,
        after={"created_resources": created_count},
        request=request,
    )
    return {"created_resources": created_count}


def generate_student_recommendations(
    student: StudentProfile,
    *,
    released_only: bool = True,
) -> dict[str, Any]:
    """Produce explainable, evidence-cited domain, pathway, training, project & certification recommendations."""
    report = build_student_report(student, released_only=released_only)

    demo_by_code = {
        d["code"]: d for d in report["demonstrated_performance"]["dimensions"]
    }
    interest_by_code = {
        d["code"]: d for d in report["stated_interest"]
    }
    self_by_code = {
        d["code"]: d for d in report["self_reported_proficiency"]
    }

    # 1. Domain-fit mapping keeping demonstrated vs interest evidence explicit
    domain_recommendations: list[dict[str, Any]] = []
    for cfg in DOMAIN_DEFINITIONS:
        demo_ev = [
            {"code": c, "percentage": demo_by_code[c]["percentage"]}
            for c in cfg["demo_dims"]
            if c in demo_by_code and demo_by_code[c]["percentage"] is not None
        ]
        int_ev = [
            {"code": c, "rating": interest_by_code[c]["average_rating"]}
            for c in cfg["interest_dims"]
            if c in interest_by_code and interest_by_code[c]["average_rating"] is not None
        ]

        avg_demo = round(sum(x["percentage"] for x in demo_ev) / len(demo_ev), 2) if demo_ev else None
        avg_int = round(sum(x["rating"] for x in int_ev) / len(int_ev), 2) if int_ev else None

        if avg_demo is not None and avg_demo >= 70.0 and (avg_int is None or avg_int >= 3.5):
            signal = "Strong Fit"
        elif avg_int is not None and avg_int >= 3.5 and (avg_demo is None or avg_demo < 60.0):
            signal = "High Interest — Build Foundations"
        elif avg_demo is not None and avg_demo >= 70.0:
            signal = "Capable — Explore Domain"
        elif avg_demo is not None:
            signal = "Developing"
        else:
            signal = "Insufficient Assessment Data"

        demo_text = ", ".join(f"{x['code']} ({x['percentage']}%)" for x in demo_ev) or "No objective scores yet"
        int_text = ", ".join(f"{x['code']} ({x['rating']}/5)" for x in int_ev) or "No stated interest rating yet"

        domain_recommendations.append({
            "domain": cfg["domain"],
            "readiness_signal": signal,
            "demonstrated_average": avg_demo,
            "interest_rating": avg_int,
            "demonstrated_evidence": demo_ev,
            "interest_evidence": int_ev,
            "explanation": f"Demonstrated evidence: {demo_text}. Stated career interest: {int_text}.",
            "_rank_score": (avg_demo or 0) + ((avg_int or 0) * 10),
        })

    domain_recommendations.sort(key=lambda d: d["_rank_score"], reverse=True)
    for d in domain_recommendations:
        d.pop("_rank_score", None)

    # 2. Match institutional LearningResource catalogue with explicit evidence citations
    resources = list(
        LearningResource.objects.for_institution(student.institution).filter(status=LearningResource.Status.ACTIVE)
    )
    gap_codes = {g["code"]: g["percentage"] for g in report["demonstrated_performance"]["gaps"]}
    strength_codes = {s["code"]: s["percentage"] for s in report["demonstrated_performance"]["strengths"]}
    strong_domains = {
        d["domain"] for d in domain_recommendations
        if d["readiness_signal"] in ("Strong Fit", "High Interest — Build Foundations", "Capable — Explore Domain")
    }

    learning_pathways = []
    training_recommendations = []
    project_recommendations = []
    certification_recommendations = []

    for res in resources:
        dim_c = res.dimension_code.upper()
        demo_item = demo_by_code.get(dim_c)
        self_item = self_by_code.get(dim_c)

        reasons = []
        priority = 1
        if dim_c in gap_codes:
            reasons.append(f"Addresses skill gap in {dim_c} ({gap_codes[dim_c]}% demonstrated)")
            priority += 3
        elif dim_c in strength_codes:
            reasons.append(f"Builds on demonstrated strength in {dim_c} ({strength_codes[dim_c]}%)")
            priority += 2
        elif demo_item and demo_item["percentage"] is not None:
            reasons.append(f"Aligned to {dim_c} ({demo_item['percentage']}% demonstrated)")
            priority += 1

        if res.target_domain in strong_domains:
            reasons.append(f"Matches domain focus: {res.target_domain}")
            priority += 1
        if self_item and self_item.get("average_rating") is not None:
            reasons.append(f"Self-reported rating in {dim_c}: {self_item['average_rating']}/5")

        if not reasons:
            reasons.append(f"Core MCA recommendation for {res.target_domain}")

        rec_obj = {
            "resource_id": str(res.id),
            "title": res.title,
            "resource_type": res.resource_type,
            "target_domain": res.target_domain,
            "dimension_code": dim_c,
            "provider": res.provider,
            "level": res.level,
            "estimated_hours": res.estimated_hours,
            "resource_url": res.resource_url,
            "description": res.description,
            "reason": " • ".join(reasons),
            "_priority": priority,
        }

        if res.resource_type == ResourceType.LEARNING_PATHWAY:
            learning_pathways.append(rec_obj)
        elif res.resource_type == ResourceType.TRAINING:
            # Prioritize training for skill gaps or beginner strengthening
            if dim_c in gap_codes:
                rec_obj["_priority"] += 3
            training_recommendations.append(rec_obj)
        elif res.resource_type == ResourceType.PROJECT:
            project_recommendations.append(rec_obj)
        elif res.resource_type == ResourceType.CERTIFICATION:
            certification_recommendations.append(rec_obj)

    for bucket in (learning_pathways, training_recommendations, project_recommendations, certification_recommendations):
        bucket.sort(key=lambda r: r["_priority"], reverse=True)
        for item in bucket:
            item.pop("_priority", None)

    return {
        "notice": NON_CLINICAL_NOTICE,
        "advisory_note": "Recommendations are non-deterministic educational suggestions citing your assessment evidence. Review and customize them in your development plan.",
        "student": report["student"],
        "summary": report["summary"],
        "domain_recommendations": domain_recommendations,
        "learning_pathways": learning_pathways[:6],
        "training_recommendations": training_recommendations[:6],
        "project_recommendations": project_recommendations[:6],
        "certification_recommendations": certification_recommendations[:6],
    }

