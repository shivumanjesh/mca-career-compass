import React, { useCallback, useEffect, useState } from "react";
import { Calendar, Plus } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import { listCohorts, listStudents } from "../../services/academicsService";
import { listAssessmentTemplates } from "../../services/assessmentsService";
import {
  createAssignment,
  listAssignments,
  updateAssignment,
} from "../../services/attemptsService";
import type { CohortRecord, StudentRecord } from "../../types/academics";
import type { AssessmentTemplateRecord } from "../../types/assessments";
import type { AssessmentAssignmentRecord } from "../../types/attempts";

export const AssignmentsPage: React.FC = () => {
  const [rows, setRows] = useState<AssessmentAssignmentRecord[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [templates, setTemplates] = useState<AssessmentTemplateRecord[]>([]);
  const [cohorts, setCohorts] = useState<CohortRecord[]>([]);
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [versionId, setVersionId] = useState("");
  const [targetType, setTargetType] = useState<"cohort" | "student">("cohort");
  const [cohortId, setCohortId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [releaseResults, setReleaseResults] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [aRes, tRes, cRes, sRes] = await Promise.all([
        listAssignments({ page }),
        listAssessmentTemplates({ page: 1 }),
        listCohorts({ page: 1 }),
        listStudents({ page: 1 }),
      ]);
      setRows(aRes.results);
      setCount(aRes.count);
      setTemplates(tRes.results);
      setCohorts(cRes.results);
      setStudents(sRes.results);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const publishedVersions = templates.flatMap((t) =>
    t.versions
      .filter((v) => v.status === "published")
      .map((v) => ({
        id: v.id,
        label: `${t.name} — v${v.version_no} (${v.total_marks} marks)`,
      })),
  );

  const openModal = () => {
    const now = new Date();
    const nextWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    setOpensAt(now.toISOString().slice(0, 16));
    setClosesAt(nextWeek.toISOString().slice(0, 16));
    setVersionId(publishedVersions[0]?.id || "");
    setCohortId(cohorts[0]?.id || "");
    setStudentId(students[0]?.id || "");
    setReleaseResults(false);
    setModalError(null);
    setModalOpen(true);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      await createAssignment({
        assessment_version_id: versionId,
        cohort_id: targetType === "cohort" ? cohortId : null,
        student_profile_id: targetType === "student" ? studentId : null,
        opens_at: new Date(opensAt).toISOString(),
        closes_at: new Date(closesAt).toISOString(),
        results_released: releaseResults,
      });
      setModalOpen(false);
      await loadData();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleRelease = async (row: AssessmentAssignmentRecord) => {
    try {
      await updateAssignment(row.id, { results_released: !row.results_released });
      await loadData();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const columns: ColumnDef<AssessmentAssignmentRecord>[] = [
    {
      key: "assessment",
      header: "Assessment",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">
            {r.template_name} (v{r.version_no})
          </div>
          <div className="text-xs text-slate-500">
            {r.duration_minutes} min • {r.total_marks} marks • {r.attempt_count} attempts
          </div>
        </div>
      ),
    },
    {
      key: "target",
      header: "Target",
      render: (r) => (
        <span className="text-xs font-medium text-slate-700">
          {r.cohort_label ? `Cohort: ${r.cohort_label}` : `Student: ${r.student_label}`}
        </span>
      ),
    },
    {
      key: "window",
      header: "Availability Window",
      render: (r) => (
        <div className="text-xs text-slate-600">
          <div>Opens: {new Date(r.opens_at).toLocaleString()}</div>
          <div>Closes: {new Date(r.closes_at).toLocaleString()}</div>
        </div>
      ),
    },
    {
      key: "release",
      header: "Results",
      render: (r) => (
        <StatusBadge
          label={r.results_released ? "Released" : "Hidden"}
          tone={r.results_released ? "success" : "warning"}
        />
      ),
    },
    {
      key: "actions",
      header: "Actions",
      className: "text-right",
      render: (r) => (
        <button
          type="button"
          onClick={() => handleToggleRelease(r)}
          className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          {r.results_released ? "Hide Results" : "Release Results"}
        </button>
      ),
    },
  ];

  return (
    <AppShell title="Assessment Assignments & Schedules">
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <Calendar className="h-4 w-4 text-[#0D9488]" />
            <span>Schedule published assessment versions for cohorts or individual students.</span>
          </div>
          <button
            type="button"
            onClick={openModal}
            className="inline-flex items-center gap-2 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white"
          >
            <Plus className="h-4 w-4" />
            Assign Assessment
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}

        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(r) => r.id}
          loading={loading}
          page={page}
          totalCount={count}
          onPageChange={setPage}
          emptyTitle="No assessment assignments scheduled yet"
        />
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Assign Published Assessment">
        <form className="space-y-4" onSubmit={handleCreate}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-700">Published Assessment Version</label>
            <select
              required
              value={versionId}
              onChange={(e) => setVersionId(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select Published Version</option>
              {publishedVersions.map((v) => (
                <option key={v.id} value={v.id}>{v.label}</option>
              ))}
            </select>
          </div>
          <div>
            <div className="text-xs font-medium text-slate-700 mb-1.5">Assignment Target</div>
            <div className="flex gap-4 text-xs">
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  checked={targetType === "cohort"}
                  onChange={() => setTargetType("cohort")}
                />
                Cohort / Batch
              </label>
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  checked={targetType === "student"}
                  onChange={() => setTargetType("student")}
                />
                Individual Student
              </label>
            </div>
          </div>
          {targetType === "cohort" ? (
            <div>
              <label className="block text-xs font-medium text-slate-700">Cohort</label>
              <select
                required
                value={cohortId}
                onChange={(e) => setCohortId(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select Cohort</option>
                {cohorts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.programme_code} {c.batch_name} Sem-{c.semester} ({c.section})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-medium text-slate-700">Student</label>
              <select
                required
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select Student</option>
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.registration_no} — {s.full_name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700">Opens At</label>
              <input type="datetime-local" required value={opensAt} onChange={(e) => setOpensAt(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-xs" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Closes At</label>
              <input type="datetime-local" required value={closesAt} onChange={(e) => setClosesAt(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-xs" />
            </div>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input type="checkbox" checked={releaseResults} onChange={(e) => setReleaseResults(e.target.checked)} />
            Release scored results to students immediately after evaluation
          </label>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Scheduling..." : "Create Assignment"}
            </button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
};

