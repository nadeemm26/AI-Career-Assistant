from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from resume.models import Resume

from .models import ATSScore


def get_score_details(score):
    """
    Return the label, CSS class and verdict according to the ATS score.
    """

    if score >= 80:
        return {
            "label": "Excellent Match",
            "css_class": "excellent",
            "verdict": (
                "Your resume strongly matches the selected job role. "
                "You have most of the required technical skills."
            ),
        }

    if score >= 60:
        return {
            "label": "Good Match",
            "css_class": "good",
            "verdict": (
                "Your resume has a good foundation, but adding the missing "
                "skills can significantly improve your job match."
            ),
        }

    if score >= 40:
        return {
            "label": "Fair Match",
            "css_class": "fair",
            "verdict": (
                "Your resume partially matches the selected role. Focus on "
                "the missing technical skills and relevant project experience."
            ),
        }

    return {
        "label": "Needs Improvement",
        "css_class": "poor",
        "verdict": (
            "Your resume currently has a low match for this job role. "
            "Build relevant skills and improve role-specific keywords."
        ),
    }


@login_required
def analysis_result(request, resume_id):
    resume = get_object_or_404(
        Resume,
        id=resume_id,
        user=request.user,
    )

    ats_scores = (
        ATSScore.objects
        .filter(resume=resume)
        .select_related("job_role")
        .prefetch_related(
            "missing_skills__skill",
            "recommendations",
            "course_recommendations__course__skill",
        )
        .order_by("-score")
    )

    selected_score = ats_scores.first()

    analysis = getattr(
        resume,
        "analysis",
        None,
    )

    if analysis:
        extracted_skills = list(
            analysis.extracted_skills
            .select_related(
                "skill",
                "skill__category",
            )
            .order_by("skill__name")
        )
    else:
        extracted_skills = []

    missing_skills = []
    recommendations = []
    course_recommendations = []
    required_skills = []

    if selected_score:
        missing_skills = list(
            selected_score.missing_skills
            .select_related("skill")
            .all()
        )

        recommendations = list(
            selected_score.recommendations
            .all()
            .order_by("priority")
        )

        course_recommendations = list(
            selected_score.course_recommendations
            .select_related(
                "course",
                "course__skill",
            )
            .filter(course__is_active=True)
            .order_by(
                "priority",
                "-course__is_free",
                "-course__rating",
            )
        )

        required_skills = list(
            selected_score.job_role.required_skills
            .select_related("skill")
            .order_by("skill__name")
        )

    extracted_skill_ids = {
        item.skill_id
        for item in extracted_skills
    }

    skill_comparison = [
        {
            "skill": required_skill.skill,
            "is_found": (
                required_skill.skill_id
                in extracted_skill_ids
            ),
        }
        for required_skill in required_skills
    ]

    required_count = len(required_skills)

    found_required_count = sum(
        1
        for item in skill_comparison
        if item["is_found"]
    )

    if required_count:
        skill_match_percent = (
            found_required_count
            / required_count
        ) * 100
    else:
        skill_match_percent = 0

    score = (
        float(selected_score.score)
        if selected_score
        else 0
    )

    score_details = get_score_details(score)

    context = {
        "resume": resume,
        "analysis": analysis,
        "ats_scores": ats_scores,
        "selected_score": selected_score,

        "score": score,
        "score_label": score_details["label"],
        "score_class": score_details["css_class"],
        "verdict": score_details["verdict"],

        "extracted_skills": extracted_skills,
        "missing_skills": missing_skills,
        "recommendations": recommendations,
        "course_recommendations": course_recommendations,
        "skill_comparison": skill_comparison,

        "required_count": required_count,
        "found_required_count": found_required_count,
        "skill_match_percent": skill_match_percent,
    }

    return render(
        request,
        "ats/analysis_result.html",
        context,
    )


@login_required
def analysis_list(request):
    resumes = (
        Resume.objects
        .filter(user=request.user)
        .select_related("analysis")
        .order_by("-uploaded_at")
    )

    context = {
        "resumes": resumes,
    }

    return render(
        request,
        "ats/analysis_list.html",
        context,
    )