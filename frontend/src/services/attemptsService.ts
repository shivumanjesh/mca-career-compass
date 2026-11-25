import { apiClient } from "./apiClient";
import { ensureCsrfCookie } from "./authService";
import type { PaginatedResponse } from "../types/api";
import type {
  AssessmentAssignmentRecord,
  AssessmentResultRecord,
  AssignmentStatus,
  AttemptRunnerPayload,
  EvaluationHistoryItem,
  PendingEvaluationItem,
  StudentAssignmentItem,
  StudentAttemptSummary,
} from "../types/attempts";

// Assignments (Admin / Assessment Admin)
export async function listAssignments(params?: {
  page?: number;
  status?: string;
}): Promise<PaginatedResponse<AssessmentAssignmentRecord>> {
  const res = await apiClient.get<PaginatedResponse<AssessmentAssignmentRecord>>(
    "/assessments/assignments/",
    { params },
  );
  return res.data;
}

export async function createAssignment(payload: {
  assessment_version_id: string;
  cohort_id?: string | null;
  student_profile_id?: string | null;
  opens_at: string;
  closes_at: string;
  results_released?: boolean;
}): Promise<AssessmentAssignmentRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<AssessmentAssignmentRecord>("/assessments/assignments/", payload);
  return res.data;
}

export async function updateAssignment(
  id: string,
  payload: Partial<{
    opens_at: string;
    closes_at: string;
    results_released: boolean;
    status: AssignmentStatus;
  }>,
): Promise<AssessmentAssignmentRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<AssessmentAssignmentRecord>(
    `/assessments/assignments/${id}/`,
    payload,
  );
  return res.data;
}

// Student Delivery & Runner
export async function listMyAssignments(): Promise<StudentAssignmentItem[]> {
  const res = await apiClient.get<StudentAssignmentItem[]>("/attempts/my-assignments/");
  return res.data;
}

export async function startOrResumeAttempt(assignmentId: string): Promise<AttemptRunnerPayload> {
  await ensureCsrfCookie();
  const res = await apiClient.post<AttemptRunnerPayload>(
    `/attempts/assignments/${assignmentId}/start/`,
  );
  return res.data;
}

export async function fetchAttemptRunner(attemptId: string): Promise<AttemptRunnerPayload> {
  const res = await apiClient.get<AttemptRunnerPayload>(`/attempts/${attemptId}/`);
  return res.data;
}

export async function autosaveResponses(
  attemptId: string,
  items: Array<{ version_question_id: string; response_json: Record<string, unknown> }>,
): Promise<{ status: string; saved_at: string }> {
  await ensureCsrfCookie();
  const res = await apiClient.put<{ status: string; saved_at: string }>(
    `/attempts/${attemptId}/responses/`,
    { items },
  );
  return res.data;
}

export async function submitAttempt(attemptId: string): Promise<StudentAttemptSummary> {
  await ensureCsrfCookie();
  const res = await apiClient.post<StudentAttemptSummary>(`/attempts/${attemptId}/submit/`);
  return res.data;
}

export async function fetchMyAttemptResult(attemptId: string): Promise<AssessmentResultRecord> {
  const res = await apiClient.get<AssessmentResultRecord>(`/attempts/${attemptId}/result/`);
  return res.data;
}

// Manual Evaluation (Faculty / Assessment Admin)
export async function listEvaluationQueue(params?: {
  page?: number;
  scoring_status?: string;
}): Promise<PaginatedResponse<PendingEvaluationItem>> {
  const res = await apiClient.get<PaginatedResponse<PendingEvaluationItem>>(
    "/attempts/evaluations/queue/",
    { params },
  );
  return res.data;
}

export async function submitManualEvaluation(
  responseId: string,
  payload: {
    awarded_marks: string | number;
    comments?: string;
    rubric_result?: Record<string, unknown>;
  },
): Promise<EvaluationHistoryItem> {
  await ensureCsrfCookie();
  const res = await apiClient.post<EvaluationHistoryItem>(
    `/attempts/evaluations/responses/${responseId}/`,
    payload,
  );
  return res.data;
}

