from django import forms

from .models import Resume


class ResumeUploadForm(forms.ModelForm):

    class Meta:
        model = Resume
        fields = ["resume_file"]

    def clean_resume_file(self):
        file = self.cleaned_data["resume_file"]

        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]

        if file.content_type not in allowed_types:
            raise forms.ValidationError(
                "Only PDF and DOCX files are allowed."
            )

        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "Maximum file size is 5 MB."
            )

        return file