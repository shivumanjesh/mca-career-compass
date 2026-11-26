export type MeasurementFamily =
  | "demonstrated_performance"
  | "self_reported_proficiency"
  | "stated_interest";

export type LifecycleStatus = "active" | "archived";

export type QuestionType =
  | "single_mcq"
  | "multiple_mcq"
  | "true_false"
  | "numeric"
  | "likert"
  | "self_rating"
  | "situational_judgement"
  | "descriptive"
  | "coding";

export type QuestionDifficulty = "easy" | "medium" | "hard";

export type ScoringMethod = "exact" | "partial_credit" | "tolerance" | "likert_scale" | "rubric";

export type AssessmentVersionStatus = "draft" | "published" | "archived";

export interface AssessmentCategoryRecord {
  id: string;
  name: string;
  description: string;
  sort_order: number;
  status: LifecycleStatus;
  dimension_count: number;
  created_at: string;
  updated_at: string;
}

export interface AssessmentDimensionRecord {
  id: string;
  category_id: string;
  category_name: string;
  code: string;
  name: string;
  description: string;
  measurement_family: MeasurementFamily;
  interpretation_guidance: string;
  sort_order: number;
  status: LifecycleStatus;
  skill_tags: string[];
  created_at: string;
  updated_at: string;
}

export interface QuestionOptionInput {
  id?: string;
  option_key: string;
  option_text: string;
  display_order: number;
  is_correct: boolean;
  points_override?: string | null;
  feedback?: string;
}

export interface QuestionRubricData {
  id?: string;
  rubric_json: Record<string, unknown>;
  max_marks: string | number;
  evaluator_guidance: string;
}

export interface QuestionDimensionLink {
  dimension_id: string;
  code?: string;
  name?: string;
  measurement_family?: MeasurementFamily;
  weight: string | number;
}

export interface QuestionRecord {
  id: string;
  question_code: string;
  question_type: QuestionType;
  prompt: string;
  difficulty: QuestionDifficulty;
  measurement_family: MeasurementFamily;
  scoring_method: ScoringMethod;
  max_marks: string;
  negative_marks: string;
  scoring_config: Record<string, unknown>;
  tags: string[];
  status: LifecycleStatus;
  options: QuestionOptionInput[];
  rubric: QuestionRubricData | null;
  dimensions: QuestionDimensionLink[];
  created_by_email: string;
  created_at: string;
  updated_at: string;
}

export interface BulkQuestionPreviewRow {
  row_number: number;
  question_code: string;
  question_type: string;
  measurement_family: string;
  dimension_codes: string[];
  prompt_preview: string;
  valid: boolean;
  errors: string[];
}

export interface BulkQuestionPreviewResponse {
  summary: {
    total_rows: number;
    valid_count: number;
    error_count: number;
  };
  rows: BulkQuestionPreviewRow[];
}

export interface BulkQuestionCommitResponse {
  created_count: number;
  skipped_count: number;
  question_codes: string[];
}

export interface AssessmentVersionSummary {
  id: string;
  version_no: number;
  status: AssessmentVersionStatus;
  duration_minutes: number;
  max_attempts: number;
  total_marks: string;
  question_count: number;
  published_at: string | null;
}

export interface AssessmentTemplateRecord {
  id: string;
  name: string;
  description: string;
  status: LifecycleStatus;
  versions: AssessmentVersionSummary[];
  created_at: string;
  updated_at: string;
}

export interface VersionQuestionRecord {
  id: string;
  question_id: string;
  question_code: string;
  question_type: QuestionType;
  prompt: string;
  measurement_family: MeasurementFamily;
  marks: string;
  negative_marks: string;
  sequence: number;
  required: boolean;
  question_snapshot: Record<string, unknown>;
}

export interface AssessmentVersionDetail {
  id: string;
  template_id: string;
  template_name: string;
  version_no: number;
  duration_minutes: number;
  max_attempts: number;
  instructions: string;
  scoring_config: Record<string, unknown>;
  randomize_questions: boolean;
  randomize_options: boolean;
  total_marks: string;
  status: AssessmentVersionStatus;
  published_at: string | null;
  question_count: number;
  version_questions: VersionQuestionRecord[];
  created_at: string;
  updated_at: string;
}

