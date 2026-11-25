import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, BarChart3, Download, Eye, TrendingUp, Users } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { DomainBarChart } from "../../components/charts/DomainBarChart";
import { ScoreDistributionChart } from "../../components/charts/ScoreDistributionChart";
import { useAuth } from "../../app/AuthContext";
import { parseApiError } from "../../services/apiClient";
import {
  fetchCohortAnalytics,
  fetchStudentReport,
  getAnalyticsExportUrl,
  listAnalyticsCohorts,
} from "../../services/analyticsService";
import type {
  AnalyticsCohortOption,
  CohortAnalyticsResponse,
  IndividualStudentReportResponse,
  StudentComparisonRow,
} from "../../types/analytics";

export const CohortAnalyticsPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const canExport = hasPermission("reports.export");

  const [cohorts, setCohorts] = useState<AnalyticsCohortOption[]>([]);
  const [selectedCohortId, setSelectedCohortId] = useState("");
  const [analytics, setAnalytics] = useState<CohortAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [studentReport, setStudentReport] = useState<IndividualStudentReportResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const loadCohorts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listAnalyticsCohorts();
      setCohorts(list);
      if (list[0]) {
        setSelectedCohortId((prev) => prev || list[0].id);
      } else {
        setLoading(false);
      }
    } catch (err) {
      setError(parseApiError(err).message);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCohorts();
  }, [loadCohorts]);

  useEffect(() => {
    if (!selectedCohortId) return;
    let active = true;
    setLoading(true);
    setError(null);
    fetchCohortAnalytics(selectedCohortId)
      .then((data) => {
        if (active) setAnalytics(data);
      })
      .catch((err) => {
        if (active) setError(parseApiError(err).message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedCohortId]);

  const openStudentReport = async (studentId: string) => {
    setReportLoading(true);
    setError(null);
    try {
      const data = await fetchStudentReport(studentId);
      setStudentReport(data);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setReportLoading(false);
    }
  };

  const comparisonColumns: ColumnDef<StudentComparisonRow>[] = [
    {
      key: "student",
      header: "Student",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">{r.full_name}</div>
          <div className="text-xs font-mono text-slate-500">{r.registration_no}</div>
        </div>
      ),
    },
    {
      key: "attempts",
      header: "Assessments",
      render: (r) => <span className="text-xs font-medium text-slate-700">{r.attempts_count}</span>,
    },
    {
      key: "avg",
      header: "Demonstrated Avg",
      render: (r) => (
        <span className="font-semibold text-[#0F2942]">
          {r.average_percentage !== null ? `${r.average_percentage}%` : "Insufficient data"}
        </span>
      ),
    },
    {
      key: "strength_gap",
      header: "Top Strength / Primary Gap",
      render: (r) => (
        <div className="flex flex-wrap gap-1.5">
          {r.top_strength && <StatusBadge label={`Strength: ${r.top_strength}`} tone="success" />}
          {r.primary_gap && <StatusBadge label={`Gap: ${r.primary_gap}`} tone="warning" />}
          {!r.top_strength && !r.primary_gap && <span className="text-xs text-slate-400">—</span>}
        </div>
      ),
    },
    {
      key: "support",
      header: "Training Signal",
      render: (r) =>
        r.needs_additional_training ? (
          <StatusBadge label="Needs Support" tone="danger" />
        ) : r.attempts_count > 0 ? (
          <StatusBadge label="On Track" tone="success" />
        ) : (
          <StatusBadge label="Not Assessed" tone="neutral" />
        ),
    },
    {
      key: "actions",
      header: "Individual Report",
      className: "text-right",
      render: (r) => (
        <button
          type="button"
          onClick={() => openStudentReport(r.student_id)}
          disabled={reportLoading}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <Eye className="h-3.5 w-3.5 text-[#0D9488]" />
          Report
        </button>
      ),
    },
  ];

  return (
    <AppShell title="Cohort Analytics & Reports">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="cohort-select" className="text-xs font-semibold uppercase text-slate-500">
              Cohort
            </label>
            <select
              id="cohort-select"
              value={selectedCohortId}
              onChange={(e) => setSelectedCohortId(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm min-w-[260px]"
            >
              {cohorts.length === 0 ? (
                <option value="">No authorized cohorts</option>
              ) : (
                cohorts.map((c) => (
                  <option key={c.id} value={c.id}>{c.label}</option>
                ))
              )}
            </select>
          </div>

          {canExport && selectedCohortId && (
            <div className="flex flex-wrap items-center gap-2">
              {(["csv", "xlsx", "pdf"] as const).map((fmt) => (
                <a
                  key={fmt}
                  href={getAnalyticsExportUrl({ format: fmt, cohortId: selectedCohortId })}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700"
                >
                  <Download className="h-3.5 w-3.5 text-[#0D9488]" />
                  Export {fmt.toUpperCase()}
                </a>
              ))}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Calculating cohort analytics...
          </div>
        ) : analytics ? (
          <>
            <div className="rounded-lg border border-slate-200 bg-slate-100/70 px-4 py-2 text-xs text-slate-600">
              {analytics.notice}
            </div>

            {/* Summary KPIs */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                icon={<Users className="h-4 w-4 text-[#0F2942]" />}
                label="Students Assessed"
                value={`${analytics.summary.assessed_students} / ${analytics.summary.total_students}`}
              />
              <KpiCard
                icon={<BarChart3 className="h-4 w-4 text-[#0D9488]" />}
                label="Cohort Demonstrated Avg"
                value={
                  analytics.summary.cohort_average_percentage !== null
                    ? `${analytics.summary.cohort_average_percentage}%`
                    : "Insufficient data"
                }
              />
              <KpiCard
                icon={<TrendingUp className="h-4 w-4 text-emerald-600" />}
                label="Cohort Strong Domains"
                value={String(analytics.cohort_strengths.length)}
              />
              <KpiCard
                icon={<AlertTriangle className="h-4 w-4 text-rose-600" />}
                label="Need Additional Training"
                value={String(analytics.summary.students_needing_training)}
              />
            </div>

            {/* Charts */}
            <div className="grid lg:grid-cols-2 gap-6">
              <DomainBarChart
                title="Demonstrated Performance by Domain"
                items={analytics.demonstrated_performance_domains.map((d) => ({
                  code: d.code,
                  label: d.name,
                  value: d.average_percentage ?? null,
                }))}
              />
              <ScoreDistributionChart buckets={analytics.score_distribution} />
            </div>

            {/* Cohort Strengths vs Gaps */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
                <h3 className="text-sm font-semibold text-emerald-900">
                  Cohort Technical & Cognitive Strengths (≥ 70%)
                </h3>
                {analytics.cohort_strengths.length === 0 ? (
                  <p className="text-xs text-slate-500">No domains averaging ≥ 70% yet.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {analytics.cohort_strengths.map((s) => (
                      <StatusBadge
                        key={s.code}
                        label={`${s.code}: ${s.average_percentage}%`}
                        tone="success"
                      />
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
                <h3 className="text-sm font-semibold text-rose-900">
                  Cohort Skill Gaps Requiring Reinforcement (&lt; 50%)
                </h3>
                {analytics.cohort_gaps.length === 0 ? (
                  <p className="text-xs text-slate-500">No domains averaging below 50%.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {analytics.cohort_gaps.map((g) => (
                      <StatusBadge
                        key={g.code}
                        label={`${g.code}: ${g.average_percentage}%`}
                        tone="danger"
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Strictly separated Self-Report & Career Interests */}
            <div className="grid lg:grid-cols-2 gap-6">
              <DomainBarChart
                title="Self-Reported Proficiency (Perceived Scale)"
                items={analytics.self_reported_proficiency_domains.map((d) => ({
                  code: d.code,
                  label: d.name,
                  value: d.average_rating,
                }))}
                maxValue={5}
                unit=" / 5"
                accentColor="#D97706"
              />
              <DomainBarChart
                title="Stated Career Interests (Interest Rating)"
                items={analytics.stated_interest_domains.map((d) => ({
                  code: d.code,
                  label: d.name,
                  value: d.average_rating,
                }))}
                maxValue={5}
                unit=" / 5"
                accentColor="#2563EB"
              />
            </div>

            {/* Student Comparison Table */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-[#0F2942]">Student Comparison</h3>
              <DataTable
                columns={comparisonColumns}
                rows={analytics.student_comparison}
                rowKey={(r) => r.student_id}
                emptyTitle="No students in selected cohort"
              />
            </div>
          </>
        ) : null}
      </div>

      {/* Individual Student Report Modal */}
      <Modal
        open={Boolean(studentReport)}
        onClose={() => setStudentReport(null)}
        title={
          studentReport
            ? `Individual Report — ${studentReport.student.full_name} (${studentReport.student.registration_no})`
            : "Individual Report"
        }
        subtitle={studentReport?.student.cohort_label || undefined}
      >
        {studentReport && (
          <div className="space-y-5 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-slate-50 border border-slate-200 p-3.5">
              <div>
                <div className="text-slate-500">Demonstrated Overall Average</div>
                <div className="text-lg font-bold text-[#0F2942]">
                  {studentReport.summary.overall_demonstrated_percentage !== null
                    ? `${studentReport.summary.overall_demonstrated_percentage}%`
                    : "Insufficient data"}
                </div>
              </div>
              {canExport && (
                <div className="flex gap-1.5">
                  {(["csv", "xlsx", "pdf"] as const).map((fmt) => (
                    <a
                      key={fmt}
                      href={getAnalyticsExportUrl({
                        format: fmt,
                        studentId: studentReport.student.id,
                      })}
                      className="rounded border border-slate-300 bg-white px-2.5 py-1 font-medium text-slate-700 hover:bg-slate-100"
                    >
                      {fmt.toUpperCase()}
                    </a>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-3 space-y-1.5">
                <div className="font-semibold text-emerald-900">Strengths (≥ 70%)</div>
                {studentReport.demonstrated_performance.strengths.length === 0 ? (
                  <div className="text-slate-500">None recorded yet</div>
                ) : (
                  studentReport.demonstrated_performance.strengths.map((s) => (
                    <div key={s.code}>{s.code}: {s.percentage}%</div>
                  ))
                )}
              </div>
              <div className="rounded-lg border border-rose-200 bg-rose-50/50 p-3 space-y-1.5">
                <div className="font-semibold text-rose-900">Skill Gaps (&lt; 50%)</div>
                {studentReport.demonstrated_performance.gaps.length === 0 ? (
                  <div className="text-slate-500">No gaps below 50%</div>
                ) : (
                  studentReport.demonstrated_performance.gaps.map((g) => (
                    <div key={g.code}>{g.code}: {g.percentage}%</div>
                  ))
                )}
              </div>
            </div>

            {studentReport.stated_interest.length > 0 && (
              <div className="space-y-1.5">
                <div className="font-semibold text-[#0F2942]">Stated Career Interests</div>
                {studentReport.stated_interest.map((i) => (
                  <div key={i.code} className="flex justify-between border-b border-slate-100 py-1">
                    <span>{i.code} — {i.name}</span>
                    <span className="font-medium">
                      {i.average_rating !== null ? `${i.average_rating} / 5` : "Recorded"}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {studentReport.assessment_history.length > 0 && (
              <div className="space-y-1.5">
                <div className="font-semibold text-[#0F2942]">Assessment History</div>
                {studentReport.assessment_history.map((h) => (
                  <div key={h.result_id} className="flex justify-between border-b border-slate-100 py-1">
                    <span>{h.template_name} (v{h.version_no})</span>
                    <span className="font-semibold">
                      {h.raw_score}/{h.max_score} ({h.normalized_score !== null ? `${h.normalized_score}%` : "N/A"})
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

const KpiCard: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({
  icon,
  label,
  value,
}) => (
  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
      {icon}
      <span>{label}</span>
    </div>
    <div className="text-2xl font-bold text-[#0F2942]">{value}</div>
  </div>
);

