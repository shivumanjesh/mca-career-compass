import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Award, Clock, Play } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  fetchMyAttemptResult,
  listMyAssignments,
  startOrResumeAttempt,
} from "../../services/attemptsService";
import type { AssessmentResultRecord, StudentAssignmentItem } from "../../types/attempts";

export const MyAssessmentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<StudentAssignmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resultModal, setResultModal] = useState<AssessmentResultRecord | null>(null);

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listMyAssignments();
      setItems(data);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const handleStart = async (assignmentId: string) => {
    setError(null);
    try {
      const payload = await startOrResumeAttempt(assignmentId);
      navigate(`/my-assessments/attempt/${payload.attempt.id}`);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleViewResult = async (attemptId: string) => {
    setError(null);
    try {
      const result = await fetchMyAttemptResult(attemptId);
      setResultModal(result);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <AppShell title="My Assessments">
      <div className="space-y-5">
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Loading assigned assessments...
          </div>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-10 text-center">
            <div className="text-sm font-semibold text-slate-800">No assessments assigned yet</div>
            <p className="text-xs text-slate-500 mt-1">
              When your institution schedules an assessment for your cohort, it will appear here.
            </p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-5">
            {items.map((item) => (
              <div
                key={item.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between gap-4"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="text-base font-bold text-[#0F2942]">
                      {item.template_name} (v{item.version_no})
                    </h2>
                    <StatusBadge
                      label={item.latest_attempt ? item.latest_attempt.status.replaceAll("_", " ") : "Not Started"}
                      tone={
                        item.latest_attempt?.status === "evaluated"
                          ? "success"
                          : item.latest_attempt?.status === "in_progress"
                            ? "warning"
                            : "neutral"
                      }
                    />
                  </div>
                  <div className="flex flex-wrap gap-4 text-xs text-slate-600">
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5 text-[#0D9488]" />
                      {item.duration_minutes} minutes
                    </span>
                    <span>Total Objective Marks: {item.total_marks}</span>
                    <span>
                      Attempts: {item.attempts_used} / {item.max_attempts}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500">
                    Window: {new Date(item.opens_at).toLocaleString()} —{" "}
                    {new Date(item.closes_at).toLocaleString()}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
                  {item.can_start_or_resume && (
                    <button
                      type="button"
                      onClick={() => handleStart(item.id)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-xs font-medium text-white"
                    >
                      <Play className="h-3.5 w-3.5" />
                      {item.latest_attempt?.status === "in_progress" ? "Resume Attempt" : "Start Assessment"}
                    </button>
                  )}
                  {item.latest_attempt &&
                    item.latest_attempt.status !== "in_progress" &&
                    item.results_released && (
                      <button
                        type="button"
                        onClick={() => handleViewResult(item.latest_attempt!.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-[#0D9488] hover:bg-teal-700 px-4 py-2 text-xs font-medium text-white"
                      >
                        <Award className="h-3.5 w-3.5" />
                        View Released Result
                      </button>
                    )}
                  {item.latest_attempt &&
                    item.latest_attempt.status !== "in_progress" &&
                    !item.results_released && (
                      <span className="text-xs text-slate-500">
                        Submitted — awaiting result release
                      </span>
                    )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Released Result Modal (strictly separating the 3 measurement families) */}
      <Modal
        open={Boolean(resultModal)}
        onClose={() => setResultModal(null)}
        title={resultModal ? `${resultModal.template_name} — Result Summary` : "Result"}
        subtitle={resultModal ? `Attempt #${resultModal.attempt_no} • Status: ${resultModal.result_status}` : undefined}
      >
        {resultModal && (
          <div className="space-y-5 text-xs">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 flex items-center justify-between">
              <div>
                <div className="text-slate-500">Demonstrated Performance Score</div>
                <div className="text-xl font-bold text-[#0F2942]">
                  {resultModal.raw_score} / {resultModal.max_score}
                </div>
              </div>
              {resultModal.normalized_score !== null && (
                <div className="text-right">
                  <div className="text-slate-500">Normalized %</div>
                  <div className="text-xl font-bold text-[#0D9488]">{resultModal.normalized_score}%</div>
                </div>
              )}
            </div>

            {resultModal.breakdown_json.demonstrated_performance.length > 0 && (
              <div className="space-y-2">
                <div className="font-semibold text-[#0F2942]">Demonstrated Performance by Dimension</div>
                {resultModal.breakdown_json.demonstrated_performance.map((d) => (
                  <div key={d.dimension_id} className="flex justify-between border-b border-slate-100 py-1.5">
                    <span>{d.code} — {d.name}</span>
                    <span className="font-semibold">
                      {d.status === "insufficient_data" ? "Insufficient data" : `${d.awarded_marks} / ${d.max_marks} (${d.percentage}%)`}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {resultModal.breakdown_json.self_reported_proficiency.length > 0 && (
              <div className="space-y-2">
                <div className="font-semibold text-amber-900">Self-Reported Proficiency (Perceived)</div>
                {resultModal.breakdown_json.self_reported_proficiency.map((d) => (
                  <div key={d.dimension_id} className="flex justify-between border-b border-slate-100 py-1.5">
                    <span>{d.code} — {d.name}</span>
                    <span className="font-medium">
                      {d.average_rating !== null ? `Avg rating: ${d.average_rating}` : `${d.responses_count} response(s)`}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {resultModal.breakdown_json.stated_interest.length > 0 && (
              <div className="space-y-2">
                <div className="font-semibold text-teal-900">Stated Career Interest</div>
                {resultModal.breakdown_json.stated_interest.map((d) => (
                  <div key={d.dimension_id} className="flex justify-between border-b border-slate-100 py-1.5">
                    <span>{d.code} — {d.name}</span>
                    <span className="font-medium">
                      {d.average_rating !== null ? `Interest rating: ${d.average_rating}` : `${d.responses_count} response(s)`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>
    </AppShell>
  );
};

