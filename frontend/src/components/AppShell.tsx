import React, { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import {
  Activity,
  Award,
  BarChart3,
  BookOpen,
  Building2,
  Calendar,
  ClipboardCheck,
  Compass,
  FileCheck2,
  FileSpreadsheet,
  GitCompare,
  GraduationCap,
  HelpCircle,
  KeyRound,
  LayoutDashboard,
  Layers,
  LogOut,
  Menu,
  PlayCircle,
  Settings,
  Sparkles,
  TrendingUp,
  UserCheck,
  Users,
  X,
} from "lucide-react";
import { useAuth } from "../app/AuthContext";
import { StatusBadge } from "./StatusBadge";
import { parseApiError } from "../services/apiClient";

interface AppShellProps {
  title: string;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ title, children }) => {
  const { auth, logout, switchInstitution, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [switchError, setSwitchError] = useState<string | null>(null);

  const handleLogout = async () => {
    const isAdmin = Boolean(
      auth?.platform_roles.length ||
        auth?.active_roles.some((r) => r === "INSTITUTION_ADMIN" || r === "ASSESSMENT_ADMIN"),
    );
    await logout();
    navigate(isAdmin ? "/admin/login" : "/login", { replace: true });
  };

  const handleSwitchInstitution = async (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextId = event.target.value;
    if (!nextId) return;
    setSwitchError(null);
    try {
      await switchInstitution(nextId);
    } catch (err) {
      setSwitchError(parseApiError(err).message);
    }
  };

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive
        ? "bg-white/15 text-white"
        : "text-slate-300 hover:bg-white/10 hover:text-white"
    }`;

  const roles = [...(auth?.platform_roles ?? []), ...(auth?.active_roles ?? [])];

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-64 bg-[#0F2942] text-white flex flex-col transition-transform lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-[#0D9488] flex items-center justify-center">
              <Compass className="h-4 w-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-semibold leading-tight">MCA Career Compass</div>
              <div className="text-[11px] text-slate-300">Institutional Portal</div>
            </div>
          </Link>
          <button
            type="button"
            className="lg:hidden text-slate-300 hover:text-white"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <NavLink to="/dashboard" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
            <LayoutDashboard className="h-4 w-4" />
            <span>Overview</span>
          </NavLink>
          {hasPermission("platform.institution.manage") && (
            <NavLink to="/platform/institutions" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Building2 className="h-4 w-4" />
              <span>Institutions</span>
            </NavLink>
          )}
          {hasPermission("institution.profile.manage") && (
            <NavLink to="/institution/profile" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Settings className="h-4 w-4" />
              <span>Institution Profile</span>
            </NavLink>
          )}
          {hasPermission("institution.user.manage") && (
            <NavLink to="/institution/users" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Users className="h-4 w-4" />
              <span>Users & Roles</span>
            </NavLink>
          )}
          {hasPermission("academics.cohort.manage") && (
            <NavLink to="/academics" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <BookOpen className="h-4 w-4" />
              <span>Academic Structure</span>
            </NavLink>
          )}
          {(hasPermission("institution.student.manage") || hasPermission("student.assigned.view")) && (
            <NavLink to="/students" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <GraduationCap className="h-4 w-4" />
              <span>{hasPermission("institution.student.manage") ? "Students" : "Assigned Students"}</span>
            </NavLink>
          )}
          {hasPermission("institution.student.import") && (
            <NavLink to="/students/import" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <FileSpreadsheet className="h-4 w-4" />
              <span>Bulk Import</span>
            </NavLink>
          )}
          {hasPermission("institution.faculty.manage") && (
            <NavLink to="/faculty" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <UserCheck className="h-4 w-4" />
              <span>Faculty</span>
            </NavLink>
          )}
          {hasPermission("assessment.dimension.manage") && (
            <NavLink to="/assessments/dimensions" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Layers className="h-4 w-4" />
              <span>Dimensions</span>
            </NavLink>
          )}
          {hasPermission("assessment.question.manage") && (
            <NavLink to="/assessments/questions" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <HelpCircle className="h-4 w-4" />
              <span>Question Bank</span>
            </NavLink>
          )}
          {hasPermission("assessment.template.manage") && (
            <NavLink to="/assessments/templates" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <FileCheck2 className="h-4 w-4" />
              <span>Assessment Builder</span>
            </NavLink>
          )}
          {hasPermission("assessment.assign") && (
            <NavLink to="/assessments/assignments" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Calendar className="h-4 w-4" />
              <span>Assignments</span>
            </NavLink>
          )}
          {hasPermission("assessment.response.evaluate") && (
            <NavLink to="/evaluations" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <ClipboardCheck className="h-4 w-4" />
              <span>Evaluations</span>
            </NavLink>
          )}
          {hasPermission("assessment.attempt.take") && (
            <NavLink to="/my-assessments" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <PlayCircle className="h-4 w-4" />
              <span>My Assessments</span>
            </NavLink>
          )}
          {hasPermission("results.self.view") && (
            <NavLink to="/my-results" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Award className="h-4 w-4" />
              <span>My Results</span>
            </NavLink>
          )}
          {(hasPermission("analytics.cohort.view") || hasPermission("results.cohort.view")) && (
            <NavLink to="/analytics" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <BarChart3 className="h-4 w-4" />
              <span>Analytics & Reports</span>
            </NavLink>
          )}
          {hasPermission("development.catalogue.manage") && (
            <NavLink to="/development/catalogue" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <BookOpen className="h-4 w-4" />
              <span>Learning Catalogue</span>
            </NavLink>
          )}
          {hasPermission("development.plan.manage") && (
            <NavLink to="/development/plans" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <UserCheck className="h-4 w-4" />
              <span>Development Plans</span>
            </NavLink>
          )}
          {hasPermission("development.self.manage") && (
            <NavLink to="/my-empowerment" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Sparkles className="h-4 w-4" />
              <span>My Empowerment</span>
            </NavLink>
          )}
          {hasPermission("intelligence.faculty.view") && (
            <NavLink to="/intelligence" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <TrendingUp className="h-4 w-4" />
              <span>Faculty Intelligence</span>
            </NavLink>
          )}
          {(hasPermission("intelligence.faculty.view") || hasPermission("analytics.executive.view")) && (
            <NavLink to="/pre-post" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <GitCompare className="h-4 w-4" />
              <span>Pre / Post Comparison</span>
            </NavLink>
          )}
          {hasPermission("analytics.executive.view") && (
            <NavLink to="/executive-reports" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Building2 className="h-4 w-4" />
              <span>Executive Reports</span>
            </NavLink>
          )}
          {(hasPermission("audit.platform.view") || hasPermission("audit.institution.view")) && (
            <NavLink to="/audit" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
              <Activity className="h-4 w-4" />
              <span>Audit Logs</span>
            </NavLink>
          )}
          <NavLink to="/account/security" className={navLinkClass} onClick={() => setSidebarOpen(false)}>
            <KeyRound className="h-4 w-4" />
            <span>Account & Password</span>
          </NavLink>
        </nav>

        <div className="p-4 border-t border-white/10 space-y-2 text-xs text-slate-300">
          <div className="flex items-center gap-2 text-white font-medium truncate">
            <UserCheck className="h-4 w-4 text-[#0D9488] shrink-0" />
            <span className="truncate">{auth?.user.full_name}</span>
          </div>
          <div className="truncate text-slate-400">{auth?.user.email}</div>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-2 w-full flex items-center justify-center gap-2 rounded-md bg-white/10 hover:bg-white/20 px-3 py-2 text-xs font-medium text-white transition"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="lg:hidden rounded-md border border-slate-200 p-1.5 text-slate-600"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-lg font-semibold text-[#0F2942]">{title}</h1>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {auth?.active_institution ? (
              <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs">
                <Building2 className="h-3.5 w-3.5 text-[#0D9488]" />
                {auth.memberships.length > 1 ? (
                  <select
                    aria-label="Active institution"
                    value={auth.active_institution.id}
                    onChange={handleSwitchInstitution}
                    className="bg-transparent font-medium text-slate-800 focus:outline-none"
                  >
                    {auth.memberships.map((m) => (
                      <option key={m.institution_id} value={m.institution_id}>
                        {m.institution_code} — {m.institution_name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="font-medium text-slate-800">
                    {auth.active_institution.code} — {auth.active_institution.name}
                  </span>
                )}
              </div>
            ) : (
              <StatusBadge label="Platform Scope" tone="neutral" />
            )}

            <div className="flex items-center gap-1.5">
              {roles.map((r) => (
                <StatusBadge key={r} label={r.replaceAll("_", " ")} tone="success" />
              ))}
            </div>
          </div>
        </header>

        {switchError && (
          <div className="mx-6 mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {switchError}
          </div>
        )}

        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
};

