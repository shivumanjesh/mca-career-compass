import React, { useEffect, useState } from "react";
import { Building2 } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import { fetchInstitutionProfile, updateInstitutionProfile } from "../../services/tenancyService";
import type { InstitutionRecord } from "../../types/tenancy";
import { useAuth } from "../../app/AuthContext";

export const InstitutionProfilePage: React.FC = () => {
  const { refreshAuth } = useAuth();
  const [profile, setProfile] = useState<InstitutionRecord | null>(null);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [contactEmail, setContactEmail] = useState("");
  const [website, setWebsite] = useState("");
  const [city, setCity] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedNotice, setSavedNotice] = useState<string | null>(null);

  useEffect(() => {
    fetchInstitutionProfile()
      .then((data) => {
        setProfile(data);
        setName(data.name);
        setTimezone(data.timezone);
        setContactEmail(String(data.settings?.contact_email || ""));
        setWebsite(String(data.settings?.website || ""));
        setCity(String(data.settings?.city || ""));
      })
      .catch((err) => setError(parseApiError(err).message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSavedNotice(null);
    try {
      const updated = await updateInstitutionProfile({
        name: name.trim(),
        timezone: timezone.trim(),
        settings: {
          ...(profile?.settings || {}),
          contact_email: contactEmail.trim(),
          website: website.trim(),
          city: city.trim(),
        },
      });
      setProfile(updated);
      await refreshAuth();
      setSavedNotice("Institution profile updated.");
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell title="Institution Profile">
      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
          Loading institution profile...
        </div>
      ) : (
        <div className="max-w-2xl bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-[#0F2942] text-white flex items-center justify-center">
                <Building2 className="h-5 w-5 text-[#0D9488]" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-[#0F2942]">{profile?.name}</h2>
                <p className="text-xs text-slate-500">
                  Code: <strong>{profile?.code}</strong> • {profile?.member_count ?? 0} total members
                </p>
              </div>
            </div>
            {profile && (
              <StatusBadge
                label={profile.status}
                tone={profile.status === "active" ? "success" : "warning"}
              />
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
              {error}
            </div>
          )}
          {savedNotice && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-700">
              {savedNotice}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSave}>
            <div>
              <label htmlFor="profile-name" className="block text-xs font-medium text-slate-700">
                Institution Display Name
              </label>
              <input
                id="profile-name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="profile-tz" className="block text-xs font-medium text-slate-700">
                  Timezone
                </label>
                <input
                  id="profile-tz"
                  type="text"
                  required
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label htmlFor="profile-city" className="block text-xs font-medium text-slate-700">
                  City / Campus Location
                </label>
                <input
                  id="profile-city"
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="e.g. Mysuru / Thandavapura"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="profile-email" className="block text-xs font-medium text-slate-700">
                  Institutional Contact Email
                </label>
                <input
                  id="profile-email"
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  placeholder="mca-office@institution.edu"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label htmlFor="profile-web" className="block text-xs font-medium text-slate-700">
                  Website URL
                </label>
                <input
                  id="profile-web"
                  type="url"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  placeholder="https://institution.edu"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-5 py-2 text-sm font-medium text-white"
              >
                {saving ? "Saving..." : "Save Profile"}
              </button>
            </div>
          </form>
        </div>
      )}
    </AppShell>
  );
};

