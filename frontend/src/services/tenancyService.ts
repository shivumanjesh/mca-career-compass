import { apiClient } from "./apiClient";
import { ensureCsrfCookie } from "./authService";
import type { PaginatedResponse } from "../types/api";
import type { RoleCode } from "../types/auth";
import type {
  DashboardSummaryResponse,
  InstitutionRecord,
  InstitutionSettings,
  InstitutionStatus,
  MembershipStatus,
  MembershipUserRecord,
} from "../types/tenancy";

export async function fetchDashboardSummary(): Promise<DashboardSummaryResponse> {
  const res = await apiClient.get<DashboardSummaryResponse>("/dashboard/summary/");
  return res.data;
}

// Platform Super Admin APIs
export async function listInstitutions(params: {
  page?: number;
  search?: string;
  status?: string;
}): Promise<PaginatedResponse<InstitutionRecord>> {
  const res = await apiClient.get<PaginatedResponse<InstitutionRecord>>("/platform/institutions/", {
    params,
  });
  return res.data;
}

export async function createInstitution(payload: {
  code: string;
  name: string;
  status: InstitutionStatus;
  timezone: string;
  settings?: InstitutionSettings;
}): Promise<InstitutionRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<InstitutionRecord>("/platform/institutions/", payload);
  return res.data;
}

export async function updateInstitution(
  institutionId: string,
  payload: Partial<{
    code: string;
    name: string;
    status: InstitutionStatus;
    timezone: string;
    settings: InstitutionSettings;
  }>,
): Promise<InstitutionRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<InstitutionRecord>(
    `/platform/institutions/${institutionId}/`,
    payload,
  );
  return res.data;
}

export async function listInstitutionAdmins(
  institutionId: string,
): Promise<PaginatedResponse<MembershipUserRecord>> {
  const res = await apiClient.get<PaginatedResponse<MembershipUserRecord>>(
    `/platform/institutions/${institutionId}/admins/`,
  );
  return res.data;
}

export async function createInstitutionAdmin(
  institutionId: string,
  payload: {
    email: string;
    first_name: string;
    last_name?: string;
    password?: string;
  },
): Promise<MembershipUserRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<MembershipUserRecord>(
    `/platform/institutions/${institutionId}/admins/`,
    payload,
  );
  return res.data;
}

// Institution Admin APIs
export async function fetchInstitutionProfile(): Promise<InstitutionRecord> {
  const res = await apiClient.get<InstitutionRecord>("/institution/profile/");
  return res.data;
}

export async function updateInstitutionProfile(payload: {
  name?: string;
  timezone?: string;
  settings?: InstitutionSettings;
}): Promise<InstitutionRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<InstitutionRecord>("/institution/profile/", payload);
  return res.data;
}

export async function listInstitutionUsers(params: {
  page?: number;
  search?: string;
  status?: string;
  role?: string;
}): Promise<PaginatedResponse<MembershipUserRecord>> {
  const res = await apiClient.get<PaginatedResponse<MembershipUserRecord>>("/institution/users/", {
    params,
  });
  return res.data;
}

export async function createInstitutionUser(payload: {
  email: string;
  first_name: string;
  last_name?: string;
  role_codes: RoleCode[];
  status: MembershipStatus;
  password?: string;
}): Promise<MembershipUserRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<MembershipUserRecord>("/institution/users/", payload);
  return res.data;
}

export async function updateInstitutionUser(
  membershipId: string,
  payload: {
    first_name?: string;
    last_name?: string;
    status?: MembershipStatus;
  },
): Promise<MembershipUserRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<MembershipUserRecord>(
    `/institution/users/${membershipId}/`,
    payload,
  );
  return res.data;
}

export async function updateInstitutionUserRoles(
  membershipId: string,
  roleCodes: RoleCode[],
): Promise<MembershipUserRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<MembershipUserRecord>(
    `/institution/users/${membershipId}/roles/`,
    { role_codes: roleCodes },
  );
  return res.data;
}

export async function issueInstitutionUserResetLink(membershipId: string): Promise<string> {
  await ensureCsrfCookie();
  const res = await apiClient.post<{ onboarding_reset_path: string }>(
    `/institution/users/${membershipId}/reset-link/`,
  );
  return res.data.onboarding_reset_path;
}

