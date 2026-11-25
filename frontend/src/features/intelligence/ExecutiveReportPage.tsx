import React, { useEffect, useState } from "react";
import { Award, Building2, CheckCircle2, Download, TrendingUp, Users } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { DomainBarChart } from "../../components/charts/DomainBarChart";
import { useAuth } from "../../app/AuthContext";
import { parseApiError } from "../../services/apiClient";
import { fetchExecutiveReport, getExecutiveExportUrl } from "../../services/analyticsService";
import type { CohortRollupRow, ExecutiveReportResponse } from "../../types/analytics";

export const ExecutiveReportPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const canExport = hasPermission("reports.export");

  const [report, setReport] = useState<ExecutiveReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExecutiveReport()
      .then((res) => {
        setReport(res);
        setError(null);
      })
      .catch((err) => setError(parseApiError(err).message))
      .finally(() => setLoading(false));
  }, []);

  const cohortColumns: ColumnDef<CohortRollupRow>[] = [
    {
      key: "cohort",
      header: "Cohort",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">{r.cohort_label}</div>
          <div className="text-xs text-slate-500">
            {r.assigned_mentors.length > 0 ? r.assigned_mentors.join(", ") : "No mentor assigned"}
          </div>
        </div>
      ),
    },
    {
      key: "participation",
      header: "Students / Assessed",
      render: (r) => (
        <span className="text-sm font-medium text-slate-700">
          {r.assessed_students} / {r.total_students}
        </span>
      ),
    },
    {
      key: "avg",
      header: "Demonstrated Avg",
      render: (r) => (
        <span className="font-semibold text-[#0F2942]">
          {r.average_demonstrated_percentage !== null
            ? `${r.average_demonstrated_percentage}%`
            : "Insufficient data"}
        </span>
      ),
    },
    {
      key: "readiness",
      header: "Readiness Breakdown",
      render: (r) => (
        <div className="flex flex-wrap gap-1.5">
          <StatusBadge label={`Ready: ${r.placement_ready_count}`} tone="success" />
          <StatusBadge label={`Near: ${r.near_ready_count}`} tone="warning" />
          <StatusBadge label={`Support: ${r.needs_support_count}`} tone="danger" />
        </div>
      ),
    },
    {
      key: "plans",
      header: "Empowerment Plans",
      render: (r) => (
        <div className="text-xs text-slate-600">
          <div>Adoption: {r.plan_adoption_rate}%</div>
          <div>Completion: {r.avg_plan_completion_percent}%</div>
        </div>
      ),
    },
  ];

  return (
    <AppShell title="Institution Executive Report">
      <div className="space-y-6">
        {report && (
          <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <Building2 className="h-5 w-5 text-[#0D9488]" />
              <div>
                <h2 className="font-semibold text-[#0F2942]">
                  {report.institution.name} ({report.institution.code})
                </h2>
                <p className="text-xs text-slate-500">
                  {report.summary.total_programmes} programme(s) · {report.summary.total_cohorts}{" "}
                  cohort(s) · {report.summary.active_faculty_count} faculty member(s)
                </p>
              </div>
            </div>

            {canExport && (
              <div className="flex flex-wrap items-center gap-2">
                {(["csv", "xlsx", "pdf"] as const).map((fmt) => (
                  <a
                    key={fmt}
                    href={getExecutiveExportUrl(fmt)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-[#0F2942] hover:bg-slate-50"
                  >
                    <Download className="h-3.5 w-3.5" />
                    <span className="uppercase">{fmt}</span>
                  </a>
                ))}
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Building institution-wide executive report...
          </div>
        ) : report ? (
          <>
            <div className="rounded-lg border border-slate-200 bg-slate-100/70 px-4 py-2 text-xs text-slate-600">
              {report.notice}
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <Users className="h-4 w-4 text-blue-700" /> Participation Rate
                </div>
                <div className="text-2xl font-bold text-[#0F2942] mt-1">
                  {report.summary.participation_rate}%
                </div>
                <div className="text-xs text-slate-500">
                  {report.summary.assessed_students} of {report.summary.total_students} students
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <TrendingUp className="h-4 w-4 text-[#0D9488]" /> Institutional Mean
                </div>
                <div className="text-2xl font-bold text-[#0F2942] mt-1">
                  {report.summary.overall_demonstrated_percentage !== null
                    ? `${report.summary.overall_demonstrated_percentage}%`
                    : "N/A"}
                </div>
                <div className="text-xs text-slate-500">Demonstrated Performance only</div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Placement Readiness
                </div>
                <div className="text-2xl font-bold text-emerald-700 mt-1">
                  {report.summary.placement_ready_rate}%
                </div>
                <div className="text-xs text-slate-500">
                  {report.summary.placement_ready_count} ready · {report.summary.needs_support_count}{" "}
                  need support
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <Award className="h-4 w-4 text-indigo-700" /> Empowerment Progress
                </div>
                <div className="text-2xl font-bold text-[#0F2942] mt-1">
                  {report.summary.avg_plan_completion_percent}%
                </div>
                <div className="text-xs text-slate-500">
                  {report.summary.active_or_completed_plans} active/completed plans
                </div>
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <DomainBarChart
                title="Demonstrated Performance Domains (Institution-Wide)"
                items={report.demonstrated_domains.map((d) => ({
                  code: d.code,
                  label: d.name,
                  value: d.average_percentage ?? null,
                }))}
              />
              <DomainBarChart
                title="Stated Career Interests (Separate Measurement Family)"
                maxValue={5}
                unit="/5"
                accentColor="#1E3A5F"
                items={report.stated_interest_domains.map((d) => ({
                  code: d.code,
                  label: d.name,
                  value: d.average_rating,
                }))}
              />
            </div>

            <DataTable
              columns={cohortColumns}
              rows={report.cohort_rollups}
              rowKey={(r) => r.cohort_id}
              emptyTitle="No cohorts configured"
              emptyDescription="Create cohorts under Academic Structure to view executive benchmarks."
            />
          </>
        ) : null}
      </div>
    </AppShell>
  );
};

