"""Student API routes."""
from django.urls import path
from apps.students.views import (
    StudentDetailView,
    StudentListCreateView,
    StudentSelfProfileView,
)

urlpatterns = [
    path("", StudentListCreateView.as_view(), name="students-list-create"),
    path("me/", StudentSelfProfileView.as_view(), name="students-self"),
    path("<uuid:student_id>/", StudentDetailView.as_view(), name="students-detail"),
]

