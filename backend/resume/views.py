from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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

