import { apiClient } from "./apiClient";
import type {
  AnalyticsCohortOption,
  AnalyticsTemplateOption,
  CohortAnalyticsResponse,
  ExecutiveReportResponse,
  FacultyIntelligenceResponse,
  IndividualStudentReportResponse,
  PrePostComparisonResponse,
} from "../types/analytics";

export async function listAnalyticsCohorts(): Promise<AnalyticsCohortOption[]> {
  const res = await apiClient.get<AnalyticsCohortOption[]>("/analytics/cohorts/");
  return res.data;
}

export async function listAnalyticsTemplates(): Promise<AnalyticsTemplateOption[]> {
  const res = await apiClient.get<AnalyticsTemplateOption[]>("/analytics/templates/");
  return res.data;
}

export async function fetchCohortAnalytics(
  cohortId: string,
  templateId?: string,
): Promise<CohortAnalyticsResponse> {
  const res = await apiClient.get<CohortAnalyticsResponse>(`/analytics/cohorts/${cohortId}/`, {
    params: templateId ? { template_id: templateId } : undefined,
  });
  return res.data;
}

export async function fetchStudentReport(
  studentId: string,
): Promise<IndividualStudentReportResponse> {
  const res = await apiClient.get<IndividualStudentReportResponse>(
    `/analytics/students/${studentId}/`,
  );
  return res.data;
}

export async function fetchMyReports(): Promise<IndividualStudentReportResponse> {
  const res = await apiClient.get<IndividualStudentReportResponse>("/analytics/my-reports/");
  return res.data;
}

export function getAnalyticsExportUrl(params: {
  format: "csv" | "xlsx" | "pdf";
  cohortId?: string;
  studentId?: string;
  templateId?: string;
}): string {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  const query = new URLSearchParams({ export_format: params.format });
  if (params.cohortId) query.set("cohort_id", params.cohortId);
  if (params.studentId) query.set("student_id", params.studentId);
  if (params.templateId) query.set("template_id", params.templateId);
  return `${base}/analytics/exports/?${query.toString()}`;
}

export async function fetchFacultyIntelligence(
  cohortId?: string,
): Promise<FacultyIntelligenceResponse> {
  const res = await apiClient.get<FacultyIntelligenceResponse>("/analytics/intelligence/", {
    params: cohortId ? { cohort_id: cohortId } : undefined,
  });
  return res.data;
}

export async function fetchPrePostComparison(params?: {
  cohortId?: string;
  preTemplateId?: string;
  postTemplateId?: string;
}): Promise<PrePostComparisonResponse> {
  const res = await apiClient.get<PrePostComparisonResponse>("/analytics/pre-post/", {
    params: {
      cohort_id: params?.cohortId || undefined,
      pre_template_id: params?.preTemplateId || undefined,
      post_template_id: params?.postTemplateId || undefined,
    },
  });
  return res.data;
}

export async function fetchExecutiveReport(): Promise<ExecutiveReportResponse> {
  const res = await apiClient.get<ExecutiveReportResponse>("/analytics/executive/");
  return res.data;
}

export function getExecutiveExportUrl(format: "csv" | "xlsx" | "pdf"): string {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  return `${base}/analytics/executive/export/?export_format=${format}`;
}

