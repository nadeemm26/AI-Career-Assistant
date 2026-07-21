from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from pathlib import Path


from .models import Resume
from .forms import ResumeUploadForm
from .services import ResumeService

@login_required
def upload_resume(request):
    if request.method == "POST":
        form = ResumeUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            uploaded_file = request.FILES.get("resume_file")

            if not uploaded_file:
                messages.error(
                    request,
                    "Please select a resume file."
                )

                return render(
                    request,
                    "resume/upload_resume.html",
                    {"form": form}
                )

            resume = form.save(commit=False)

            resume.user = request.user
            resume.original_filename = uploaded_file.name
            resume.file_size = uploaded_file.size
            resume.file_type = (
                Path(uploaded_file.name)
                .suffix
                .lower()
                .replace(".", "")
            )

            resume.status = "processing"
            resume.save()

            try:
                from ats.services import ATSService

                ATSService.analyze_resume(resume)

                resume.status = "completed"
                resume.save(update_fields=["status", "updated_at"])

                messages.success(
                    request,
                    "Resume uploaded and analyzed successfully."
                )

                return redirect(
                    "ats:analysis_result",
                    resume_id=resume.id
                )

            except Exception as error:
                resume.status = "failed"
                resume.save(update_fields=["status", "updated_at"])

                messages.error(
                    request,
                    f"Resume analysis failed: {error}"
                )

    else:
        form = ResumeUploadForm()

    return render(
        request,
        "resume/upload_resume.html",
        {"form": form}
    )

@login_required
def resume_list(request):
    resumes = Resume.objects.filter(
        user=request.user
    ).order_by("-uploaded_at")

    return render(
        request,
        "resume/resume_list.html",
        {"resumes": resumes}
    )

@login_required
def download_resume(request, pk):

    try:
        resume = Resume.objects.get(
            id=pk,
            user=request.user
        )

    except Resume.DoesNotExist:
        raise Http404()

    return FileResponse(
        resume.resume_file.open("rb"),
        as_attachment=True,
        filename=resume.original_filename,
    )

@login_required
def delete_resume(request, pk):

    try:
        resume = Resume.objects.get(
            id=pk,
            user=request.user
        )

    except Resume.DoesNotExist:
        raise Http404()

    resume.resume_file.delete(save=False)
    resume.delete()

    messages.success(
        request,
        "Resume deleted successfully."
    )

    return redirect("resume_list")

