from django.db import models
from resume.models import Resume
from jobs.models import JobRole, Skill


class ResumeAnalysis(models.Model):

    resume = models.OneToOneField(
        Resume,
        on_delete=models.CASCADE,
        related_name="analysis"
    )

    extracted_text = models.TextField()

    total_skills = models.PositiveIntegerField(default=0)

    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis - {self.resume.id}"


class ATSScore(models.Model):

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="ats_scores"
    )

    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE
    )

    score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.resume} - {self.job_role}"


class MissingSkill(models.Model):

    ats_score = models.ForeignKey(
        ATSScore,
        on_delete=models.CASCADE,
        related_name="missing_skills"
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.skill.name


class Recommendation(models.Model):

    ats_score = models.ForeignKey(
        ATSScore,
        on_delete=models.CASCADE,
        related_name="recommendations"
    )

    title = models.CharField(max_length=200)

    description = models.TextField()

    priority = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title

class ExtractedSkill(models.Model):

    analysis = models.ForeignKey(
        ResumeAnalysis,
        on_delete=models.CASCADE,
        related_name="extracted_skills"
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="extracted_resumes"
    )

    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "skill"],
                name="unique_extracted_skill_per_analysis"
            )
        ]

    def __str__(self):
        return f"{self.analysis.resume.original_filename} - {self.skill.name}"