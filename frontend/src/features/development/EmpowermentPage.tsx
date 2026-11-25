import React, { useCallback, useEffect, useState } from "react";
import {
  Award,
  BookOpen,
  Briefcase,
  CheckCircle2,
  Compass,
  FolderKanban,
  GraduationCap,
  Plus,
  Sparkles,
} from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  addPlanActivity,
  createDevelopmentPlan,
  fetchMyRecommendations,
  listDevelopmentPlans,
  recordActivityProgress,
} from "../../services/developmentService";
import type {
  DevelopmentActivity,
  DevelopmentPlan,
  PlanStatus,
  RecommendedResourceItem,
  StudentRecommendationsResponse,
} from "../../types/development";

const PLAN_TONE: Record<PlanStatus, "success" | "warning" | "danger" | "neutral"> = {
  proposed: "warning",
  active: "neutral",
  completed: "success",
  archived: "neutral",
};

export const EmpowermentPage: React.FC = () => {
  const [recs, setRecs] = useState<StudentRecommendationsResponse | null>(null);
  const [plans, setPlans] = useState<DevelopmentPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  const [newPlanOpen, setNewPlanOpen] = useState(false);
  const [planTitle, setPlanTitle] = useState("");
  const [planDomain, setPlanDomain] = useState("Software Development");
  const [planNotes, setPlanNotes] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [savingPlan, setSavingPlan] = useState(false);

  const [adoptResource, setAdoptResource] = useState<RecommendedResourceItem | null>(null);
  const [adoptPlanId, setAdoptPlanId] = useState("");
  const [adopting, setAdopting] = useState(false);

  const [progressTarget, setProgressTarget] = useState<DevelopmentActivity | null>(null);
  const [progressPct, setProgressPct] = useState(50);
  const [reflection, setReflection] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [savingProgress, setSavingProgress] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [recData, planPage] = await Promise.all([
        fetchMyRecommendations(),
        listDevelopmentPlans({ page: 1 }),
      ]);
      setRecs(recData);
      setPlans(planPage.results);
      if (planPage.results[0]) {
        setAdoptPlanId((prev) => prev || planPage.results[0].id);
      }
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPlan(true);
    setError(null);
    try {
      const created = await createDevelopmentPlan({
        title: planTitle,
        target_domain: planDomain,
        notes: planNotes,
        target_date: targetDate || null,
      });
      setNewPlanOpen(false);
      setPlanTitle("");
      setPlanNotes("");
      setTargetDate("");
      setAdoptPlanId(created.id);
      setBanner("Development plan proposed! Add recommended pathways or trainings below.");
      await loadAll();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSavingPlan(false);
    }
  };

  const handleAdoptResource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adoptResource) return;
    setAdopting(true);
    setError(null);
    try {
      let targetPlanId = adoptPlanId;
      if (!targetPlanId) {
        const created = await createDevelopmentPlan({
          title: `${adoptResource.target_domain} Empowerment Plan`,
          target_domain: adoptResource.target_domain,
          notes: "Created directly from evidence-cited recommendation.",
        });
        targetPlanId = created.id;
      }
      await addPlanActivity(targetPlanId, { resource_id: adoptResource.resource_id });
      setAdoptResource(null);
      setBanner(`Added "${adoptResource.title}" to your development plan.`);
      await loadAll();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setAdopting(false);
    }
  };

  const handleRecordProgress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!progressTarget) return;
    setSavingProgress(true);
    setError(null);
    try {
      await recordActivityProgress(progressTarget.id, {
        progress_percent: progressPct,
        reflection,
        evidence_url: evidenceUrl,
      });
      setProgressTarget(null);
      setReflection("");
      setEvidenceUrl("");
      setBanner("Progress & reflection saved.");
      await loadAll();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSavingProgress(false);
    }
  };

  const renderResourceSection = (
    heading: string,
    icon: React.ReactNode,
    items: RecommendedResourceItem[],
  ) => (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-semibold text-[#0F2942]">{heading}</h3>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-slate-500">No active catalogue entries in this category yet.</p>
      ) : (
        <div className="grid md:grid-cols-2 gap-3">
          {items.map((item) => (
            <div
              key={item.resource_id}
              className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 flex flex-col justify-between gap-3"
            >
              <div className="space-y-1.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-sm text-[#0F2942]">{item.title}</div>
                  {item.dimension_code && (
                    <span className="shrink-0 rounded bg-white border border-slate-200 px-1.5 py-0.5 text-[11px] font-mono text-slate-700">
                      {item.dimension_code}
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-600">
                  {item.target_domain} · <span className="capitalize">{item.level}</span> ·{" "}
                  {item.estimated_hours} hrs {item.provider ? `· ${item.provider}` : ""}
                </div>
                {item.description && <p className="text-xs text-slate-600">{item.description}</p>}
                <div className="rounded bg-teal-50 border border-teal-200/80 px-2.5 py-1.5 text-xs text-teal-900">
                  <span className="font-semibold">Why recommended:</span> {item.reason}
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    setAdoptResource(item);
                    setAdoptPlanId(plans.find((p) => p.status !== "archived")?.id || "");
                  }}
                  className="inline-flex items-center gap-1 rounded-md bg-[#0F2942] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#1E3A5F]"
                >
                  <Plus className="h-3.5 w-3.5" /> Add to Plan
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <AppShell title="My Empowerment & Roadmap">
      <div className="space-y-6">
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

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Computing evidence-cited domain & learning recommendations...
          </div>
        ) : recs ? (
          <>
            <div className="rounded-lg border border-slate-200 bg-slate-100/70 px-4 py-2.5 text-xs text-slate-700 space-y-1">
              <div>{recs.notice}</div>
              <div className="text-slate-500">{recs.advisory_note}</div>
            </div>

            {/* Domain Fit Cards */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <Compass className="h-4 w-4 text-[#0D9488]" />
                <h2 className="text-base font-semibold text-[#0F2942]">
                  Evidence-Cited Career Domain Mapping
                </h2>
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {recs.domain_recommendations.map((d) => (
                  <div
                    key={d.domain}
                    className="rounded-lg border border-slate-200 p-4 space-y-2.5 bg-white"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-semibold text-sm text-[#0F2942]">{d.domain}</div>
                      <StatusBadge
                        label={d.readiness_signal}
                        tone={
                          d.readiness_signal === "Strong Fit"
                            ? "success"
                            : d.readiness_signal.includes("Build Foundations")
                              ? "warning"
                              : "neutral"
                        }
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="rounded bg-slate-50 px-2.5 py-1.5">
                        <div className="text-slate-500">Demonstrated Avg</div>
                        <div className="font-semibold text-[#0F2942]">
                          {d.demonstrated_average !== null ? `${d.demonstrated_average}%` : "No data"}
                        </div>
                      </div>
                      <div className="rounded bg-slate-50 px-2.5 py-1.5">
                        <div className="text-slate-500">Stated Interest</div>
                        <div className="font-semibold text-[#0F2942]">
                          {d.interest_rating !== null ? `${d.interest_rating} / 5` : "No data"}
                        </div>
                      </div>
                    </div>
                    <p className="text-xs text-slate-600">{d.explanation}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Categorized Recommendations */}
            {renderResourceSection(
              "Recommended Learning Pathways",
              <BookOpen className="h-4 w-4 text-blue-700" />,
              recs.learning_pathways,
            )}
            {renderResourceSection(
              "Recommended Trainings & Remedial Workshops",
              <GraduationCap className="h-4 w-4 text-amber-600" />,
              recs.training_recommendations,
            )}
            {renderResourceSection(
              "Recommended Portfolio & Capstone Projects",
              <Briefcase className="h-4 w-4 text-[#0D9488]" />,
              recs.project_recommendations,
            )}
            {renderResourceSection(
              "Recommended Industry Certifications",
              <Award className="h-4 w-4 text-indigo-700" />,
              recs.certification_recommendations,
            )}

            {/* Development Plans & Progress */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <FolderKanban className="h-4 w-4 text-[#0D9488]" />
                  <h2 className="text-base font-semibold text-[#0F2942]">
                    My Development Plans & Progress Tracking
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => setNewPlanOpen(true)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-[#0F2942] px-3.5 py-2 text-xs font-semibold text-white hover:bg-[#1E3A5F]"
                >
                  <Plus className="h-3.5 w-3.5" /> Propose New Plan
                </button>
              </div>

              {plans.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
                  No development plans yet. Propose a plan or click "Add to Plan" on any recommendation above.
                </div>
              ) : (
                <div className="space-y-4">
                  {plans.map((plan) => (
                    <div
                      key={plan.id}
                      className="rounded-xl border border-slate-200 p-4 space-y-3 bg-slate-50/40"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-[#0F2942]">{plan.title}</h3>
                            <StatusBadge label={plan.status} tone={PLAN_TONE[plan.status]} />
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5">
                            {plan.target_domain || "General Empowerment"} · Created by{" "}
                            {plan.created_by_name}
                            {plan.target_date ? ` · Target: ${plan.target_date}` : ""}
                          </div>
                          {plan.notes && <p className="text-xs text-slate-600 mt-1">{plan.notes}</p>}
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-slate-500">Overall Completion</div>
                          <div className="text-lg font-bold text-[#0F2942]">
                            {plan.overall_progress_percent}%
                          </div>
                        </div>
                      </div>

                      {plan.activities.length === 0 ? (
                        <div className="text-xs text-slate-500 italic">
                          No activities added yet — adopt a recommendation above.
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {plan.activities.map((act) => (
                            <div
                              key={act.id}
                              className="rounded-lg border border-slate-200 bg-white p-3 flex flex-wrap items-center justify-between gap-3"
                            >
                              <div className="space-y-1 flex-1 min-w-[220px]">
                                <div className="flex items-center gap-2">
                                  <CheckCircle2
                                    className={`h-4 w-4 ${
                                      act.status === "completed"
                                        ? "text-emerald-600"
                                        : "text-slate-300"
                                    }`}
                                  />
                                  <span className="font-medium text-sm text-[#0F2942]">
                                    {act.title}
                                  </span>
                                  <StatusBadge
                                    label={`${act.progress_percent}%`}
                                    tone={
                                      act.status === "completed"
                                        ? "success"
                                        : act.status === "in_progress"
                                          ? "warning"
                                          : "neutral"
                                    }
                                  />
                                </div>
                                {act.progress_records[0]?.reflection && (
                                  <div className="text-xs text-slate-600 pl-6">
                                    Latest reflection: "{act.progress_records[0].reflection}"
                                  </div>
                                )}
                              </div>
                              <button
                                type="button"
                                onClick={() => {
                                  setProgressTarget(act);
                                  setProgressPct(act.progress_percent);
                                  setReflection("");
                                  setEvidenceUrl(act.evidence_url || "");
                                }}
                                className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-800 hover:bg-blue-100"
                              >
                                <Sparkles className="h-3.5 w-3.5" /> Update Progress
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : null}

        {/* Modal: Propose New Plan */}
        <Modal
          open={newPlanOpen}
          title="Propose Development Plan"
          subtitle="Proposed plans can be reviewed and approved by your Faculty mentor."
          onClose={() => setNewPlanOpen(false)}
        >
          <form onSubmit={handleCreatePlan} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Plan Title *</label>
              <input
                type="text"
                required
                value={planTitle}
                onChange={(e) => setPlanTitle(e.target.value)}
                placeholder="e.g., Semester 2 DSA & Backend Mastery"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Domain</label>
                <input
                  type="text"
                  value={planDomain}
                  onChange={(e) => setPlanDomain(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Date</label>
                <input
                  type="date"
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Goals & Notes</label>
              <textarea
                rows={3}
                value={planNotes}
                onChange={(e) => setPlanNotes(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setNewPlanOpen(false)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingPlan}
                className="rounded-lg bg-[#0F2942] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1E3A5F]"
              >
                {savingPlan ? "Saving..." : "Propose Plan"}
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal: Adopt Recommended Resource */}
        <Modal
          open={adoptResource !== null}
          title="Add Recommendation to Plan"
          subtitle={adoptResource?.title}
          onClose={() => setAdoptResource(null)}
        >
          <form onSubmit={handleAdoptResource} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Select Development Plan
              </label>
              <select
                value={adoptPlanId}
                onChange={(e) => setAdoptPlanId(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Create a new plan automatically</option>
                {plans
                  .filter((p) => p.status !== "archived")
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title} ({p.status})
                    </option>
                  ))}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAdoptResource(null)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={adopting}
                className="rounded-lg bg-[#0F2942] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1E3A5F]"
              >
                {adopting ? "Adding..." : "Add Activity"}
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal: Record Progress */}
        <Modal
          open={progressTarget !== null}
          title="Update Activity Progress"
          subtitle={progressTarget?.title}
          onClose={() => setProgressTarget(null)}
        >
          <form onSubmit={handleRecordProgress} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Progress Percentage ({progressPct}%)
              </label>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={progressPct}
                onChange={(e) => setProgressPct(Number(e.target.value))}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Reflection / Learning Takeaway
              </label>
              <textarea
                rows={3}
                value={reflection}
                onChange={(e) => setReflection(e.target.value)}
                placeholder="Summarize what you practiced, built, or solved..."
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Evidence URL (GitHub / Certificate / Portfolio Link)
              </label>
              <input
                type="url"
                value={evidenceUrl}
                onChange={(e) => setEvidenceUrl(e.target.value)}
                placeholder="https://..."
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setProgressTarget(null)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingProgress}
                className="rounded-lg bg-[#0F2942] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1E3A5F]"
              >
                {savingProgress ? "Saving..." : "Save Progress"}
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </AppShell>
  );
};

