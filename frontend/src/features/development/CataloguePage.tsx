import React, { useCallback, useEffect, useState } from "react";
import { Archive, BookOpen, ExternalLink, Plus, RotateCcw, Search, Sparkles } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  createLearningResource,
  listLearningResources,
  seedLearningCatalogue,
  updateLearningResource,
} from "../../services/developmentService";
import type {
  LearningResource,
  LearningResourceType,
  ResourceLevel,
} from "../../types/development";

const RESOURCE_TYPE_LABELS: Record<LearningResourceType, string> = {
  learning_pathway: "Learning Pathway",
  training: "Training / Workshop",
  project: "Hands-on Project",
  certification: "Certification",
  milestone: "Custom Milestone",
};

export const CataloguePage: React.FC = () => {
  const [rows, setRows] = useState<LearningResource[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [targetDomain, setTargetDomain] = useState("Software Development");
  const [resType, setResType] = useState<LearningResourceType>("learning_pathway");
  const [dimensionCode, setDimensionCode] = useState("");
  const [provider, setProvider] = useState("");
  const [level, setLevel] = useState<ResourceLevel>("intermediate");
  const [estimatedHours, setEstimatedHours] = useState(20);
  const [resourceUrl, setResourceUrl] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const loadResources = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listLearningResources({
        page,
        search: search.trim() || undefined,
        resource_type: resourceType || undefined,
        status: statusFilter || undefined,
      });
      setRows(res.results);
      setCount(res.count);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, search, resourceType, statusFilter]);

  useEffect(() => {
    loadResources();
  }, [loadResources]);

  const handleSeed = async () => {
    setSeeding(true);
    setError(null);
    setBanner(null);
    try {
      const res = await seedLearningCatalogue();
      setBanner(
        res.created_resources > 0
          ? `Seeded ${res.created_resources} starter MCA learning resources.`
          : "All starter learning catalogue items already exist.",
      );
      await loadResources();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSeeding(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createLearningResource({
        title,
        target_domain: targetDomain,
        resource_type: resType,
        dimension_code: dimensionCode,
        provider,
        level,
        estimated_hours: estimatedHours,
        resource_url: resourceUrl,
        description,
      });
      setModalOpen(false);
      setTitle("");
      setDimensionCode("");
      setProvider("");
      setResourceUrl("");
      setDescription("");
      setBanner("Learning resource added to the institutional catalogue.");
      await loadResources();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleStatus = async (item: LearningResource) => {
    const nextStatus = item.status === "active" ? "archived" : "active";
    try {
      await updateLearningResource(item.id, { status: nextStatus });
      await loadResources();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const columns: ColumnDef<LearningResource>[] = [
    {
      key: "title",
      header: "Resource",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942] flex items-center gap-2">
            <span>{r.title}</span>
            {r.resource_url && (
              <a
                href={r.resource_url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-700 hover:text-blue-900"
                title="Open resource link"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>
          {r.description && (
            <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{r.description}</p>
          )}
        </div>
      ),
    },
    {
      key: "type",
      header: "Category",
      render: (r) => (
        <div className="space-y-1">
          <StatusBadge label={RESOURCE_TYPE_LABELS[r.resource_type]} tone="neutral" />
          <div className="text-xs text-slate-600">{r.target_domain}</div>
        </div>
      ),
    },
    {
      key: "dimension",
      header: "Skill Dimension",
      render: (r) =>
        r.dimension_code ? (
          <span className="inline-flex rounded bg-slate-100 px-2 py-0.5 text-xs font-mono font-medium text-[#0F2942]">
            {r.dimension_code}
          </span>
        ) : (
          <span className="text-xs text-slate-400">General</span>
        ),
    },
    {
      key: "details",
      header: "Level & Effort",
      render: (r) => (
        <div className="text-xs text-slate-600">
          <div className="capitalize font-medium">{r.level} · {r.estimated_hours} hrs</div>
          {r.provider && <div className="text-slate-500">{r.provider}</div>}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => (
        <StatusBadge
          label={r.status === "active" ? "Active" : "Archived"}
          tone={r.status === "active" ? "success" : "neutral"}
        />
      ),
    },
    {
      key: "actions",
      header: "Actions",
      className: "text-right",
      render: (r) => (
        <button
          type="button"
          onClick={() => handleToggleStatus(r)}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          {r.status === "active" ? (
            <>
              <Archive className="h-3.5 w-3.5" /> Archive
            </>
          ) : (
            <>
              <RotateCcw className="h-3.5 w-3.5" /> Restore
            </>
          )}
        </button>
      ),
    },
  ];

  return (
    <AppShell title="Learning & Empowerment Catalogue">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <BookOpen className="h-4 w-4 text-[#0D9488]" />
            <span>
              Curate institutional pathways, remedial trainings, capstone projects, and certifications.
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleSeed}
              disabled={seeding}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-[#0F2942] hover:bg-slate-50 disabled:opacity-60"
            >
              <Sparkles className="h-3.5 w-3.5 text-[#0D9488]" />
              <span>{seeding ? "Seeding..." : "Seed Starter Catalogue"}</span>
            </button>
            <button
              type="button"
              onClick={() => setModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#0F2942] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1E3A5F]"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Add Learning Resource</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}
        {banner && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-800">
            {banner}
          </div>
        )}

        <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search title, dimension code, domain, provider..."
              className="w-full rounded-lg border border-slate-300 pl-9 pr-3 py-2 text-sm focus:border-blue-600 focus:outline-none"
            />
          </div>
          <select
            value={resourceType}
            onChange={(e) => {
              setResourceType(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700"
          >
            <option value="">All Resource Types</option>
            <option value="learning_pathway">Learning Pathways</option>
            <option value="training">Trainings / Workshops</option>
            <option value="project">Hands-on Projects</option>
            <option value="certification">Certifications</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700"
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="">All Statuses</option>
          </select>
        </div>

        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(r) => r.id}
          loading={loading}
          emptyTitle="No learning resources in catalogue"
          emptyDescription="Seed the starter MCA learning catalogue or add custom resources."
          page={page}
          totalCount={count}
          onPageChange={setPage}
        />

        <Modal
          open={modalOpen}
          title="Add Learning Resource"
          subtitle="Resources are scoped to the active institution and matched against student skill dimensions."
          onClose={() => setModalOpen(false)}
        >
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Full-Stack REST API Workshop"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Type *</label>
                <select
                  value={resType}
                  onChange={(e) => setResType(e.target.value as LearningResourceType)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="learning_pathway">Learning Pathway</option>
                  <option value="training">Training / Workshop</option>
                  <option value="project">Hands-on Project</option>
                  <option value="certification">Certification</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Domain *</label>
                <input
                  type="text"
                  required
                  value={targetDomain}
                  onChange={(e) => setTargetDomain(e.target.value)}
                  placeholder="e.g., Software Development"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Dimension Code</label>
                <input
                  type="text"
                  value={dimensionCode}
                  onChange={(e) => setDimensionCode(e.target.value)}
                  placeholder="e.g., DSA"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Level</label>
                <select
                  value={level}
                  onChange={(e) => setLevel(e.target.value as ResourceLevel)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hours</label>
                <input
                  type="number"
                  min={1}
                  max={2000}
                  value={estimatedHours}
                  onChange={(e) => setEstimatedHours(Number(e.target.value) || 10)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Provider</label>
                <input
                  type="text"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  placeholder="e.g., MCA Skill Lab"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Reference URL</label>
                <input
                  type="url"
                  value={resourceUrl}
                  onChange={(e) => setResourceUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Description</label>
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-[#0F2942] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1E3A5F] disabled:opacity-60"
              >
                {saving ? "Saving..." : "Create Resource"}
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </AppShell>
  );
};

