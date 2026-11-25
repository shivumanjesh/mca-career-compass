import React, { useCallback, useEffect, useState } from "react";
import { Copy, Layers, Plus, Search, Trash2 } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  assignFacultyCohort,
  createFaculty,
  listCohorts,
  listFaculty,
  removeFacultyCohort,
  updateFaculty,
} from "../../services/academicsService";
import type {
  ActiveStatus,
  AssignmentType,
  CohortRecord,
  FacultyRecord,
} from "../../types/academics";

export const FacultyPage: React.FC = () => {
  const [rows, setRows] = useState<FacultyRecord[]>([]);
  const [cohorts, setCohorts] = useState<CohortRecord[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create/Edit Faculty Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<FacultyRecord | null>(null);
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [empCode, setEmpCode] = useState("");
  const [department, setDepartment] = useState("MCA");
  const [designation, setDesignation] = useState("Assistant Professor");
  const [status, setStatus] = useState<ActiveStatus>("active");
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Cohort Assignment Modal
  const [assignTarget, setAssignTarget] = useState<FacultyRecord | null>(null);
  const [assignCohortId, setAssignCohortId] = useState("");
  const [assignType, setAssignType] = useState<AssignmentType>("mentor");

  const [onboardingModal, setOnboardingModal] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [facRes, cohRes] = await Promise.all([
        listFaculty({
          page,
          search: search.trim() || undefined,
          status: statusFilter || undefined,
        }),
        listCohorts({ page: 1 }),
      ]);
      setRows(facRes.results);
      setCount(facRes.count);
      setCohorts(cohRes.results);
      if (assignTarget) {
        const refreshed = facRes.results.find((f) => f.id === assignTarget.id) || null;
        setAssignTarget(refreshed);
      }
      if (!assignCohortId && cohRes.results[0]) {
        setAssignCohortId(cohRes.results[0].id);
      }
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, assignTarget?.id, assignCohortId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditing(null);
    setEmail("");
    setFirstName("");
    setLastName("");
    setEmpCode("");
    setDepartment("MCA");
    setDesignation("Assistant Professor");
    setStatus("active");
    setModalError(null);
    setModalOpen(true);
  };

  const openEdit = (fac: FacultyRecord) => {
    setEditing(fac);
    setEmail(fac.email);
    setFirstName(fac.first_name);
    setLastName(fac.last_name);
    setEmpCode(fac.employee_code || "");
    setDepartment(fac.department || "");
    setDesignation(fac.designation || "");
    setStatus(fac.status);
    setModalError(null);
    setModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      if (editing) {
        await updateFaculty(editing.id, {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          employee_code: empCode.trim() || null,
          department: department.trim(),
          designation: designation.trim(),
          status,
        });
      } else {
        const created = await createFaculty({
          email: email.trim(),
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          employee_code: empCode.trim() || null,
          department: department.trim(),
          designation: designation.trim(),
          status,
        });
        if (created.onboarding_reset_path) {
          setCopied(false);
          setOnboardingModal(`${window.location.origin}${created.onboarding_reset_path}`);
        }
      }
      setModalOpen(false);
      await loadData();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleAssignCohort = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignTarget || !assignCohortId) return;
    setSaving(true);
    setModalError(null);
    try {
      await assignFacultyCohort(assignTarget.id, assignCohortId, assignType);
      await loadData();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveAssignment = async (assignmentId: string) => {
    if (!assignTarget) return;
    setModalError(null);
    try {
      await removeFacultyCohort(assignTarget.id, assignmentId);
      await loadData();
    } catch (err) {
      setModalError(parseApiError(err).message);
    }
  };

  const columns: ColumnDef<FacultyRecord>[] = [
    {
      key: "faculty",
      header: "Faculty Member",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">{r.full_name}</div>
          <div className="text-xs text-slate-500">
            {r.email} {r.employee_code ? `• ${r.employee_code}` : ""}
          </div>
        </div>
      ),
    },
    {
      key: "dept",
      header: "Department / Designation",
      render: (r) => (
        <div className="text-xs">
          <div className="font-medium text-slate-800">{r.department || "—"}</div>
          <div className="text-slate-500">{r.designation || "—"}</div>
        </div>
      ),
    },
    {
      key: "cohorts",
      header: "Assigned Cohorts",
      render: (r) => (
        <div className="flex flex-wrap gap-1">
          {r.cohort_assignments.length === 0 ? (
            <span className="text-xs text-slate-400">None</span>
          ) : (
            r.cohort_assignments.map((a) => (
              <StatusBadge
                key={a.id}
                label={`${a.programme_code} Sem-${a.semester} (${a.section}) • ${a.assignment_type}`}
                tone="neutral"
              />
            ))
          )}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => (
        <StatusBadge label={r.status} tone={r.status === "active" ? "success" : "warning"} />
      ),
    },
    {
      key: "actions",
      header: "Actions",
      className: "text-right",
      render: (r) => (
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => {
              setModalError(null);
              setAssignTarget(r);
            }}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <Layers className="h-3.5 w-3.5 text-[#0D9488]" />
            Cohorts
          </button>
          <button
            type="button"
            onClick={() => openEdit(r)}
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Edit
          </button>
        </div>
      ),
    },
  ];

  return (
    <AppShell title="Faculty Management">
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
                placeholder="Search name, code, or dept..."
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
            </select>
          </div>

          <button
            type="button"
            onClick={openCreate}
            className="inline-flex items-center gap-2 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white"
          >
            <Plus className="h-4 w-4" />
            Add Faculty
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
          emptyTitle="No faculty profiles found"
        />
      </div>

      {/* Create / Edit Faculty Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit Faculty — ${editing.full_name}` : "Add Faculty"}
      >
        <form className="space-y-4" onSubmit={handleSave}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          {!editing && (
            <div>
              <label htmlFor="f-email" className="block text-xs font-medium text-slate-700">Email</label>
              <input
                id="f-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="f-first" className="block text-xs font-medium text-slate-700">First Name</label>
              <input id="f-first" type="text" required value={firstName} onChange={(e) => setFirstName(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="f-last" className="block text-xs font-medium text-slate-700">Last Name</label>
              <input id="f-last" type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="f-code" className="block text-xs font-medium text-slate-700">Employee Code</label>
              <input id="f-code" type="text" value={empCode} onChange={(e) => setEmpCode(e.target.value.toUpperCase())} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase" />
            </div>
            <div>
              <label htmlFor="f-dept" className="block text-xs font-medium text-slate-700">Department</label>
              <input id="f-dept" type="text" value={department} onChange={(e) => setDepartment(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="f-desig" className="block text-xs font-medium text-slate-700">Designation</label>
              <input id="f-desig" type="text" value={designation} onChange={(e) => setDesignation(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="f-status" className="block text-xs font-medium text-slate-700">Status</label>
              <select id="f-status" value={status} onChange={(e) => setStatus(e.target.value as ActiveStatus)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Saving..." : editing ? "Save Changes" : "Create Faculty"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Cohort Assignment Modal */}
      <Modal
        open={Boolean(assignTarget)}
        onClose={() => setAssignTarget(null)}
        title={assignTarget ? `Cohort Assignments — ${assignTarget.full_name}` : "Cohort Assignments"}
        subtitle="Faculty can access students exclusively within their assigned cohorts."
      >
        <div className="space-y-4">
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <form className="space-y-3 border-b border-slate-200 pb-4" onSubmit={handleAssignCohort}>
            <select
              aria-label="Select cohort"
              required
              value={assignCohortId}
              onChange={(e) => setAssignCohortId(e.target.value)}
              className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select Cohort</option>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.programme_code} {c.batch_name} Sem-{c.semester} ({c.section})
                </option>
              ))}
            </select>
            <div className="flex items-center gap-2">
              <select
                aria-label="Assignment type"
                value={assignType}
                onChange={(e) => setAssignType(e.target.value as AssignmentType)}
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="mentor">Mentor</option>
                <option value="hod">HOD</option>
                <option value="faculty">Faculty</option>
                <option value="coordinator">Coordinator</option>
              </select>
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-[#0D9488] px-4 py-2 text-sm font-medium text-white"
              >
                Assign
              </button>
            </div>
          </form>

          <div className="space-y-2">
            {assignTarget?.cohort_assignments.length ? (
              <ul className="divide-y divide-slate-100">
                {assignTarget.cohort_assignments.map((a) => (
                  <li key={a.id} className="py-2 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-slate-800">{a.cohort_label}</span>
                      <span className="ml-2 text-slate-500 uppercase">({a.assignment_type})</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveAssignment(a.id)}
                      className="text-rose-600 hover:text-rose-800 p-1"
                      aria-label="Remove assignment"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-500">No cohort assignments yet.</p>
            )}
          </div>
        </div>
      </Modal>

      <Modal
        open={Boolean(onboardingModal)}
        onClose={() => setOnboardingModal(null)}
        title="Faculty Password Setup Link"
        subtitle="Share this one-time link securely with the faculty member."
      >
        {onboardingModal && (
          <div className="flex items-center gap-2">
            <input type="text" readOnly value={onboardingModal} className="flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-mono" />
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(onboardingModal);
                setCopied(true);
              }}
              className="inline-flex items-center gap-1 rounded-lg bg-[#0D9488] px-3 py-2 text-xs font-medium text-white"
            >
              <Copy className="h-3.5 w-3.5" />
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        )}
      </Modal>
    </AppShell>
  );
};

