import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CheckCircle2, ChevronLeft, ChevronRight, Clock, Save, Send } from "lucide-react";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  autosaveResponses,
  fetchAttemptRunner,
  submitAttempt,
} from "../../services/attemptsService";
import type { AttemptRunnerPayload, RunnerQuestion } from "../../types/attempts";

function formatClock(totalSeconds: number): string {
  const hrs = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  if (hrs > 0) {
    return `${hrs}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function hasAnswer(q: RunnerQuestion, resp?: Record<string, unknown>): boolean {
  if (!resp) return false;
  if (q.question_type === "numeric") {
    return resp.numeric_value !== undefined && String(resp.numeric_value).trim() !== "";
  }
  if (q.question_type === "descriptive") {
    return Boolean(String(resp.text || "").trim());
  }
  if (q.question_type === "coding") {
    return Boolean(String(resp.code || "").trim());
  }
  const keys = resp.selected_keys as string[] | undefined;
  return Boolean(keys && keys.length > 0);
}

export const TestRunnerPage: React.FC = () => {
  const { attemptId } = useParams<{ attemptId: string }>();
  const navigate = useNavigate();

  const [payload, setPayload] = useState<AttemptRunnerPayload | null>(null);
  const [responses, setResponses] = useState<Record<string, Record<string, unknown>>>({});
  const [currentIdx, setCurrentIdx] = useState(0);
  const [remainingSec, setRemainingSec] = useState(0);
  const [loading, setLoading] = useState(true);
  const [savingStatus, setSavingStatus] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const responsesRef = useRef(responses);
  responsesRef.current = responses;

  const persistCurrentResponses = useCallback(async () => {
    if (!attemptId || !payload) return;
    if (payload.attempt.status !== "in_progress") return;
    const items = Object.entries(responsesRef.current).map(([version_question_id, response_json]) => ({
      version_question_id,
      response_json,
    }));
    if (items.length === 0) return;
    try {
      setSavingStatus("Saving...");
      const res = await autosaveResponses(attemptId, items);
      setSavingStatus(`Saved ${new Date(res.saved_at).toLocaleTimeString()}`);
    } catch (err) {
      setError(parseApiError(err).message);
      setSavingStatus("Save failed");
    }
  }, [attemptId, payload]);

  useEffect(() => {
    if (!attemptId) return;
    setLoading(true);
    fetchAttemptRunner(attemptId)
      .then((data) => {
        setPayload(data);
        setResponses(data.saved_responses || {});
        setRemainingSec(data.remaining_seconds);
        setError(null);
      })
      .catch((err) => setError(parseApiError(err).message))
      .finally(() => setLoading(false));
  }, [attemptId]);

  // Countdown timer display (server remains authoritative)
  useEffect(() => {
    if (!payload || payload.attempt.status !== "in_progress") return;
    const timer = window.setInterval(() => {
      setRemainingSec((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [payload]);

  // Periodic autosave every 20 seconds
  useEffect(() => {
    if (!payload || payload.attempt.status !== "in_progress") return;
    const interval = window.setInterval(() => {
      persistCurrentResponses();
    }, 20000);
    return () => window.clearInterval(interval);
  }, [payload, persistCurrentResponses]);

  const handleNavigateQuestion = async (nextIdx: number) => {
    await persistCurrentResponses();
    setCurrentIdx(nextIdx);
  };

  const handleFinalSubmit = async () => {
    if (!attemptId) return;
    setSubmitting(true);
    setError(null);
    try {
      await persistCurrentResponses();
      await submitAttempt(attemptId);
      setConfirmOpen(false);
      navigate("/my-assessments", { replace: true });
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center text-sm text-slate-600">
        Loading assessment runner...
      </div>
    );
  }

  if (!payload) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-xl border border-slate-200 p-8 max-w-md w-full space-y-4 text-center">
          <div className="text-sm text-rose-700">{error || "Unable to load attempt."}</div>
          <button
            type="button"
            onClick={() => navigate("/my-assessments")}
            className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm text-white"
          >
            Back to My Assessments
          </button>
        </div>
      </div>
    );
  }

  const questions = payload.questions;
  const activeQ = questions[currentIdx];
  const currentResp = activeQ ? responses[activeQ.version_question_id] || {} : {};
  const isReadOnly = payload.attempt.status !== "in_progress";
  const answeredCount = questions.filter((q) => hasAnswer(q, responses[q.version_question_id])).length;

  const updateAnswer = (vqId: string, nextResp: Record<string, unknown>) => {
    setResponses((prev) => ({ ...prev, [vqId]: nextResp }));
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Runner Header */}
      <header className="bg-[#0F2942] text-white px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-base font-semibold">
            {payload.attempt.template_name} (v{payload.attempt.version_no})
          </h1>
          <p className="text-xs text-slate-300">
            Attempt #{payload.attempt.attempt_no} • Answered {answeredCount} of {questions.length}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {savingStatus && <span className="text-xs text-teal-300">{savingStatus}</span>}
          <div className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-1.5 text-sm font-mono">
            <Clock className="h-4 w-4 text-[#0D9488]" />
            <span>{formatClock(remainingSec)}</span>
          </div>
          {!isReadOnly && (
            <button
              type="button"
              onClick={() => setConfirmOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#0D9488] hover:bg-teal-600 px-4 py-2 text-xs font-semibold text-white"
            >
              <Send className="h-3.5 w-3.5" />
              Submit Assessment
            </button>
          )}
        </div>
      </header>

      {error && (
        <div className="mx-6 mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="flex-1 max-w-6xl w-full mx-auto p-6 grid lg:grid-cols-12 gap-6">
        {/* Main Question Area */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between space-y-6">
          {activeQ && (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[#0F2942]">
                    Question {currentIdx + 1} of {questions.length}
                  </span>
                  <StatusBadge label={activeQ.question_type.replaceAll("_", " ")} tone="neutral" />
                </div>
                <span className="text-xs text-slate-500">
                  Marks: +{activeQ.marks}
                  {Number(activeQ.negative_marks) > 0 ? ` / -${activeQ.negative_marks}` : ""}
                </span>
              </div>

              <div className="text-base font-medium text-slate-900 whitespace-pre-wrap leading-relaxed">
                {activeQ.prompt}
              </div>

              {/* Input Widgets by Question Type */}
              {(activeQ.question_type === "single_mcq" ||
                activeQ.question_type === "true_false" ||
                activeQ.question_type === "likert" ||
                activeQ.question_type === "self_rating" ||
                activeQ.question_type === "situational_judgement") && (
                <div className="space-y-2.5">
                  {activeQ.options.map((opt) => {
                    const selected = ((currentResp.selected_keys as string[]) || [])[0] === opt.option_key;
                    return (
                      <label
                        key={opt.option_key}
                        className={`flex items-center gap-3 rounded-lg border p-3.5 text-sm cursor-pointer transition ${
                          selected
                            ? "border-blue-600 bg-blue-50 text-[#0F2942]"
                            : "border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="radio"
                          disabled={isReadOnly}
                          name={`q-${activeQ.version_question_id}`}
                          checked={selected}
                          onChange={() =>
                            updateAnswer(activeQ.version_question_id, { selected_keys: [opt.option_key] })
                          }
                        />
                        <span className="font-mono text-xs font-semibold text-slate-500">{opt.option_key}.</span>
                        <span>{opt.option_text}</span>
                      </label>
                    );
                  })}
                </div>
              )}

              {activeQ.question_type === "multiple_mcq" && (
                <div className="space-y-2.5">
                  {activeQ.options.map((opt) => {
                    const selectedKeys = (currentResp.selected_keys as string[]) || [];
                    const checked = selectedKeys.includes(opt.option_key);
                    return (
                      <label
                        key={opt.option_key}
                        className={`flex items-center gap-3 rounded-lg border p-3.5 text-sm cursor-pointer transition ${
                          checked
                            ? "border-blue-600 bg-blue-50 text-[#0F2942]"
                            : "border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          disabled={isReadOnly}
                          checked={checked}
                          onChange={() => {
                            const next = checked
                              ? selectedKeys.filter((k) => k !== opt.option_key)
                              : [...selectedKeys, opt.option_key];
                            updateAnswer(activeQ.version_question_id, { selected_keys: next });
                          }}
                        />
                        <span className="font-mono text-xs font-semibold text-slate-500">{opt.option_key}.</span>
                        <span>{opt.option_text}</span>
                      </label>
                    );
                  })}
                </div>
              )}

              {activeQ.question_type === "numeric" && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Enter Numeric Answer
                  </label>
                  <input
                    type="number"
                    step="any"
                    disabled={isReadOnly}
                    value={String(currentResp.numeric_value ?? "")}
                    onChange={(e) =>
                      updateAnswer(activeQ.version_question_id, { numeric_value: e.target.value })
                    }
                    className="w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              )}

              {activeQ.question_type === "descriptive" && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Your Written Response
                  </label>
                  <textarea
                    rows={6}
                    disabled={isReadOnly}
                    value={String(currentResp.text ?? "")}
                    onChange={(e) =>
                      updateAnswer(activeQ.version_question_id, { text: e.target.value })
                    }
                    placeholder="Write your explanation clearly..."
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              )}

              {activeQ.question_type === "coding" && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Code Solution
                  </label>
                  <textarea
                    rows={9}
                    disabled={isReadOnly}
                    value={String(currentResp.code ?? "")}
                    onChange={(e) =>
                      updateAnswer(activeQ.version_question_id, { code: e.target.value })
                    }
                    placeholder="// Write your solution code here..."
                    className="w-full rounded-lg border border-slate-300 bg-slate-950 text-slate-100 font-mono px-3 py-2.5 text-xs"
                  />
                </div>
              )}
            </div>
          )}

          {/* Footer Navigation */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <button
              type="button"
              disabled={currentIdx <= 0}
              onClick={() => handleNavigateQuestion(currentIdx - 1)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-medium text-slate-700 disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>

            <button
              type="button"
              disabled={isReadOnly}
              onClick={persistCurrentResponses}
              className="inline-flex items-center gap-1.5 rounded-lg border border-teal-300 bg-teal-50 px-3.5 py-2 text-xs font-medium text-teal-900"
            >
              <Save className="h-3.5 w-3.5" />
              Save Progress
            </button>

            <button
              type="button"
              disabled={currentIdx >= questions.length - 1}
              onClick={() => handleNavigateQuestion(currentIdx + 1)}
              className="inline-flex items-center gap-1 rounded-lg bg-[#0F2942] px-3.5 py-2 text-xs font-medium text-white disabled:opacity-40"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Question Palette Sidebar */}
        <aside className="lg:col-span-4 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Question Navigation
            </h2>
            <div className="grid grid-cols-5 gap-2">
              {questions.map((q, idx) => {
                const answered = hasAnswer(q, responses[q.version_question_id]);
                const active = idx === currentIdx;
                return (
                  <button
                    key={q.version_question_id}
                    type="button"
                    onClick={() => handleNavigateQuestion(idx)}
                    className={`rounded-lg py-2 text-xs font-semibold border transition ${
                      active
                        ? "border-blue-600 bg-blue-600 text-white"
                        : answered
                          ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                          : "border-slate-200 bg-slate-50 text-slate-700"
                    }`}
                  >
                    {idx + 1}
                  </button>
                );
              })}
            </div>
            {payload.instructions && (
              <div className="text-xs text-slate-600 border-t border-slate-100 pt-3">
                <strong className="text-[#0F2942]">Instructions:</strong> {payload.instructions}
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* Submit Confirmation Modal */}
      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Confirm Final Submission"
        subtitle="Once submitted, responses cannot be edited."
      >
        <div className="space-y-4 text-sm">
          <p className="text-slate-600">
            You have answered <strong>{answeredCount}</strong> of <strong>{questions.length}</strong>{" "}
            questions. Submit your assessment now?
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setConfirmOpen(false)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm"
            >
              Review Answers
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={handleFinalSubmit}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#0D9488] px-4 py-2 text-sm font-medium text-white"
            >
              <CheckCircle2 className="h-4 w-4" />
              {submitting ? "Submitting..." : "Confirm Submit"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

