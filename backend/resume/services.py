import os

from .models import Resume


class ResumeService:

    @staticmethod
    def upload_resume(user, form):

        file = form.cleaned_data["resume_file"]

        resume = form.save(commit=False)

        resume.user = user
        resume.original_filename = file.name
        resume.file_size = file.size
        resume.file_type = os.path.splitext(file.name)[1].lower()

        resume.save()

        return resume