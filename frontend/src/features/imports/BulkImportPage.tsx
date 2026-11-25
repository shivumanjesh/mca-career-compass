import React, { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Download, FileSpreadsheet, Upload } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import { listCohorts } from "../../services/academicsService";
import {
  commitImportJob,
  getImportErrorsExportUrl,
  getImportTemplateUrl,
  listImportJobs,
  uploadImportFile,
  validateImportJob,
} from "../../services/importsService";
import type { CohortRecord } from "../../types/academics";
import type { ImportJobRecord, PreviewRow } from "../../types/imports";

const MAPPABLE_FIELDS: Array<{ key: string; label: string; required?: boolean }> = [
  { key: "registration_no", label: "Registration No. / USN", required: true },
  { key: "email", label: "Email Address", required: true },
  { key: "first_name", label: "First Name", required: true },
  { key: "last_name", label: "Last Name" },
  { key: "programme_code", label: "Programme Code" },
  { key: "batch_name", label: "Batch Name" },
  { key: "semester", label: "Semester" },
  { key: "section", label: "Section" },
  { key: "admission_year", label: "Admission Year" },
  { key: "phone", label: "Phone" },
];

export const BulkImportPage: React.FC = () => {
  const [cohorts, setCohorts] = useState<CohortRecord[]>([]);
  const [jobs, setJobs] = useState<ImportJobRecord[]>([]);
  const [jobsCount, setJobsCount] = useState(0);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsLoading, setJobsLoading] = useState(true);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeJob, setActiveJob] = useState<ImportJobRecord | null>(null);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [defaultCohortId, setDefaultCohortId] = useState<string>("");
  const [previewRows, setPreviewRows] = useState<PreviewRow[]>([]);
  const [commitMode, setCommitMode] = useState<"skip_invalid" | "all_or_nothing">("skip_invalid");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadJobsAndCohorts = useCallback(async () => {
    setJobsLoading(true);
    try {
      const [jobsRes, cohRes] = await Promise.all([
        listImportJobs(jobsPage),
        listCohorts({ page: 1 }),
      ]);
      setJobs(jobsRes.results);
      setJobsCount(jobsRes.count);
      setCohorts(cohRes.results);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setJobsLoading(false);
    }
  }, [jobsPage]);

  useEffect(() => {
    loadJobsAndCohorts();
  }, [loadJobsAndCohorts]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please choose an .xlsx or .csv file first.");
      return;
    }
    setBusy(true);
    setError(null);
    setPreviewRows([]);
    try {
      const job = await uploadImportFile(selectedFile);
      setActiveJob(job);
      setSelectedSheet(job.summary_json.selected_sheet || "");
      setMapping(job.summary_json.suggested_mapping || {});
      await loadJobsAndCohorts();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const handleValidate = async () => {
    if (!activeJob) return;
    setBusy(true);
    setError(null);
    try {
      const res = await validateImportJob(activeJob.id, {
        column_mapping: mapping,
        sheet_name: selectedSheet || undefined,
        default_cohort_id: defaultCohortId || null,
      });
      setActiveJob(res.job);
      setPreviewRows(res.preview_rows);
      await loadJobsAndCohorts();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const handleCommit = async () => {
    if (!activeJob) return;
    setBusy(true);
    setError(null);
    try {
      const committed = await commitImportJob(activeJob.id, commitMode);
      setActiveJob(committed);
      await loadJobsAndCohorts();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const jobColumns: ColumnDef<ImportJobRecord>[] = [
    {
      key: "file",
      header: "File",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">{r.file_name}</div>
          <div className="text-xs text-slate-500">By {r.created_by_email}</div>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => (
        <StatusBadge
          label={r.status}
          tone={
            r.status === "committed"
              ? "success"
              : r.status === "failed"
                ? "danger"
                : "neutral"
          }
        />
      ),
    },
    {
      key: "counts",
      header: "Rows (Total / Valid / Errors)",
      render: (r) => (
        <span className="text-xs font-medium text-slate-700">
          {r.total_rows} / <span className="text-emerald-700">{r.success_rows}</span> /{" "}
          <span className="text-rose-700">{r.error_rows}</span>
        </span>
      ),
    },
    {
      key: "created",
      header: "Timestamp",
      render: (r) => <span className="text-xs text-slate-500">{new Date(r.created_at).toLocaleString()}</span>,
    },
    {
      key: "export",
      header: "Error Report",
      className: "text-right",
      render: (r) =>
        r.error_rows > 0 ? (
          <a
            href={getImportErrorsExportUrl(r.id)}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5 text-[#0D9488]" />
            CSV Report
          </a>
        ) : (
          <span className="text-xs text-slate-400">No errors</span>
        ),
    },
  ];

  const headers = activeJob?.summary_json.headers || [];
  const sheets = activeJob?.summary_json.sheet_names || [];

  return (
    <AppShell title="Bulk Student Import">
      <div className="space-y-6">
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {/* Step 1: Template & Upload */}
        <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-[#0F2942]">
                Step 1: Download Template & Upload Spreadsheet (.xlsx / .csv)
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Imported accounts are provisioned without plaintext passwords and use secure password-setup tokens.
              </p>
            </div>
            <a
              href={getImportTemplateUrl()}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3.5 py-2 text-xs font-medium text-slate-700"
            >
              <Download className="h-4 w-4 text-[#0D9488]" />
              Download Excel Template (.xlsx)
            </a>
          </div>

          <form className="flex flex-wrap items-center gap-3" onSubmit={handleUpload}>
            <label className="flex items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-2.5 text-sm text-slate-700 cursor-pointer hover:bg-slate-100">
              <FileSpreadsheet className="h-4 w-4 text-[#0F2942]" />
              <span>{selectedFile ? selectedFile.name : "Choose .xlsx or .csv file..."}</span>
              <input
                type="file"
                accept=".xlsx,.csv"
                className="hidden"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              />
            </label>
            <button
              type="submit"
              disabled={busy || !selectedFile}
              className="inline-flex items-center gap-2 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-4 py-2.5 text-sm font-medium text-white"
            >
              <Upload className="h-4 w-4" />
              {busy ? "Processing..." : "Upload & Inspect"}
            </button>
          </form>
        </section>

        {/* Step 2: Map Columns */}
        {activeJob && activeJob.status !== "committed" && (
          <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold text-[#0F2942]">
                  Step 2: Map Columns & Cohort Defaults ({activeJob.file_name})
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Match spreadsheet headers to student fields. Required fields are marked with *.
                </p>
              </div>
              {sheets.length > 1 && (
                <select
                  aria-label="Select worksheet"
                  value={selectedSheet}
                  onChange={(e) => setSelectedSheet(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                >
                  {sheets.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              )}
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {MAPPABLE_FIELDS.map((field) => (
                <div key={field.key}>
                  <label className="block text-xs font-medium text-slate-700">
                    {field.label} {field.required && <span className="text-rose-600">*</span>}
                  </label>
                  <select
                    value={mapping[field.key] || ""}
                    onChange={(e) =>
                      setMapping((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
                  >
                    <option value="">-- Not Mapped --</option>
                    {headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-slate-700">
                  Fallback Cohort (optional)
                </label>
                <select
                  value={defaultCohortId}
                  onChange={(e) => setDefaultCohortId(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
                >
                  <option value="">None (use sheet columns or leave unassigned)</option>
                  {cohorts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.programme_code} {c.batch_name} Sem-{c.semester} ({c.section})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                disabled={busy}
                onClick={handleValidate}
                className="rounded-lg bg-[#0D9488] hover:bg-teal-700 disabled:opacity-50 px-5 py-2 text-sm font-medium text-white"
              >
                {busy ? "Validating..." : "Validate & Preview Rows"}
              </button>
            </div>
          </section>
        )}

        {/* Step 3: Preview & Commit */}
        {activeJob && activeJob.status === "validated" && (
          <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold text-[#0F2942]">
                  Step 3: Validation Preview & Confirm Import
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Total: <strong>{activeJob.total_rows}</strong> • Valid:{" "}
                  <strong className="text-emerald-700">{activeJob.success_rows}</strong> • Errors/Duplicates:{" "}
                  <strong className="text-rose-700">{activeJob.error_rows}</strong>
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <select
                  aria-label="Commit mode"
                  value={commitMode}
                  onChange={(e) => setCommitMode(e.target.value as "skip_invalid" | "all_or_nothing")}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                >
                  <option value="skip_invalid">Import valid rows & skip invalid/duplicates</option>
                  <option value="all_or_nothing">Strict all-or-nothing (abort if any error)</option>
                </select>
                <button
                  type="button"
                  disabled={busy}
                  onClick={handleCommit}
                  className="rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-5 py-2 text-sm font-medium text-white"
                >
                  {busy ? "Committing..." : "Confirm & Commit Import"}
                </button>
              </div>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="min-w-full divide-y divide-slate-200 text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold text-slate-600">Row</th>
                    <th className="px-3 py-2 text-left font-semibold text-slate-600">Status</th>
                    <th className="px-3 py-2 text-left font-semibold text-slate-600">Reg No.</th>
                    <th className="px-3 py-2 text-left font-semibold text-slate-600">Email</th>
                    <th className="px-3 py-2 text-left font-semibold text-slate-600">Name</th>
                    <th className="px-3 py-2 text-left font-semibold text-slate-600">Validation Feedback</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {previewRows.map((row) => (
                    <tr key={row.row_number}>
                      <td className="px-3 py-2 font-mono">{row.row_number}</td>
                      <td className="px-3 py-2">
                        <StatusBadge
                          label={row.status}
                          tone={row.status === "valid" ? "success" : "danger"}
                        />
                      </td>
                      <td className="px-3 py-2 font-mono">{row.data.registration_no}</td>
                      <td className="px-3 py-2">{row.data.email}</td>
                      <td className="px-3 py-2">
                        {row.data.first_name} {row.data.last_name}
                      </td>
                      <td className="px-3 py-2">
                        {row.errors.length === 0 ? (
                          <span className="text-emerald-700">Ready to import</span>
                        ) : (
                          <ul className="list-disc pl-4 text-rose-700 space-y-0.5">
                            {row.errors.map((err, i) => (
                              <li key={i}>{err.message}</li>
                            ))}
                          </ul>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Step 4: Committed Banner */}
        {activeJob && activeJob.status === "committed" && (
          <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-emerald-700" />
              <div>
                <div className="text-sm font-semibold text-emerald-900">
                  Import Committed — {activeJob.file_name}
                </div>
                <div className="text-xs text-emerald-800">
                  Created: <strong>{activeJob.success_rows}</strong> students • Skipped/Failed:{" "}
                  <strong>{activeJob.error_rows}</strong> rows
                </div>
              </div>
            </div>
            {activeJob.error_rows > 0 && (
              <a
                href={getImportErrorsExportUrl(activeJob.id)}
                className="inline-flex items-center gap-2 rounded-lg bg-white border border-emerald-300 px-3.5 py-2 text-xs font-medium text-emerald-900 hover:bg-emerald-100"
              >
                <Download className="h-4 w-4" />
                Download Error Report (CSV)
              </a>
            )}
          </section>
        )}

        {/* Import History */}
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-[#0F2942]">Import Job History</h3>
          <DataTable
            columns={jobColumns}
            rows={jobs}
            rowKey={(r) => r.id}
            loading={jobsLoading}
            page={jobsPage}
            totalCount={jobsCount}
            onPageChange={setJobsPage}
            emptyTitle="No student import jobs yet"
          />
        </section>
      </div>
    </AppShell>
  );
};

