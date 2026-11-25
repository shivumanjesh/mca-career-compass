"""Phase 3 attempts & evaluation URL routes."""
from django.urls import path
from apps.attempts.views import (
    EvaluateResponseView,
    EvaluationQueueListView,
    StudentAttemptDetailView,
    StudentAttemptResultView,
    StudentAutosaveResponsesView,
    StudentMyAssignmentsView,
    StudentStartAttemptView,
    StudentSubmitAttemptView,
)

urlpatterns = [
    path("my-assignments/", StudentMyAssignmentsView.as_view(), name="attempts-my-assignments"),
    path("assignments/<uuid:assignment_id>/start/", StudentStartAttemptView.as_view(), name="attempts-start"),
    path("<uuid:attempt_id>/", StudentAttemptDetailView.as_view(), name="attempts-detail"),
    path("<uuid:attempt_id>/responses/", StudentAutosaveResponsesView.as_view(), name="attempts-autosave"),
    path("<uuid:attempt_id>/submit/", StudentSubmitAttemptView.as_view(), name="attempts-submit"),
    path("<uuid:attempt_id>/result/", StudentAttemptResultView.as_view(), name="attempts-result"),
    path("evaluations/queue/", EvaluationQueueListView.as_view(), name="evaluations-queue"),
    path("evaluations/responses/<uuid:response_id>/", EvaluateResponseView.as_view(), name="evaluations-create"),
]

