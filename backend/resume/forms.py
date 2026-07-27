from django import forms

from .models import Resume


class ResumeUploadForm(forms.ModelForm):

    class Meta:
        model = Resume
        fields = ["resume_file"]

        widgets = {
            "resume_file": forms.ClearableFileInput(
                attrs={
                    "class": "resume-file-input",
                    "id": "resumeFileInput",
                    "accept": ".pdf,.docx",
                }
            )
        }

    def clean_resume_file(self):
        resume_file = self.cleaned_data.get("resume_file")

        if not resume_file:
            raise forms.ValidationError(
                "Please select a resume file."
            )

        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
        ]

        allowed_extensions = [".pdf", ".docx"]

        file_name = resume_file.name.lower()

        extension_valid = any(
            file_name.endswith(extension)
            for extension in allowed_extensions
        )

        if (
            resume_file.content_type not in allowed_types
            or not extension_valid
        ):
            raise forms.ValidationError(
                "Only PDF and DOCX files are allowed."
            )

        max_file_size = 5 * 1024 * 1024

        if resume_file.size > max_file_size:
            raise forms.ValidationError(
                "Maximum file size is 5 MB."
            )

        return resume_file