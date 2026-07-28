from django.conf import settings
from django.db import models

from resume.models import Resume


class Report(models.Model):
    REPORT_TYPE_CHOICES = (
        ("pdf", "PDF"),
        ("excel", "Excel"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("generated", "Generated"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
    )

    report_file = models.FileField(
        upload_to="reports/",
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.full_name} - "
            f"{self.resume.original_filename} - "
            f"{self.report_type.upper()}"
        )