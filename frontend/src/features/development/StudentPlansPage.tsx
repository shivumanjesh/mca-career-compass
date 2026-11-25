import React, { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Compass, FolderKanban, Plus, UserCheck } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  addPlanActivity,
  createDevelopmentPlan,
  fetchStudentRecommendations,
  listDevelopmentPlans,
  listDevelopmentStudents,
  updateDevelopmentPlan,
} from "../../services/developmentService";
import type {
  DevelopmentPlan,
  DevelopmentStudentOption,
  LearningResourceType,
  PlanStatus,
  StudentRecommendationsResponse,
} from "../../types/development";

const PLAN_TONE: Record<PlanStatus, "success" | "warning" | "danger" | "neutral"> = {
  proposed: "warning",
  active: "neutral",
  completed: "success",
  archived: "neutral",
};

export const StudentPlansPage: React.FC = () => {
  const [students, setStudents] = useState<DevelopmentStudentOption[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [recs, setRecs] = useState<StudentRecommendationsResponse | null>(null);
  const [plans, setPlans] = useState<DevelopmentPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  const [newPlanOpen, setNewPlanOpen] = useState(false);
  const [planTitle, setPlanTitle] = useState("");
  const [planDomain, setPlanDomain] = useState("Software Development");
  const [planNotes, setPlanNotes] = useState("");
  const [savingPlan, setSavingPlan] = useState(false);

  const [milestonePlan, setMilestonePlan] = useState<DevelopmentPlan | null>(null);
  const [milestoneTitle, setMilestoneTitle] = useState("");
  const [milestoneType, setMilestoneType] = useState<LearningResourceType>("milestone");
  const [milestoneDue, setMilestoneDue] = useState("");
  const [savingMilestone, setSavingMilestone] = useState(false);

  const loadStudents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listDevelopmentStudents();
      setStudents(list);
      if (list[0]) {
        setSelectedStudentId((prev) => prev || list[0].id);
      }
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  const loadStudentWorkspace = useCallback(async (studentId: string) => {
    if (!studentId) return;
    setDetailLoading(true);
    setError(null);
    try {
      const [recData, planPage] = await Promise.all([
        fetchStudentRecommendations(studentId),
        listDevelopmentPlans({ student_id: studentId }),
      ]);
      setRecs(recData);
      setPlans(planPage.results);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedStudentId) {
      loadStudentWorkspace(selectedStudentId);
    }
  }, [selectedStudentId, loadStudentWorkspace]);

  const handleCreateMentoredPlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStudentId) return;
    setSavingPlan(true);
    setError(null);
    try {
      await createDevelopmentPlan({
        student_id: selectedStudentId,
        title: planTitle,
        target_domain: planDomain,
        notes: planNotes,
      });
      setNewPlanOpen(false);
      setPlanTitle("");
      setPlanNotes("");
      setBanner("Mentored development plan created.");
      await loadStudentWorkspace(selectedStudentId);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSavingPlan(false);
    }
  };

  const handleApprovePlan = async (planId: string) => {
    try {
      await updateDevelopmentPlan(planId, { status: "active" });
      setBanner("Proposed student plan approved to Active.");
      await loadStudentWorkspace(selectedStudentId);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleAssignRecommended = async (resourceId: string, title: string) => {
    const activePlan = plans.find((p) => p.status === "active" || p.status === "proposed");
    try {
      let planId = activePlan?.id;
      if (!planId) {
        const created = await createDevelopmentPlan({
          student_id: selectedStudentId,
          title: "Faculty Mentored Development Plan",
          target_domain: recs?.domain_recommendations[0]?.domain || "Software Development",
        });
        planId = created.id;
      }
      await addPlanActivity(planId, { resource_id: resourceId });
      setBanner(`Assigned "${title}" to student plan.`);
      await loadStudentWorkspace(selectedStudentId);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleAddCustomMilestone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!milestonePlan) return;
    setSavingMilestone(true);
    try {
      await addPlanActivity(milestonePlan.id, {
        title: milestoneTitle,
        activity_type: milestoneType,
        due_date: milestoneDue || null,
      });
      setMilestonePlan(null);
      setMilestoneTitle("");
      setMilestoneDue("");
      setBanner("Custom milestone added to plan.");
      await loadStudentWorkspace(selectedStudentId);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSavingMilestone(false);
    }
  };

  return (
    <AppShell title="Student Mentorship & Development Plans">
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Authorized Student
            </label>
            <select
              value={selectedStudentId}
              onChange={(e) => setSelectedStudentId(e.target.value)}
              disabled={loading || students.length === 0}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-[#0F2942] min-w-[280px]"
            >
              {students.length === 0 ? (
                <option value="">No authorized students available</option>
              ) : (
                students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.registration_no} — {s.full_name} {s.cohort_label ? `(${s.cohort_label})` : ""}
                  </option>
                ))
              )}
            </select>
          </div>
          {selectedStudentId && (
            <button
              type="button"
              onClick={() => setNewPlanOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#0F2942] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1E3A5F]"
            >
              <Plus className="h-3.5 w-3.5" /> Create Mentored Plan
            </button>
          )}
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

        {detailLoading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-sm text-slate-500">
            Loading student recommendations and development plans...
          </div>
        ) : recs ? (
          <>
            {/* Domain Signals & Quick Assign Recommendations */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <Compass className="h-4 w-4 text-[#0D9488]" />
                <h2 className="text-base font-semibold text-[#0F2942]">
                  Evidence-Cited Domain Signals — {recs.student.full_name} ({recs.student.registration_no})
                </h2>
              </div>
              <div className="grid md:grid-cols-3 gap-3">
                {recs.domain_recommendations.slice(0, 3).map((d) => (
                  <div key={d.domain} className="rounded-lg border border-slate-200 p-3.5 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-sm text-[#0F2942]">{d.domain}</span>
                      <StatusBadge label={d.readiness_signal} tone="neutral" />
                    </div>
                    <p className="text-xs text-slate-600">{d.explanation}</p>
                  </div>
                ))}
              </div>

              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
                  Top Recommended Trainings & Pathways (Click to Assign)
                </h3>
                <div className="grid md:grid-cols-2 gap-3">
                  {[...recs.training_recommendations.slice(0, 2), ...recs.learning_pathways.slice(0, 2)].map(
                    (item) => (
                      <div
                        key={item.resource_id}
                        className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 flex items-center justify-between gap-3"
                      >
                        <div className="space-y-0.5">
                          <div className="font-semibold text-xs text-[#0F2942]">{item.title}</div>
                          <div className="text-[11px] text-teal-800">{item.reason}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleAssignRecommended(item.resource_id, item.title)}
                          className="shrink-0 rounded-md border border-[#0F2942] px-2.5 py-1 text-xs font-semibold text-[#0F2942] hover:bg-[#0F2942] hover:text-white"
                        >
                          Assign
                        </button>
                      </div>
                    ),
                  )}
                </div>
              </div>
            </div>

            {/* Plans List */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <FolderKanban className="h-4 w-4 text-[#0D9488]" />
                <h2 className="text-base font-semibold text-[#0F2942]">
                  Development Plans & Student Reflections
                </h2>
              </div>

              {plans.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
                  No development plans created for this student yet.
                </div>
              ) : (
                <div className="space-y-4">
                  {plans.map((plan) => (
                    <div key={plan.id} className="rounded-xl border border-slate-200 p-4 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-[#0F2942]">{plan.title}</h3>
                            <StatusBadge label={plan.status} tone={PLAN_TONE[plan.status]} />
                          </div>
                          <div className="text-xs text-slate-500">
                            {plan.target_domain || "General"} · Overall {plan.overall_progress_percent}%
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {plan.status === "proposed" && (
                            <button
                              type="button"
                              onClick={() => handleApprovePlan(plan.id)}
                              className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
                            >
                              <UserCheck className="h-3.5 w-3.5" /> Approve to Active
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => setMilestonePlan(plan)}
                            className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                          >
                            <Plus className="h-3.5 w-3.5" /> Add Milestone
                          </button>
                        </div>
                      </div>

                      {plan.activities.length > 0 && (
                        <div className="space-y-2">
                          {plan.activities.map((act) => (
                            <div
                              key={act.id}
                              className="rounded-lg border border-slate-200 bg-slate-50/50 p-3 space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 text-sm font-medium text-[#0F2942]">
                                  <CheckCircle2
                                    className={`h-4 w-4 ${
                                      act.status === "completed" ? "text-emerald-600" : "text-slate-300"
                                    }`}
                                  />
                                  <span>{act.title}</span>
                                </div>
                                <StatusBadge
                                  label={`${act.progress_percent}% (${act.status})`}
                                  tone={act.status === "completed" ? "success" : "neutral"}
                                />
                              </div>
                              {act.progress_records.length > 0 && (
                                <div className="text-xs text-slate-600 pl-6">
                                  Latest update by {act.progress_records[0].recorded_by_name}:{" "}
                                  {act.progress_records[0].reflection || "Progress logged"}
                                </div>
                              )}
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

        <Modal
          open={newPlanOpen}
          title="Create Mentored Development Plan"
          onClose={() => setNewPlanOpen(false)}
        >
          <form onSubmit={handleCreateMentoredPlan} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Plan Title *</label>
              <input
                type="text"
                required
                value={planTitle}
                onChange={(e) => setPlanTitle(e.target.value)}
                placeholder="e.g., DSA & System Foundations Mentorship"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
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
              <label className="block text-xs font-semibold text-slate-700 mb-1">Mentor Notes</label>
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
                {savingPlan ? "Saving..." : "Create Plan"}
              </button>
            </div>
          </form>
        </Modal>

        <Modal
          open={milestonePlan !== null}
          title="Add Custom Milestone / Activity"
          subtitle={milestonePlan?.title}
          onClose={() => setMilestonePlan(null)}
        >
          <form onSubmit={handleAddCustomMilestone} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Activity Title *</label>
              <input
                type="text"
                required
                value={milestoneTitle}
                onChange={(e) => setMilestoneTitle(e.target.value)}
                placeholder="e.g., Weekly Coding Mock Interview"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Activity Type</label>
                <select
                  value={milestoneType}
                  onChange={(e) => setMilestoneType(e.target.value as LearningResourceType)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="milestone">Custom Milestone</option>
                  <option value="training">Training / Workshop</option>
                  <option value="project">Hands-on Project</option>
                  <option value="learning_pathway">Learning Pathway</option>
                  <option value="certification">Certification</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Due Date</label>
                <input
                  type="date"
                  value={milestoneDue}
                  onChange={(e) => setMilestoneDue(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setMilestonePlan(null)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingMilestone}
                className="rounded-lg bg-[#0F2942] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1E3A5F]"
              >
                {savingMilestone ? "Adding..." : "Add Activity"}
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </AppShell>
  );
};

