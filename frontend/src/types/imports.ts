export type ImportJobStatus = "uploaded" | "validated" | "committed" | "failed" | "cancelled";

export interface ImportJobRecord {
  id: string;
  file_name: string;
  status: ImportJobStatus;
  total_rows: number;
  success_rows: number;
  error_rows: number;
  summary_json: {
    sheet_names?: string[];
    selected_sheet?: string;
    headers?: string[];
    sample_rows?: Array<Record<string, string>>;
    suggested_mapping?: Record<string, string>;
    column_mapping?: Record<string, string>;
    default_cohort_id?: string | null;
    created_rows?: number;
    skipped_rows?: number;
    failed_rows?: number;
    [key: string]: unknown;
  };
  created_by_email: string;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface PreviewRowError {
  field: string;
  code: string;
  message: string;
}

export interface PreviewRow {
  row_number: number;
  status: "valid" | "error";
  data: Record<string, string>;
  errors: PreviewRowError[];
}

export interface ImportRowErrorRecord {
  id: string;
  row_number: number;
  field_name: string;
  error_code: string;
  message: string;
  row_data: Record<string, string> | null;
  created_at: string;
}

