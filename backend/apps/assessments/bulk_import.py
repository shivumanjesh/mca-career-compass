"""Bulk XLSX/CSV Question Bank template generator, validator, preview, and atomic commit."""
import csv
import io
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from rest_framework.exceptions import ValidationError

from apps.assessments.models import AssessmentDimension, MeasurementFamily, Question
from apps.assessments.services import _validate_question_scoring_and_dimensions, create_question
from apps.audit.services import log_audit_event
from apps.tenancy.models import Institution

MAX_BULK_QUESTION_ROWS = 500

TEMPLATE_HEADERS = [
    "question_code",
    "question_type",
    "prompt",
    "measurement_family",
    "dimension_code",
    "max_marks",
    "negative_marks",
    "difficulty",
    "scoring_method",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "correct_options",
    "correct_numeric_value",
    "numeric_tolerance",
    "rubric_guidance",
    "tags",
]

SAMPLE_ROWS = [
    [
        "BULK_PROG_01",
        "single_mcq",
        "Which built-in Python data structure guarantees O(1) average-case key lookup?",
        "demonstrated_performance",
        "PROG",
        2,
        0.5,
        "easy",
        "exact",
        "Dictionary (dict)",
        "List (list)",
        "Tuple (tuple)",
        "Deque",
        "",
        "A",
        "",
        "",
        "",
        "python,data-structures",
    ],
    [
        "BULK_DSA_01",
        "true_false",
        "Breadth-First Search (BFS) uses a Queue to explore vertices level by level.",
        "demonstrated_performance",
        "DSA",
        1,
        0,
        "easy",
        "exact",
        "",
        "",
        "",
        "",
        "",
        "TRUE",
        "",
        "",
        "",
        "graphs,bfs",
    ],
    [
        "BULK_NUM_01",
        "numeric",
        "How many edges does a tree with 15 vertices contain?",
        "demonstrated_performance",
        "DSA",
        2,
        0,
        "medium",
        "tolerance",
        "",
        "",
        "",
        "",
        "",
        "",
        14,
        0,
        "",
        "trees",
    ],
    [
        "BULK_DBMS_01",
        "descriptive",
        "Explain the difference between Second Normal Form (2NF) and Third Normal Form (3NF) with an example.",
        "demonstrated_performance",
        "DBMS",
        5,
        0,
        "medium",
        "rubric",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "Award 2 marks for 2NF (partial dependency), 2 marks for 3NF (transitive dependency), 1 mark for valid example.",
        "normalization,sql",
    ],
    [
        "BULK_INT_SDE",
        "likert",
        "Rate your interest in pursuing a Software Development Engineering (SDE) career track.",
        "stated_interest",
        "INT_SDE",
        5,
        0,
        "easy",
        "likert_scale",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "career-interest",
    ],
]

DEFAULT_SCORING_BY_TYPE = {
    Question.QuestionType.SINGLE_MCQ: Question.ScoringMethod.EXACT,
    Question.QuestionType.TRUE_FALSE: Question.ScoringMethod.EXACT,
    Question.QuestionType.MULTIPLE_MCQ: Question.ScoringMethod.PARTIAL_CREDIT,
    Question.QuestionType.NUMERIC: Question.ScoringMethod.TOLERANCE,
    Question.QuestionType.LIKERT: Question.ScoringMethod.LIKERT_SCALE,
    Question.QuestionType.SELF_RATING: Question.ScoringMethod.LIKERT_SCALE,
    Question.QuestionType.SITUATIONAL_JUDGEMENT: Question.ScoringMethod.PARTIAL_CREDIT,
    Question.QuestionType.DESCRIPTIVE: Question.ScoringMethod.RUBRIC,
    Question.QuestionType.CODING: Question.ScoringMethod.RUBRIC,
}

DEFAULT_LIKERT_LABELS = [
    ("1", "Strongly Disagree / Very Low"),
    ("2", "Disagree / Low"),
    ("3", "Neutral / Moderate"),
    ("4", "Agree / High"),
    ("5", "Strongly Agree / Very High"),
]


def build_question_template_xlsx() -> bytes:
    """Build a styled Excel (.xlsx) template with examples and instructions for bulk question authoring."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Questions"

    header_fill = PatternFill(start_color="0F2942", end_color="0F2942", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    ws.append(TEMPLATE_HEADERS)
    for col_idx in range(1, len(TEMPLATE_HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        ws.column_dimensions[cell.column_letter].width = 22

    for row in SAMPLE_ROWS:
        ws.append(row)

    inst_ws = wb.create_sheet(title="Instructions")
    inst_ws.append(["Column", "Required", "Accepted Values / Notes"])
    notes = [
        ("question_code", "Yes", "Unique uppercase code per institution (e.g. PROG_Q01)."),
        ("question_type", "Yes", "single_mcq, multiple_mcq, true_false, numeric, likert, self_rating, situational_judgement, descriptive, coding"),
        ("prompt", "Yes", "Full question text displayed to students."),
        ("measurement_family", "Yes", "demonstrated_performance, self_reported_proficiency, or stated_interest (must match linked dimension)."),
        ("dimension_code", "Yes", "Active dimension code (e.g. PROG) or weighted list (e.g. PROG:1.0,DSA:0.5)."),
        ("max_marks", "Yes", "Non-negative marks (e.g. 2 or 5)."),
        ("negative_marks", "No", "Default 0."),
        ("difficulty", "No", "easy, medium (default), or hard."),
        ("scoring_method", "No", "Auto-inferred from question_type if blank (exact, partial_credit, tolerance, likert_scale, rubric)."),
        ("option_a .. option_e", "Conditional", "Required for MCQ/SJT. Optional for true_false (auto TRUE/FALSE) and likert/self_rating (auto 1-5 scale)."),
        ("correct_options", "Conditional", "Option keys for MCQ/T-F (e.g. A, A,C, TRUE, or FALSE)."),
        ("correct_numeric_value", "Conditional", "Required when question_type = numeric."),
        ("numeric_tolerance", "No", "Allowed +/- tolerance for numeric questions (default 0)."),
        ("rubric_guidance", "No", "Evaluator rubric instructions for descriptive/coding questions."),
        ("tags", "No", "Comma-separated tags (e.g. python,loops)."),
    ]
    for item in notes:
        inst_ws.append(list(item))

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def build_question_template_csv() -> str:
    """Build a CSV starter template with the same sample rows."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TEMPLATE_HEADERS)
    for row in SAMPLE_ROWS:
        writer.writerow(row)
    return buf.getvalue()


def _read_uploaded_rows(uploaded_file) -> list[tuple[int, dict[str, str]]]:
    if uploaded_file is None:
        raise ValidationError({"file": "Please upload a .xlsx or .csv file."})

    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in {".xlsx", ".csv"}:
        raise ValidationError({"file": "Only .xlsx and .csv files are supported."})

    if uploaded_file.size > settings.MAX_IMPORT_FILE_SIZE_BYTES:
        max_mb = settings.MAX_IMPORT_FILE_SIZE_BYTES // (1024 * 1024)
        raise ValidationError({"file": f"File exceeds maximum allowed size of {max_mb} MB."})

    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    if not file_bytes:
        raise ValidationError({"file": "Uploaded file is empty."})

    if ext == ".xlsx":
        if not file_bytes.startswith(b"PK"):
            raise ValidationError({"file": "Uploaded .xlsx file is invalid or corrupted."})
        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        try:
            if not wb.sheetnames:
                raise ValidationError({"file": "Workbook contains no sheets."})
            ws = wb[wb.sheetnames[0]]
            raw_iter = ws.iter_rows(values_only=True)
            return _normalize_table_rows(raw_iter)
        finally:
            wb.close()

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")
    return _normalize_table_rows(csv.reader(io.StringIO(text)))


def _normalize_table_rows(rows_iter) -> list[tuple[int, dict[str, str]]]:
    headers: list[str] = []
    parsed_rows: list[tuple[int, dict[str, str]]] = []
    for idx, row in enumerate(rows_iter, start=1):
        cells = ["" if v is None else str(v).strip() for v in row]
        if idx == 1:
            headers = ["_".join(c.strip().lower().replace("-", "_").split()) for c in cells]
            if not any(headers):
                raise ValidationError({"file": "Header row is empty."})
            continue
        if not any(cells):
            continue
        row_dict = {
            headers[col_i]: (cells[col_i] if col_i < len(cells) else "")
            for col_i in range(len(headers))
            if headers[col_i]
        }
        parsed_rows.append((idx, row_dict))
        if len(parsed_rows) > MAX_BULK_QUESTION_ROWS:
            raise ValidationError({"file": f"Maximum {MAX_BULK_QUESTION_ROWS} questions per bulk import batch."})

    if not parsed_rows:
        raise ValidationError({"file": "No question rows found beneath the header row."})
    return parsed_rows


def _parse_dimension_links(raw_dim: str, dim_by_code: dict[str, AssessmentDimension]) -> list[dict]:
    if not raw_dim:
        raise ValidationError({"dimension_code": "dimension_code is required."})
    links = []
    for token in raw_dim.split(","):
        part = token.strip()
        if not part:
            continue
        if ":" in part:
            code_part, weight_part = part.split(":", 1)
            code = code_part.strip().upper()
            try:
                weight = Decimal(weight_part.strip())
            except InvalidOperation as exc:
                raise ValidationError({"dimension_code": f"Invalid weight for dimension '{code}'."}) from exc
        else:
            code = part.upper()
            weight = Decimal("1.00")

        dim = dim_by_code.get(code)
        if dim is None:
            raise ValidationError({"dimension_code": f"Active dimension code '{code}' not found in institution."})
        links.append({"dimension_id": dim.id, "weight": weight, "code": code})
    return links


def _build_options_from_row(question_type: str, row: dict[str, str]) -> list[dict]:
    correct_raw = row.get("correct_options", "").strip().upper()
    correct_tokens = {tok.strip() for tok in correct_raw.split(",") if tok.strip()}

    if question_type in (
        Question.QuestionType.SINGLE_MCQ,
        Question.QuestionType.MULTIPLE_MCQ,
        Question.QuestionType.TRUE_FALSE,
        Question.QuestionType.LIKERT,
        Question.QuestionType.SELF_RATING,
        Question.QuestionType.SITUATIONAL_JUDGEMENT,
    ):
        explicit_opts: list[dict] = []
        for idx, letter in enumerate(("a", "b", "c", "d", "e"), start=1):
            text = row.get(f"option_{letter}", "").strip()
            if text:
                key = letter.upper()
                explicit_opts.append({
                    "option_key": key,
                    "option_text": text,
                    "display_order": idx,
                    "is_correct": key in correct_tokens,
                })

        if explicit_opts:
            return explicit_opts

        if question_type == Question.QuestionType.TRUE_FALSE:
            true_correct = bool(correct_tokens & {"TRUE", "T", "1", "A", "YES"})
            false_correct = bool(correct_tokens & {"FALSE", "F", "0", "B", "NO"})
            return [
                {"option_key": "TRUE", "option_text": "True", "display_order": 1, "is_correct": true_correct},
                {"option_key": "FALSE", "option_text": "False", "display_order": 2, "is_correct": false_correct},
            ]

        if question_type in (Question.QuestionType.LIKERT, Question.QuestionType.SELF_RATING):
            return [
                {"option_key": key, "option_text": label, "display_order": idx, "is_correct": False}
                for idx, (key, label) in enumerate(DEFAULT_LIKERT_LABELS, start=1)
            ]

    return []


def parse_and_validate_question_upload(*, institution: Institution, uploaded_file) -> dict[str, Any]:
    """Parse an uploaded XLSX/CSV question bank sheet and validate every row without committing."""
    raw_rows = _read_uploaded_rows(uploaded_file)

    dim_by_code = {
        d.code.upper(): d
        for d in AssessmentDimension.objects.for_institution(institution).filter(status="active")
    }
    existing_codes = set(
        c.upper() for c in Question.objects.for_institution(institution).values_list("question_code", flat=True)
    )
    seen_in_file: set[str] = set()

    preview_rows: list[dict[str, Any]] = []
    valid_payloads: list[dict[str, Any]] = []

    for row_num, row in raw_rows:
        errors: list[str] = []
        q_code = row.get("question_code", "").strip().upper()
        q_type = row.get("question_type", "").strip().lower()
        prompt = row.get("prompt", "").strip()
        family = row.get("measurement_family", "").strip().lower()
        difficulty = (row.get("difficulty", "").strip().lower() or Question.Difficulty.MEDIUM)
        scoring_method = (row.get("scoring_method", "").strip().lower() or DEFAULT_SCORING_BY_TYPE.get(q_type, ""))
        raw_dim = row.get("dimension_code", "").strip()

        if not q_code:
            errors.append("question_code is required.")
        elif len(q_code) > 60:
            errors.append("question_code exceeds 60 characters.")
        elif q_code in existing_codes:
            errors.append(f"Question code '{q_code}' already exists in Question Bank.")
        elif q_code in seen_in_file:
            errors.append(f"Duplicate question_code '{q_code}' inside uploaded file.")
        if q_code:
            seen_in_file.add(q_code)

        if q_type not in set(Question.QuestionType.values):
            errors.append(f"Invalid question_type '{q_type}'.")
        if not prompt:
            errors.append("prompt is required.")
        if family not in set(MeasurementFamily.values):
            errors.append(f"Invalid measurement_family '{family}'.")
        if difficulty not in set(Question.Difficulty.values):
            errors.append(f"Invalid difficulty '{difficulty}' (expected easy, medium, or hard).")
        if scoring_method not in set(Question.ScoringMethod.values):
            errors.append(f"Invalid scoring_method '{scoring_method}'.")

        try:
            max_marks = Decimal(row.get("max_marks") or "1.00")
        except InvalidOperation:
            max_marks = Decimal("0.00")
            errors.append("max_marks must be a valid number.")

        try:
            negative_marks = Decimal(row.get("negative_marks") or "0.00")
        except InvalidOperation:
            negative_marks = Decimal("0.00")
            errors.append("negative_marks must be a valid number.")

        scoring_config: dict[str, Any] = {}
        if q_type == Question.QuestionType.NUMERIC:
            raw_num = row.get("correct_numeric_value", "").strip()
            if not raw_num:
                errors.append("correct_numeric_value is required for numeric questions.")
            else:
                try:
                    scoring_config["correct_value"] = float(raw_num)
                except ValueError:
                    errors.append("correct_numeric_value must be numeric.")
            raw_tol = row.get("numeric_tolerance", "").strip()
            if raw_tol:
                try:
                    scoring_config["tolerance"] = float(raw_tol)
                except ValueError:
                    errors.append("numeric_tolerance must be numeric.")
            else:
                scoring_config["tolerance"] = 0.0

        options = _build_options_from_row(q_type, row)
        rubric = None
        if q_type in (Question.QuestionType.DESCRIPTIVE, Question.QuestionType.CODING):
            guidance = row.get("rubric_guidance", "").strip()
            if scoring_method == Question.ScoringMethod.RUBRIC or guidance:
                rubric = {
                    "rubric_json": {"criteria": ["Correctness & Clarity"]},
                    "max_marks": max_marks,
                    "evaluator_guidance": guidance,
                }

        dim_links: list[dict] = []
        try:
            dim_links = _parse_dimension_links(raw_dim, dim_by_code)
        except ValidationError as exc:
            errors.extend(_flatten_validation_messages(exc))

        if not errors:
            try:
                _validate_question_scoring_and_dimensions(
                    institution=institution,
                    question_type=q_type,
                    measurement_family=family,
                    scoring_method=scoring_method,
                    max_marks=max_marks,
                    negative_marks=negative_marks,
                    scoring_config=scoring_config,
                    options=options,
                    rubric=rubric,
                    dimension_links=dim_links,
                )
            except ValidationError as exc:
                errors.extend(_flatten_validation_messages(exc))

        tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
        is_valid = len(errors) == 0
        payload = {
            "question_code": q_code,
            "question_type": q_type,
            "prompt": prompt,
            "difficulty": difficulty,
            "measurement_family": family,
            "scoring_method": scoring_method,
            "max_marks": max_marks,
            "negative_marks": negative_marks,
            "scoring_config": scoring_config,
            "tags": tags,
            "options": options,
            "rubric": rubric,
            "dimensions": [{"dimension_id": d["dimension_id"], "weight": d["weight"]} for d in dim_links],
        }
        if is_valid:
            valid_payloads.append(payload)

        preview_rows.append({
            "row_number": row_num,
            "question_code": q_code or "—",
            "question_type": q_type or "—",
            "measurement_family": family or "—",
            "dimension_codes": [d["code"] for d in dim_links] or ([raw_dim.upper()] if raw_dim else []),
            "prompt_preview": (prompt[:85] + "...") if len(prompt) > 85 else prompt,
            "valid": is_valid,
            "errors": errors,
        })

    return {
        "summary": {
            "total_rows": len(preview_rows),
            "valid_count": len(valid_payloads),
            "error_count": len(preview_rows) - len(valid_payloads),
        },
        "rows": preview_rows,
        "_valid_payloads": valid_payloads,
    }


def _flatten_validation_messages(exc: ValidationError) -> list[str]:
    detail = exc.detail
    if isinstance(detail, dict):
        msgs: list[str] = []
        for val in detail.values():
            if isinstance(val, list):
                msgs.extend(str(item) for item in val)
            else:
                msgs.append(str(val))
        return msgs
    if isinstance(detail, list):
        return [str(item) for item in detail]
    return [str(detail)]


@transaction.atomic
def commit_question_import(
    *,
    institution: Institution,
    uploaded_file,
    mode: str = "skip_invalid",
    actor_user,
    request=None,
) -> dict[str, Any]:
    """Validate and commit bulk questions into the active institution's Question Bank."""
    if mode not in {"skip_invalid", "all_or_nothing"}:
        raise ValidationError({"mode": "mode must be 'skip_invalid' or 'all_or_nothing'."})

    parsed = parse_and_validate_question_upload(institution=institution, uploaded_file=uploaded_file)
    summary = parsed["summary"]
    if mode == "all_or_nothing" and summary["error_count"] > 0:
        raise ValidationError({
            "file": f"All-or-nothing import aborted because {summary['error_count']} row(s) have validation errors.",
        })
    if summary["valid_count"] == 0:
        raise ValidationError({"file": "No valid questions found to import."})

    created_codes: list[str] = []
    for payload in parsed["_valid_payloads"]:
        q = create_question(
            institution=institution,
            data=payload,
            actor_user=actor_user,
            emit_audit=False,
            request=request,
        )
        created_codes.append(q.question_code)

    log_audit_event(
        action="QUESTION_BULK_IMPORTED",
        entity_type="Institution",
        entity_id=institution.id,
        institution=institution,
        actor_user=actor_user,
        after={
            "mode": mode,
            "created_count": len(created_codes),
            "skipped_errors": summary["error_count"],
            "question_codes": created_codes[:50],
        },
        request=request,
    )
    return {
        "created_count": len(created_codes),
        "skipped_count": summary["error_count"],
        "question_codes": created_codes,
    }
