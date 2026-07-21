from django.urls import path
from . import views

app_name = "ats"

urlpatterns = [
    path(
        "",
        views.analysis_list,
        name="analysis_list"
    ),

    path(
        "result/<int:resume_id>/",
        views.analysis_result,
        name="analysis_result"
    ),
]