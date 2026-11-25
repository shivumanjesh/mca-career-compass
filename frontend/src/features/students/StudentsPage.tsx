import React, { useCallback, useEffect, useState } from "react";
import { Copy, Plus, Search } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../app/AuthContext";
import { parseApiError } from "../../services/apiClient";
import {
  createStudent,
  listCohorts,
  listStudents,
  updateStudent,
} from "../../services/academicsService";
import type { ActiveStatus, CohortRecord, StudentRecord } from "../../types/academics";

export const StudentsPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("institution.student.manage");

  const [rows, setRows] = useState<StudentRecord[]>([]);
  const [cohorts, setCohorts] = useState<CohortRecord[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [cohortFilter, setCohortFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create / Edit Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<StudentRecord | null>(null);
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [regNo, setRegNo] = useState("");
  const [cohortId, setCohortId] = useState("");
  const [admissionYear, setAdmissionYear] = useState<string>("2025");
  const [phone, setPhone] = useState("");
  const [status, setStatus] = useState<ActiveStatus>("active");
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const [onboardingModal, setOnboardingModal] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [stuRes, cohRes] = await Promise.all([
        listStudents({
          page,
          search: search.trim() || undefined,
          cohort_id: cohortFilter || undefined,
          status: statusFilter || undefined,
        }),
        listCohorts({ page: 1 }),
      ]);
      setRows(stuRes.results);
      setCount(stuRes.count);
      setCohorts(cohRes.results);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, search, cohortFilter, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditing(null);
    setEmail("");
    setFirstName("");
    setLastName("");
    setRegNo("");
    setCohortId(cohorts[0]?.id || "");
    setAdmissionYear("2025");
    setPhone("");
    setStatus("active");
    setModalError(null);
    setModalOpen(true);
  };

  const openEdit = (stu: StudentRecord) => {
    setEditing(stu);
    setEmail(stu.email);
    setFirstName(stu.first_name);
    setLastName(stu.last_name);
    setRegNo(stu.registration_no);
    setCohortId(stu.cohort_id || "");
    setAdmissionYear(stu.admission_year ? String(stu.admission_year) : "");
    setPhone(stu.phone || "");
    setStatus(stu.status);
    setModalError(null);
    setModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      if (editing) {
        await updateStudent(editing.id, {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          registration_no: regNo.trim(),
          cohort_id: cohortId || null,
          admission_year: admissionYear ? Number(admissionYear) : null,
          phone: phone.trim(),
          status,
        });
      } else {
        const created = await createStudent({
          email: email.trim(),
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          registration_no: regNo.trim(),
          cohort_id: cohortId || null,
          admission_year: admissionYear ? Number(admissionYear) : null,
          phone: phone.trim(),
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

  const columns: ColumnDef<StudentRecord>[] = [
    {
      key: "reg",
      header: "Registration No.",
      render: (r) => <span className="font-mono font-semibold text-[#0F2942]">{r.registration_no}</span>,
    },
    {
      key: "name",
      header: "Student",
      render: (r) => (
        <div>
          <div className="font-semibold text-slate-900">{r.full_name}</div>
          <div className="text-xs text-slate-500">{r.email}</div>
        </div>
      ),
    },
    {
      key: "cohort",
      header: "Programme / Cohort",
      render: (r) =>
        r.cohort_label ? (
          <span className="text-xs text-slate-700 font-medium">{r.cohort_label}</span>
        ) : (
          <span className="text-xs text-slate-400">Unassigned</span>
        ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => (
        <StatusBadge label={r.status} tone={r.status === "active" ? "success" : "warning"} />
      ),
    },
    ...(canManage
      ? [
          {
            key: "actions",
            header: "Actions",
            className: "text-right",
            render: (r: StudentRecord) => (
              <button
                type="button"
                onClick={() => openEdit(r)}
                className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Edit
              </button>
            ),
          },
        ]
      : []),
  ];

  return (
    <AppShell title={canManage ? "Student Management" : "Assigned Students"}>
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
                placeholder="Search USN, name, or email..."
                className="pl-9 pr-3 py-2 rounded-lg border border-slate-300 bg-white text-sm w-64 focus:border-blue-600 focus:outline-none"
              />
            </div>
            <select
              aria-label="Filter by cohort"
              value={cohortFilter}
              onChange={(e) => {
                setCohortFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            >
              <option value="">All Cohorts</option>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.programme_code} {c.batch_name} Sem-{c.semester} ({c.section})
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
            </select>
          </div>

          {canManage && (
            <button
              type="button"
              onClick={openCreate}
              className="inline-flex items-center gap-2 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white"
            >
              <Plus className="h-4 w-4" />
              Add Student
            </button>
          )}
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
          emptyTitle="No student profiles found"
          emptyDescription={
            canManage
              ? "Add a student manually or import a cohort spreadsheet in Bulk Import."
              : "No students are currently assigned to your cohorts."
          }
        />
      </div>

      {/* Create / Edit Student Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit Student — ${editing.registration_no}` : "Add Student"}
      >
        <form className="space-y-4" onSubmit={handleSave}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          {!editing && (
            <div>
              <label htmlFor="s-email" className="block text-xs font-medium text-slate-700">
                Institutional Email
              </label>
              <input
                id="s-email"
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
              <label htmlFor="s-first" className="block text-xs font-medium text-slate-700">First Name</label>
              <input
                id="s-first"
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="s-last" className="block text-xs font-medium text-slate-700">Last Name</label>
              <input
                id="s-last"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="s-reg" className="block text-xs font-medium text-slate-700">Registration No. / USN</label>
              <input
                id="s-reg"
                type="text"
                required
                value={regNo}
                onChange={(e) => setRegNo(e.target.value.toUpperCase())}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
              />
            </div>
            <div>
              <label htmlFor="s-adm" className="block text-xs font-medium text-slate-700">Admission Year</label>
              <input
                id="s-adm"
                type="number"
                min={1990}
                max={2100}
                value={admissionYear}
                onChange={(e) => setAdmissionYear(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label htmlFor="s-cohort" className="block text-xs font-medium text-slate-700">Cohort / Batch</label>
            <select
              id="s-cohort"
              value={cohortId}
              onChange={(e) => setCohortId(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Unassigned</option>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.programme_code} {c.batch_name} Sem-{c.semester} ({c.section})
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="s-phone" className="block text-xs font-medium text-slate-700">Phone</label>
              <input
                id="s-phone"
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="s-status" className="block text-xs font-medium text-slate-700">Status</label>
              <select
                id="s-status"
                value={status}
                onChange={(e) => setStatus(e.target.value as ActiveStatus)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Saving..." : editing ? "Save Changes" : "Create Student"}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={Boolean(onboardingModal)}
        onClose={() => setOnboardingModal(null)}
        title="Student Password Setup Link"
        subtitle="Share this one-time link securely with the student."
      >
        {onboardingModal && (
          <div className="space-y-4">
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
          </div>
        )}
      </Modal>
    </AppShell>
  );
};

