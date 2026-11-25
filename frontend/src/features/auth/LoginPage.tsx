import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Compass, GraduationCap, ShieldCheck } from "lucide-react";
import { useAuth } from "../../app/AuthContext";
import { parseApiError } from "../../services/apiClient";
import { requestPasswordReset } from "../../services/authService";
import type { LoginPortal } from "../../types/auth";

interface LoginPageProps {
  portal: LoginPortal;
}

export const LoginPage: React.FC<LoginPageProps> = ({ portal }) => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const isAdminPortal = portal === "admin";

  const [institutionCode, setInstitutionCode] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showReset, setShowReset] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetNotice, setResetNotice] = useState<string | null>(null);
  const [resetLoading, setResetLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const me = await login({
        portal,
        identifier: identifier.trim(),
        password,
        institution_code: institutionCode.trim() || undefined,
      });
      if (me.user.must_change_password) {
        navigate("/account/security", { replace: true });
      } else {
        navigate("/dashboard", { replace: true });
      }
    } catch (err) {
      const parsed = parseApiError(err);
      setError(parsed.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetLoading(true);
    setResetNotice(null);
    try {
      const msg = await requestPasswordReset(resetEmail.trim());
      setResetNotice(msg);
    } catch (err) {
      setResetNotice(parseApiError(err).message);
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md space-y-3 text-center">
        <Link to="/" className="inline-flex items-center gap-2.5 justify-center">
          <div className="h-10 w-10 rounded-xl bg-[#0F2942] flex items-center justify-center">
            <Compass className="h-5 w-5 text-[#0D9488]" />
          </div>
          <span className="text-xl font-bold text-[#0F2942]">MCA Career Compass</span>
        </Link>
        <div className="flex items-center justify-center gap-2 text-sm font-medium text-slate-600">
          {isAdminPortal ? (
            <>
              <ShieldCheck className="h-4 w-4 text-[#0D9488]" />
              <span>Administration Portal</span>
            </>
          ) : (
            <>
              <GraduationCap className="h-4 w-4 text-blue-700" />
              <span>Faculty & Student Portal</span>
            </>
          )}
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm rounded-xl border border-slate-200 sm:px-8 space-y-6">
          <div>
            <h1 className="text-lg font-semibold text-[#0F2942]">
              {isAdminPortal ? "Administrative Sign In" : "Academic Sign In"}
            </h1>
            <p className="mt-1 text-xs text-slate-500">
              {isAdminPortal
                ? "For Platform Super Admins, Institution Admins, and Assessment Admins."
                : "For MCA Students and Faculty / HOD members."}
            </p>
          </div>

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700">
              {error}
            </div>
          )}

          {!showReset ? (
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="institution-code" className="block text-xs font-medium text-slate-700">
                  Institution Code {isAdminPortal ? "(leave blank for Platform Super Admin)" : ""}
                </label>
                <input
                  id="institution-code"
                  type="text"
                  value={institutionCode}
                  onChange={(e) => setInstitutionCode(e.target.value)}
                  placeholder="e.g. MITT"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
              </div>

              <div>
                <label htmlFor="identifier" className="block text-xs font-medium text-slate-700">
                  {isAdminPortal ? "Email Address" : "Email Address or Registration No."}
                </label>
                <input
                  id="identifier"
                  type="text"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder={isAdminPortal ? "admin@institution.edu" : "student@institution.edu or 4MT24MC001"}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-xs font-medium text-slate-700">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
              </div>

              <div className="flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={() => setShowReset(true)}
                  className="font-medium text-blue-700 hover:text-blue-800"
                >
                  Forgot password?
                </button>
                <Link
                  to={isAdminPortal ? "/login" : "/admin/login"}
                  className="text-slate-500 hover:text-slate-700"
                >
                  {isAdminPortal ? "Student/Faculty login →" : "Admin portal →"}
                </Link>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-4 py-2.5 text-sm font-medium text-white transition"
              >
                {submitting ? "Signing in..." : "Sign In"}
              </button>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={handleResetRequest}>
              <div>
                <label htmlFor="reset-email" className="block text-xs font-medium text-slate-700">
                  Registered Email Address
                </label>
                <input
                  id="reset-email"
                  type="email"
                  required
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  placeholder="user@institution.edu"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
              </div>
              {resetNotice && (
                <div className="rounded-lg border border-teal-200 bg-teal-50 px-3.5 py-2.5 text-xs text-teal-800">
                  {resetNotice}
                </div>
              )}
              <div className="flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowReset(false);
                    setResetNotice(null);
                  }}
                  className="text-xs font-medium text-slate-600 hover:text-slate-800"
                >
                  ← Back to Sign In
                </button>
                <button
                  type="submit"
                  disabled={resetLoading}
                  className="rounded-lg bg-[#0D9488] hover:bg-teal-700 disabled:opacity-50 px-4 py-2 text-sm font-medium text-white transition"
                >
                  {resetLoading ? "Sending..." : "Request Reset"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

