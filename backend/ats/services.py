from django.db import transaction

from jobs.models import JobRole, Skill

from .models import (
    ResumeAnalysis,
    ExtractedSkill,
    ATSScore,
    MissingSkill,
    Recommendation,
)

from .parser import ResumeParser
from .skill_extractor import SkillExtractor
from .ats_calculator import ATSCalculator


class ATSService:

    @staticmethod
    @transaction.atomic
    def analyze_resume(resume):

        # ---------- Extract Resume Text ----------

        text = ResumeParser.extract_text(
            resume.resume_file.path
        )

        found_skill_names = SkillExtractor.extract(text)

        analysis, _ = ResumeAnalysis.objects.update_or_create(
            resume=resume,
            defaults={
                "extracted_text": text,
                "total_skills": 0,
            }
        )

        # ---------- Clear Old Records ----------

        analysis.extracted_skills.all().delete()
        ATSScore.objects.filter(resume=resume).delete()

        # ---------- Save Extracted Skills ----------

        all_skills = Skill.objects.all()

        skill_map = {
            skill.name.lower(): skill
            for skill in all_skills
        }

        matched_skills = []

        for name in found_skill_names:

            skill = skill_map.get(name.lower())

            if skill:

                matched_skills.append(skill)

                ExtractedSkill.objects.create(
                    analysis=analysis,
                    skill=skill,
                    confidence_score=100
                )

        analysis.total_skills = len(matched_skills)
        analysis.save()

        # ---------- Calculate ATS for Every Job ----------

        jobs = JobRole.objects.all()

        for job in jobs:

            required = [
                obj.skill
                for obj in job.required_skills.select_related("skill")
            ]

            score = ATSCalculator.calculate(
                found_skill_names,
                required
            )

            ats = ATSScore.objects.create(
                resume=resume,
                job_role=job,
                score=score
            )

            # ---------- Missing Skills ----------

            found_lower = {
                s.lower()
                for s in found_skill_names
            }

            for skill in required:

                if skill.name.lower() not in found_lower:

                    MissingSkill.objects.create(
                        ats_score=ats,
                        skill=skill
                    )

            # ---------- Recommendation ----------

            if score < 60:

                Recommendation.objects.create(
                    ats_score=ats,
                    title="Improve Resume",
                    description="Add more required skills for this job role.",
                    priority=1
                )

            elif score < 80:

                Recommendation.objects.create(
                    ats_score=ats,
                    title="Good Resume",
                    description="Improve a few missing skills to increase ATS.",
                    priority=2
                )

            else:

                Recommendation.objects.create(
                    ats_score=ats,
                    title="Excellent Resume",
                    description="Your resume matches most job requirements.",
                    priority=3
                )

        return analysis 
