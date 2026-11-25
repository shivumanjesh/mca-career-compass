"""Serializers for Phase 3 student attempt, autosave, and manual evaluation APIs."""
from rest_framework import serializers
from apps.attempts.models import AssessmentAttempt, AssessmentResult, Evaluation, Response


class AutosaveItemSerializer(serializers.Serializer):
    version_question_id = serializers.UUIDField()
    response_json = serializers.JSONField()


class AutosaveRequestSerializer(serializers.Serializer):
    items = AutosaveItemSerializer(many=True, min_length=1)


class EvaluationCreateSerializer(serializers.Serializer):
    awarded_marks = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0)
    comments = serializers.CharField(required=False, allow_blank=True, default="")
    rubric_result = serializers.JSONField(required=False, default=dict)


class EvaluationSerializer(serializers.ModelSerializer):
    evaluator_email = serializers.EmailField(source="evaluator_user.email", read_only=True)
    evaluator_name = serializers.CharField(source="evaluator_user.full_name", read_only=True)

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "version_no",
            "awarded_marks",
            "comments",
            "rubric_result",
            "evaluator_email",
            "evaluator_name",
            "evaluated_at",
        ]


class PendingEvaluationResponseSerializer(serializers.ModelSerializer):
    attempt_id = serializers.UUIDField(source="attempt.id", read_only=True)
    student_reg_no = serializers.CharField(source="attempt.student_profile.registration_no", read_only=True)
    student_name = serializers.CharField(source="attempt.student_profile.membership.user.full_name", read_only=True)
    template_name = serializers.CharField(source="attempt.assignment.assessment_version.template.name", read_only=True)
    version_no = serializers.IntegerField(source="attempt.assignment.assessment_version.version_no", read_only=True)
    question_code = serializers.SerializerMethodField()
    question_type = serializers.SerializerMethodField()
    prompt = serializers.SerializerMethodField()
    max_marks = serializers.DecimalField(source="version_question.marks", max_digits=7, decimal_places=2, read_only=True)
    rubric = serializers.SerializerMethodField()
    evaluations = EvaluationSerializer(many=True, read_only=True)

    class Meta:
        model = Response
        fields = [
            "id",
            "attempt_id",
            "student_reg_no",
            "student_name",
            "template_name",
            "version_no",
            "question_code",
            "question_type",
            "prompt",
            "max_marks",
            "rubric",
            "response_json",
            "awarded_marks",
            "scoring_status",
            "submitted_at",
            "evaluations",
        ]

    def get_question_code(self, obj: Response):
        return (obj.version_question.question_snapshot or {}).get("question_code")

    def get_question_type(self, obj: Response):
        return (obj.version_question.question_snapshot or {}).get("question_type")

    def get_prompt(self, obj: Response):
        return (obj.version_question.question_snapshot or {}).get("prompt")

    def get_rubric(self, obj: Response):
        return (obj.version_question.question_snapshot or {}).get("rubric")


class AssessmentResultSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="attempt.assignment.assessment_version.template.name", read_only=True)
    version_no = serializers.IntegerField(source="attempt.assignment.assessment_version.version_no", read_only=True)
    attempt_no = serializers.IntegerField(source="attempt.attempt_no", read_only=True)

    class Meta:
        model = AssessmentResult
        fields = [
            "id",
            "attempt_id",
            "template_name",
            "version_no",
            "attempt_no",
            "raw_score",
            "max_score",
            "normalized_score",
            "breakdown_json",
            "result_status",
            "calculated_at",
            "algorithm_version",
        ]


class AssessmentAttemptSummarySerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="assignment.assessment_version.template.name", read_only=True)
    version_no = serializers.IntegerField(source="assignment.assessment_version.version_no", read_only=True)
    results_released = serializers.BooleanField(source="assignment.results_released", read_only=True)

    class Meta:
        model = AssessmentAttempt
        fields = [
            "id",
            "assignment_id",
            "template_name",
            "version_no",
            "attempt_no",
            "status",
            "started_at",
            "expires_at",
            "submitted_at",
            "total_awarded",
            "max_marks",
            "results_released",
        ]

