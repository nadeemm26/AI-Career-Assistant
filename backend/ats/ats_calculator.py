class ATSCalculator:

    @staticmethod
    def calculate(found_skills, required_skills):

        required_names = [
            skill.name.lower()
            for skill in required_skills
        ]

        found_names = [
            skill.lower()
            for skill in found_skills
        ]

        matched = len(
            set(found_names).intersection(required_names)
        )

        if len(required_names) == 0:
            return 0

        score = (matched / len(required_names)) * 100

        return round(score, 2)