import React, { useCallback, useEffect, useState } from "react";
import { Plus, Search, Trash2 } from "lucide-react";
import { AppShell } from "../../components/AppShell";
import { DataTable, type ColumnDef } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { parseApiError } from "../../services/apiClient";
import {
  createQuestion,
  listAssessmentDimensions,
  listQuestions,
  updateQuestion,
} from "../../services/assessmentsService";
import type {
  AssessmentDimensionRecord,
  LifecycleStatus,
  MeasurementFamily,
  QuestionDifficulty,
  QuestionOptionInput,
  QuestionRecord,
  QuestionType,
  ScoringMethod,
} from "../../types/assessments";

const QUESTION_TYPES: Array<{ value: QuestionType; label: string }> = [
  { value: "single_mcq", label: "Single Choice MCQ" },
  { value: "multiple_mcq", label: "Multiple Choice MCQ" },
  { value: "true_false", label: "True / False" },
  { value: "numeric", label: "Numeric Response" },
  { value: "likert", label: "Likert Scale" },
  { value: "self_rating", label: "Self-Rating" },
  { value: "situational_judgement", label: "Situational Judgement" },
  { value: "descriptive", label: "Descriptive" },
  { value: "coding", label: "Coding Task" },
];

const OPTION_BASED_TYPES = new Set<QuestionType>([
  "single_mcq",
  "multiple_mcq",
  "true_false",
  "likert",
  "self_rating",
  "situational_judgement",
]);

export const QuestionBankPage: React.FC = () => {
  const [rows, setRows] = useState<QuestionRecord[]>([]);
  const [dimensions, setDimensions] = useState<AssessmentDimensionRecord[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [familyFilter, setFamilyFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create / Edit Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<QuestionRecord | null>(null);
  const [qCode, setQCode] = useState("");
  const [qType, setQType] = useState<QuestionType>("single_mcq");
  const [prompt, setPrompt] = useState("");
  const [difficulty, setDifficulty] = useState<QuestionDifficulty>("medium");
  const [family, setFamily] = useState<MeasurementFamily>("demonstrated_performance");
  const [scoringMethod, setScoringMethod] = useState<ScoringMethod>("exact");
  const [maxMarks, setMaxMarks] = useState("2.00");
  const [negMarks, setNegMarks] = useState("0.00");
  const [dimensionId, setDimensionId] = useState("");
  const [numericValue, setNumericValue] = useState("0");
  const [numericTolerance, setNumericTolerance] = useState("0");
  const [rubricGuidance, setRubricGuidance] = useState("");
  const [options, setOptions] = useState<QuestionOptionInput[]>([
    { option_key: "A", option_text: "", display_order: 1, is_correct: true },
    { option_key: "B", option_text: "", display_order: 2, is_correct: false },
  ]);
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [qRes, dRes] = await Promise.all([
        listQuestions({
          page,
          search: search.trim() || undefined,
          question_type: typeFilter || undefined,
          measurement_family: familyFilter || undefined,
        }),
        listAssessmentDimensions({ page: 1, status: "active" }),
      ]);
      setRows(qRes.results);
      setCount(qRes.count);
      setDimensions(dRes.results);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [page, search, typeFilter, familyFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const compatibleDims = dimensions.filter((d) => d.measurement_family === family);

  const handleFamilyChange = (nextFamily: MeasurementFamily) => {
    setFamily(nextFamily);
    const firstMatch = dimensions.find((d) => d.measurement_family === nextFamily);
    setDimensionId(firstMatch?.id || "");
  };

  const handleTypeChange = (nextType: QuestionType) => {
    setQType(nextType);
    if (nextType === "likert" || nextType === "self_rating") {
      setScoringMethod("likert_scale");
      if (family === "demonstrated_performance") {
        handleFamilyChange("self_reported_proficiency");
      }
      setOptions([
        { option_key: "1", option_text: "Strongly Disagree / Novice", display_order: 1, is_correct: false },
        { option_key: "2", option_text: "Disagree / Developing", display_order: 2, is_correct: false },
        { option_key: "3", option_text: "Neutral / Intermediate", display_order: 3, is_correct: false },
        { option_key: "4", option_text: "Agree / Proficient", display_order: 4, is_correct: false },
        { option_key: "5", option_text: "Strongly Agree / Expert", display_order: 5, is_correct: false },
      ]);
    } else if (nextType === "true_false") {
      setScoringMethod("exact");
      setOptions([
        { option_key: "T", option_text: "True", display_order: 1, is_correct: true },
        { option_key: "F", option_text: "False", display_order: 2, is_correct: false },
      ]);
    } else if (nextType === "numeric") {
      setScoringMethod("tolerance");
    } else if (nextType === "descriptive" || nextType === "coding") {
      setScoringMethod("rubric");
    } else {
      setScoringMethod("exact");
    }
  };

  const openCreate = () => {
    setEditing(null);
    setQCode("");
    setPrompt("");
    setDifficulty("medium");
    const defaultFamily: MeasurementFamily = "demonstrated_performance";
    setFamily(defaultFamily);
    setQType("single_mcq");
    setScoringMethod("exact");
    setMaxMarks("2.00");
    setNegMarks("0.00");
    setDimensionId(dimensions.find((d) => d.measurement_family === defaultFamily)?.id || "");
    setOptions([
      { option_key: "A", option_text: "", display_order: 1, is_correct: true },
      { option_key: "B", option_text: "", display_order: 2, is_correct: false },
    ]);
    setRubricGuidance("");
    setModalError(null);
    setModalOpen(true);
  };

  const openEdit = (q: QuestionRecord) => {
    setEditing(q);
    setQCode(q.question_code);
    setQType(q.question_type);
    setPrompt(q.prompt);
    setDifficulty(q.difficulty);
    setFamily(q.measurement_family);
    setScoringMethod(q.scoring_method);
    setMaxMarks(q.max_marks);
    setNegMarks(q.negative_marks);
    setDimensionId(q.dimensions[0]?.dimension_id || "");
    setOptions(
      q.options.length > 0
        ? q.options
        : [
            { option_key: "A", option_text: "", display_order: 1, is_correct: true },
            { option_key: "B", option_text: "", display_order: 2, is_correct: false },
          ],
    );
    setNumericValue(String(q.scoring_config?.correct_value ?? "0"));
    setNumericTolerance(String(q.scoring_config?.tolerance ?? "0"));
    setRubricGuidance(q.rubric?.evaluator_guidance || "");
    setModalError(null);
    setModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dimensionId) {
      setModalError("Select a compatible Assessment Dimension.");
      return;
    }
    setSaving(true);
    setModalError(null);

    const payload = {
      question_code: qCode.trim().toUpperCase(),
      question_type: qType,
      prompt: prompt.trim(),
      difficulty,
      measurement_family: family,
      scoring_method: scoringMethod,
      max_marks: maxMarks,
      negative_marks: negMarks,
      scoring_config:
        qType === "numeric"
          ? { correct_value: Number(numericValue), tolerance: Number(numericTolerance || 0) }
          : {},
      options: OPTION_BASED_TYPES.has(qType) ? options : [],
      rubric:
        qType === "descriptive" || qType === "coding"
          ? {
              rubric_json: { criteria: ["Correctness & Clarity"] },
              max_marks: Number(maxMarks),
              evaluator_guidance: rubricGuidance.trim(),
            }
          : null,
      dimensions: [{ dimension_id: dimensionId, weight: "1.00" }],
    };

    try {
      if (editing) {
        await updateQuestion(editing.id, payload);
      } else {
        await createQuestion(payload);
      }
      setModalOpen(false);
      await loadData();
    } catch (err) {
      setModalError(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  const toggleArchive = async (q: QuestionRecord) => {
    const nextStatus: LifecycleStatus = q.status === "active" ? "archived" : "active";
    try {
      await updateQuestion(q.id, { status: nextStatus });
      await loadData();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const columns: ColumnDef<QuestionRecord>[] = [
    {
      key: "code",
      header: "Question",
      render: (r) => (
        <div className="max-w-md">
          <div className="font-mono text-xs font-semibold text-[#0F2942]">{r.question_code}</div>
          <div className="text-sm text-slate-800 line-clamp-2">{r.prompt}</div>
        </div>
      ),
    },
    {
      key: "type",
      header: "Type / Difficulty",
      render: (r) => (
        <div className="text-xs">
          <div className="font-medium text-slate-800">{r.question_type.replaceAll("_", " ")}</div>
          <div className="text-slate-500 capitalize">{r.difficulty}</div>
        </div>
      ),
    },
    {
      key: "dimensions",
      header: "Dimensions & Family",
      render: (r) => (
        <div className="space-y-1">
          <div className="flex flex-wrap gap-1">
            {r.dimensions.map((d) => (
              <StatusBadge key={d.dimension_id} label={d.code || "DIM"} tone="neutral" />
            ))}
          </div>
          <div className="text-[11px] text-slate-500">{r.measurement_family.replaceAll("_", " ")}</div>
        </div>
      ),
    },
    {
      key: "marks",
      header: "Marks",
      render: (r) => (
        <span className="text-xs font-medium text-slate-700">
          +{r.max_marks} {Number(r.negative_marks) > 0 ? `/ -${r.negative_marks}` : ""}
        </span>
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
            onClick={() => openEdit(r)}
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => toggleArchive(r)}
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700"
          >
            {r.status === "active" ? "Archive" : "Restore"}
          </button>
        </div>
      ),
    },
  ];

  return (
    <AppShell title="Question Bank">
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
                placeholder="Search code or prompt..."
                className="pl-9 pr-3 py-2 rounded-lg border border-slate-300 bg-white text-sm w-60"
              />
            </div>
            <select
              aria-label="Filter by question type"
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All Question Types</option>
              {QUESTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <select
              aria-label="Filter by measurement family"
              value={familyFilter}
              onChange={(e) => {
                setFamilyFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All Families</option>
              <option value="demonstrated_performance">Demonstrated Performance</option>
              <option value="self_reported_proficiency">Self-Reported Proficiency</option>
              <option value="stated_interest">Stated Career Interest</option>
            </select>
          </div>

          <button
            type="button"
            onClick={openCreate}
            className="inline-flex items-center gap-2 rounded-lg bg-[#0F2942] hover:bg-[#1E3A5F] px-4 py-2 text-sm font-medium text-white"
          >
            <Plus className="h-4 w-4" />
            New Question
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
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
          emptyTitle="No questions in bank yet"
          emptyDescription="Create dimensions first, then add MCQ, numeric, Likert, coding, or descriptive questions."
        />
      </div>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit Question — ${editing.question_code}` : "Create Question"}
        subtitle="Questions link exclusively to dimensions within the same measurement family."
      >
        <form className="space-y-4" onSubmit={handleSave}>
          {modalError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {modalError}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700">Question Code</label>
              <input
                type="text"
                required
                value={qCode}
                onChange={(e) => setQCode(e.target.value.toUpperCase())}
                placeholder="e.g. DSA_001"
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm uppercase"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Question Type</label>
              <select
                value={qType}
                onChange={(e) => handleTypeChange(e.target.value as QuestionType)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {QUESTION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700">Measurement Family</label>
              <select
                value={family}
                onChange={(e) => handleFamilyChange(e.target.value as MeasurementFamily)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="demonstrated_performance">Demonstrated Performance</option>
                <option value="self_reported_proficiency">Self-Reported Proficiency</option>
                <option value="stated_interest">Stated Career Interest</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Assessment Dimension</label>
              <select
                required
                value={dimensionId}
                onChange={(e) => setDimensionId(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select Matching Dimension</option>
                {compatibleDims.map((d) => (
                  <option key={d.id} value={d.id}>{d.code} — {d.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700">Question Prompt</label>
            <textarea
              rows={3}
              required
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as QuestionDifficulty)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Max Marks</label>
              <input
                type="number"
                step="0.5"
                min="0"
                required
                value={maxMarks}
                onChange={(e) => setMaxMarks(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Negative Marks</label>
              <input
                type="number"
                step="0.25"
                min="0"
                required
                value={negMarks}
                onChange={(e) => setNegMarks(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          {OPTION_BASED_TYPES.has(qType) && (
            <div className="space-y-2 border-t border-slate-200 pt-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700">Answer Options</span>
                <button
                  type="button"
                  onClick={() =>
                    setOptions((prev) => [
                      ...prev,
                      {
                        option_key: String.fromCharCode(65 + prev.length),
                        option_text: "",
                        display_order: prev.length + 1,
                        is_correct: false,
                      },
                    ])
                  }
                  className="text-xs font-medium text-blue-700 hover:underline"
                >
                  + Add Option
                </button>
              </div>
              {options.map((opt, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    type="text"
                    required
                    value={opt.option_key}
                    onChange={(e) =>
                      setOptions((prev) =>
                        prev.map((o, i) => (i === idx ? { ...o, option_key: e.target.value } : o)),
                      )
                    }
                    className="w-12 rounded border border-slate-300 px-2 py-1.5 text-xs font-mono"
                  />
                  <input
                    type="text"
                    required
                    value={opt.option_text}
                    onChange={(e) =>
                      setOptions((prev) =>
                        prev.map((o, i) => (i === idx ? { ...o, option_text: e.target.value } : o)),
                      )
                    }
                    placeholder="Option text..."
                    className="flex-1 rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                  {qType !== "likert" && qType !== "self_rating" && (
                    <label className="flex items-center gap-1 text-xs text-slate-700">
                      <input
                        type="checkbox"
                        checked={opt.is_correct}
                        onChange={(e) =>
                          setOptions((prev) =>
                            prev.map((o, i) => (i === idx ? { ...o, is_correct: e.target.checked } : o)),
                          )
                        }
                      />
                      Correct
                    </label>
                  )}
                  {options.length > 2 && (
                    <button
                      type="button"
                      onClick={() => setOptions((prev) => prev.filter((_, i) => i !== idx))}
                      className="text-rose-600 p-1"
                      aria-label="Remove option"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {qType === "numeric" && (
            <div className="grid grid-cols-2 gap-3 border-t border-slate-200 pt-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Expected Numeric Value</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={numericValue}
                  onChange={(e) => setNumericValue(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Tolerance (+/-)</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={numericTolerance}
                  onChange={(e) => setNumericTolerance(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          )}

          {(qType === "descriptive" || qType === "coding") && (
            <div className="border-t border-slate-200 pt-3">
              <label className="block text-xs font-medium text-slate-700">Evaluator Rubric Guidance</label>
              <textarea
                rows={2}
                required
                value={rubricGuidance}
                onChange={(e) => setRubricGuidance(e.target.value)}
                placeholder="Outline key evaluation criteria and mark distribution..."
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#0F2942] px-4 py-2 text-sm font-medium text-white">
              {saving ? "Saving..." : editing ? "Save Question" : "Create Question"}
            </button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
};

