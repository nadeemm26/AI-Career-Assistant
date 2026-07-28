from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "resume",
        "report_type",
        "status",
        "created_at",
        "generated_at",
    )

    list_filter = (
        "report_type",
        "status",
        "created_at",
    )

    search_fields = (
        "user__full_name",
        "user__email",
        "resume__original_filename",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("-created_at",)