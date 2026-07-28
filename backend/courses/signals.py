from urllib.parse import quote_plus

from django.db.models.signals import post_save
from django.dispatch import receiver

from jobs.models import Skill

from .models import Course


@receiver(post_save, sender=Skill)
def create_default_courses(sender, instance, created, **kwargs):
    """
    Automatically create default courses whenever
    a new Skill is added.
    """

    if not created:
        return

    encoded_skill = quote_plus(instance.name)

    default_courses = [
        {
            "title": f"Learn {instance.name} - Free Full Course",
            "provider": "freeCodeCamp / YouTube",
            "description": f"Learn {instance.name} from beginner to advanced.",
            "course_url": (
                "https://www.youtube.com/results"
                f"?search_query=freecodecamp+{encoded_skill}+full+course"
            ),
            "level": "beginner",
            "is_free": True,
        },
        {
            "title": f"{instance.name} Professional Course",
            "provider": "Coursera",
            "description": f"Professional training for {instance.name}.",
            "course_url": (
                f"https://www.coursera.org/search?query={encoded_skill}"
            ),
            "level": "intermediate",
            "is_free": False,
        },
        {
            "title": f"{instance.name} Bootcamp",
            "provider": "Udemy",
            "description": f"Project-based {instance.name} course.",
            "course_url": (
                "https://www.udemy.com/courses/search/"
                f"?q={encoded_skill}"
            ),
            "level": "intermediate",
            "is_free": False,
        },
    ]

    for item in default_courses:
        Course.objects.get_or_create(
            title=item["title"],
            provider=item["provider"],
            skill=instance,
            defaults={
                "description": item["description"],
                "course_url": item["course_url"],
                "level": item["level"],
                "duration": "Self-paced",
                "is_free": item["is_free"],
                "price": 0,
                "rating": None,
                "is_active": True,
            },
        )