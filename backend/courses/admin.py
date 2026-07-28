from django.contrib import admin

from .models import Course, CourseRecommendation


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "provider",
        "skill",
        "level",
        "is_free",
        "price",
        "is_active",
    )

    list_filter = (
        "level",
        "is_free",
        "is_active",
        "provider",
        "skill__category",
    )

    search_fields = (
        "title",
        "provider",
        "skill__name",
    )

    ordering = ("skill__name", "title")


@admin.register(CourseRecommendation)
class CourseRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "ats_score",
        "priority",
        "recommended_at",
    )

    list_filter = (
        "priority",
        "course__provider",
        "course__level",
    )

    search_fields = (
        "course__title",
        "course__skill__name",
        "ats_score__resume__original_filename",
    )

    ordering = ("priority", "-recommended_at")