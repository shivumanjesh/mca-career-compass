import React, { useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Compass, ShieldCheck, GraduationCap, ServerCrash, CheckCircle2 } from "lucide-react";
import { AuthProvider } from "./AuthContext";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { StatusBadge } from "../components/StatusBadge";
import { LoginPage } from "../features/auth/LoginPage";
import { ResetPasswordPage } from "../features/auth/ResetPasswordPage";
import { AccountSecurityPage } from "../features/auth/AccountSecurityPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { InstitutionsPage } from "../features/institutions/InstitutionsPage";
import { InstitutionProfilePage } from "../features/institutions/InstitutionProfilePage";
import { UsersPage } from "../features/users/UsersPage";
import { AcademicsPage } from "../features/academics/AcademicsPage";
import { StudentsPage } from "../features/students/StudentsPage";
import { BulkImportPage } from "../features/imports/BulkImportPage";
import { FacultyPage } from "../features/faculty/FacultyPage";
import { AuditLogsPage } from "../features/audit/AuditLogsPage";
import { DimensionsPage } from "../features/assessments/DimensionsPage";
import { QuestionBankPage } from "../features/assessments/QuestionBankPage";
import { AssessmentBuilderPage } from "../features/assessments/AssessmentBuilderPage";
import { AssignmentsPage } from "../features/assessments/AssignmentsPage";
import { MyAssessmentsPage } from "../features/attempts/MyAssessmentsPage";
import { TestRunnerPage } from "../features/attempts/TestRunnerPage";
import { EvaluationQueuePage } from "../features/attempts/EvaluationQueuePage";
import { CohortAnalyticsPage } from "../features/analytics/CohortAnalyticsPage";
import { MyResultsPage } from "../features/analytics/MyResultsPage";
import { CataloguePage } from "../features/development/CataloguePage";
import { EmpowermentPage } from "../features/development/EmpowermentPage";
import { StudentPlansPage } from "../features/development/StudentPlansPage";
import { ExecutiveReportPage } from "../features/intelligence/ExecutiveReportPage";
import { IntelligenceDashboardPage } from "../features/intelligence/IntelligenceDashboardPage";
import { PrePostComparisonPage } from "../features/intelligence/PrePostComparisonPage";
import { apiClient, parseApiError } from "../services/apiClient";
import type { HealthCheckResponse } from "../types/api";

const PlatformLanding: React.FC = () => {
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let active = true;
    apiClient
      .get<HealthCheckResponse>("/health/")
      .then((res) => {
        if (active) {
          setHealth(res.data);
          setErrorMessage(null);
        }
      })
      .catch((err) => {
        if (active) {
          setErrorMessage(parseApiError(err).message);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="bg-[#0F2942] text-white border-b border-slate-800">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-[#0D9488] flex items-center justify-center">
              <Compass className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight">MCA Career Compass</h1>
              <p className="text-xs text-slate-300">Institutional Student Talent Mapping & Empowerment</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="rounded-md bg-white/10 hover:bg-white/20 px-3.5 py-2 text-sm font-medium transition"
            >
              Student & Faculty Login
            </Link>
            <Link
              to="/admin/login"
              className="rounded-md bg-[#0D9488] hover:bg-teal-600 px-3.5 py-2 text-sm font-medium transition"
            >
              Admin Portal
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 space-y-8">
        <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-2xl space-y-3">
              <StatusBadge label="Phase 1 Foundation" tone="neutral" />
              <h2 className="text-2xl font-bold text-[#0F2942]">
                Evidence-Based MCA Talent Mapping & Development Platform
              </h2>
              <p className="text-slate-600 text-sm leading-relaxed">
                Multi-institution architecture with strict tenant isolation, role-based access control,
                academic batch management, staged student spreadsheet imports, and immutable audit trails.
              </p>
            </div>

            <div className="min-w-[260px] rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Live API Health Check
              </div>
              {loading ? (
                <p className="text-sm text-slate-500">Checking backend connectivity...</p>
              ) : health ? (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-sm font-medium text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>API: {health.status.toUpperCase()}</span>
                  </div>
                  <p className="text-xs text-slate-600">
                    Database: <span className="font-medium">{health.database}</span>
                  </p>
                </div>
              ) : (
                <div className="flex items-start gap-2 text-xs text-rose-700">
                  <ServerCrash className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{errorMessage || "Backend unreachable"}</span>
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
            <div className="h-10 w-10 rounded-lg bg-blue-50 text-[#1E3A5F] flex items-center justify-center">
              <GraduationCap className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-[#0F2942]">Academic Portal (/login)</h3>
            <p className="text-sm text-slate-600">
              Dedicated sign-in for MCA Students and Faculty / HOD members scoped to their institution.
            </p>
            <Link
              to="/login"
              className="inline-flex items-center text-sm font-medium text-blue-700 hover:text-blue-800"
            >
              Go to Student & Faculty Login →
            </Link>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
            <div className="h-10 w-10 rounded-lg bg-teal-50 text-[#0D9488] flex items-center justify-center">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-[#0F2942]">Administration Portal (/admin/login)</h3>
            <p className="text-sm text-slate-600">
              Dedicated sign-in for Platform Super Admins, Institution Admins, and Assessment Admins.
            </p>
            <Link
              to="/admin/login"
              className="inline-flex items-center text-sm font-medium text-teal-700 hover:text-teal-800"
            >
              Go to Admin Portal →
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PlatformLanding />} />
          <Route path="/login" element={<LoginPage key="academic" portal="academic" />} />
          <Route path="/admin/login" element={<LoginPage key="admin" portal="admin" />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/platform/institutions"
            element={
              <ProtectedRoute requiredPermission="platform.institution.manage" loginPath="/admin/login">
                <InstitutionsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/institution/profile"
            element={
              <ProtectedRoute requiredPermission="institution.profile.manage" loginPath="/admin/login">
                <InstitutionProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/institution/users"
            element={
              <ProtectedRoute requiredPermission="institution.user.manage" loginPath="/admin/login">
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/academics"
            element={
              <ProtectedRoute requiredPermission="academics.cohort.manage" loginPath="/admin/login">
                <AcademicsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/students"
            element={
              <ProtectedRoute requiredAnyPermissions={["institution.student.manage", "student.assigned.view"]}>
                <StudentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/students/import"
            element={
              <ProtectedRoute requiredPermission="institution.student.import" loginPath="/admin/login">
                <BulkImportPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/faculty"
            element={
              <ProtectedRoute requiredPermission="institution.faculty.manage" loginPath="/admin/login">
                <FacultyPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assessments/dimensions"
            element={
              <ProtectedRoute requiredPermission="assessment.dimension.manage" loginPath="/admin/login">
                <DimensionsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assessments/questions"
            element={
              <ProtectedRoute requiredPermission="assessment.question.manage" loginPath="/admin/login">
                <QuestionBankPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assessments/templates"
            element={
              <ProtectedRoute requiredPermission="assessment.template.manage" loginPath="/admin/login">
                <AssessmentBuilderPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assessments/assignments"
            element={
              <ProtectedRoute requiredPermission="assessment.assign" loginPath="/admin/login">
                <AssignmentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/evaluations"
            element={
              <ProtectedRoute requiredPermission="assessment.response.evaluate">
                <EvaluationQueuePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-assessments"
            element={
              <ProtectedRoute requiredPermission="assessment.attempt.take">
                <MyAssessmentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-assessments/attempt/:attemptId"
            element={
              <ProtectedRoute requiredPermission="assessment.attempt.take">
                <TestRunnerPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-results"
            element={
              <ProtectedRoute requiredPermission="results.self.view">
                <MyResultsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute requiredAnyPermissions={["analytics.cohort.view", "results.cohort.view"]}>
                <CohortAnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/development/catalogue"
            element={
              <ProtectedRoute requiredPermission="development.catalogue.manage" loginPath="/admin/login">
                <CataloguePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/development/plans"
            element={
              <ProtectedRoute requiredPermission="development.plan.manage">
                <StudentPlansPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-empowerment"
            element={
              <ProtectedRoute requiredPermission="development.self.manage">
                <EmpowermentPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/intelligence"
            element={
              <ProtectedRoute requiredPermission="intelligence.faculty.view">
                <IntelligenceDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/pre-post"
            element={
              <ProtectedRoute requiredAnyPermissions={["intelligence.faculty.view", "analytics.executive.view"]}>
                <PrePostComparisonPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/executive-reports"
            element={
              <ProtectedRoute requiredPermission="analytics.executive.view" loginPath="/admin/login">
                <ExecutiveReportPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit"
            element={
              <ProtectedRoute
                requiredAnyPermissions={["audit.platform.view", "audit.institution.view"]}
                loginPath="/admin/login"
              >
                <AuditLogsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/account/security"
            element={
              <ProtectedRoute>
                <AccountSecurityPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
