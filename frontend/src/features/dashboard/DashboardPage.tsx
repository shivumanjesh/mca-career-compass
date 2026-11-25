import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Building2, GraduationCap, ShieldCheck, Users } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../app/AuthContext";
import { parseApiError } from "../../services/apiClient";
import { fetchDashboardSummary } from "../../services/tenancyService";
import type { DashboardSummaryResponse } from "../../types/tenancy";

export const DashboardPage: React.FC = () => {
  const { auth, hasPermission } = useAuth();
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchDashboardSummary()
      .then((data) => {
        if (active) {
          setSummary(data);
          setError(null);
        }
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
  }, [auth?.active_institution?.id]);

  return (
    <AppShell title="Workspace Overview">
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[#0F2942]">
              Welcome, {auth?.user.full_name}
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              {auth?.active_institution
                ? `Active Institution: ${auth.active_institution.name} (${auth.active_institution.code})`
                : "Platform Super Administration Console"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {hasPermission("platform.institution.manage") && (
              <Link
                to="/platform/institutions"
                className="rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white transition"
              >
                Manage Institutions
              </Link>
            )}
            {hasPermission("institution.user.manage") && (
              <Link
                to="/institution/users"
                className="rounded-lg bg-[#0D9488] hover:bg-teal-700 px-4 py-2 text-sm font-medium text-white transition"
              >
                Manage Users & Roles
              </Link>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Loading live metrics...
          </div>
        ) : summary?.scope === "platform" ? (
          <>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={<Building2 className="h-4 w-4 text-[#0D9488]" />}
                label="Total Institutions"
                value={summary.metrics.total_institutions}
              />
              <StatCard
                icon={<ShieldCheck className="h-4 w-4 text-emerald-600" />}
                label="Active Institutions"
                value={summary.metrics.active_institutions}
              />
              <StatCard
                icon={<Users className="h-4 w-4 text-blue-700" />}
                label="Global User Accounts"
                value={summary.metrics.total_users}
              />
              <StatCard
                icon={<Activity className="h-4 w-4 text-slate-600" />}
                label="Audit Events"
                value={summary.metrics.total_audit_events}
              />
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[#0F2942]">Recent Institutions</h3>
                <Link to="/platform/institutions" className="text-xs font-medium text-blue-700 hover:underline">
                  View all →
                </Link>
              </div>
              {summary.recent_institutions.length === 0 ? (
                <p className="text-sm text-slate-500">No institutions registered yet.</p>
              ) : (
                <div className="divide-y divide-slate-100">
                  {summary.recent_institutions.map((inst) => (
                    <div key={inst.id} className="py-3 flex items-center justify-between text-sm">
                      <div>
                        <span className="font-semibold text-[#0F2942]">{inst.name}</span>
                        <span className="ml-2 text-xs text-slate-500">({inst.code})</span>
                      </div>
                      <StatusBadge
                        label={inst.status}
                        tone={inst.status === "active" ? "success" : "warning"}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : summary?.scope === "institution" ? (
          <>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={<Users className="h-4 w-4 text-[#0D9488]" />}
                label="Active Members"
                value={summary.metrics.active_members}
                subtitle={`${summary.metrics.total_members} total memberships`}
              />
              <StatCard
                icon={<GraduationCap className="h-4 w-4 text-blue-700" />}
                label="Students"
                value={summary.metrics.student_count}
              />
              <StatCard
                icon={<ShieldCheck className="h-4 w-4 text-indigo-700" />}
                label="Faculty Profiles"
                value={summary.metrics.faculty_count}
              />
              <StatCard
                icon={<Activity className="h-4 w-4 text-slate-600" />}
                label="Published Assessments"
                value={summary.metrics.published_version_count ?? 0}
                subtitle={`${summary.metrics.question_count ?? 0} questions • ${summary.metrics.dimension_count ?? 0} dimensions`}
              />
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
              <h3 className="text-sm font-semibold text-[#0F2942]">Role Distribution</h3>
              {Object.keys(summary.role_breakdown).length === 0 ? (
                <p className="text-sm text-slate-500">No role assignments recorded yet.</p>
              ) : (
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {Object.entries(summary.role_breakdown).map(([roleCode, total]) => (
                    <div key={roleCode} className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
                      <div className="text-xs font-medium text-slate-500">
                        {roleCode.replaceAll("_", " ")}
                      </div>
                      <div className="text-xl font-bold text-[#0F2942] mt-1">{total}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : summary?.scope === "faculty" ? (
          <>
            <div className="grid sm:grid-cols-3 gap-4">
              <StatCard
                icon={<Building2 className="h-4 w-4 text-[#0D9488]" />}
                label="Assigned Cohorts"
                value={summary.metrics.assigned_cohorts}
              />
              <StatCard
                icon={<GraduationCap className="h-4 w-4 text-blue-700" />}
                label="Assigned Students"
                value={summary.metrics.assigned_students}
              />
              <StatCard
                icon={<Activity className="h-4 w-4 text-amber-600" />}
                label="Pending Evaluations"
                value={summary.metrics.pending_evaluations ?? 0}
              />
            </div>
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[#0F2942]">My Assigned Cohorts</h3>
                <Link to="/students" className="text-xs font-medium text-blue-700 hover:underline">
                  View Assigned Students →
                </Link>
              </div>
              {summary.cohorts.length === 0 ? (
                <p className="text-sm text-slate-500">No cohorts are currently assigned to your faculty profile.</p>
              ) : (
                <div className="divide-y divide-slate-100">
                  {summary.cohorts.map((c) => (
                    <div key={c.cohort_id} className="py-3 flex items-center justify-between text-sm">
                      <div>
                        <span className="font-semibold text-[#0F2942]">{c.cohort_label}</span>
                        <span className="ml-2 text-xs text-slate-500 uppercase">({c.assignment_type})</span>
                      </div>
                      <StatusBadge label={`${c.student_count} students`} tone="neutral" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : summary?.scope === "student" ? (
          <div className="space-y-5">
            {summary.metrics && (
              <div className="grid sm:grid-cols-2 gap-4">
                <StatCard
                  icon={<Building2 className="h-4 w-4 text-[#0D9488]" />}
                  label="Assigned Assessments"
                  value={summary.metrics.assigned_assessments}
                />
                <StatCard
                  icon={<GraduationCap className="h-4 w-4 text-blue-700" />}
                  label="Completed Attempts"
                  value={summary.metrics.completed_attempts}
                />
              </div>
            )}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[#0F2942]">My Academic Profile</h3>
                <Link to="/my-assessments" className="text-xs font-medium text-blue-700 hover:underline">
                  Go to My Assessments →
                </Link>
              </div>
            {summary.student_profile ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-xs text-slate-500">Registration No.</div>
                  <div className="font-mono font-semibold text-[#0F2942] mt-0.5">
                    {summary.student_profile.registration_no}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Programme</div>
                  <div className="font-medium text-slate-800 mt-0.5">
                    {summary.student_profile.programme || "Unassigned"}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Cohort</div>
                  <div className="font-medium text-slate-800 mt-0.5">
                    {summary.student_profile.cohort || "Unassigned"}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Status</div>
                  <div className="mt-0.5">
                    <StatusBadge
                      label={summary.student_profile.status}
                      tone={summary.student_profile.status === "active" ? "success" : "warning"}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Your student profile is pending academic cohort assignment.</p>
            )}
            </div>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
};

const StatCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number;
  subtitle?: string;
}> = ({ icon, label, value, subtitle }) => (
  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
      {icon}
      <span>{label}</span>
    </div>
    <div className="text-2xl font-bold text-[#0F2942]">{value}</div>
    {subtitle && <div className="text-xs text-slate-500">{subtitle}</div>}
  </div>
);
