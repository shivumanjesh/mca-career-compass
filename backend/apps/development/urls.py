"""Phase 5 URL routes for Student Empowerment & Development Plans."""
from django.urls import path

from apps.development.views import (
    ActivityProgressCreateView,
    DevelopmentPlanDetailView,
    DevelopmentPlanListCreateView,
    DevelopmentStudentListView,
    LearningResourceDetailView,
    LearningResourceListCreateView,
    MyRecommendationsView,
    PlanActivityCreateView,
    SeedLearningCatalogueView,
    StudentRecommendationsView,
)

urlpatterns = [
    path("catalogue/seed/", SeedLearningCatalogueView.as_view(), name="development-catalogue-seed"),
    path("catalogue/", LearningResourceListCreateView.as_view(), name="development-catalogue"),
    path("catalogue/<uuid:resource_id>/", LearningResourceDetailView.as_view(), name="development-catalogue-detail"),
    path("my-recommendations/", MyRecommendationsView.as_view(), name="development-my-recommendations"),
    path("students/", DevelopmentStudentListView.as_view(), name="development-students"),
    path("students/<uuid:student_id>/recommendations/", StudentRecommendationsView.as_view(), name="development-student-recommendations"),
    path("plans/", DevelopmentPlanListCreateView.as_view(), name="development-plans"),
    path("plans/<uuid:plan_id>/", DevelopmentPlanDetailView.as_view(), name="development-plan-detail"),
    path("plans/<uuid:plan_id>/activities/", PlanActivityCreateView.as_view(), name="development-plan-activities"),
    path("activities/<uuid:activity_id>/progress/", ActivityProgressCreateView.as_view(), name="development-activity-progress"),
]

