import React, { useCallback, useEffect, useState } from "react";
import { Plus, Search, Sparkles } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  createAssessmentCategory,
  createAssessmentDimension,
  listAssessmentCategories,
  listAssessmentDimensions,
  seedStarterCatalogue,
  updateAssessmentCategory,
  updateAssessmentDimension,
} from "../../services/assessmentsService";
import type {
  AssessmentCategoryRecord,
  AssessmentDimensionRecord,
  LifecycleStatus,
  MeasurementFamily,
} from "../../types/assessments";

const FAMILY_LABELS: Record<MeasurementFamily, { label: string; tone: "success" | "warning" | "neutral" }> = {
  demonstrated_performance: { label: "Demonstrated Performance", tone: "success" },
  self_reported_proficiency: { label: "Self-Reported Proficiency", tone: "warning" },
  stated_interest: { label: "Stated Career Interest", tone: "neutral" },
};

export const DimensionsPage: React.FC = () => {
  const [tab, setTab] = useState<"dimensions" | "categories">("dimensions");
  const [categories, setCategories] = useState<AssessmentCategoryRecord[]>([]);
  const [dimensions, setDimensions] = useState<AssessmentDimensionRecord[]>([]);
  const [dimCount, setDimCount] = useState(0);
  const [dimPage, setDimPage] = useState(1);
  const [search, setSearch] = useState("");
  const [familyFilter, setFamilyFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Dimension Modal
  const [dimModalOpen, setDimModalOpen] = useState(false);
  const [editingDim, setEditingDim] = useState<AssessmentDimensionRecord | null>(null);
  const [dCategoryId, setDCategoryId] = useState("");
  const [dCode, setDCode] = useState("");
  const [dName, setDName] = useState("");
  const [dDesc, setDDesc] = useState("");
  const [dFamily, setDFamily] = useState<MeasurementFamily>("demonstrated_performance");
  const [dGuidance, setDGuidance] = useState("");
  const [dTags, setDTags] = useState("");

  // Category Modal
  const [catModalOpen, setCatModalOpen] = useState(false);
  const [cName, setCName] = useState("");
  const [cDesc, setCDesc] = useState("");
  const [cOrder, setCOrder] = useState(1);

  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [catRes, dimRes] = await Promise.all([
        listAssessmentCategories({ page: 1 }),
        listAssessmentDimensions({
          page: dimPage,
          search: search.trim() || undefined,
          category_id: categoryFilter || undefined,
          measurement_family: familyFilter || undefined,
        }),
      ]);
      setCategories(catRes.results);
      setDimensions(dimRes.results);
      setDimCount(dimRes.count);
      if (!dCategoryId && catRes.results[0]) {
        setDCategoryId(catRes.results[0].id);
      }
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [dimPage, search, categoryFilter, familyFilter, dCategoryId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSeedStarter = async () => {
    setNotice(null);
    setError(null);
    try {
      const res = await seedStarterCatalogue();
      setNotice(
        `Starter catalogue synced: ${res.created_categories} categories and ${res.created_dimensions} dimensions added.`,
      );
      await loadData();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const openCreateDim = () => {
    setEditingDim(null);
    setDCode("");
    setDName("");
    setDDesc("");
    setDFamily("demonstrated_performance");
    setDGuidance("");
    setDTags("");
    setModalError(null);
    setDimModalOpen(true);
  };

  const openEditDim = (d: AssessmentDimensionRecord) => {
    setEditingDim(d);
    setDCategoryId(d.category_id);
    setDCode(d.code);
    setDName(d.name);
    setDDesc(d.description);
    setDFamily(d.measurement_family);
    setDGuidance(d.interpretation_guidance);
    setDTags(d.skill_tags.join(", "));
    setModalError(null);
    setDimModalOpen(true);
  };

  const handleSaveDim = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    const skill_tags = dTags
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      if (editingDim) {
        await updateAssessmentDimension(editingDim.id, {
          category_id: dCategoryId,
          code: dCode,
          name: dName,
          description: dDesc,
          measurement_family: dFamily,
          interpretation_guidance: dGuidance,
          skill_tags,
        });
      } else {
        await createAssessmentDimension({
          category_id: dCategoryId,
          code: dCode,
          name: dName,
          description: dDesc,
          measurement_family: dFamily,
          interpretation_guidance: dGuidance,
          skill_tags,
        });
      }
      setDimModalOpen(false);
      await loadData();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setModalError(null);
    try {
      await createAssessmentCategory({ name: cName, description: cDesc, sort_order: cOrder });
      setCatModalOpen(false);
      setCName("");
      setCDesc("");
      await loadData();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const toggleStatus = async (kind: "dim" | "cat", id: string, current: LifecycleStatus) => {
    const next: LifecycleStatus = current === "active" ? "archived" : "active";
    try {
      if (kind === "dim") await updateAssessmentDimension(id, { status: next });
      else await updateAssessmentCategory(id, { status: next });
      await loadData();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const dimColumns: ColumnDef<AssessmentDimensionRecord>[] = [
    {
      key: "name",
      header: "Dimension",
      render: (r) => (
        <div>
          <div className="font-semibold text-[#0F2942]">
            {r.code} — {r.name}
          </div>
          <div className="text-xs text-slate-500">{r.category_name}</div>
        </div>
      ),
    },
    {
      key: "family",
      header: "Measurement Family",
      render: (r) => {
        const meta = FAMILY_LABELS[r.measurement_family];
        return <StatusBadge label={meta.label} tone={meta.tone} />;
      },
    },
    {
      key: "tags",
      header: "Skill Tags",
      render: (r) => (
        <div className="flex flex-wrap gap-1">
          {r.skill_tags.length === 0 ? (
            <span className="text-xs text-slate-400">—</span>
          ) : (
            r.skill_tags.map((t) => <StatusBadge key={t} label={t} tone="neutral" />)
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
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => openEditDim(r)}
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => toggleStatus("dim", r.id, r.status)}
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            {r.status === "active" ? "Archive" : "Restore"}
          </button>
        </div>
      ),
    },
  ];

  const catColumns: ColumnDef<AssessmentCategoryRecord>[] = [
    { key: "name", header: "Category Name", render: (r) => <strong className="text-[#0F2942]">{r.name}</strong> },
    { key: "desc", header: "Description", render: (r) => <span className="text-xs text-slate-600">{r.description || "—"}</span> },
    { key: "count", header: "Dimensions", render: (r) => r.dimension_count },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge label={r.status} tone={r.status === "active" ? "success" : "warning"} />,
    },
    {
      key: "actions",
      header: "Actions",
      className: "text-right",
      render: (r) => (
        <button
          type="button"
          onClick={() => toggleStatus("cat", r.id, r.status)}
          className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700"
        >
          {r.status === "active" ? "Archive" : "Restore"}
        </button>
      ),
    },
  ];

  return (
    <AppShell title="Assessment Dimensions & Categories">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
            <button
              type="button"
              onClick={() => setTab("dimensions")}
              className={`rounded-md px-3.5 py-1.5 text-xs font-medium ${
                tab === "dimensions" ? "bg-[#0F2942] text-white" : "text-slate-600"
              }`}
            >
              Dimensions ({dimCount})
            </button>
            <button
              type="button"
              onClick={() => setTab("categories")}
              className={`rounded-md px-3.5 py-1.5 text-xs font-medium ${
                tab === "categories" ? "bg-[#0F2942] text-white" : "text-slate-600"
              }`}
            >
              Categories ({categories.length})
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleSeedStarter}
              className="inline-flex items-center gap-1.5 rounded-lg border border-teal-300 bg-teal-50 hover:bg-teal-100 px-3.5 py-2 text-xs font-medium text-teal-900"
            >
              <Sparkles className="h-3.5 w-3.5 text-[#0D9488]" />
              Seed Starter Catalogue
            </button>
            <button
              type="button"
              onClick={() => {
                setModalError(null);
                if (tab === "dimensions") openCreateDim();
                else setCatModalOpen(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white"
            >
              <Plus className="h-4 w-4" />
              {tab === "dimensions" ? "New Dimension" : "New Category"}
            </button>
          </div>
        </div>

        {notice && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-800">
            {notice}
          </div>
        )}
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
            {error}
          </div>
        )}

        {tab === "dimensions" && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setDimPage(1);
                }}
                placeholder="Search code or dimension..."
                className="pl-9 pr-3 py-2 rounded-lg border border-slate-300 bg-white text-sm w-60"
              />
            </div>
            <select
              aria-label="Filter by category"
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setDimPage(1);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <select
              aria-label="Filter by measurement family"
              value={familyFilter}
              onChange={(e) => {
                setFamilyFilter(e.target.value);
                setDimPage(1);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All Measurement Families</option>
              <option value="demonstrated_performance">Demonstrated Performance</option>
              <option value="self_reported_proficiency">Self-Reported Proficiency</option>
              <option value="stated_interest">Stated Career Interest</option>
            </select>
          </div>
        )}

        {tab === "dimensions" ? (
          <DataTable
            columns={dimColumns}
            rows={dimensions}
            rowKey={(r) => r.id}
            loading={loading}
            page={dimPage}
            totalCount={dimCount}
            onPageChange={setDimPage}
            emptyTitle="No assessment dimensions configured"
            emptyDescription="Create custom dimensions or use 'Seed Starter Catalogue' to load Technical, Cognitive, Soft Skills, and Career Interest dimensions."
          />
        ) : (
          <DataTable
            columns={catColumns}
            rows={categories}
            rowKey={(r) => r.id}
            loading={loading}
            emptyTitle="No categories configured"
          />
        )}
      </div>

      {/* Create/Edit Dimension Modal */}
      <Modal
        open={dimModalOpen}
        onClose={() => setDimModalOpen(false)}
        title={editingDim ? `Edit Dimension — ${editingDim.code}` : "Create Assessment Dimension"}
        subtitle="Keep demonstrated performance, self-reported proficiency, and stated career interest strictly separated."
      >
        <form className="space-y-4" onSubmit={handleSaveDim}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700">Category</label>
              <select
                required
                value={dCategoryId}
                onChange={(e) => setDCategoryId(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select Category</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Code</label>
              <input
                type="text"
                required
                value={dCode}
                onChange={(e) => setDCode(e.target.value.toUpperCase())}
                placeholder="e.g. DSA"
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Dimension Name</label>
            <input
              type="text"
              required
              value={dName}
              onChange={(e) => setDName(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Measurement Family</label>
            <select
              value={dFamily}
              onChange={(e) => setDFamily(e.target.value as MeasurementFamily)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="demonstrated_performance">Demonstrated Performance (Objective / Rubric)</option>
              <option value="self_reported_proficiency">Self-Reported Proficiency (Likert / Perceived)</option>
              <option value="stated_interest">Stated Career Interest (Domain Preference)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Skill Tags (comma-separated)</label>
            <input
              type="text"
              value={dTags}
              onChange={(e) => setDTags(e.target.value)}
              placeholder="Python, Algorithms, Complexity"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Interpretation Guidance</label>
            <textarea
              rows={2}
              value={dGuidance}
              onChange={(e) => setDGuidance(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setDimModalOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Saving..." : "Save Dimension"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Create Category Modal */}
      <Modal open={catModalOpen} onClose={() => setCatModalOpen(false)} title="Create Assessment Category">
        <form className="space-y-4" onSubmit={handleCreateCategory}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-700">Category Name</label>
            <input type="text" required value={cName} onChange={(e) => setCName(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Description</label>
            <textarea rows={2} value={cDesc} onChange={(e) => setCDesc(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Sort Order</label>
            <input type="number" min={0} value={cOrder} onChange={(e) => setCOrder(Number(e.target.value))} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setCatModalOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Saving..." : "Create Category"}
            </button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
};

