from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404

from .models import Resume
from .forms import ResumeUploadForm
from .services import ResumeService


@login_required
def upload_resume(request):

    if request.method == "POST":

        form = ResumeUploadForm(request.POST, request.FILES)

        if form.is_valid():

            ResumeService.upload_resume(request.user, form)

            messages.success(request, "Resume uploaded successfully.")

            return redirect("resume_list")

    else:

        form = ResumeUploadForm()

    return render(
        request,
        "resume/upload_resume.html",
        {
            "form": form
        }
    )

@login_required
def resume_list(request):

    resumes = Resume.objects.filter(user=request.user)

    context = {
        "resumes": resumes
    }

    return render(
        request,
        "resume/resume_list.html",
        context,
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

