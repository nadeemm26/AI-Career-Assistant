from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Report
from .services import PDFReportService


@login_required
def report_list(request):
    reports = (
        Report.objects
        .filter(user=request.user)
        .select_related(
            "resume",
            "user",
        )
        .order_by("-created_at")
    )

    context = {
        "reports": reports,
        "total_reports": reports.count(),
        "generated_reports": reports.filter(
            status="generated"
        ).count(),
        "failed_reports": reports.filter(
            status="failed"
        ).count(),
        "pdf_reports": reports.filter(
            report_type="pdf"
        ).count(),
    }

    return render(
        request,
        "reports/report_list.html",
        context,
    )


@login_required
def generate_pdf_report(request, resume_id):
    if request.method != "POST":
        messages.error(
            request,
            "Invalid report generation request.",
        )

        return redirect(
            "ats:analysis_result",
            resume_id=resume_id,
        )

    try:
        PDFReportService.generate(
            user=request.user,
            resume_id=resume_id,
        )

        messages.success(
            request,
            "PDF report generated successfully. "
            "You can download it from the Reports page.",
        )

        # PDF direct download ke badle Reports page open hoga
        return redirect(
            "reports:report_list"
        )

    except ValueError as error:
        messages.error(
            request,
            str(error),
        )

    except Exception as error:
        messages.error(
            request,
            f"Unable to generate PDF report: {error}",
        )

    return redirect(
        "ats:analysis_result",
        resume_id=resume_id,
    )


@login_required
def download_report(request, report_id):
    report = get_object_or_404(
        Report,
        id=report_id,
        user=request.user,
        status="generated",
    )

    if not report.report_file:
        raise Http404(
            "Report file is not available."
        )

    try:
        report.report_file.open("rb")

        return FileResponse(
            report.report_file,
            as_attachment=True,
            filename=report.report_file.name.split("/")[-1],
            content_type="application/pdf",
        )

    except FileNotFoundError:
        raise Http404(
            "Report file was not found."
        )


@login_required
def delete_report(request, report_id):
    if request.method != "POST":
        messages.error(
            request,
            "Invalid delete request.",
        )

        return redirect(
            "reports:report_list"
        )

    report = get_object_or_404(
        Report,
        id=report_id,
        user=request.user,
    )

    if report.report_file:
        report.report_file.delete(
            save=False
        )

    report.delete()

    messages.success(
        request,
        "Report deleted successfully.",
    )

    return redirect(
        "reports:report_list"
    )