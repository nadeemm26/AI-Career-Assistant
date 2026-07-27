import re


class ResumeContentValidator:
    """
    Validates whether extracted document text appears
    to contain resume-related content.
    """

    SECTION_KEYWORDS = {
        "skills": [
            "skills",
            "technical skills",
            "core competencies",
            "technologies",
        ],
        "education": [
            "education",
            "academic qualification",
            "academic background",
            "qualification",
        ],
        "experience": [
            "experience",
            "work experience",
            "employment history",
            "professional experience",
            "internship",
        ],
        "projects": [
            "projects",
            "academic projects",
            "personal projects",
            "project experience",
        ],
        "summary": [
            "summary",
            "professional summary",
            "career objective",
            "objective",
            "profile",
        ],
        "certifications": [
            "certification",
            "certifications",
            "courses",
            "training",
        ],
    }

    @classmethod
    def validate(cls, text):
        if not text or not text.strip():
            return False, "No readable text was found in this file."

        normalized_text = re.sub(
            r"\s+",
            " ",
            text.lower()
        ).strip()

        # Very small documents are unlikely to be resumes.
        if len(normalized_text) < 150:
            return False, (
                "The uploaded document does not contain "
                "enough readable resume content."
            )

        detected_sections = []

        for section, keywords in cls.SECTION_KEYWORDS.items():
            if any(
                keyword in normalized_text
                for keyword in keywords
            ):
                detected_sections.append(section)

        email_found = bool(
            re.search(
                r"[\w.+-]+@[\w-]+\.[\w.-]+",
                normalized_text
            )
        )

        phone_found = bool(
            re.search(
                r"(?:\+?\d[\d\s\-()]{8,}\d)",
                normalized_text
            )
        )

        contact_found = email_found or phone_found

        # Resume should contain at least three known sections.
        if len(detected_sections) < 3:
            return False, (
                "This document does not appear to be a resume. "
                "Please upload a file containing sections such as "
                "Skills, Education, Experience or Projects."
            )

        # Resume should normally include some contact information.
        if not contact_found:
            return False, (
                "No email address or phone number was detected. "
                "Please upload a valid resume."
            )

        return True, {
            "detected_sections": detected_sections,
            "email_found": email_found,
            "phone_found": phone_found,
        }