import type { MeasurementFamily, QuestionType } from "./assessments";

export type AssignmentStatus = "active" | "closed" | "cancelled";
export type AttemptStatus = "in_progress" | "submitted" | "partially_evaluated" | "evaluated";

export interface AssessmentAssignmentRecord {
  id: string;
  assessment_version_id: string;
  template_name: string;
  version_no: number;
  duration_minutes: number;
  total_marks: string;
  cohort_id: string | null;
  cohort_label: string | null;
  student_profile_id: string | null;
  student_label: string | null;
  opens_at: string;
  closes_at: string;
  results_released: boolean;
  status: AssignmentStatus;
  attempt_count: number;
  created_at: string;
}

export interface StudentAttemptSummary {
  id: string;
  assignment_id: string;
  template_name: string;
  version_no: number;
  attempt_no: number;
  status: AttemptStatus;
  started_at: string;
  expires_at: string;
  submitted_at: string | null;
  total_awarded: string;
  max_marks: string;
  results_released: boolean;
}

export interface StudentAssignmentItem {
  id: string;
  template_name: string;
  version_no: number;
  duration_minutes: number;
  max_attempts: number;
  total_marks: string;
  opens_at: string;
  closes_at: string;
  status: AssignmentStatus;
  results_released: boolean;
  attempts_used: number;
  can_start_or_resume: boolean;
  latest_attempt: StudentAttemptSummary | null;
}

export interface RunnerQuestion {
  version_question_id: string;
  sequence: number;
  marks: string;
  negative_marks: string;
  required: boolean;
  question_code: string;
  question_type: QuestionType;
  prompt: string;
  difficulty: string;
  measurement_family: MeasurementFamily;
  options: Array<{
    option_key: string;
    option_text: string;
    display_order: number;
  }>;
}

export interface AttemptRunnerPayload {
  attempt: StudentAttemptSummary;
  instructions: string;
  duration_minutes: number;
  server_time: string;
  remaining_seconds: number;
  questions: RunnerQuestion[];
  saved_responses: Record<string, Record<string, unknown>>;
}

export interface DimensionResultItem {
  dimension_id: string;
  code: string;
  name: string;
  awarded_marks?: string;
  max_marks?: string;
  percentage?: number | null;
  responses_count?: number;
  average_rating?: number | null;
  selected_keys?: string[];
  status: string;
}

export interface AssessmentResultRecord {
  id: string;
  attempt_id: string;
  template_name: string;
  version_no: number;
  attempt_no: number;
  raw_score: string;
  max_score: string;
  normalized_score: string | null;
  breakdown_json: {
    demonstrated_performance: DimensionResultItem[];
    self_reported_proficiency: DimensionResultItem[];
    stated_interest: DimensionResultItem[];
  };
  result_status: "pending_manual" | "finalized";
  calculated_at: string;
  algorithm_version: string;
}

export interface EvaluationHistoryItem {
  id: string;
  version_no: number;
  awarded_marks: string;
  comments: string;
  rubric_result: Record<string, unknown>;
  evaluator_email: string;
  evaluator_name: string;
  evaluated_at: string;
}

export interface PendingEvaluationItem {
  id: string;
  attempt_id: string;
  student_reg_no: string;
  student_name: string;
  template_name: string;
  version_no: number;
  question_code: string;
  question_type: QuestionType;
  prompt: string;
  max_marks: string;
  rubric: {
    rubric_json: Record<string, unknown>;
    max_marks: string;
    evaluator_guidance: string;
  } | null;
  response_json: Record<string, unknown>;
  awarded_marks: string | null;
  scoring_status: "pending_manual" | "manually_evaluated";
  submitted_at: string | null;
  evaluations: EvaluationHistoryItem[];
}

