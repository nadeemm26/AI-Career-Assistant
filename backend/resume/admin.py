from django.contrib import admin
from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "original_filename",
        "status",
        "uploaded_at",
    )

    list_filter = ("status",)

    search_fields = (
        "original_filename",
        "user__email",
    )