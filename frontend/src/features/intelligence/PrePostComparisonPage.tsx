import React, { useCallback, useEffect, useState } from "react";
import { ArrowRight, GitCompare, TrendingDown, TrendingUp } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  fetchPrePostComparison,
  listAnalyticsCohorts,
  listAnalyticsTemplates,
} from "../../services/analyticsService";
import type {
  AnalyticsCohortOption,
  AnalyticsTemplateOption,
  PrePostComparisonResponse,
} from "../../types/analytics";

type TrajectoryRow = PrePostComparisonResponse["student_trajectories"][number];

export const PrePostComparisonPage: React.FC = () => {
  const [cohorts, setCohorts] = useState<AnalyticsCohortOption[]>([]);
  const [templates, setTemplates] = useState<AnalyticsTemplateOption[]>([]);
  const [cohortId, setCohortId] = useState("");
  const [preTemplateId, setPreTemplateId] = useState("");
  const [postTemplateId, setPostTemplateId] = useState("");

  const [data, setData] = useState<PrePostComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listAnalyticsCohorts(), listAnalyticsTemplates()])
      .then(([c, t]) => {
        setCohorts(c);
        setTemplates(t);
      })
      .catch(() => undefined);
  }, []);

  const loadComparison = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPrePostComparison({
        cohortId: cohortId || undefined,
        preTemplateId: preTemplateId || undefined,
        postTemplateId: postTemplateId || undefined,
      });
      setData(res);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [cohortId, preTemplateId, postTemplateId]);

  useEffect(() => {
    loadComparison();
  }, [loadComparison]);

  const studentColumns: ColumnDef<TrajectoryRow>[] = [
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
      key: "pre",
      header: "Baseline (Pre)",
      render: (r) => (
        <div className="text-xs">
          <div className="font-semibold text-slate-800">{r.pre_score}%</div>
          <div className="text-slate-500">{r.pre_template}</div>
        </div>
      ),
    },
    {
      key: "post",
      header: "Follow-up (Post)",
      render: (r) => (
        <div className="text-xs">
          <div className="font-semibold text-[#0F2942]">{r.post_score}%</div>
          <div className="text-slate-500">{r.post_template}</div>
        </div>
      ),
    },
    {
      key: "delta",
      header: "Gain / Delta",
      render: (r) => (
        <div className="flex items-center gap-2">
          <StatusBadge
            label={`${r.delta > 0 ? "+" : ""}${r.delta}%`}
            tone={
              r.trend === "improved" ? "success" : r.trend === "declined" ? "danger" : "neutral"
            }
          />
          <span className="text-xs capitalize text-slate-500">{r.trend}</span>
        </div>
      ),
    },
  ];

  return (
    <AppShell title="Pre / Post Assessment Comparison">
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 p-4 grid sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Cohort Filter</label>
            <select
              value={cohortId}
              onChange={(e) => setCohortId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">All Authorized Cohorts</option>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Baseline (Pre) Template
            </label>
            <select
              value={preTemplateId}
              onChange={(e) => setPreTemplateId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Auto: Earliest Attempt</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Follow-Up (Post) Template
            </label>
            <select
              value={postTemplateId}
              onChange={(e) => setPostTemplateId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Auto: Latest Attempt</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Comparing baseline and follow-up assessments...
          </div>
        ) : data ? (
          <>
            <div className="rounded-lg border border-slate-200 bg-slate-100/70 px-4 py-2 text-xs text-slate-600 flex flex-wrap items-center justify-between gap-2">
              <span>{data.notice}</span>
              <span className="font-medium text-[#0F2942]">
                Comparing: {data.pre_label} <ArrowRight className="inline h-3 w-3" /> {data.post_label}
              </span>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="text-xs font-semibold uppercase text-slate-500">
                  Comparable Students
                </div>
                <div className="text-2xl font-bold text-[#0F2942] mt-1">
                  {data.summary.comparable_students}
                </div>
              </div>
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="text-xs font-semibold uppercase text-slate-500">Pre Mean</div>
                <div className="text-2xl font-bold text-slate-700 mt-1">
                  {data.summary.pre_average_percentage !== null
                    ? `${data.summary.pre_average_percentage}%`
                    : "N/A"}
                </div>
              </div>
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="text-xs font-semibold uppercase text-slate-500">Post Mean</div>
                <div className="text-2xl font-bold text-[#0F2942] mt-1">
                  {data.summary.post_average_percentage !== null
                    ? `${data.summary.post_average_percentage}%`
                    : "N/A"}
                </div>
              </div>
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="text-xs font-semibold uppercase text-slate-500">Mean Delta</div>
                <div
                  className={`text-2xl font-bold mt-1 flex items-center gap-1.5 ${
                    (data.summary.average_delta ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"
                  }`}
                >
                  {(data.summary.average_delta ?? 0) >= 0 ? (
                    <TrendingUp className="h-5 w-5" />
                  ) : (
                    <TrendingDown className="h-5 w-5" />
                  )}
                  <span>
                    {data.summary.average_delta !== null
                      ? `${data.summary.average_delta > 0 ? "+" : ""}${data.summary.average_delta}%`
                      : "N/A"}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center gap-2">
                <GitCompare className="h-4 w-4 text-[#0D9488]" />
                <h2 className="text-sm font-semibold text-[#0F2942]">
                  Domain-Level Demonstrated Score Delta
                </h2>
              </div>
              {data.dimension_deltas.length === 0 ? (
                <p className="text-xs text-slate-500">
                  No paired pre/post demonstrated dimension attempts found yet.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                      <tr>
                        <th className="px-4 py-2 text-left">Dimension</th>
                        <th className="px-4 py-2 text-right">Pre %</th>
                        <th className="px-4 py-2 text-right">Post %</th>
                        <th className="px-4 py-2 text-right">Delta</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.dimension_deltas.map((d) => (
                        <tr key={d.code}>
                          <td className="px-4 py-2 font-medium text-[#0F2942]">
                            {d.code} — {d.name}
                          </td>
                          <td className="px-4 py-2 text-right">
                            {d.pre_percentage !== null ? `${d.pre_percentage}%` : "—"}
                          </td>
                          <td className="px-4 py-2 text-right">
                            {d.post_percentage !== null ? `${d.post_percentage}%` : "—"}
                          </td>
                          <td className="px-4 py-2 text-right">
                            {d.delta_percentage !== null ? (
                              <StatusBadge
                                label={`${d.delta_percentage > 0 ? "+" : ""}${d.delta_percentage}%`}
                                tone={
                                  d.delta_percentage > 0
                                    ? "success"
                                    : d.delta_percentage < 0
                                      ? "danger"
                                      : "neutral"
                                }
                              />
                            ) : (
                              "—"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <DataTable
              columns={studentColumns}
              rows={data.student_trajectories}
              rowKey={(r) => r.student_id}
              emptyTitle="No comparable student pairs yet"
              emptyDescription="Students must complete both a baseline and follow-up assessment to compute trajectories."
            />
          </>
        ) : null}
      </div>
    </AppShell>
  );
};

