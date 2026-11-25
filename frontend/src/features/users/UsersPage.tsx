import React, { useCallback, useEffect, useState } from "react";
import { Copy, KeyRound, Plus, Search, Shield } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  createInstitutionUser,
  issueInstitutionUserResetLink,
  listInstitutionUsers,
  updateInstitutionUser,
  updateInstitutionUserRoles,
} from "../../services/tenancyService";
import type { RoleCode } from "../../types/auth";
import type { MembershipStatus, MembershipUserRecord } from "../../types/tenancy";

const INSTITUTION_ROLES: Array<{ code: RoleCode; label: string }> = [
  { code: "INSTITUTION_ADMIN", label: "Institution Admin" },
  { code: "ASSESSMENT_ADMIN", label: "Assessment Admin" },
  { code: "FACULTY_HOD", label: "Faculty / HOD" },
  { code: "STUDENT", label: "Student" },
];

export const UsersPage: React.FC = () => {
  const [rows, setRows] = useState<MembershipUserRecord[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create User Modal
  const [createOpen, setCreateOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<RoleCode[]>(["FACULTY_HOD"]);
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // One-time onboarding/reset link modal
  const [resetLinkModal, setResetLinkModal] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Role Assignment Modal
  const [roleTarget, setRoleTarget] = useState<MembershipUserRecord | null>(null);
  const [editRoles, setEditRoles] = useState<RoleCode[]>([]);

  // Edit User Modal
  const [editTarget, setEditTarget] = useState<MembershipUserRecord | null>(null);
  const [editFirst, setEditFirst] = useState("");
  const [editLast, setEditLast] = useState("");
  const [editStatus, setEditStatus] = useState<MembershipStatus>("active");

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listInstitutionUsers({
        page,
        search: search.trim() || undefined,
        status: statusFilter || undefined,
        role: roleFilter || undefined,
      });
      setRows(res.results);
      setCount(res.count);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, roleFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const toggleRoleInList = (list: RoleCode[], role: RoleCode): RoleCode[] =>
    list.includes(role) ? list.filter((r) => r !== role) : [...list, role];

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedRoles.length === 0) {
      setModalError("Select at least one role.");
      return;
    }
    setSaving(true);
    setModalError(null);
    try {
      const created = await createInstitutionUser({
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        role_codes: selectedRoles,
        status: "active",
      });
      setCreateOpen(false);
      setEmail("");
      setFirstName("");
      setLastName("");
      if (created.onboarding_reset_path) {
        setCopied(false);
        setResetLinkModal(`${window.location.origin}${created.onboarding_reset_path}`);
      }
      await loadUsers();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveRoles = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roleTarget) return;
    setSaving(true);
    setModalError(null);
    try {
      await updateInstitutionUserRoles(roleTarget.id, editRoles);
      setRoleTarget(null);
      await loadUsers();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTarget) return;
    setSaving(true);
    setModalError(null);
    try {
      await updateInstitutionUser(editTarget.id, {
        first_name: editFirst.trim(),
        last_name: editLast.trim(),
        status: editStatus,
      });
      setEditTarget(null);
      await loadUsers();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleIssueResetLink = async (member: MembershipUserRecord) => {
    setError(null);
    try {
      const path = await issueInstitutionUserResetLink(member.id);
      setCopied(false);
      setResetLinkModal(`${window.location.origin}${path}`);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const columns: ColumnDef<MembershipUserRecord>[] = [
    {
      key: "user",
      header: "User",
      render: (row) => (
        <div>
          <div className="font-semibold text-[#0F2942]">{row.full_name}</div>
          <div className="text-xs text-slate-500">{row.email}</div>
        </div>
      ),
    },
    {
      key: "roles",
      header: "Institution Roles",
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          {row.roles.map((r) => (
            <StatusBadge key={r} label={r.replaceAll("_", " ")} tone="neutral" />
          ))}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => (
        <StatusBadge
          label={row.status}
          tone={row.status === "active" ? "success" : "warning"}
        />
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
            onClick={() => {
              setModalError(null);
              setRoleTarget(row);
              setEditRoles(row.roles);
            }}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Shield className="h-3.5 w-3.5 text-blue-700" />
            Roles
          </button>
          <button
            type="button"
            onClick={() => {
              setModalError(null);
              setEditTarget(row);
              setEditFirst(row.first_name);
              setEditLast(row.last_name);
              setEditStatus(row.status);
            }}
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => handleIssueResetLink(row)}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
            title="Issue password setup/reset link"
          >
            <KeyRound className="h-3.5 w-3.5 text-[#0D9488]" />
            Reset Link
          </button>
        </div>
      ),
    },
  ];

  return (
    <AppShell title="Users & Roles">
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
                placeholder="Search name or email..."
                className="pl-9 pr-3 py-2 rounded-lg border border-slate-300 bg-white text-sm w-60 focus:border-blue-600 focus:outline-none"
              />
            </div>
            <select
              aria-label="Filter by role"
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            >
              <option value="">All Roles</option>
              {INSTITUTION_ROLES.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.label}
                </option>
              ))}
            </select>
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
              <option value="pending">Pending</option>
            </select>
          </div>

          <button
            type="button"
            onClick={() => {
              setModalError(null);
              setCreateOpen(true);
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white"
          >
            <Plus className="h-4 w-4" />
            Add User
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
          emptyTitle="No institution users match the filter"
        />
      </div>

      {/* Create User Modal */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Add Institution User"
        subtitle="Creates an institution-scoped membership and generates a one-time password setup link."
      >
        <form className="space-y-4" onSubmit={handleCreateUser}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div>
            <label htmlFor="u-email" className="block text-xs font-medium text-slate-700">
              Email Address
            </label>
            <input
              id="u-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="u-first" className="block text-xs font-medium text-slate-700">
                First Name
              </label>
              <input
                id="u-first"
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="u-last" className="block text-xs font-medium text-slate-700">
                Last Name
              </label>
              <input
                id="u-last"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <div className="text-xs font-medium text-slate-700 mb-2">Assign Roles</div>
            <div className="grid grid-cols-2 gap-2">
              {INSTITUTION_ROLES.map((r) => (
                <label
                  key={r.code}
                  className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs cursor-pointer hover:bg-slate-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedRoles.includes(r.code)}
                    onChange={() => setSelectedRoles(toggleRoleInList(selectedRoles, r.code))}
                  />
                  <span>{r.label}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-4 py-2 text-sm font-medium text-white"
            >
              {saving ? "Creating..." : "Create User"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Roles Modal */}
      <Modal
        open={Boolean(roleTarget)}
        onClose={() => setRoleTarget(null)}
        title={roleTarget ? `Manage Roles — ${roleTarget.full_name}` : "Manage Roles"}
        subtitle="Role changes apply immediately to subsequent API requests."
      >
        <form className="space-y-4" onSubmit={handleSaveRoles}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div className="space-y-2">
            {INSTITUTION_ROLES.map((r) => (
              <label
                key={r.code}
                className="flex items-center gap-2.5 rounded-lg border border-slate-200 px-3 py-2.5 text-sm cursor-pointer hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={editRoles.includes(r.code)}
                  onChange={() => setEditRoles(toggleRoleInList(editRoles, r.code))}
                />
                <span className="font-medium text-slate-800">{r.label}</span>
              </label>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setRoleTarget(null)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-4 py-2 text-sm font-medium text-white"
            >
              {saving ? "Updating..." : "Save Roles"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit User Status / Name Modal */}
      <Modal
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        title={editTarget ? `Edit User — ${editTarget.email}` : "Edit User"}
      >
        <form className="space-y-4" onSubmit={handleSaveEdit}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="eu-first" className="block text-xs font-medium text-slate-700">
                First Name
              </label>
              <input
                id="eu-first"
                type="text"
                required
                value={editFirst}
                onChange={(e) => setEditFirst(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="eu-last" className="block text-xs font-medium text-slate-700">
                Last Name
              </label>
              <input
                id="eu-last"
                type="text"
                value={editLast}
                onChange={(e) => setEditLast(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label htmlFor="eu-status" className="block text-xs font-medium text-slate-700">
              Membership Status
            </label>
            <select
              id="eu-status"
              value={editStatus}
              onChange={(e) => setEditStatus(e.target.value as MembershipStatus)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="pending">Pending</option>
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditTarget(null)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] disabled:opacity-50 px-4 py-2 text-sm font-medium text-white"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </Modal>

      {/* One-time Reset / Onboarding Link Modal */}
      <Modal
        open={Boolean(resetLinkModal)}
        onClose={() => setResetLinkModal(null)}
        title="One-Time Password Setup Link"
        subtitle="Share this secure link directly with the user. It is never saved in plaintext or audit logs."
      >
        {resetLinkModal && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={resetLinkModal}
                className="flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-mono text-slate-700"
              />
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(resetLinkModal);
                  setCopied(true);
                }}
                className="inline-flex items-center gap-1 rounded-lg bg-[#0D9488] px-3 py-2 text-xs font-medium text-white"
              >
                <Copy className="h-3.5 w-3.5" />
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setResetLinkModal(null)}
                className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </Modal>
    </AppShell>
  );
};

