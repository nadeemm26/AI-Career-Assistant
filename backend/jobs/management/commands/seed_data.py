from django.core.management.base import BaseCommand

from jobs.models import SkillCategory, Skill, JobRole, JobRequiredSkill


class Command(BaseCommand):

    help = "Seed initial skills and job roles"

    def handle(self, *args, **kwargs):

        programming, _ = SkillCategory.objects.get_or_create(
            name="Programming"
        )

        skills = [
            "Python",
            "Django",
            "FastAPI",
            "Flask",
            "HTML",
            "CSS",
            "JavaScript",
            "Bootstrap",
            "MySQL",
            "PostgreSQL",
            "SQL",
            "Git",
            "GitHub",
            "REST API",
        ]

        for skill in skills:
            Skill.objects.get_or_create(
                category=programming,
                name=skill,
            )

        python_role, _ = JobRole.objects.get_or_create(
            title="Python Developer",
            description="Backend Python Developer"
        )

        required = [
            "Python",
            "Django",
            "MySQL",
            "SQL",
            "Git",
            "GitHub",
            "HTML",
            "CSS",
            "JavaScript",
            "REST API",
        ]

        for skill in required:

            skill_obj = Skill.objects.get(name=skill)

            JobRequiredSkill.objects.get_or_create(
                job_role=python_role,
                skill=skill_obj,
                defaults={
                    "weight": 10
                }
            )

        self.stdout.write(
            self.style.SUCCESS("Database Seeded Successfully.")
        )