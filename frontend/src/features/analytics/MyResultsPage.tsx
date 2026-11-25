import React, { useEffect, useState } from "react";
import { Award, Compass, TrendingUp } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { StatusBadge } from "../../components/StatusBadge";
import { DomainBarChart } from "../../components/charts/DomainBarChart";
import { parseApiError } from "../../services/apiClient";
import { fetchMyReports } from "../../services/analyticsService";
import type { IndividualStudentReportResponse } from "../../types/analytics";

export const MyResultsPage: React.FC = () => {
  const [report, setReport] = useState<IndividualStudentReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMyReports()
      .then((data) => {
        setReport(data);
        setError(null);
      })
      .catch((err) => setError(parseApiError(err).message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell title="My Results & Talent Profile">
      <div className="space-y-6">
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Loading your released results...
          </div>
        ) : report ? (
          <>
            <div className="rounded-lg border border-slate-200 bg-slate-100/70 px-4 py-2 text-xs text-slate-600">
              {report.notice}
            </div>

            <div className="grid sm:grid-cols-3 gap-4">
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500">
                  <Award className="h-4 w-4 text-[#0D9488]" />
                  <span>My Demonstrated Average</span>
                </div>
                <div className="text-2xl font-bold text-[#0F2942]">
                  {report.summary.overall_demonstrated_percentage !== null
                    ? `${report.summary.overall_demonstrated_percentage}%`
                    : "Insufficient data"}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500">
                  <TrendingUp className="h-4 w-4 text-blue-700" />
                  <span>Cohort Benchmark</span>
                </div>
                <div className="text-2xl font-bold text-[#0F2942]">
                  {report.summary.cohort_benchmark_percentage !== null
                    ? `${report.summary.cohort_benchmark_percentage}%`
                    : "—"}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500">
                  <Compass className="h-4 w-4 text-slate-600" />
                  <span>Released Assessments</span>
                </div>
                <div className="text-2xl font-bold text-[#0F2942]">
                  {report.summary.assessments_count}
                </div>
              </div>
            </div>

            <DomainBarChart
              title="My Demonstrated Performance by Domain"
              items={report.demonstrated_performance.dimensions.map((d) => ({
                code: d.code,
                label: d.name,
                value: d.percentage ?? null,
              }))}
            />

            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
                <h3 className="text-sm font-semibold text-emerald-900">Identified Strengths (≥ 70%)</h3>
                {report.demonstrated_performance.strengths.length === 0 ? (
                  <p className="text-xs text-slate-500">Complete assessments to identify strong domains.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {report.demonstrated_performance.strengths.map((s) => (
                      <StatusBadge key={s.code} label={`${s.code} (${s.percentage}%)`} tone="success" />
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
                <h3 className="text-sm font-semibold text-rose-900">Growth Areas (&lt; 50%)</h3>
                {report.demonstrated_performance.gaps.length === 0 ? (
                  <p className="text-xs text-slate-500">No domains below 50% in released results.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {report.demonstrated_performance.gaps.map((g) => (
                      <StatusBadge key={g.code} label={`${g.code} (${g.percentage}%)`} tone="danger" />
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <DomainBarChart
                title="My Self-Reported Proficiency"
                items={report.self_reported_proficiency.map((d) => ({
                  code: d.code,
                  label: d.name,
                  value: d.average_rating,
                }))}
                maxValue={5}
                unit=" / 5"
                accentColor="#D97706"
              />
              <DomainBarChart
                title="My Stated Career Interests"
                items={report.stated_interest.map((d) => ({
                  code: d.code,
                  label: d.name,
                  value: d.average_rating,
                }))}
                maxValue={5}
                unit=" / 5"
                accentColor="#2563EB"
              />
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-3">
              <h3 className="text-sm font-semibold text-[#0F2942]">Released Assessment History</h3>
              {report.assessment_history.length === 0 ? (
                <p className="text-xs text-slate-500">No released assessment results available yet.</p>
              ) : (
                <div className="divide-y divide-slate-100 text-xs">
                  {report.assessment_history.map((h) => (
                    <div key={h.result_id} className="py-2.5 flex items-center justify-between">
                      <div>
                        <span className="font-semibold text-[#0F2942]">{h.template_name}</span>
                        <span className="ml-2 text-slate-500">v{h.version_no} • Attempt #{h.attempt_no}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-semibold">
                          {h.raw_score} / {h.max_score} ({h.normalized_score !== null ? `${h.normalized_score}%` : "N/A"})
                        </span>
                        <StatusBadge
                          label={h.result_status === "finalized" ? "Finalized" : "Pending Manual"}
                          tone={h.result_status === "finalized" ? "success" : "warning"}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
};

