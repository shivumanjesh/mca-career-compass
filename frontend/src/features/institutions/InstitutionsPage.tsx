import React, { useCallback, useEffect, useState } from "react";
import { Building2, Copy, Plus, Search, UserPlus } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  createInstitution,
  createInstitutionAdmin,
  listInstitutionAdmins,
  listInstitutions,
  updateInstitution,
} from "../../services/tenancyService";
import type {
  InstitutionRecord,
  InstitutionStatus,
  MembershipUserRecord,
} from "../../types/tenancy";

const STATUS_TONE: Record<InstitutionStatus, "success" | "warning" | "danger"> = {
  active: "success",
  inactive: "warning",
  suspended: "danger",
};

export const InstitutionsPage: React.FC = () => {
  const [rows, setRows] = useState<InstitutionRecord[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create/Edit Institution Modal
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<InstitutionRecord | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [status, setStatus] = useState<InstitutionStatus>("active");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Manage Institution Admins Modal
  const [adminTarget, setAdminTarget] = useState<InstitutionRecord | null>(null);
  const [admins, setAdmins] = useState<MembershipUserRecord[]>([]);
  const [adminsLoading, setAdminsLoading] = useState(false);
  const [adminEmail, setAdminEmail] = useState("");
  const [adminFirst, setAdminFirst] = useState("");
  const [adminLast, setAdminLast] = useState("");
  const [adminSaving, setAdminSaving] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [onboardingPath, setOnboardingPath] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadInstitutions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listInstitutions({
        page,
        search: search.trim() || undefined,
        status: statusFilter || undefined,
      });
      setRows(res.results);
      setCount(res.count);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    loadInstitutions();
  }, [loadInstitutions]);

  const openCreate = () => {
    setEditing(null);
    setCode("");
    setName("");
    setTimezone("Asia/Kolkata");
    setStatus("active");
    setFormError(null);
    setFormOpen(true);
  };

  const openEdit = (inst: InstitutionRecord) => {
    setEditing(inst);
    setCode(inst.code);
    setName(inst.name);
    setTimezone(inst.timezone);
    setStatus(inst.status);
    setFormError(null);
    setFormOpen(true);
  };

  const handleSaveInstitution = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      if (editing) {
        await updateInstitution(editing.id, { code, name, timezone, status });
      } else {
        await createInstitution({ code, name, timezone, status });
      }
      setFormOpen(false);
      await loadInstitutions();
    } catch (err) {
      setFormError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleStatus = async (inst: InstitutionRecord) => {
    const nextStatus: InstitutionStatus = inst.status === "active" ? "inactive" : "active";
    try {
      await updateInstitution(inst.id, { status: nextStatus });
      await loadInstitutions();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const openAdminsModal = async (inst: InstitutionRecord) => {
    setAdminTarget(inst);
    setAdminEmail("");
    setAdminFirst("");
    setAdminLast("");
    setAdminError(null);
    setOnboardingPath(null);
    setCopied(false);
    setAdminsLoading(true);
    try {
      const res = await listInstitutionAdmins(inst.id);
      setAdmins(res.results);
    } catch (err) {
      setAdminError(parseApiError(err).message);
    } finally {
      setAdminsLoading(false);
    }
  };

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminTarget) return;
    setAdminSaving(true);
    setAdminError(null);
    setOnboardingPath(null);
    setCopied(false);
    try {
      const created = await createInstitutionAdmin(adminTarget.id, {
        email: adminEmail.trim(),
        first_name: adminFirst.trim(),
        last_name: adminLast.trim(),
      });
      if (created.onboarding_reset_path) {
        setOnboardingPath(`${window.location.origin}${created.onboarding_reset_path}`);
      }
      setAdminEmail("");
      setAdminFirst("");
      setAdminLast("");
      const refreshed = await listInstitutionAdmins(adminTarget.id);
      setAdmins(refreshed.results);
      await loadInstitutions();
    } catch (err) {
      setAdminError(parseApiError(err).message);
    } finally {
      setAdminSaving(false);
    }
  };

  const columns: ColumnDef<InstitutionRecord>[] = [
    {
      key: "code",
      header: "Institution",
      render: (row) => (
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-slate-100 text-[#0F2942] flex items-center justify-center font-semibold text-xs">
            <Building2 className="h-4 w-4" />
          </div>
          <div>
            <div className="font-semibold text-[#0F2942]">{row.name}</div>
            <div className="text-xs text-slate-500">Code: {row.code}</div>
          </div>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge label={row.status} tone={STATUS_TONE[row.status]} />,
    },
    {
      key: "timezone",
      header: "Timezone",
      render: (row) => <span className="text-slate-600 text-xs">{row.timezone}</span>,
    },
    {
      key: "counts",
      header: "Members / Admins",
      render: (row) => (
        <span className="text-slate-700 text-xs font-medium">
          {row.member_count} members • {row.admin_count} admins
        </span>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      className: "text-right",
      render: (row) => (
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => openAdminsModal(row)}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <UserPlus className="h-3.5 w-3.5 text-[#0D9488]" />
            Admins
          </button>
          <button
            type="button"
            onClick={() => openEdit(row)}
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => handleToggleStatus(row)}
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            {row.status === "active" ? "Deactivate" : "Activate"}
          </button>
        </div>
      ),
    },
  ];

  return (
    <AppShell title="Institution Management">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                placeholder="Search code or name..."
                className="pl-9 pr-3 py-2 rounded-lg border border-slate-300 bg-white text-sm w-64 focus:border-blue-600 focus:outline-none"
              />
            </div>
            <select
              aria-label="Filter by status"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
            </select>
          </div>

          <button
            type="button"
            onClick={openCreate}
            className="inline-flex items-center gap-2 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white transition"
          >
            <Plus className="h-4 w-4" />
            New Institution
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(r) => r.id}
          loading={loading}
          page={page}
          totalCount={count}
          onPageChange={setPage}
          emptyTitle="No institutions created yet"
          emptyDescription="Create your first participating institution to begin onboarding."
        />
      </div>

      {/* Create / Edit Institution Modal */}
      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `Edit ${editing.code}` : "Create Institution"}
        subtitle="Institutions maintain strictly isolated student, faculty, and assessment records."
      >
        <form className="space-y-4" onSubmit={handleSaveInstitution}>
          {formError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {formError}
            </div>
          )}
          <div>
            <label htmlFor="inst-code" className="block text-xs font-medium text-slate-700">
              Institution Code
            </label>
            <input
              id="inst-code"
              type="text"
              required
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="e.g. MITT"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
            />
          </div>
          <div>
            <label htmlFor="inst-name" className="block text-xs font-medium text-slate-700">
              Institution Name
            </label>
            <input
              id="inst-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Maharaja Institute of Technology Thandavapura"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="inst-tz" className="block text-xs font-medium text-slate-700">
                Timezone
              </label>
              <input
                id="inst-tz"
                type="text"
                required
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="inst-status" className="block text-xs font-medium text-slate-700">
                Status
              </label>
              <select
                id="inst-status"
                value={status}
                onChange={(e) => setStatus(e.target.value as InstitutionStatus)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setFormOpen(false)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-4 py-2 text-sm font-medium text-white"
            >
              {saving ? "Saving..." : editing ? "Save Changes" : "Create Institution"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Provision & List Institution Admins Modal */}
      <Modal
        open={Boolean(adminTarget)}
        onClose={() => setAdminTarget(null)}
        title={adminTarget ? `Institution Admins — ${adminTarget.code}` : "Institution Admins"}
        subtitle="Provision Institution Administrators with an onboarding password-setup link."
      >
        <div className="space-y-5">
          {adminError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {adminError}
            </div>
          )}

          {onboardingPath && (
            <div className="rounded-lg border border-teal-200 bg-teal-50 p-3.5 space-y-2">
              <div className="text-xs font-semibold text-teal-900">
                One-Time Password Setup Link (share securely; not stored in database)
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={onboardingPath}
                  className="flex-1 rounded border border-teal-300 bg-white px-2.5 py-1.5 text-xs font-mono text-slate-700"
                />
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(onboardingPath);
                    setCopied(true);
                  }}
                  className="inline-flex items-center gap-1 rounded bg-[#0D9488] px-2.5 py-1.5 text-xs font-medium text-white"
                >
                  <Copy className="h-3.5 w-3.5" />
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
            </div>
          )}

          <form className="space-y-3 border-b border-slate-200 pb-4" onSubmit={handleCreateAdmin}>
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Add Institution Admin
            </div>
            <div>
              <input
                type="email"
                required
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                placeholder="admin@institution.edu"
                className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                required
                value={adminFirst}
                onChange={(e) => setAdminFirst(e.target.value)}
                placeholder="First Name"
                className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                type="text"
                value={adminLast}
                onChange={(e) => setAdminLast(e.target.value)}
                placeholder="Last Name"
                className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={adminSaving}
              className="w-full rounded-lg bg-[#0D9488] hover:bg-teal-700 disabled:opacity-50 px-4 py-2 text-sm font-medium text-white"
            >
              {adminSaving ? "Provisioning..." : "Create Institution Admin"}
            </button>
          </form>

          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Existing Administrators ({admins.length})
            </div>
            {adminsLoading ? (
              <p className="text-xs text-slate-500">Loading admins...</p>
            ) : admins.length === 0 ? (
              <p className="text-xs text-slate-500">No institution administrators assigned yet.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {admins.map((a) => (
                  <li key={a.id} className="py-2 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-medium text-slate-800">{a.full_name}</div>
                      <div className="text-slate-500">{a.email}</div>
                    </div>
                    <StatusBadge
                      label={a.status}
                      tone={a.status === "active" ? "success" : "warning"}
                    />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </Modal>
    </AppShell>
  );
};

