from urllib.parse import quote_plus

from django.core.management.base import BaseCommand

from jobs.models import Skill
from courses.models import Course


class Command(BaseCommand):
    help = "Create default courses for existing skills that do not have courses."


    def handle(self, *args, **kwargs):

        created_count = 0

        for skill in Skill.objects.all():

            # Skip if courses already exist
            if Course.objects.filter(skill=skill).exists():
                continue

            encoded = quote_plus(skill.name)

            courses = [
                {
                    "title": f"Learn {skill.name} - Free Full Course",
                    "provider": "freeCodeCamp / YouTube",
                    "description": f"Learn {skill.name} from beginner to advanced.",
                    "course_url": f"https://www.youtube.com/results?search_query=freecodecamp+{encoded}+full+course",
                    "level": "beginner",
                    "is_free": True,
                },
                {
                    "title": f"{skill.name} Professional Course",
                    "provider": "Coursera",
                    "description": f"Professional training for {skill.name}.",
                    "course_url": f"https://www.coursera.org/search?query={encoded}",
                    "level": "intermediate",
                    "is_free": False,
                },
                {
                    "title": f"{skill.name} Bootcamp",
                    "provider": "Udemy",
                    "description": f"Project-based {skill.name} training.",
                    "course_url": f"https://www.udemy.com/courses/search/?q={encoded}",
                    "level": "intermediate",
                    "is_free": False,
                },
            ]

            for item in courses:

                Course.objects.create(
                    skill=skill,
                    title=item["title"],
                    provider=item["provider"],
                    description=item["description"],
                    course_url=item["course_url"],
                    level=item["level"],
                    duration="Self-paced",
                    is_free=item["is_free"],
                    price=0,
                    rating=None,
                    is_active=True,
                )

                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created {created_count} courses."
            )
        )