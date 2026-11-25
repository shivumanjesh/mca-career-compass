import React, { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  createAcademicYear,
  createCohort,
  createProgramme,
  listAcademicYears,
  listCohorts,
  listProgrammes,
  updateAcademicYear,
  updateCohort,
  updateProgramme,
} from "../../services/academicsService";
import type {
  AcademicYearRecord,
  ActiveStatus,
  CohortRecord,
  ProgrammeRecord,
} from "../../types/academics";

type TabKey = "cohorts" | "programmes" | "years";

export const AcademicsPage: React.FC = () => {
  const [tab, setTab] = useState<TabKey>("cohorts");
  const [programmes, setProgrammes] = useState<ProgrammeRecord[]>([]);
  const [years, setYears] = useState<AcademicYearRecord[]>([]);
  const [cohorts, setCohorts] = useState<CohortRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Programme modal
  const [progOpen, setProgOpen] = useState(false);
  const [progCode, setProgCode] = useState("MCA");
  const [progName, setProgName] = useState("");
  const [progLevel, setProgLevel] = useState("PG");

  // Academic year modal
  const [ayOpen, setAyOpen] = useState(false);
  const [ayName, setAyName] = useState("");
  const [ayStart, setAyStart] = useState("");
  const [ayEnd, setAyEnd] = useState("");

  // Cohort modal
  const [cohortOpen, setCohortOpen] = useState(false);
  const [cProgrammeId, setCProgrammeId] = useState("");
  const [cYearId, setCYearId] = useState("");
  const [cBatch, setCBatch] = useState("");
  const [cSemester, setCSemester] = useState(1);
  const [cSection, setCSection] = useState("A");

  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pRes, yRes, cRes] = await Promise.all([
        listProgrammes({ page: 1 }),
        listAcademicYears({ page: 1 }),
        listCohorts({ page: 1 }),
      ]);
      setProgrammes(pRes.results);
      setYears(yRes.results);
      setCohorts(cRes.results);
      if (!cProgrammeId && pRes.results[0]) setCProgrammeId(pRes.results[0].id);
      if (!cYearId && yRes.results[0]) setCYearId(yRes.results[0].id);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [cProgrammeId, cYearId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleCreateProgramme = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      await createProgramme({ code: progCode, name: progName, level: progLevel, status: "active" });
      setProgOpen(false);
      setProgName("");
      await loadAll();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateYear = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      await createAcademicYear({ name: ayName, start_date: ayStart, end_date: ayEnd, status: "active" });
      setAyOpen(false);
      setAyName("");
      await loadAll();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateCohort = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      await createCohort({
        programme_id: cProgrammeId,
        academic_year_id: cYearId,
        batch_name: cBatch,
        semester: cSemester,
        section: cSection,
        status: "active",
      });
      setCohortOpen(false);
      setCBatch("");
      await loadAll();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const toggleStatus = async (kind: TabKey, id: string, current: ActiveStatus) => {
    const next: ActiveStatus = current === "active" ? "inactive" : "active";
    try {
      if (kind === "programmes") await updateProgramme(id, { status: next });
      if (kind === "years") await updateAcademicYear(id, { status: next });
      if (kind === "cohorts") await updateCohort(id, { status: next });
      await loadAll();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const cohortCols: ColumnDef<CohortRecord>[] = [
    {
      key: "batch",
      header: "Cohort / Batch",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">
            {r.programme_code} — {r.batch_name}
          </div>
          <div className="text-xs text-slate-500">Academic Year: {r.academic_year_name}</div>
        </div>
      ),
    },
    {
      key: "sem",
      header: "Semester / Section",
      render: (r) => (
        <span className="text-slate-700 font-medium text-xs">
          Sem {r.semester} • Section {r.section}
        </span>
      ),
    },
    {
      key: "students",
      header: "Students",
      render: (r) => <span className="text-slate-700 text-xs font-medium">{r.student_count}</span>,
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
        <button
          type="button"
          onClick={() => toggleStatus("cohorts", r.id, r.status)}
          className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          {r.status === "active" ? "Deactivate" : "Activate"}
        </button>
      ),
    },
  ];

  const programmeCols: ColumnDef<ProgrammeRecord>[] = [
    { key: "code", header: "Code", render: (r) => <strong className="text-[#0F2942]">{r.code}</strong> },
    { key: "name", header: "Name", render: (r) => r.name },
    { key: "level", header: "Level", render: (r) => r.level },
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
        <button
          type="button"
          onClick={() => toggleStatus("programmes", r.id, r.status)}
          className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          {r.status === "active" ? "Deactivate" : "Activate"}
        </button>
      ),
    },
  ];

  const yearCols: ColumnDef<AcademicYearRecord>[] = [
    { key: "name", header: "Academic Year", render: (r) => <strong className="text-[#0F2942]">{r.name}</strong> },
    { key: "start", header: "Start Date", render: (r) => r.start_date },
    { key: "end", header: "End Date", render: (r) => r.end_date },
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
        <button
          type="button"
          onClick={() => toggleStatus("years", r.id, r.status)}
          className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          {r.status === "active" ? "Deactivate" : "Activate"}
        </button>
      ),
    },
  ];

  return (
    <AppShell title="Academic Structure">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
            {(
              [
                ["cohorts", `Cohorts & Batches (${cohorts.length})`],
                ["programmes", `Programmes (${programmes.length})`],
                ["years", `Academic Years (${years.length})`],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={`rounded-md px-3.5 py-1.5 text-xs font-medium transition ${
                  tab === key
                    ? "bg-[#0F2942] text-white"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => {
              setModalError(null);
              if (tab === "cohorts") setCohortOpen(true);
              if (tab === "programmes") setProgOpen(true);
              if (tab === "years") setAyOpen(true);
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white"
          >
            <Plus className="h-4 w-4" />
            {tab === "cohorts"
              ? "New Cohort"
              : tab === "programmes"
                ? "New Programme"
                : "New Academic Year"}
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {tab === "cohorts" && (
          <DataTable
            columns={cohortCols}
            rows={cohorts}
            rowKey={(r) => r.id}
            loading={loading}
            emptyTitle="No cohorts configured yet"
            emptyDescription="Create a Programme and Academic Year first, then add your MCA batch/semester/section cohorts."
          />
        )}
        {tab === "programmes" && (
          <DataTable
            columns={programmeCols}
            rows={programmes}
            rowKey={(r) => r.id}
            loading={loading}
            emptyTitle="No programmes configured yet"
          />
        )}
        {tab === "years" && (
          <DataTable
            columns={yearCols}
            rows={years}
            rowKey={(r) => r.id}
            loading={loading}
            emptyTitle="No academic years configured yet"
          />
        )}
      </div>

      {/* Create Programme Modal */}
      <Modal open={progOpen} onClose={() => setProgOpen(false)} title="Create Programme">
        <form className="space-y-4" onSubmit={handleCreateProgramme}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="p-code" className="block text-xs font-medium text-slate-700">Code</label>
              <input
                id="p-code"
                type="text"
                required
                value={progCode}
                onChange={(e) => setProgCode(e.target.value.toUpperCase())}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
              />
            </div>
            <div>
              <label htmlFor="p-level" className="block text-xs font-medium text-slate-700">Level</label>
              <input
                id="p-level"
                type="text"
                required
                value={progLevel}
                onChange={(e) => setProgLevel(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label htmlFor="p-name" className="block text-xs font-medium text-slate-700">Programme Name</label>
            <input
              id="p-name"
              type="text"
              required
              value={progName}
              onChange={(e) => setProgName(e.target.value)}
              placeholder="Master of Computer Applications"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setProgOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Saving..." : "Create Programme"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Create Academic Year Modal */}
      <Modal open={ayOpen} onClose={() => setAyOpen(false)} title="Create Academic Year">
        <form className="space-y-4" onSubmit={handleCreateYear}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div>
            <label htmlFor="ay-name" className="block text-xs font-medium text-slate-700">Name</label>
            <input
              id="ay-name"
              type="text"
              required
              value={ayName}
              onChange={(e) => setAyName(e.target.value)}
              placeholder="2025-26"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="ay-start" className="block text-xs font-medium text-slate-700">Start Date</label>
              <input
                id="ay-start"
                type="date"
                required
                value={ayStart}
                onChange={(e) => setAyStart(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="ay-end" className="block text-xs font-medium text-slate-700">End Date</label>
              <input
                id="ay-end"
                type="date"
                required
                value={ayEnd}
                onChange={(e) => setAyEnd(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setAyOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Saving..." : "Create Academic Year"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Create Cohort Modal */}
      <Modal open={cohortOpen} onClose={() => setCohortOpen(false)} title="Create Cohort / Batch">
        <form className="space-y-4" onSubmit={handleCreateCohort}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="c-prog" className="block text-xs font-medium text-slate-700">Programme</label>
              <select
                id="c-prog"
                required
                value={cProgrammeId}
                onChange={(e) => setCProgrammeId(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select Programme</option>
                {programmes.map((p) => (
                  <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="c-ay" className="block text-xs font-medium text-slate-700">Academic Year</label>
              <select
                id="c-ay"
                required
                value={cYearId}
                onChange={(e) => setCYearId(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select Year</option>
                {years.map((y) => (
                  <option key={y.id} value={y.id}>{y.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="c-batch" className="block text-xs font-medium text-slate-700">Batch Name</label>
            <input
              id="c-batch"
              type="text"
              required
              value={cBatch}
              onChange={(e) => setCBatch(e.target.value)}
              placeholder="e.g. MCA 2025-2027"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="c-sem" className="block text-xs font-medium text-slate-700">Semester (1-8)</label>
              <input
                id="c-sem"
                type="number"
                min={1}
                max={8}
                required
                value={cSemester}
                onChange={(e) => setCSemester(Number(e.target.value))}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="c-sec" className="block text-xs font-medium text-slate-700">Section</label>
              <input
                id="c-sec"
                type="text"
                required
                value={cSection}
                onChange={(e) => setCSection(e.target.value.toUpperCase())}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setCohortOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Saving..." : "Create Cohort"}
            </button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
};

