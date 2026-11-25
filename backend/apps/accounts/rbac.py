"""Canonical Role and Permission definitions for Phase 1+."""

ROLE_PLATFORM_SUPER_ADMIN = "PLATFORM_SUPER_ADMIN"
ROLE_INSTITUTION_ADMIN = "INSTITUTION_ADMIN"
ROLE_ASSESSMENT_ADMIN = "ASSESSMENT_ADMIN"
ROLE_FACULTY_HOD = "FACULTY_HOD"
ROLE_STUDENT = "STUDENT"

ADMIN_PORTAL_ROLES = {
    ROLE_PLATFORM_SUPER_ADMIN,
    ROLE_INSTITUTION_ADMIN,
    ROLE_ASSESSMENT_ADMIN,
}

ACADEMIC_PORTAL_ROLES = {
    ROLE_FACULTY_HOD,
    ROLE_STUDENT,
}

CANONICAL_ROLES = [
    (ROLE_PLATFORM_SUPER_ADMIN, "Platform Super Admin", "platform"),
    (ROLE_INSTITUTION_ADMIN, "Institution Admin", "institution"),
    (ROLE_ASSESSMENT_ADMIN, "Assessment Admin", "institution"),
    (ROLE_FACULTY_HOD, "Faculty / HOD", "institution"),
    (ROLE_STUDENT, "Student", "institution"),
]

# Phase 1 + future-ready permission catalogue
CANONICAL_PERMISSIONS = [
    # Platform scope
    ("platform.institution.manage", "Manage Institutions", "platform", "Create, edit, and activate/deactivate institutions."),
    ("platform.admin.manage", "Manage Institution Admins", "platform", "Create and manage institution administrators."),
    ("audit.platform.view", "View Platform Audit Logs", "platform", "Read platform-wide audit events."),
    # Institution scope (Phase 1)
    ("institution.profile.manage", "Manage Institution Profile", "institution", "View and update active institution profile."),
    ("institution.user.manage", "Manage Institution Users", "institution", "Create, edit, deactivate users and assign institution roles."),
    ("academics.cohort.manage", "Manage Academic Structure", "institution", "Manage programmes, academic years, and cohorts."),
    ("institution.student.manage", "Manage Students", "institution", "Create, edit, and deactivate student profiles."),
    ("institution.student.import", "Import Students", "institution", "Upload, validate, and commit bulk student spreadsheets."),
    ("institution.faculty.manage", "Manage Faculty", "institution", "Create, edit, deactivate faculty and assign cohorts."),
    ("student.assigned.view", "View Assigned Cohort Students", "institution", "View students in assigned cohorts."),
    ("student.self.view", "View Own Student Profile", "institution", "View personal student profile and dashboard."),
    ("audit.institution.view", "View Institution Audit Logs", "institution", "Read audit events for the active institution."),
    # Phase 2 Assessment Administration permissions
    ("assessment.dimension.manage", "Manage Assessment Dimensions", "institution", "Manage assessment categories, dimensions, and skill tags."),
    ("assessment.question.manage", "Manage Question Bank", "institution", "Create, edit, and archive assessment questions."),
    ("assessment.scoring.manage", "Manage Scoring & Rubrics", "institution", "Configure marks, negative marking, and evaluation rubrics."),
    ("assessment.template.manage", "Manage Assessment Templates", "institution", "Build and configure draft assessment templates and versions."),
    ("assessment.publish", "Publish Assessment Versions", "institution", "Publish immutable assessment versions."),
    # Phase 3 Delivery & Evaluation permissions
    ("assessment.assign", "Assign Assessments", "institution", "Assign published assessments to cohorts or students and schedule availability."),
    ("assessment.attempt.take", "Take Assigned Assessments", "institution", "Start, autosave, and submit assigned assessments."),
    ("assessment.response.evaluate", "Evaluate Assessment Responses", "institution", "Manually evaluate descriptive and coding responses."),
    ("results.self.view", "View Own Released Results", "institution", "View own released assessment scores."),
    # Phase 4 Results, Analytics & Exports permissions
    ("results.cohort.view", "View Student & Cohort Results", "institution", "View individual and cohort assessment results within authorized scope."),
    ("analytics.cohort.view", "View Cohort Analytics", "institution", "View domain analytics, score distributions, and student comparisons."),
    ("reports.export", "Export Analytics Reports", "institution", "Export authorized assessment reports to CSV, XLSX, and PDF."),
    # Phase 5 Student Empowerment permissions
    ("development.catalogue.manage", "Manage Learning Catalogue", "institution", "Manage learning pathways, training, project, and certification resources."),
    ("development.plan.manage", "Manage Student Development Plans", "institution", "Create and review development plans for authorized students."),
    ("development.self.manage", "Manage Own Development Plan", "institution", "View personal recommendations, create development goals, and log progress."),
    # Phase 6 Institutional Intelligence & Executive Reports permissions
    ("intelligence.faculty.view", "View Faculty & HOD Intelligence", "institution", "View cohort-scoped placement readiness, mentoring telemetry, and pre/post comparisons."),
    ("analytics.executive.view", "View Institution Executive Reports", "institution", "View institution-wide executive summary, cohort benchmarks, and placement readiness rollups."),
]

ROLE_PERMISSION_MAP = {
    ROLE_PLATFORM_SUPER_ADMIN: [
        "platform.institution.manage",
        "platform.admin.manage",
        "audit.platform.view",
    ],
    ROLE_INSTITUTION_ADMIN: [
        "institution.profile.manage",
        "institution.user.manage",
        "academics.cohort.manage",
        "institution.student.manage",
        "institution.student.import",
        "institution.faculty.manage",
        "assessment.assign",
        "results.cohort.view",
        "analytics.cohort.view",
        "analytics.executive.view",
        "intelligence.faculty.view",
        "reports.export",
        "development.catalogue.manage",
        "development.plan.manage",
        "audit.institution.view",
    ],
    ROLE_ASSESSMENT_ADMIN: [
        "institution.profile.manage",
        "assessment.dimension.manage",
        "assessment.question.manage",
        "assessment.scoring.manage",
        "assessment.template.manage",
        "assessment.publish",
        "assessment.assign",
        "assessment.response.evaluate",
        "results.cohort.view",
        "analytics.cohort.view",
        "analytics.executive.view",
        "intelligence.faculty.view",
        "reports.export",
        "development.catalogue.manage",
        "development.plan.manage",
        "audit.institution.view",
    ],
    ROLE_FACULTY_HOD: [
        "student.assigned.view",
        "assessment.response.evaluate",
        "results.cohort.view",
        "analytics.cohort.view",
        "intelligence.faculty.view",
        "reports.export",
        "development.plan.manage",
    ],
    ROLE_STUDENT: [
        "student.self.view",
        "assessment.attempt.take",
        "results.self.view",
        "development.self.manage",
    ],
}

