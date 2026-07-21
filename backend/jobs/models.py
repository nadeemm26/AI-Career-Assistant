from django.db import models


class SkillCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Skill(models.Model):
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.CASCADE,
        related_name="skills"
    )

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class JobRole(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

class JobRequiredSkill(models.Model):
    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE,
        related_name="required_skills"
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE
    )

    weight = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("job_role", "skill")

    def __str__(self):
        return f"{self.job_role} - {self.skill}"

