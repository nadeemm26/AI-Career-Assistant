from .skills import SKILLS


class SkillExtractor:

    @staticmethod
    def extract(text):

        text = text.lower()

        found_skills = []

        for skill in SKILLS:

            if skill.lower() in text:
                found_skills.append(skill)

        return sorted(list(set(found_skills)))