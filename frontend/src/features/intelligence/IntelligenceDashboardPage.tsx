import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Briefcase, CheckCircle2, ClipboardList, FolderKanban, Users } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { DomainBarChart } from "../../components/charts/DomainBarChart";
import { parseApiError } from "../../services/apiClient";
import { fetchFacultyIntelligence, listAnalyticsCohorts } from "../../services/analyticsService";
import type {
  AnalyticsCohortOption,
  FacultyIntelligenceResponse,
  ReadinessBand,
  StudentReadinessRow,
} from "../../types/analytics";

const BAND_TONE: Record<ReadinessBand, "success" | "warning" | "danger" | "neutral"> = {
  placement_ready: "success",
  near_ready: "warning",
  needs_support: "danger",
  insufficient_data: "neutral",
};

export const IntelligenceDashboardPage: React.FC = () => {
  const [cohorts, setCohorts] = useState<AnalyticsCohortOption[]>([]);
  const [selectedCohortId, setSelectedCohortId] = useState("");
  const [bandFilter, setBandFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [data, setData] = useState<FacultyIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCohorts = useCallback(async () => {
    try {
      const list = await listAnalyticsCohorts();
      setCohorts(list);
    } catch {
      // ignore if user relies on full dashboard load
    }
  }, []);

  const loadIntelligence = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchFacultyIntelligence(selectedCohortId || undefined);
      setData(res);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [selectedCohortId]);

  useEffect(() => {
    loadCohorts();
  }, [loadCohorts]);

  useEffect(() => {
    loadIntelligence();
  }, [loadIntelligence]);

  const filteredStudents = (data?.student_readiness || []).filter((s) => {
    if (bandFilter && s.readiness_band !== bandFilter) return false;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      return (
        s.registration_no.toLowerCase().includes(q) ||
        s.full_name.toLowerCase().includes(q) ||
        (s.primary_gap || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const columns: ColumnDef<StudentReadinessRow>[] = [
    {
      key: "student",
      header: "Student",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">{r.full_name}</div>
          <div className="text-xs text-slate-500">
            {r.registration_no} · {r.cohort_label}
          </div>
        </div>
      ),
    },
    {
      key: "scores",
      header: "Demonstrated / Core Tech",
      render: (r) => (
        <div className="text-xs space-y-0.5">
          <div>
            Overall:{" "}
            <strong className="text-[#0F2942]">
              {r.overall_demonstrated_percentage !== null
                ? `${r.overall_demonstrated_percentage}%`
                : "Insufficient data"}
            </strong>
          </div>
          <div className="text-slate-500">
            Core Tech:{" "}
            {r.core_technical_percentage !== null ? `${r.core_technical_percentage}%` : "N/A"}
          </div>
        </div>
      ),
    },
    {
      key: "strength_gap",
      header: "Strength / Priority Gap",
      render: (r) => (
        <div className="text-xs space-y-0.5">
          <div>Strength: {r.top_strength || "—"}</div>
          <div className="text-rose-700">Gap: {r.primary_gap || "—"}</div>
        </div>
      ),
    },
    {
      key: "plans",
      header: "Development Plan",
      render: (r) => (
        <div className="text-xs">
          <div className="font-medium text-slate-700">
            {r.plans_count} plan(s) · {r.plan_completion_percent}%
          </div>
          {r.pending_manual_count > 0 && (
            <div className="text-amber-700">{r.pending_manual_count} pending eval</div>
          )}
        </div>
      ),
    },
    {
      key: "readiness",
      header: "Placement Readiness",
      render: (r) => (
        <div className="space-y-1">
          <StatusBadge label={r.readiness_label} tone={BAND_TONE[r.readiness_band]} />
          <div className="text-[11px] text-slate-500 max-w-xs">{r.evidence_summary}</div>
        </div>
      ),
    },
  ];

  return (
    <AppShell title="Faculty & HOD Intelligence">
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Cohort Scope
            </label>
            <select
              value={selectedCohortId}
              onChange={(e) => setSelectedCohortId(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-[#0F2942]"
            >
              <option value="">All Authorized Cohorts</option>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="text-xs text-slate-500">
            Readiness bands are derived solely from Demonstrated Performance & Development Plans.
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Aggregating cohort intelligence & placement readiness...
          </div>
        ) : data ? (
          <>
            <div className="rounded-lg border border-slate-200 bg-slate-100/70 px-4 py-2 text-xs text-slate-600">
              {data.notice}
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <Users className="h-4 w-4 text-[#0F2942]" /> Students
                </div>
                <div className="text-2xl font-bold text-[#0F2942]">
                  {data.summary.assessed_students}/{data.summary.total_students}
                </div>
                <div className="text-xs text-slate-500">
                  Assessed ({data.summary.authorized_cohorts} cohort(s))
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Placement Ready
                </div>
                <div className="text-2xl font-bold text-emerald-700">
                  {data.summary.placement_ready_count}
                </div>
                <div className="text-xs text-slate-500">
                  Near ready: {data.summary.near_ready_count}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <AlertTriangle className="h-4 w-4 text-rose-600" /> Support Needed
                </div>
                <div className="text-2xl font-bold text-rose-700">
                  {data.summary.needs_support_count}
                </div>
                <div className="text-xs text-slate-500">
                  No data: {data.summary.insufficient_data_count}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <FolderKanban className="h-4 w-4 text-[#0D9488]" /> Plan Adoption
                </div>
                <div className="text-2xl font-bold text-[#0F2942]">
                  {data.summary.avg_plan_completion_percent}%
                </div>
                <div className="text-xs text-slate-500">
                  {data.summary.students_with_plans} students with active plans
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                  <ClipboardList className="h-4 w-4 text-amber-600" /> Pending Grading
                </div>
                <div className="text-2xl font-bold text-[#0F2942]">
                  {data.summary.pending_manual_evaluations}
                </div>
                <div className="text-xs text-slate-500">Manual responses awaiting rubric</div>
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <DomainBarChart
                title="Demonstrated Performance Hotspots"
                items={data.domain_hotspots.map((d) => ({
                  code: d.code,
                  label: d.name,
                  value: d.average_percentage ?? null,
                }))}
              />

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex items-center gap-2">
                  <Briefcase className="h-4 w-4 text-[#0D9488]" />
                  <h3 className="text-sm font-semibold text-[#0F2942]">
                    Cohort Mentorship & Readiness Rollup
                  </h3>
                </div>
                <div className="space-y-3">
                  {data.cohort_rollups.map((c) => (
                    <div
                      key={c.cohort_id}
                      className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-[#0F2942]">{c.cohort_label}</span>
                        <span className="text-xs font-semibold text-[#0F2942]">
                          Avg:{" "}
                          {c.average_demonstrated_percentage !== null
                            ? `${c.average_demonstrated_percentage}%`
                            : "N/A"}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600">
                        Ready: <strong>{c.placement_ready_count}</strong> · Near:{" "}
                        <strong>{c.near_ready_count}</strong> · Support:{" "}
                        <strong className="text-rose-700">{c.needs_support_count}</strong> · Plan
                        Adoption: <strong>{c.plan_adoption_rate}%</strong>
                      </div>
                      <div className="text-[11px] text-slate-500">
                        Assigned Mentors:{" "}
                        {c.assigned_mentors.length > 0
                          ? c.assigned_mentors.join(", ")
                          : "No mentor assigned yet"}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap items-center gap-3">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter students by registration no, name, or gap..."
                className="flex-1 min-w-[220px] rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <select
                value={bandFilter}
                onChange={(e) => setBandFilter(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700"
              >
                <option value="">All Readiness Bands</option>
                <option value="placement_ready">Placement Ready</option>
                <option value="near_ready">Near Ready</option>
                <option value="needs_support">Foundational Support Needed</option>
                <option value="insufficient_data">Insufficient Assessment Data</option>
              </select>
            </div>

            <DataTable
              columns={columns}
              rows={filteredStudents}
              rowKey={(r) => r.student_id}
              emptyTitle="No matching students"
              emptyDescription="Adjust readiness band or search criteria."
            />
          </>
        ) : null}
      </div>
    </AppShell>
  );
};

