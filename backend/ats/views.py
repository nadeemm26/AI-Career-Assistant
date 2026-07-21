from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from resume.models import Resume

from .models import ATSScore


@login_required
def analysis_result(request, resume_id):
    resume = get_object_or_404(
        Resume,
        id=resume_id,
        user=request.user
    )

    ats_scores = (
        ATSScore.objects
        .filter(resume=resume)
        .select_related("job_role")
        .prefetch_related(
            "missing_skills__skill",
            "recommendations"
        )
        .order_by("-score")
    )

    selected_score = ats_scores.first()

    analysis = getattr(resume, "analysis", None)

    extracted_skills = []

    if analysis:
        extracted_skills = (
            analysis.extracted_skills
            .select_related("skill", "skill__category")
            .order_by("skill__name")
        )

    missing_skills = []
    recommendations = []
    required_skills = []

    if selected_score:
        missing_skills = selected_score.missing_skills.all()
        recommendations = selected_score.recommendations.all().order_by(
            "priority"
        )

        required_skills = (
            selected_score.job_role.required_skills
            .select_related("skill")
            .order_by("skill__name")
        )

    extracted_skill_ids = {
        item.skill_id
        for item in extracted_skills
    }

    skill_comparison = []

    for required_skill in required_skills:
        skill_comparison.append({
            "skill": required_skill.skill,
            "is_found": required_skill.skill_id in extracted_skill_ids
        })

    score = float(selected_score.score) if selected_score else 0

    if score >= 80:
        score_label = "Excellent Match"
        score_class = "excellent"
        verdict = (
            "Your resume strongly matches the selected job role. "
            "You have most of the required technical skills."
        )
    elif score >= 60:
        score_label = "Good Match"
        score_class = "good"
        verdict = (
            "Your resume has a good foundation, but adding the missing "
            "skills can significantly improve your job match."
        )
    elif score >= 40:
        score_label = "Fair Match"
        score_class = "fair"
        verdict = (
            "Your resume partially matches the selected role. Focus on "
            "the missing technical skills and relevant project experience."
        )
    else:
        score_label = "Needs Improvement"
        score_class = "poor"
        verdict = (
            "Your resume currently has a low match for this job role. "
            "Build relevant skills and improve role-specific keywords."
        )

    context = {
        "resume": resume,
        "analysis": analysis,
        "ats_scores": ats_scores,
        "selected_score": selected_score,
        "score": score,
        "score_label": score_label,
        "score_class": score_class,
        "verdict": verdict,
        "extracted_skills": extracted_skills,
        "missing_skills": missing_skills,
        "recommendations": recommendations,
        "skill_comparison": skill_comparison,
    }

    return render(
        request,
        "ats/analysis_result.html",
        context
    )

@login_required
def analysis_list(request):

    resumes = Resume.objects.filter(
        user=request.user
    ).select_related(
        "analysis"
    ).order_by(
        "-uploaded_at"
    )

    context = {
        "resumes": resumes
    }

    return render(
        request,
        "ats/analysis_list.html",
        context
    )