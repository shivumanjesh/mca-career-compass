import { apiClient } from "./apiClient";
import type { PaginatedResponse } from "../types/api";
import type {
  DevelopmentActivity,
  DevelopmentPlan,
  DevelopmentStudentOption,
  LearningResource,
  LearningResourceType,
  PlanStatus,
  ProgressRecordItem,
  ResourceLevel,
  ResourceStatus,
  StudentRecommendationsResponse,
} from "../types/development";

export async function seedLearningCatalogue(): Promise<{ created_resources: number }> {
  const res = await apiClient.post<{ created_resources: number }>("/development/catalogue/seed/");
  return res.data;
}

export async function listLearningResources(params?: {
  page?: number;
  search?: string;
  resource_type?: string;
  target_domain?: string;
  status?: string;
}): Promise<PaginatedResponse<LearningResource>> {
  const res = await apiClient.get<PaginatedResponse<LearningResource>>("/development/catalogue/", {
    params,
  });
  return res.data;
}

export async function createLearningResource(payload: {
  dimension_code?: string;
  target_domain: string;
  resource_type: LearningResourceType;
  title: string;
  description?: string;
  provider?: string;
  level?: ResourceLevel;
  estimated_hours?: number;
  resource_url?: string;
}): Promise<LearningResource> {
  const res = await apiClient.post<LearningResource>("/development/catalogue/", payload);
  return res.data;
}

export async function updateLearningResource(
  resourceId: string,
  payload: Partial<{
    dimension_code: string;
    target_domain: string;
    resource_type: LearningResourceType;
    title: string;
    description: string;
    provider: string;
    level: ResourceLevel;
    estimated_hours: number;
    resource_url: string;
    status: ResourceStatus;
  }>,
): Promise<LearningResource> {
  const res = await apiClient.patch<LearningResource>(
    `/development/catalogue/${resourceId}/`,
    payload,
  );
  return res.data;
}

export async function fetchMyRecommendations(): Promise<StudentRecommendationsResponse> {
  const res = await apiClient.get<StudentRecommendationsResponse>("/development/my-recommendations/");
  return res.data;
}

export async function listDevelopmentStudents(params?: {
  search?: string;
  cohort_id?: string;
}): Promise<DevelopmentStudentOption[]> {
  const res = await apiClient.get<DevelopmentStudentOption[]>("/development/students/", {
    params,
  });
  return res.data;
}

export async function fetchStudentRecommendations(
  studentId: string,
): Promise<StudentRecommendationsResponse> {
  const res = await apiClient.get<StudentRecommendationsResponse>(
    `/development/students/${studentId}/recommendations/`,
  );
  return res.data;
}

export async function listDevelopmentPlans(params?: {
  page?: number;
  student_id?: string;
  status?: string;
  search?: string;
}): Promise<PaginatedResponse<DevelopmentPlan>> {
  const res = await apiClient.get<PaginatedResponse<DevelopmentPlan>>("/development/plans/", {
    params,
  });
  return res.data;
}

export async function createDevelopmentPlan(payload: {
  student_id?: string;
  title: string;
  target_domain?: string;
  notes?: string;
  status?: PlanStatus;
  start_date?: string | null;
  target_date?: string | null;
}): Promise<DevelopmentPlan> {
  const res = await apiClient.post<DevelopmentPlan>("/development/plans/", payload);
  return res.data;
}

export async function updateDevelopmentPlan(
  planId: string,
  payload: Partial<{
    title: string;
    target_domain: string;
    notes: string;
    status: PlanStatus;
    start_date: string | null;
    target_date: string | null;
  }>,
): Promise<DevelopmentPlan> {
  const res = await apiClient.patch<DevelopmentPlan>(`/development/plans/${planId}/`, payload);
  return res.data;
}

export async function addPlanActivity(
  planId: string,
  payload: {
    resource_id?: string | null;
    dimension_id?: string | null;
    title?: string;
    description?: string;
    activity_type?: LearningResourceType;
    due_date?: string | null;
    evidence_url?: string;
  },
): Promise<DevelopmentActivity> {
  const res = await apiClient.post<DevelopmentActivity>(
    `/development/plans/${planId}/activities/`,
    payload,
  );
  return res.data;
}

export async function recordActivityProgress(
  activityId: string,
  payload: {
    progress_percent: number;
    reflection?: string;
    evidence_url?: string;
  },
): Promise<{
  record: ProgressRecordItem;
  activity_status: string;
  activity_progress_percent: number;
  plan_status: PlanStatus;
}> {
  const res = await apiClient.post<{
    record: ProgressRecordItem;
    activity_status: string;
    activity_progress_percent: number;
    plan_status: PlanStatus;
  }>(`/development/activities/${activityId}/progress/`, payload);
  return res.data;
}

