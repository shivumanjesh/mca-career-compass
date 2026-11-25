"""Academic structure API routes."""
from django.urls import path
from apps.academics.views import (
    AcademicYearDetailView,
    AcademicYearListCreateView,
    CohortDetailView,
    CohortListCreateView,
    ProgrammeDetailView,
    ProgrammeListCreateView,
)

urlpatterns = [
    path("programmes/", ProgrammeListCreateView.as_view(), name="academics-programmes"),
    path("programmes/<uuid:programme_id>/", ProgrammeDetailView.as_view(), name="academics-programme-detail"),
    path("academic-years/", AcademicYearListCreateView.as_view(), name="academics-years"),
    path("academic-years/<uuid:academic_year_id>/", AcademicYearDetailView.as_view(), name="academics-year-detail"),
    path("cohorts/", CohortListCreateView.as_view(), name="academics-cohorts"),
    path("cohorts/<uuid:cohort_id>/", CohortDetailView.as_view(), name="academics-cohort-detail"),
]

