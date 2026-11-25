import { apiClient } from "./apiClient";
import { ensureCsrfCookie } from "./authService";
import type { PaginatedResponse } from "../types/api";
import type {
  ImportJobRecord,
  ImportRowErrorRecord,
  PreviewRow,
} from "../types/imports";

export function getImportTemplateUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  return `${base}/students/import/template/`;
}

export function getImportErrorsExportUrl(jobId: string): string {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  return `${base}/students/import-jobs/${jobId}/errors/export/`;
}

export async function uploadImportFile(file: File): Promise<ImportJobRecord> {
  await ensureCsrfCookie();
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiClient.post<ImportJobRecord>("/students/import/upload/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function validateImportJob(
  jobId: string,
  payload: {
    column_mapping: Record<string, string>;
    sheet_name?: string;
    default_cohort_id?: string | null;
  },
): Promise<{ job: ImportJobRecord; preview_rows: PreviewRow[] }> {
  await ensureCsrfCookie();
  const res = await apiClient.post<{ job: ImportJobRecord; preview_rows: PreviewRow[] }>(
    `/students/import/${jobId}/validate/`,
    payload,
  );
  return res.data;
}

export async function commitImportJob(
  jobId: string,
  mode: "skip_invalid" | "all_or_nothing",
): Promise<ImportJobRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<ImportJobRecord>(`/students/import/${jobId}/commit/`, { mode });
  return res.data;
}

export async function listImportJobs(page = 1): Promise<PaginatedResponse<ImportJobRecord>> {
  const res = await apiClient.get<PaginatedResponse<ImportJobRecord>>("/students/import-jobs/", {
    params: { page },
  });
  return res.data;
}

export async function fetchImportJobDetail(
  jobId: string,
): Promise<{ job: ImportJobRecord; errors: ImportRowErrorRecord[] }> {
  const res = await apiClient.get<{ job: ImportJobRecord; errors: ImportRowErrorRecord[] }>(
    `/students/import-jobs/${jobId}/`,
  );
  return res.data;
}

