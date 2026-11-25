import React, { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Copy, Eye, Lock, Plus, Trash2 } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  cloneAssessmentVersion,
  createAssessmentTemplate,
  fetchAssessmentVersion,
  listAssessmentTemplates,
  listQuestions,
  publishAssessmentVersion,
  updateDraftAssessmentVersion,
} from "../../services/assessmentsService";
import type {
  AssessmentTemplateRecord,
  AssessmentVersionDetail,
  QuestionRecord,
} from "../../types/assessments";

interface DraftItemRow {
  question_id: string;
  question_code: string;
  question_type: string;
  prompt: string;
  marks: string;
  negative_marks: string;
  required: boolean;
}

export const AssessmentBuilderPage: React.FC = () => {
  const [templates, setTemplates] = useState<AssessmentTemplateRecord[]>([]);
  const [questions, setQuestions] = useState<QuestionRecord[]>([]);
  const [activeVersion, setActiveVersion] = useState<AssessmentVersionDetail | null>(null);

  const [duration, setDuration] = useState(60);
  const [maxAttempts, setMaxAttempts] = useState(1);
  const [instructions, setInstructions] = useState("");
  const [randomizeQ, setRandomizeQ] = useState(false);
  const [randomizeOpt, setRandomizeOpt] = useState(false);
  const [draftItems, setDraftItems] = useState<DraftItemRow[]>([]);
  const [addQuestionId, setAddQuestionId] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [tName, setTName] = useState("");
  const [tDesc, setTDesc] = useState("");
  const [tDur, setTDur] = useState(60);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadTemplatesAndQuestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tRes, qRes] = await Promise.all([
        listAssessmentTemplates({ page: 1 }),
        listQuestions({ page: 1, status: "active" }),
      ]);
      setTemplates(tRes.results);
      setQuestions(qRes.results);
      if (!addQuestionId && qRes.results[0]) {
        setAddQuestionId(qRes.results[0].id);
      }
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [addQuestionId]);

  useEffect(() => {
    loadTemplatesAndQuestions();
  }, [loadTemplatesAndQuestions]);

  const openVersion = async (versionId: string) => {
    setError(null);
    setNotice(null);
    try {
      const detail = await fetchAssessmentVersion(versionId);
      setActiveVersion(detail);
      setDuration(detail.duration_minutes);
      setMaxAttempts(detail.max_attempts);
      setInstructions(detail.instructions);
      setRandomizeQ(detail.randomize_questions);
      setRandomizeOpt(detail.randomize_options);
      setDraftItems(
        detail.version_questions.map((vq) => ({
          question_id: vq.question_id,
          question_code: vq.question_code,
          question_type: vq.question_type,
          prompt: vq.prompt,
          marks: vq.marks,
          negative_marks: vq.negative_marks,
          required: vq.required,
        })),
      );
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await createAssessmentTemplate({
        name: tName.trim(),
        description: tDesc.trim(),
        duration_minutes: tDur,
      });
      setCreateOpen(false);
      setTName("");
      setTDesc("");
      await loadTemplatesAndQuestions();
      if (created.versions[0]) {
        await openVersion(created.versions[0].id);
      }
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleAddQuestion = () => {
    if (!addQuestionId) return;
    const q = questions.find((item) => item.id === addQuestionId);
    if (!q) return;
    if (draftItems.some((item) => item.question_id === q.id)) {
      setError(`Question ${q.question_code} is already in this version.`);
      return;
    }
    setError(null);
    setDraftItems((prev) => [
      ...prev,
      {
        question_id: q.id,
        question_code: q.question_code,
        question_type: q.question_type,
        prompt: q.prompt,
        marks: q.max_marks,
        negative_marks: q.negative_marks,
        required: true,
      },
    ]);
  };

  const handleSaveDraft = async () => {
    if (!activeVersion) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateDraftAssessmentVersion(activeVersion.id, {
        duration_minutes: duration,
        max_attempts: maxAttempts,
        instructions,
        randomize_questions: randomizeQ,
        randomize_options: randomizeOpt,
        items: draftItems.map((item) => ({
          question_id: item.question_id,
          marks: item.marks,
          negative_marks: item.negative_marks,
          required: item.required,
        })),
      });
      setActiveVersion(updated);
      setNotice("Draft version saved.");
      await loadTemplatesAndQuestions();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!activeVersion) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      // Save latest draft settings/items first, then publish
      await updateDraftAssessmentVersion(activeVersion.id, {
        duration_minutes: duration,
        max_attempts: maxAttempts,
        instructions,
        randomize_questions: randomizeQ,
        randomize_options: randomizeOpt,
        items: draftItems.map((item) => ({
          question_id: item.question_id,
          marks: item.marks,
          negative_marks: item.negative_marks,
          required: item.required,
        })),
      });
      const published = await publishAssessmentVersion(activeVersion.id);
      setActiveVersion(published);
      setNotice(`Version v${published.version_no} published as an immutable snapshot.`);
      await loadTemplatesAndQuestions();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const handleClone = async () => {
    if (!activeVersion) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const cloned = await cloneAssessmentVersion(activeVersion.id);
      await loadTemplatesAndQuestions();
      await openVersion(cloned.id);
      setNotice(`Cloned into editable draft v${cloned.version_no}.`);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const isDraft = activeVersion?.status === "draft";
  const computedTotal = draftItems.reduce((sum, item) => sum + Number(item.marks || 0), 0);

  return (
    <AppShell title="Assessment Builder & Versioning">
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Left column: Templates & Versions */}
        <div className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#0F2942]">Assessment Templates</h2>
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="inline-flex items-center gap-1 rounded-lg bg-[#0F2942] px-3 py-1.5 text-xs font-medium text-white"
            >
              <Plus className="h-3.5 w-3.5" />
              New Template
            </button>
          </div>

          {loading ? (
            <div className="bg-white rounded-xl border border-slate-200 p-4 text-xs text-slate-500">
              Loading templates...
            </div>
          ) : templates.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-6 text-center text-xs text-slate-500">
              No assessment templates created yet.
            </div>
          ) : (
            <div className="space-y-3">
              {templates.map((t) => (
                <div key={t.id} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-2.5">
                  <div>
                    <div className="font-semibold text-sm text-[#0F2942]">{t.name}</div>
                    {t.description && <div className="text-xs text-slate-500 mt-0.5">{t.description}</div>}
                  </div>
                  <div className="space-y-1.5">
                    {t.versions.map((v) => (
                      <button
                        key={v.id}
                        type="button"
                        onClick={() => openVersion(v.id)}
                        className={`w-full flex items-center justify-between rounded-lg border px-3 py-2 text-xs transition ${
                          activeVersion?.id === v.id
                            ? "border-blue-600 bg-blue-50"
                            : "border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <span className="font-semibold text-slate-800">
                          v{v.version_no} ({v.question_count} Qs • {v.total_marks} marks)
                        </span>
                        <StatusBadge
                          label={v.status}
                          tone={v.status === "published" ? "success" : "warning"}
                        />
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right column: Version Editor */}
        <div className="lg:col-span-8 space-y-4">
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
              {error}
            </div>
          )}
          {notice && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-800">
              {notice}
            </div>
          )}

          {!activeVersion ? (
            <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-sm text-slate-500">
              Select a template version on the left (or create a new template) to configure questions and publish.
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-[#0F2942]">
                      {activeVersion.template_name} — v{activeVersion.version_no}
                    </h3>
                    <StatusBadge
                      label={activeVersion.status}
                      tone={activeVersion.status === "published" ? "success" : "warning"}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Total Marks: <strong>{isDraft ? computedTotal.toFixed(2) : activeVersion.total_marks}</strong> • Questions:{" "}
                    <strong>{draftItems.length}</strong>
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setPreviewOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    Preview
                  </button>
                  {isDraft ? (
                    <>
                      <button
                        type="button"
                        disabled={saving}
                        onClick={handleSaveDraft}
                        className="rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-50"
                      >
                        Save Draft
                      </button>
                      <button
                        type="button"
                        disabled={saving}
                        onClick={handlePublish}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-[#0D9488] hover:bg-teal-700 px-4 py-1.5 text-xs font-medium text-white"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Publish Version
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      disabled={saving}
                      onClick={handleClone}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-1.5 text-xs font-medium text-white"
                    >
                      <Copy className="h-3.5 w-3.5" />
                      Create New Draft Version
                    </button>
                  )}
                </div>
              </div>

              {!isDraft && (
                <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900">
                  <Lock className="h-4 w-4 shrink-0" />
                  <span>
                    This published version is immutable (frozen at {activeVersion.published_at ? new Date(activeVersion.published_at).toLocaleString() : "publish"}). Clone to a new draft version to make edits.
                  </span>
                </div>
              )}

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Duration (minutes)</label>
                  <input
                    type="number"
                    min={1}
                    disabled={!isDraft}
                    value={duration}
                    onChange={(e) => setDuration(Number(e.target.value))}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Max Attempts</label>
                  <input
                    type="number"
                    min={1}
                    disabled={!isDraft}
                    value={maxAttempts}
                    onChange={(e) => setMaxAttempts(Number(e.target.value))}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">Assessment Instructions</label>
                <textarea
                  rows={2}
                  disabled={!isDraft}
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                />
              </div>

              <div className="flex flex-wrap gap-6 text-xs text-slate-700">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    disabled={!isDraft}
                    checked={randomizeQ}
                    onChange={(e) => setRandomizeQ(e.target.checked)}
                  />
                  Randomize question order per attempt
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    disabled={!isDraft}
                    checked={randomizeOpt}
                    onChange={(e) => setRandomizeOpt(e.target.checked)}
                  />
                  Randomize answer options
                </label>
              </div>

              {isDraft && (
                <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 pt-4">
                  <select
                    aria-label="Select question from bank"
                    value={addQuestionId}
                    onChange={(e) => setAddQuestionId(e.target.value)}
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-xs"
                  >
                    <option value="">Select active question from bank...</option>
                    {questions.map((q) => (
                      <option key={q.id} value={q.id}>
                        [{q.question_code}] ({q.question_type}) {q.prompt.slice(0, 70)}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleAddQuestion}
                    className="rounded-lg bg-[#0D9488] px-3.5 py-2 text-xs font-medium text-white"
                  >
                    Add Question
                  </button>
                </div>
              )}

              <div className="space-y-2">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Questions in Version ({draftItems.length})
                </div>
                {draftItems.length === 0 ? (
                  <p className="text-xs text-slate-500">No questions added to this version yet.</p>
                ) : (
                  <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg">
                    {draftItems.map((item, idx) => (
                      <div key={item.question_id} className="p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
                        <div className="min-w-0 flex-1">
                          <span className="font-mono font-semibold text-[#0F2942] mr-2">
                            #{idx + 1} {item.question_code}
                          </span>
                          <span className="text-slate-600">{item.prompt}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <label className="text-slate-500">Marks</label>
                          <input
                            type="number"
                            step="0.5"
                            min="0"
                            disabled={!isDraft}
                            value={item.marks}
                            onChange={(e) =>
                              setDraftItems((prev) =>
                                prev.map((row, i) => (i === idx ? { ...row, marks: e.target.value } : row)),
                              )
                            }
                            className="w-16 rounded border border-slate-300 px-2 py-1 text-xs"
                          />
                          {isDraft && (
                            <button
                              type="button"
                              onClick={() =>
                                setDraftItems((prev) => prev.filter((_, i) => i !== idx))
                              }
                              className="text-rose-600 p-1"
                              aria-label="Remove question"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Template Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Create Assessment Template">
        <form className="space-y-4" onSubmit={handleCreateTemplate}>
          <div>
            <label className="block text-xs font-medium text-slate-700">Template Name</label>
            <input type="text" required value={tName} onChange={(e) => setTName(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Description</label>
            <textarea rows={2} value={tDesc} onChange={(e) => setTDesc(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Initial Duration (minutes)</label>
            <input type="number" min={1} required value={tDur} onChange={(e) => setTDur(Number(e.target.value))} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setCreateOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">Create Template</button>
          </div>
        </form>
      </Modal>

      {/* Preview Modal */}
      <Modal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        title={activeVersion ? `Assessment Preview — ${activeVersion.template_name} (v${activeVersion.version_no})` : "Preview"}
        subtitle={`Duration: ${duration} min • Max Attempts: ${maxAttempts}`}
      >
        <div className="space-y-4 text-xs">
          {instructions && (
            <div className="rounded-lg bg-slate-50 border border-slate-200 p-3 text-slate-700">
              <strong>Instructions:</strong> {instructions}
            </div>
          )}
          {draftItems.map((item, idx) => (
            <div key={item.question_id} className="rounded-lg border border-slate-200 p-3 space-y-1">
              <div className="flex justify-between font-semibold text-[#0F2942]">
                <span>Q{idx + 1}. {item.question_code}</span>
                <span>{item.marks} marks</span>
              </div>
              <p className="text-slate-700">{item.prompt}</p>
            </div>
          ))}
        </div>
      </Modal>
    </AppShell>
  );
};

