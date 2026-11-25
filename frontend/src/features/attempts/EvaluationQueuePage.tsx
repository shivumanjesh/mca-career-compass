import React, { useCallback, useEffect, useState } from "react";
import { ClipboardCheck } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  listEvaluationQueue,
  submitManualEvaluation,
} from "../../services/attemptsService";
import type { PendingEvaluationItem } from "../../types/attempts";

export const EvaluationQueuePage: React.FC = () => {
  const [rows, setRows] = useState<PendingEvaluationItem[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("pending_manual");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<PendingEvaluationItem | null>(null);
  const [awardedMarks, setAwardedMarks] = useState("0");
  const [comments, setComments] = useState("");
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listEvaluationQueue({
        page,
        scoring_status: statusFilter || undefined,
      });
      setRows(res.results);
      setCount(res.count);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const openGrade = (item: PendingEvaluationItem) => {
    setSelected(item);
    setAwardedMarks(item.awarded_marks ?? "0");
    setComments("");
    setModalError(null);
  };

  const handleSubmitGrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setSaving(true);
    setModalError(null);
    try {
      await submitManualEvaluation(selected.id, {
        awarded_marks: awardedMarks,
        comments: comments.trim(),
      });
      setSelected(null);
      await loadQueue();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const columns: ColumnDef<PendingEvaluationItem>[] = [
    {
      key: "student",
      header: "Student",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">{r.student_name}</div>
          <div className="text-xs font-mono text-slate-500">{r.student_reg_no}</div>
        </div>
      ),
    },
    {
      key: "question",
      header: "Assessment / Question",
      render: (r) => (
        <div>
          <div className="text-xs font-semibold text-slate-800">
            {r.template_name} (v{r.version_no}) — {r.question_code}
          </div>
          <div className="text-xs text-slate-500 line-clamp-1">{r.prompt}</div>
        </div>
      ),
    },
    {
      key: "marks",
      header: "Marks",
      render: (r) => (
        <span className="text-xs font-medium text-slate-700">
          {r.awarded_marks !== null ? `${r.awarded_marks} / ${r.max_marks}` : `Max ${r.max_marks}`}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => (
        <StatusBadge
          label={r.scoring_status === "pending_manual" ? "Pending" : "Evaluated"}
          tone={r.scoring_status === "pending_manual" ? "warning" : "success"}
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
          onClick={() => openGrade(r)}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ClipboardCheck className="h-3.5 w-3.5 text-[#0D9488]" />
          {r.scoring_status === "pending_manual" ? "Evaluate" : "Re-evaluate"}
        </button>
      ),
    },
  ];

  return (
    <AppShell title="Manual Response Evaluation">
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <select
            aria-label="Filter by evaluation status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
          >
            <option value="pending_manual">Pending Manual Evaluation</option>
            <option value="manually_evaluated">Evaluated Responses</option>
            <option value="">All Manual Responses</option>
          </select>
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
          emptyTitle="No manual responses in evaluation queue"
          emptyDescription="Only Descriptive and Coding submissions enter this manual grading queue. Objective questions (MCQ, True/False, Numeric) are automatically scored on submission."
        />
      </div>

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? `Evaluate ${selected.question_code} — ${selected.student_reg_no}` : "Evaluate"}
        subtitle={selected ? `Max Marks: ${selected.max_marks}` : undefined}
      >
        {selected && (
          <form className="space-y-4 text-xs" onSubmit={handleSubmitGrade}>
            {modalError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {modalError}
              </div>
            )}

            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1">
              <div className="font-semibold text-[#0F2942]">Prompt</div>
              <div className="text-slate-700 whitespace-pre-wrap">{selected.prompt}</div>
            </div>

            {selected.rubric && (
              <div className="rounded-lg border border-teal-200 bg-teal-50 p-3 space-y-1">
                <div className="font-semibold text-teal-900">Evaluator Rubric Guidance</div>
                <div className="text-teal-800">{selected.rubric.evaluator_guidance}</div>
              </div>
            )}

            <div className="rounded-lg border border-slate-200 p-3 space-y-1">
              <div className="font-semibold text-[#0F2942]">Student Response</div>
              <pre className="whitespace-pre-wrap font-mono text-slate-800 bg-slate-50 p-2 rounded">
                {String(selected.response_json?.text ?? selected.response_json?.code ?? "")}
              </pre>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-slate-700">
                  Awarded Marks (0 – {selected.max_marks})
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max={Number(selected.max_marks)}
                  required
                  value={awardedMarks}
                  onChange={(e) => setAwardedMarks(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block font-medium text-slate-700">Evaluator Comments</label>
              <textarea
                rows={2}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            {selected.evaluations.length > 0 && (
              <div className="border-t border-slate-200 pt-3 space-y-1">
                <div className="font-semibold text-slate-600">Prior Evaluation History</div>
                {selected.evaluations.map((ev) => (
                  <div key={ev.id} className="text-[11px] text-slate-500">
                    v{ev.version_no}: {ev.awarded_marks} marks by {ev.evaluator_name} ({new Date(ev.evaluated_at).toLocaleString()})
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setSelected(null)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
              <button type="submit" disabled={saving} className="rounded-lg bg-[#0D9488] px-4 py-2 text-sm font-medium text-white">
                {saving ? "Saving..." : "Record Evaluation"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </AppShell>
  );
};

