from django.urls import path

from . import views


app_name = "reports"


urlpatterns = [
    path(
        "",
        views.report_list,
        name="report_list",
    ),

    path(
        "generate/pdf/<int:resume_id>/",
        views.generate_pdf_report,
        name="generate_pdf",
    ),

    path(
        "download/<int:report_id>/",
        views.download_report,
        name="download_report",
    ),

    path(
        "delete/<int:report_id>/",
        views.delete_report,
        name="delete_report",
    ),
]