import React, { useCallback, useEffect, useState } from "react";
import { Eye, Search } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import { listAuditEvents } from "../../services/auditService";
import type { AuditEventRecord } from "../../types/audit";

export const AuditLogsPage: React.FC = () => {
  const [rows, setRows] = useState<AuditEventRecord[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [entityType, setEntityType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<AuditEventRecord | null>(null);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAuditEvents({
        page,
        search: search.trim() || undefined,
        entity_type: entityType || undefined,
      });
      setRows(res.results);
      setCount(res.count);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, search, entityType]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  const columns: ColumnDef<AuditEventRecord>[] = [
    {
      key: "time",
      header: "Timestamp",
      render: (r) => (
        <span className="text-xs text-slate-600">{new Date(r.created_at).toLocaleString()}</span>
      ),
    },
    {
      key: "action",
      header: "Action",
      render: (r) => <StatusBadge label={r.action} tone="neutral" />,
    },
    {
      key: "entity",
      header: "Target Entity",
      render: (r) => (
        <div className="text-xs">
          <div className="font-semibold text-[#0F2942]">{r.entity_type}</div>
          {r.institution_code && <div className="text-slate-500">Tenant: {r.institution_code}</div>}
        </div>
      ),
    },
    {
      key: "actor",
      header: "Actor",
      render: (r) => (
        <div className="text-xs">
          <div className="font-medium text-slate-800">{r.actor_name || "System / Anonymous"}</div>
          <div className="text-slate-500">{r.actor_email || "—"}</div>
        </div>
      ),
    },
    {
      key: "details",
      header: "Metadata",
      className: "text-right",
      render: (r) => (
        <button
          type="button"
          onClick={() => setSelected(r)}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <Eye className="h-3.5 w-3.5 text-[#0D9488]" />
          Inspect
        </button>
      ),
    },
  ];

  return (
    <AppShell title="Audit Trail">
      <div className="space-y-5">
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
              placeholder="Search action, actor email, or code..."
              className="pl-9 pr-3 py-2 rounded-lg border border-slate-300 bg-white text-sm w-72 focus:border-blue-600 focus:outline-none"
            />
          </div>
          <select
            aria-label="Filter by entity type"
            value={entityType}
            onChange={(e) => {
              setEntityType(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
          >
            <option value="">All Entities</option>
            <option value="Institution">Institution</option>
            <option value="Membership">Membership</option>
            <option value="User">User</option>
            <option value="Programme">Programme</option>
            <option value="AcademicYear">AcademicYear</option>
            <option value="Cohort">Cohort</option>
            <option value="StudentProfile">StudentProfile</option>
            <option value="FacultyProfile">FacultyProfile</option>
            <option value="CohortFaculty">CohortFaculty</option>
            <option value="ImportJob">ImportJob</option>
            <option value="AssessmentCategory">AssessmentCategory</option>
            <option value="AssessmentDimension">AssessmentDimension</option>
            <option value="Question">Question</option>
            <option value="AssessmentTemplate">AssessmentTemplate</option>
            <option value="AssessmentVersion">AssessmentVersion</option>
          </select>
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
          emptyTitle="No audit events found"
        />
      </div>

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? `Audit Event — ${selected.action}` : "Audit Event"}
        subtitle={selected ? `${selected.entity_type} • ${new Date(selected.created_at).toLocaleString()}` : undefined}
      >
        {selected && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 bg-slate-50 rounded-lg p-3 border border-slate-200">
              <div>
                <div className="text-slate-500">Actor</div>
                <div className="font-medium text-slate-800">{selected.actor_email || "Anonymous"}</div>
              </div>
              <div>
                <div className="text-slate-500">Institution</div>
                <div className="font-medium text-slate-800">{selected.institution_code || "Platform"}</div>
              </div>
              <div className="col-span-2">
                <div className="text-slate-500">HMAC IP Hash</div>
                <div className="font-mono text-[11px] text-slate-700 break-all">{selected.ip_hash || "—"}</div>
              </div>
            </div>

            {selected.before_json && (
              <div>
                <div className="font-semibold text-slate-700 mb-1">Before</div>
                <pre className="rounded-lg bg-slate-900 text-slate-100 p-3 overflow-x-auto text-[11px]">
                  {JSON.stringify(selected.before_json, null, 2)}
                </pre>
              </div>
            )}

            {selected.after_json && (
              <div>
                <div className="font-semibold text-slate-700 mb-1">After</div>
                <pre className="rounded-lg bg-slate-900 text-slate-100 p-3 overflow-x-auto text-[11px]">
                  {JSON.stringify(selected.after_json, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </AppShell>
  );
};

