from django.urls import path
from . import views

app_name = "ats"

urlpatterns = [
    # path("ats/test/",views.test_parser,name="test_parser",),
    path(
        "result/<int:resume_id>/",
        views.analysis_result,
        name="analysis_result"
    ),
]

