"""Phase 2 Assessment Administration API routes."""
from django.urls import path
from apps.assessments.views import (
    AssignmentDetailView,
    AssignmentListCreateView,
    CategoryDetailView,
    CategoryListCreateView,
    DimensionDetailView,
    DimensionListCreateView,
    QuestionDetailView,
    QuestionListCreateView,
    SeedStarterCatalogueView,
    TemplateDetailView,
    TemplateListCreateView,
    VersionCloneView,
    VersionDetailView,
    VersionPublishView,
)

urlpatterns = [
    path("seed-catalogue/", SeedStarterCatalogueView.as_view(), name="assessments-seed-catalogue"),
    path("categories/", CategoryListCreateView.as_view(), name="assessments-categories"),
    path("categories/<uuid:category_id>/", CategoryDetailView.as_view(), name="assessments-category-detail"),
    path("dimensions/", DimensionListCreateView.as_view(), name="assessments-dimensions"),
    path("dimensions/<uuid:dimension_id>/", DimensionDetailView.as_view(), name="assessments-dimension-detail"),
    path("questions/", QuestionListCreateView.as_view(), name="assessments-questions"),
    path("questions/<uuid:question_id>/", QuestionDetailView.as_view(), name="assessments-question-detail"),
    path("templates/", TemplateListCreateView.as_view(), name="assessments-templates"),
    path("templates/<uuid:template_id>/", TemplateDetailView.as_view(), name="assessments-template-detail"),
    path("versions/<uuid:version_id>/", VersionDetailView.as_view(), name="assessments-version-detail"),
    path("versions/<uuid:version_id>/publish/", VersionPublishView.as_view(), name="assessments-version-publish"),
    path("versions/<uuid:version_id>/clone/", VersionCloneView.as_view(), name="assessments-version-clone"),
    path("assignments/", AssignmentListCreateView.as_view(), name="assessments-assignments"),
    path("assignments/<uuid:assignment_id>/", AssignmentDetailView.as_view(), name="assessments-assignment-detail"),
]

