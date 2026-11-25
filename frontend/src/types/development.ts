export type LearningResourceType =
  | "learning_pathway"
  | "training"
  | "project"
  | "certification"
  | "milestone";

export type ResourceLevel = "beginner" | "intermediate" | "advanced";

export type ResourceStatus = "active" | "archived";

export type PlanStatus = "proposed" | "active" | "completed" | "archived";

export type ActivityStatus = "not_started" | "in_progress" | "completed";

export interface LearningResource {
  id: string;
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
  created_at: string;
  updated_at: string;
}

export interface DomainRecommendation {
  domain: string;
  readiness_signal: string;
  demonstrated_average: number | null;
  interest_rating: number | null;
  demonstrated_evidence: Array<{ code: string; percentage: number }>;
  interest_evidence: Array<{ code: string; rating: number }>;
  explanation: string;
}

export interface RecommendedResourceItem {
  resource_id: string;
  title: string;
  resource_type: LearningResourceType;
  target_domain: string;
  dimension_code: string;
  provider: string;
  level: ResourceLevel;
  estimated_hours: number;
  resource_url: string;
  description: string;
  reason: string;
}

export interface StudentRecommendationsResponse {
  notice: string;
  advisory_note: string;
  student: {
    id: string;
    registration_no: string;
    full_name: string;
    email: string;
    cohort_id: string | null;
    cohort_label: string | null;
  };
  summary: {
    assessments_count: number;
    overall_demonstrated_percentage: number | null;
    cohort_benchmark_percentage: number | null;
    needs_additional_training: boolean;
  };
  domain_recommendations: DomainRecommendation[];
  learning_pathways: RecommendedResourceItem[];
  training_recommendations: RecommendedResourceItem[];
  project_recommendations: RecommendedResourceItem[];
  certification_recommendations: RecommendedResourceItem[];
}

export interface ProgressRecordItem {
  id: string;
  activity_id: string;
  progress_percent: number;
  reflection: string;
  evidence_url: string;
  recorded_by_name: string;
  recorded_by_email: string;
  recorded_at: string;
}

export interface DevelopmentActivity {
  id: string;
  plan_id: string;
  resource_id: string | null;
  resource_title: string | null;
  resource_url: string | null;
  dimension_id: string | null;
  dimension_code: string | null;
  dimension_name: string | null;
  title: string;
  description: string;
  activity_type: LearningResourceType;
  due_date: string | null;
  status: ActivityStatus;
  progress_percent: number;
  evidence_url: string;
  progress_records: ProgressRecordItem[];
  created_at: string;
  updated_at: string;
}

export interface DevelopmentPlan {
  id: string;
  student_id: string;
  student_registration_no: string;
  student_name: string;
  student_cohort_label: string | null;
  created_by_name: string;
  title: string;
  target_domain: string;
  notes: string;
  status: PlanStatus;
  start_date: string | null;
  target_date: string | null;
  overall_progress_percent: number;
  activities: DevelopmentActivity[];
  created_at: string;
  updated_at: string;
}

export interface DevelopmentStudentOption {
  id: string;
  registration_no: string;
  full_name: string;
  email: string;
  cohort_id: string | null;
  cohort_label: string | null;
}

