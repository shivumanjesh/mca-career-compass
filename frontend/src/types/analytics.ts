export interface AnalyticsCohortOption {
  id: string;
  label: string;
}

export interface DemonstratedDimensionStat {
  dimension_id?: string;
  code: string;
  name: string;
  awarded_marks?: string;
  max_marks?: string;
  percentage?: number | null;
  average_percentage?: number | null;
  status: string;
}

export interface SurveyDimensionStat {
  dimension_id?: string;
  code: string;
  name: string;
  responses_count: number;
  average_rating: number | null;
  status?: string;
}

export interface StudentComparisonRow {
  student_id: string;
  registration_no: string;
  full_name: string;
  attempts_count: number;
  average_percentage: number | null;
  top_strength: string | null;
  primary_gap: string | null;
  needs_additional_training: boolean;
  dimension_scores: Record<string, number | null>;
}

export interface CohortAnalyticsResponse {
  notice: string;
  cohort: {
    id: string;
    label: string;
    programme_code: string;
    batch_name: string;
    semester: number;
    section: string;
  };
  summary: {
    total_students: number;
    assessed_students: number;
    total_results: number;
    finalized_results: number;
    pending_manual_results: number;
    cohort_average_percentage: number | null;
    students_needing_training: number;
  };
  score_distribution: Array<{ label: string; count: number }>;
  demonstrated_performance_domains: DemonstratedDimensionStat[];
  cohort_strengths: DemonstratedDimensionStat[];
  cohort_gaps: DemonstratedDimensionStat[];
  self_reported_proficiency_domains: SurveyDimensionStat[];
  stated_interest_domains: SurveyDimensionStat[];
  student_comparison: StudentComparisonRow[];
}

export interface IndividualStudentReportResponse {
  notice: string;
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
  demonstrated_performance: {
    dimensions: DemonstratedDimensionStat[];
    strengths: DemonstratedDimensionStat[];
    moderate: DemonstratedDimensionStat[];
    gaps: DemonstratedDimensionStat[];
    insufficient_data: DemonstratedDimensionStat[];
  };
  self_reported_proficiency: SurveyDimensionStat[];
  stated_interest: SurveyDimensionStat[];
  assessment_history: Array<{
    result_id: string;
    attempt_id: string;
    template_id: string;
    template_name: string;
    version_no: number;
    attempt_no: number;
    submitted_at: string | null;
    raw_score: string;
    max_score: string;
    normalized_score: number | null;
    result_status: string;
  }>;
}

export interface AnalyticsTemplateOption {
  id: string;
  name: string;
}

export type ReadinessBand =
  | "placement_ready"
  | "near_ready"
  | "needs_support"
  | "insufficient_data";

export interface StudentReadinessRow {
  student_id: string;
  registration_no: string;
  full_name: string;
  cohort_id: string | null;
  cohort_label: string;
  attempts_count: number;
  overall_demonstrated_percentage: number | null;
  core_technical_percentage: number | null;
  top_strength: string | null;
  primary_gap: string | null;
  plans_count: number;
  plan_completion_percent: number;
  pending_manual_count: number;
  readiness_band: ReadinessBand;
  readiness_label: string;
  evidence_summary: string;
}

export interface CohortRollupRow {
  cohort_id: string;
  cohort_label: string;
  programme_code: string;
  batch_name: string;
  semester: number;
  section: string;
  assigned_mentors: string[];
  total_students: number;
  assessed_students: number;
  average_demonstrated_percentage: number | null;
  placement_ready_count: number;
  near_ready_count: number;
  needs_support_count: number;
  pending_manual_evaluations: number;
  plan_adoption_rate: number;
  avg_plan_completion_percent: number;
}

export interface FacultyIntelligenceResponse {
  notice: string;
  summary: {
    authorized_cohorts: number;
    total_students: number;
    assessed_students: number;
    placement_ready_count: number;
    near_ready_count: number;
    needs_support_count: number;
    insufficient_data_count: number;
    average_demonstrated_percentage: number | null;
    pending_manual_evaluations: number;
    students_with_plans: number;
    active_or_completed_plans: number;
    avg_plan_completion_percent: number;
  };
  readiness_distribution: Array<{ band: ReadinessBand; label: string; count: number }>;
  cohort_rollups: CohortRollupRow[];
  domain_hotspots: DemonstratedDimensionStat[];
  self_reported_domains: SurveyDimensionStat[];
  stated_interest_domains: SurveyDimensionStat[];
  student_readiness: StudentReadinessRow[];
}

export interface PrePostComparisonResponse {
  notice: string;
  mode: "template_pair" | "earliest_vs_latest";
  pre_label: string;
  post_label: string;
  summary: {
    comparable_students: number;
    pre_average_percentage: number | null;
    post_average_percentage: number | null;
    average_delta: number | null;
    improved_students_count: number;
    declined_students_count: number;
    unchanged_students_count: number;
  };
  dimension_deltas: Array<{
    code: string;
    name: string;
    pre_percentage: number | null;
    post_percentage: number | null;
    delta_percentage: number | null;
    matched_students: number;
  }>;
  student_trajectories: Array<{
    student_id: string;
    registration_no: string;
    full_name: string;
    cohort_label: string;
    pre_template: string;
    post_template: string;
    pre_score: number;
    post_score: number;
    delta: number;
    trend: "improved" | "declined" | "unchanged";
  }>;
}

export interface ExecutiveReportResponse {
  notice: string;
  institution: {
    id: string;
    code: string;
    name: string;
  };
  summary: {
    total_programmes: number;
    total_academic_years: number;
    total_cohorts: number;
    active_faculty_count: number;
    total_students: number;
    assessed_students: number;
    participation_rate: number;
    overall_demonstrated_percentage: number | null;
    placement_ready_count: number;
    placement_ready_rate: number;
    near_ready_count: number;
    needs_support_count: number;
    active_or_completed_plans: number;
    avg_plan_completion_percent: number;
    pending_manual_evaluations: number;
  };
  readiness_distribution: Array<{ band: ReadinessBand; label: string; count: number }>;
  cohort_rollups: CohortRollupRow[];
  demonstrated_domains: DemonstratedDimensionStat[];
  demonstrated_strengths: DemonstratedDimensionStat[];
  demonstrated_gaps: DemonstratedDimensionStat[];
  self_reported_domains: SurveyDimensionStat[];
  stated_interest_domains: SurveyDimensionStat[];
}

