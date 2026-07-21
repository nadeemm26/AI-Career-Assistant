from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from resume.models import Resume
from ats.models import ATSScore
from jobs.models import JobRole


@login_required
def dashboard(request):

    resumes = Resume.objects.filter(
        user=request.user
    )

    ats_scores = ATSScore.objects.filter(
        resume__user=request.user
    )

    context = {
        "total_resumes": resumes.count(),

        "completed_resumes": resumes.filter(
            status="completed"
        ).count(),

        "total_analyses": ats_scores.count(),

        "latest_resumes": resumes[:5],

        "latest_score": ats_scores.order_by(
            "-created_at"
        ).first(),
    }

    return render(
        request,
        "core/dashboard.html",
        context
    )


@login_required
def job_roles(request):

    job_roles_list = JobRole.objects.all()

    return render(
        request,
        "core/job_roles.html",
        {
            "job_roles": job_roles_list
        }
    )


@login_required
def courses(request):

    return render(
        request,
        "core/courses.html"
    )


@login_required
def reports(request):

    resumes = Resume.objects.filter(
        user=request.user
    )

    ats_scores = ATSScore.objects.filter(
        resume__user=request.user
    ).select_related(
        "resume",
        "job_role"
    ).order_by(
        "-created_at"
    )

    context = {
        "total_resumes": resumes.count(),

        "completed_resumes": resumes.filter(
            status="completed"
        ).count(),

        "total_reports": ats_scores.count(),

        "reports": ats_scores,
    }

    return render(
        request,
        "core/reports.html",
        context
    )

    