import { apiClient } from "./apiClient";
import { ensureCsrfCookie } from "./authService";
import type { PaginatedResponse } from "../types/api";
import type {
  AssessmentCategoryRecord,
  AssessmentDimensionRecord,
  AssessmentTemplateRecord,
  AssessmentVersionDetail,
  LifecycleStatus,
  MeasurementFamily,
  QuestionDifficulty,
  QuestionDimensionLink,
  QuestionOptionInput,
  QuestionRecord,
  QuestionRubricData,
  QuestionType,
  ScoringMethod,
} from "../types/assessments";

export async function seedStarterCatalogue(): Promise<{
  created_categories: number;
  created_dimensions: number;
}> {
  await ensureCsrfCookie();
  const res = await apiClient.post<{ created_categories: number; created_dimensions: number }>(
    "/assessments/seed-catalogue/",
  );
  return res.data;
}

// Categories
export async function listAssessmentCategories(params?: {
  page?: number;
  status?: string;
}): Promise<PaginatedResponse<AssessmentCategoryRecord>> {
  const res = await apiClient.get<PaginatedResponse<AssessmentCategoryRecord>>(
    "/assessments/categories/",
    { params },
  );
  return res.data;
}

export async function createAssessmentCategory(payload: {
  name: string;
  description?: string;
  sort_order?: number;
}): Promise<AssessmentCategoryRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<AssessmentCategoryRecord>("/assessments/categories/", payload);
  return res.data;
}

export async function updateAssessmentCategory(
  id: string,
  payload: Partial<{ name: string; description: string; sort_order: number; status: LifecycleStatus }>,
): Promise<AssessmentCategoryRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<AssessmentCategoryRecord>(
    `/assessments/categories/${id}/`,
    payload,
  );
  return res.data;
}

// Dimensions
export async function listAssessmentDimensions(params?: {
  page?: number;
  search?: string;
  category_id?: string;
  measurement_family?: string;
  status?: string;
}): Promise<PaginatedResponse<AssessmentDimensionRecord>> {
  const res = await apiClient.get<PaginatedResponse<AssessmentDimensionRecord>>(
    "/assessments/dimensions/",
    { params },
  );
  return res.data;
}

export async function createAssessmentDimension(payload: {
  category_id: string;
  code: string;
  name: string;
  description?: string;
  measurement_family: MeasurementFamily;
  interpretation_guidance?: string;
  sort_order?: number;
  skill_tags?: string[];
}): Promise<AssessmentDimensionRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<AssessmentDimensionRecord>("/assessments/dimensions/", payload);
  return res.data;
}

export async function updateAssessmentDimension(
  id: string,
  payload: Partial<{
    category_id: string;
    code: string;
    name: string;
    description: string;
    measurement_family: MeasurementFamily;
    interpretation_guidance: string;
    sort_order: number;
    status: LifecycleStatus;
    skill_tags: string[];
  }>,
): Promise<AssessmentDimensionRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<AssessmentDimensionRecord>(
    `/assessments/dimensions/${id}/`,
    payload,
  );
  return res.data;
}

// Questions
export async function listQuestions(params?: {
  page?: number;
  search?: string;
  question_type?: string;
  measurement_family?: string;
  difficulty?: string;
  dimension_id?: string;
  status?: string;
}): Promise<PaginatedResponse<QuestionRecord>> {
  const res = await apiClient.get<PaginatedResponse<QuestionRecord>>("/assessments/questions/", {
    params,
  });
  return res.data;
}

export interface QuestionWritePayload {
  question_code: string;
  question_type: QuestionType;
  prompt: string;
  difficulty: QuestionDifficulty;
  measurement_family: MeasurementFamily;
  scoring_method: ScoringMethod;
  max_marks: string | number;
  negative_marks: string | number;
  scoring_config?: Record<string, unknown>;
  tags?: string[];
  status?: LifecycleStatus;
  options?: QuestionOptionInput[];
  rubric?: QuestionRubricData | null;
  dimensions: QuestionDimensionLink[];
}

export async function createQuestion(payload: QuestionWritePayload): Promise<QuestionRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<QuestionRecord>("/assessments/questions/", payload);
  return res.data;
}

export async function updateQuestion(
  id: string,
  payload: Partial<QuestionWritePayload>,
): Promise<QuestionRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<QuestionRecord>(`/assessments/questions/${id}/`, payload);
  return res.data;
}

// Templates & Versions
export async function listAssessmentTemplates(params?: {
  page?: number;
  search?: string;
  status?: string;
}): Promise<PaginatedResponse<AssessmentTemplateRecord>> {
  const res = await apiClient.get<PaginatedResponse<AssessmentTemplateRecord>>(
    "/assessments/templates/",
    { params },
  );
  return res.data;
}

export async function createAssessmentTemplate(payload: {
  name: string;
  description?: string;
  duration_minutes?: number;
  max_attempts?: number;
  instructions?: string;
}): Promise<AssessmentTemplateRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<AssessmentTemplateRecord>("/assessments/templates/", payload);
  return res.data;
}

export async function fetchAssessmentVersion(versionId: string): Promise<AssessmentVersionDetail> {
  const res = await apiClient.get<AssessmentVersionDetail>(`/assessments/versions/${versionId}/`);
  return res.data;
}

export async function updateDraftAssessmentVersion(
  versionId: string,
  payload: Partial<{
    duration_minutes: number;
    max_attempts: number;
    instructions: string;
    randomize_questions: boolean;
    randomize_options: boolean;
    items: Array<{
      question_id: string;
      marks: string | number;
      negative_marks: string | number;
      required: boolean;
    }>;
  }>,
): Promise<AssessmentVersionDetail> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<AssessmentVersionDetail>(
    `/assessments/versions/${versionId}/`,
    payload,
  );
  return res.data;
}

export async function publishAssessmentVersion(versionId: string): Promise<AssessmentVersionDetail> {
  await ensureCsrfCookie();
  const res = await apiClient.post<AssessmentVersionDetail>(
    `/assessments/versions/${versionId}/publish/`,
  );
  return res.data;
}

export async function cloneAssessmentVersion(versionId: string): Promise<AssessmentVersionDetail> {
  await ensureCsrfCookie();
  const res = await apiClient.post<AssessmentVersionDetail>(
    `/assessments/versions/${versionId}/clone/`,
  );
  return res.data;
}

