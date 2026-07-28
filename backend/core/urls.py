from django.urls import path

from . import views


urlpatterns = [
    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "job-roles/",
        views.job_roles,
        name="job_roles",
    ),

    path(
        "reports/",
        views.reports,
        name="reports",
    ),
]