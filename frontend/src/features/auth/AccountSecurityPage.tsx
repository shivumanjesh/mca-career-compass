import React, { useState } from "react";
import { AppShell } from "../../components/AppShell";
import { useAuth } from "../../app/AuthContext";
import { changePassword } from "../../services/authService";
import { parseApiError } from "../../services/apiClient";

export const AccountSecurityPage: React.FC = () => {
  const { auth, refreshAuth } = useAuth();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }
    setSaving(true);
    try {
      await changePassword(oldPassword, newPassword);
      await refreshAuth();
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess("Your password has been updated.");
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell title="Account & Password">
      <div className="max-w-xl bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div>
          <h2 className="text-base font-semibold text-[#0F2942]">Change Password</h2>
          <p className="text-xs text-slate-500 mt-1">
            Signed in as <span className="font-medium text-slate-700">{auth?.user.email}</span>.
          </p>
        </div>

        {auth?.user.must_change_password && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
            Please update your temporary password before continuing.
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}
        {success && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-700">
            {success}
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="old-pw" className="block text-xs font-medium text-slate-700">
              Current Password
            </label>
            <input
              id="old-pw"
              type="password"
              required
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
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
            disabled={saving}
            className="rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-4 py-2 text-sm font-medium text-white"
          >
            {saving ? "Saving..." : "Update Password"}
          </button>
        </form>
      </div>
    </AppShell>
  );
};

