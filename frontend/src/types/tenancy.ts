import type { RoleCode } from "./auth";

export type InstitutionStatus = "active" | "inactive" | "suspended";
export type MembershipStatus = "active" | "inactive" | "pending";

export interface InstitutionSettings {
  contact_email?: string;
  website?: string;
  city?: string;
  [key: string]: unknown;
}

export interface InstitutionRecord {
  id: string;
  code: string;
  name: string;
  status: InstitutionStatus;
  timezone: string;
  settings: InstitutionSettings;
  member_count: number;
  admin_count: number;
  created_at: string;
  updated_at: string;
}

export interface MembershipUserRecord {
  id: string;
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  status: MembershipStatus;
  user_is_active: boolean;
  must_change_password: boolean;
  last_login: string | null;
  roles: RoleCode[];
  created_at: string;
  updated_at: string;
  onboarding_reset_path?: string;
}

export interface PlatformDashboardSummary {
  scope: "platform";
  metrics: {
    total_institutions: number;
    active_institutions: number;
    inactive_institutions: number;
    total_users: number;
    total_audit_events: number;
  };
  recent_institutions: Array<{
    id: string;
    code: string;
    name: string;
    status: InstitutionStatus;
    timezone: string;
    created_at: string;
  }>;
}

export interface InstitutionDashboardSummary {
  scope: "institution";
  institution: {
    id: string;
    code: string;
    name: string;
    status: InstitutionStatus;
    timezone: string;
  };
  metrics: {
    total_members: number;
    active_members: number;
    student_count: number;
    faculty_count: number;
    cohort_count: number;
    dimension_count?: number;
    question_count?: number;
    template_count?: number;
    published_version_count?: number;
    audit_events_count: number;
  };
  role_breakdown: Record<string, number>;
}

export interface StudentDashboardSummary {
  scope: "student";
  institution: {
    id: string;
    code: string;
    name: string;
  };
  metrics?: {
    assigned_assessments: number;
    completed_attempts: number;
  };
  student_profile: {
    registration_no: string;
    admission_year: number | null;
    status: "active" | "inactive";
    cohort: string | null;
    programme: string | null;
    semester: number | null;
    section: string | null;
  } | null;
}

export interface FacultyDashboardSummary {
  scope: "faculty";
  institution: {
    id: string;
    code: string;
    name: string;
  };
  metrics: {
    assigned_cohorts: number;
    assigned_students: number;
    pending_evaluations?: number;
  };
  cohorts: Array<{
    cohort_id: string;
    cohort_label: string;
    assignment_type: string;
    student_count: number;
  }>;
}

export interface UnassignedDashboardSummary {
  scope: "unassigned";
  metrics: Record<string, never>;
}

export type DashboardSummaryResponse =
  | PlatformDashboardSummary
  | InstitutionDashboardSummary
  | StudentDashboardSummary
  | FacultyDashboardSummary
  | UnassignedDashboardSummary;

