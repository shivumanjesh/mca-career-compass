export type RoleCode =
  | "PLATFORM_SUPER_ADMIN"
  | "INSTITUTION_ADMIN"
  | "ASSESSMENT_ADMIN"
  | "FACULTY_HOD"
  | "STUDENT";

export type LoginPortal = "admin" | "academic";

export interface AuthUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  is_active: boolean;
  must_change_password: boolean;
}

export interface InstitutionSummary {
  id: string;
  code: string;
  name: string;
  status: "active" | "inactive" | "suspended";
  timezone: string;
}

export interface MembershipSummary {
  id: string;
  institution_id: string;
  institution_code: string;
  institution_name: string;
  status: "active" | "inactive" | "pending";
  roles: RoleCode[];
}

export interface AuthMeResponse {
  user: AuthUser;
  platform_roles: RoleCode[];
  active_institution: InstitutionSummary | null;
  active_membership_id: string | null;
  active_roles: RoleCode[];
  permissions: string[];
  memberships: MembershipSummary[];
}

export interface LoginPayload {
  portal: LoginPortal;
  identifier: string;
  password: string;
  institution_code?: string;
}

