"""Faculty API routes."""
from django.urls import path
from apps.faculty.views import (
    FacultyCohortAssignDeleteView,
    FacultyCohortAssignListCreateView,
    FacultyDetailView,
    FacultyListCreateView,
    FacultySelfCohortsView,
)

urlpatterns = [
    path("", FacultyListCreateView.as_view(), name="faculty-list-create"),
    path("me/cohorts/", FacultySelfCohortsView.as_view(), name="faculty-self-cohorts"),
    path("<uuid:faculty_id>/", FacultyDetailView.as_view(), name="faculty-detail"),
    path("<uuid:faculty_id>/cohorts/", FacultyCohortAssignListCreateView.as_view(), name="faculty-cohorts"),
    path(
        "<uuid:faculty_id>/cohorts/<uuid:assignment_id>/",
        FacultyCohortAssignDeleteView.as_view(),
        name="faculty-cohort-delete",
    ),
]

