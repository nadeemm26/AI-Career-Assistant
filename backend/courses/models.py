from django.db import models

from ats.models import ATSScore
from jobs.models import Skill


class Course(models.Model):
    LEVEL_CHOICES = (
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    )

    title = models.CharField(max_length=200)

    provider = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    course_url = models.URLField(max_length=500)

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="beginner",
    )

    duration = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: 6 hours, 4 weeks",
    )

    is_free = models.BooleanField(default=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["skill__name", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["title", "provider", "skill"],
                name="unique_course_provider_skill",
            )
        ]

    def __str__(self):
        return f"{self.title} - {self.provider}"


class CourseRecommendation(models.Model):
    ats_score = models.ForeignKey(
        ATSScore,
        on_delete=models.CASCADE,
        related_name="course_recommendations",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )

    reason = models.TextField()

    priority = models.PositiveIntegerField(default=1)

    recommended_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["priority", "-recommended_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["ats_score", "course"],
                name="unique_course_recommendation_per_score",
            )
        ]

    def __str__(self):
        return (
            f"{self.course.title} recommended for "
            f"ATS Score {self.ats_score_id}"
        )