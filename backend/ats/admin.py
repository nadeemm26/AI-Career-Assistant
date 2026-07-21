from django.contrib import admin
from .models import (
    ResumeAnalysis,
    ExtractedSkill,
    ATSScore,
    MissingSkill,
    Recommendation,
)

@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "resume",
        "total_skills",
        "analyzed_at",
    )


@admin.register(ExtractedSkill)
class ExtractedSkillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "analysis",
        "skill",
        "confidence_score",
        "created_at",
    )

    search_fields = (
        "skill__name",
        "analysis__resume__original_filename",
    )

admin.site.register(ATSScore)
admin.site.register(MissingSkill)
admin.site.register(Recommendation)