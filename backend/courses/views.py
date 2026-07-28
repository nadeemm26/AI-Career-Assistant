from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from jobs.models import Skill

from .models import Course


def course_list(request):
    courses = (
        Course.objects
        .filter(is_active=True)
        .select_related("skill")
    )

    search_query = request.GET.get("q", "").strip()
    selected_skill = request.GET.get("skill", "").strip()
    selected_level = request.GET.get("level", "").strip()
    selected_provider = request.GET.get("provider", "").strip()
    selected_price_type = request.GET.get("price_type", "").strip()

    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query)
            | Q(provider__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(skill__name__icontains=search_query)
        )

    if selected_skill:
        courses = courses.filter(skill_id=selected_skill)

    if selected_level:
        courses = courses.filter(level=selected_level)

    if selected_provider:
        courses = courses.filter(provider=selected_provider)

    if selected_price_type == "free":
        courses = courses.filter(is_free=True)

    elif selected_price_type == "paid":
        courses = courses.filter(is_free=False)

    courses = courses.order_by(
        "skill__name",
        "level",
        "title",
    )

    paginator = Paginator(courses, 9)

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    skills = (
        Skill.objects
        .filter(courses__is_active=True)
        .distinct()
        .order_by("name")
    )

    providers = (
        Course.objects
        .filter(is_active=True)
        .exclude(provider="")
        .values_list("provider", flat=True)
        .distinct()
        .order_by("provider")
    )

    active_courses = Course.objects.filter(is_active=True)

    context = {
        "page_obj": page_obj,
        "courses": page_obj.object_list,
        "skills": skills,
        "providers": providers,
        "level_choices": Course.LEVEL_CHOICES,

        "search_query": search_query,
        "selected_skill": selected_skill,
        "selected_level": selected_level,
        "selected_provider": selected_provider,
        "selected_price_type": selected_price_type,

        "total_courses": active_courses.count(),
        "free_courses_count": active_courses.filter(
            is_free=True
        ).count(),
        "paid_courses_count": active_courses.filter(
            is_free=False
        ).count(),
        "filtered_courses_count": paginator.count,
    }

    return render(
        request,
        "courses/course_list.html",
        context,
    )