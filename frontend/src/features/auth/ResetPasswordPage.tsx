import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { KeyRound } from "lucide-react";
import { confirmPasswordReset } from "../../services/authService";
import { parseApiError } from "../../services/apiClient";

export const ResetPasswordPage: React.FC = () => {
  const [params] = useSearchParams();
  const uid = params.get("uid") || "";
  const token = params.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    try {
      const detail = await confirmPasswordReset(uid, token, newPassword);
      setMessage(detail);
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-xl border border-slate-200 shadow-sm p-8 space-y-5">
        <div className="flex items-center gap-2.5">
          <KeyRound className="h-5 w-5 text-[#0D9488]" />
          <h1 className="text-lg font-bold text-[#0F2942]">Set / Reset Password</h1>
        </div>

        {!uid || !token ? (
          <div className="text-sm text-rose-700">
            Missing password reset token parameters. Request a fresh link from the login page.
          </div>
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {error}
              </div>
            )}
            {message && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                {message}
              </div>
            )}
            <div>
              <label htmlFor="new-pw" className="block text-xs font-medium text-slate-700">
                New Password (minimum 10 characters)
              </label>
              <input
                id="new-pw"
                type="password"
                required
                minLength={10}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="confirm-pw" className="block text-xs font-medium text-slate-700">
                Confirm New Password
              </label>
              <input
                id="confirm-pw"
                type="password"
                required
                minLength={10}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-4 py-2.5 text-sm font-medium text-white"
            >
              {submitting ? "Updating..." : "Update Password"}
            </button>
          </form>
        )}

        <div className="flex justify-between text-xs pt-2 border-t border-slate-100">
          <Link to="/login" className="text-blue-700 hover:underline">
            Student / Faculty Login
          </Link>
          <Link to="/admin/login" className="text-blue-700 hover:underline">
            Admin Login
          </Link>
        </div>
      </div>
    </div>
  );
};

