"""Objective scoring engine & family-separated breakdown calculator (Phase 3)."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from apps.assessments.models import MeasurementFamily, Question
from apps.attempts.models import AssessmentAttempt, AssessmentResult, Response


def _has_answer(question_type: str, response_json: dict[str, Any]) -> bool:
    if not response_json:
        return False
    if question_type in (
        Question.QuestionType.SINGLE_MCQ,
        Question.QuestionType.MULTIPLE_MCQ,
        Question.QuestionType.TRUE_FALSE,
        Question.QuestionType.LIKERT,
        Question.QuestionType.SELF_RATING,
        Question.QuestionType.SITUATIONAL_JUDGEMENT,
    ):
        return bool(response_json.get("selected_keys"))
    if question_type == Question.QuestionType.NUMERIC:
        val = response_json.get("numeric_value")
        return val is not None and str(val).strip() != ""
    if question_type == Question.QuestionType.DESCRIPTIVE:
        return bool(str(response_json.get("text", "")).strip())
    if question_type == Question.QuestionType.CODING:
        return bool(str(response_json.get("code", "")).strip())
    return False


def score_single_response(version_question, response_json: dict[str, Any]) -> tuple[Decimal | None, str]:
    """Score one response strictly from VersionQuestion.question_snapshot."""
    snap = version_question.question_snapshot or {}
    q_type = snap.get("question_type", version_question.question.question_type)
    m_family = snap.get("measurement_family", version_question.question.measurement_family)
    scoring_method = snap.get("scoring_method", Question.ScoringMethod.EXACT)
    scoring_config = snap.get("scoring_config") or {}
    options = snap.get("options") or []
    max_marks = Decimal(str(version_question.marks))
    neg_marks = Decimal(str(version_question.negative_marks))

    if not _has_answer(q_type, response_json):
        if q_type in (Question.QuestionType.DESCRIPTIVE, Question.QuestionType.CODING):
            return Decimal("0.00"), Response.ScoringStatus.AUTO_SCORED
        if m_family != MeasurementFamily.DEMONSTRATED_PERFORMANCE or q_type in (
            Question.QuestionType.LIKERT,
            Question.QuestionType.SELF_RATING,
        ):
            return None, Response.ScoringStatus.UNANSWERED
        return Decimal("0.00"), Response.ScoringStatus.UNANSWERED

    # Non-objective self-reported proficiency / stated interest items are never scored as objective competence
    if m_family != MeasurementFamily.DEMONSTRATED_PERFORMANCE or q_type in (
        Question.QuestionType.LIKERT,
        Question.QuestionType.SELF_RATING,
    ):
        return None, Response.ScoringStatus.NON_SCORED_SURVEY

    if q_type in (Question.QuestionType.DESCRIPTIVE, Question.QuestionType.CODING):
        return None, Response.ScoringStatus.PENDING_MANUAL

    if q_type in (
        Question.QuestionType.SINGLE_MCQ,
        Question.QuestionType.TRUE_FALSE,
        Question.QuestionType.SITUATIONAL_JUDGEMENT,
    ):
        selected = [str(k).upper() for k in (response_json.get("selected_keys") or [])]
        if not selected:
            return Decimal("0.00"), Response.ScoringStatus.UNANSWERED
        chosen_key = selected[0]
        opt_map = {str(o["option_key"]).upper(): o for o in options}
        chosen_opt = opt_map.get(chosen_key)
        if chosen_opt and chosen_opt.get("points_override") is not None:
            return Decimal(str(chosen_opt["points_override"])), Response.ScoringStatus.AUTO_SCORED
        correct_keys = {str(o["option_key"]).upper() for o in options if o.get("is_correct")}
        if chosen_key in correct_keys:
            return max_marks, Response.ScoringStatus.AUTO_SCORED
        return -neg_marks, Response.ScoringStatus.AUTO_SCORED

    if q_type == Question.QuestionType.MULTIPLE_MCQ:
        selected = {str(k).upper() for k in (response_json.get("selected_keys") or [])}
        if not selected:
            return Decimal("0.00"), Response.ScoringStatus.UNANSWERED
        correct_keys = {str(o["option_key"]).upper() for o in options if o.get("is_correct")}
        if scoring_method == Question.ScoringMethod.PARTIAL_CREDIT and correct_keys:
            right_chosen = len(selected & correct_keys)
            wrong_chosen = len(selected - correct_keys)
            per_correct = max_marks / Decimal(len(correct_keys))
            raw = (Decimal(right_chosen) * per_correct) - (Decimal(wrong_chosen) * neg_marks)
            awarded = max(Decimal("0.00"), raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return awarded, Response.ScoringStatus.AUTO_SCORED
        if selected == correct_keys:
            return max_marks, Response.ScoringStatus.AUTO_SCORED
        return -neg_marks, Response.ScoringStatus.AUTO_SCORED

    if q_type == Question.QuestionType.NUMERIC:
        try:
            student_val = Decimal(str(response_json.get("numeric_value")))
            target_val = Decimal(str(scoring_config.get("correct_value")))
            tolerance = Decimal(str(scoring_config.get("tolerance", "0")))
        except Exception:
            return -neg_marks, Response.ScoringStatus.AUTO_SCORED
        if abs(student_val - target_val) <= abs(tolerance):
            return max_marks, Response.ScoringStatus.AUTO_SCORED
        return -neg_marks, Response.ScoringStatus.AUTO_SCORED

    return Decimal("0.00"), Response.ScoringStatus.AUTO_SCORED


def recalculate_attempt_result(attempt: AssessmentAttempt) -> AssessmentResult:
    """Aggregate attempt marks and strictly separate the three measurement families."""
    vqs = list(
        attempt.assignment.assessment_version.version_questions.select_related("question").order_by("sequence")
    )
    responses_by_vq = {r.version_question_id: r for r in attempt.responses.all()}

    has_pending_manual = False
    objective_raw = Decimal("0.00")
    objective_max = Decimal("0.00")

    demonstrated_dims: dict[str, dict[str, Any]] = {}
    self_report_dims: dict[str, dict[str, Any]] = {}
    interest_dims: dict[str, dict[str, Any]] = {}

    for vq in vqs:
        snap = vq.question_snapshot or {}
        m_family = snap.get("measurement_family", vq.question.measurement_family)
        dims = snap.get("dimensions") or []
        resp = responses_by_vq.get(vq.id)
        scoring_status = resp.scoring_status if resp else Response.ScoringStatus.UNANSWERED
        awarded = resp.awarded_marks if resp and resp.awarded_marks is not None else Decimal("0.00")

        if scoring_status == Response.ScoringStatus.PENDING_MANUAL:
            has_pending_manual = True

        if m_family == MeasurementFamily.DEMONSTRATED_PERFORMANCE:
            objective_max += Decimal(str(vq.marks))
            if scoring_status in (
                Response.ScoringStatus.AUTO_SCORED,
                Response.ScoringStatus.MANUALLY_EVALUATED,
            ):
                objective_raw += awarded

            for d in dims:
                code = d["code"]
                bucket = demonstrated_dims.setdefault(
                    code,
                    {
                        "dimension_id": d["dimension_id"],
                        "code": code,
                        "name": d["name"],
                        "awarded_marks": Decimal("0.00"),
                        "max_marks": Decimal("0.00"),
                        "answered_count": 0,
                        "total_count": 0,
                    },
                )
                bucket["total_count"] += 1
                bucket["max_marks"] += Decimal(str(vq.marks))
                if scoring_status in (
                    Response.ScoringStatus.AUTO_SCORED,
                    Response.ScoringStatus.MANUALLY_EVALUATED,
                ):
                    bucket["answered_count"] += 1
                    bucket["awarded_marks"] += awarded
        else:
            target_map = (
                self_report_dims
                if m_family == MeasurementFamily.SELF_REPORTED_PROFICIENCY
                else interest_dims
            )
            selected_keys = (resp.response_json or {}).get("selected_keys", []) if resp else []
            numeric_rating = None
            if selected_keys:
                try:
                    numeric_rating = float(selected_keys[0])
                except (TypeError, ValueError):
                    numeric_rating = None

            for d in dims:
                code = d["code"]
                bucket = target_map.setdefault(
                    code,
                    {
                        "dimension_id": d["dimension_id"],
                        "code": code,
                        "name": d["name"],
                        "responses_count": 0,
                        "ratings": [],
                        "selected_keys": [],
                    },
                )
                if selected_keys:
                    bucket["responses_count"] += 1
                    bucket["selected_keys"].extend(selected_keys)
                    if numeric_rating is not None:
                        bucket["ratings"].append(numeric_rating)

    def _finalize_demo(items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for item in items.values():
            max_m = item["max_marks"]
            raw_m = item["awarded_marks"]
            pct = (
                float((raw_m / max_m * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
                if max_m > 0 and item["answered_count"] > 0
                else None
            )
            out.append({
                "dimension_id": item["dimension_id"],
                "code": item["code"],
                "name": item["name"],
                "awarded_marks": str(raw_m),
                "max_marks": str(max_m),
                "percentage": pct,
                "status": "insufficient_data" if item["answered_count"] == 0 else "scored",
            })
        return out

    def _finalize_survey(items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for item in items.values():
            ratings = item["ratings"]
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
            out.append({
                "dimension_id": item["dimension_id"],
                "code": item["code"],
                "name": item["name"],
                "responses_count": item["responses_count"],
                "average_rating": avg_rating,
                "selected_keys": item["selected_keys"],
                "status": "insufficient_data" if item["responses_count"] == 0 else "recorded",
            })
        return out

    normalized = (
        (objective_raw / objective_max * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if objective_max > 0
        else None
    )

    attempt.total_awarded = objective_raw
    attempt.max_marks = objective_max
    if has_pending_manual:
        any_manual_done = any(
            r.scoring_status == Response.ScoringStatus.MANUALLY_EVALUATED for r in responses_by_vq.values()
        )
        attempt.status = (
            AssessmentAttempt.Status.PARTIALLY_EVALUATED
            if any_manual_done
            else AssessmentAttempt.Status.SUBMITTED
        )
        result_status = AssessmentResult.ResultStatus.PENDING_MANUAL
    else:
        attempt.status = AssessmentAttempt.Status.EVALUATED
        result_status = AssessmentResult.ResultStatus.FINALIZED

    attempt.save(update_fields=["total_awarded", "max_marks", "status", "updated_at"])

    breakdown = {
        "demonstrated_performance": _finalize_demo(demonstrated_dims),
        "self_reported_proficiency": _finalize_survey(self_report_dims),
        "stated_interest": _finalize_survey(interest_dims),
    }

    result, _ = AssessmentResult.objects.update_or_create(
        attempt=attempt,
        defaults={
            "institution": attempt.institution,
            "raw_score": objective_raw,
            "max_score": objective_max,
            "normalized_score": normalized,
            "breakdown_json": breakdown,
            "result_status": result_status,
            "algorithm_version": "v1.0",
        },
    )
    return result

