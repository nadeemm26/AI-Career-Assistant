import re

from .skills import SKILLS


class SkillExtractor:
    """
    Extract technical skills from resume text using exact matching,
    aliases and common skill-name variations.
    """

    SKILL_ALIASES = {
        "javascript": [
            "javascript",
            "java script",
            "js",
            "ecmascript",
        ],
        "typescript": [
            "typescript",
            "type script",
            "ts",
        ],
        "node.js": [
            "node.js",
            "nodejs",
            "node js",
            "node-js",
        ],
        "react.js": [
            "react.js",
            "reactjs",
            "react js",
            "react",
        ],
        "vue.js": [
            "vue.js",
            "vuejs",
            "vue js",
            "vue",
        ],
        "express.js": [
            "express.js",
            "expressjs",
            "express js",
            "express",
        ],
        "next.js": [
            "next.js",
            "nextjs",
            "next js",
        ],
        "angular": [
            "angular",
            "angular.js",
            "angularjs",
        ],
        "asp.net": [
            "asp.net",
            "asp net",
            "aspnet",
        ],
        ".net": [
            ".net",
            "dot net",
            "dotnet",
        ],
        "c#": [
            "c#",
            "c sharp",
            "csharp",
        ],
        "c++": [
            "c++",
            "cpp",
            "c plus plus",
        ],
        "mysql": [
            "mysql",
            "my sql",
        ],
        "postgresql": [
            "postgresql",
            "postgres",
            "postgre sql",
        ],
        "mongodb": [
            "mongodb",
            "mongo db",
            "mongo",
        ],
        "microsoft sql server": [
            "microsoft sql server",
            "ms sql server",
            "mssql",
            "sql server",
        ],
        "html": [
            "html",
            "html5",
        ],
        "css": [
            "css",
            "css3",
        ],
        "bootstrap": [
            "bootstrap",
            "bootstrap 5",
            "bootstrap5",
        ],
        "tailwind css": [
            "tailwind css",
            "tailwindcss",
            "tailwind",
        ],
        "github": [
            "github",
            "git hub",
        ],
        "visual studio code": [
            "visual studio code",
            "vs code",
            "vscode",
        ],
        "machine learning": [
            "machine learning",
            "ml",
        ],
        "artificial intelligence": [
            "artificial intelligence",
            "ai",
        ],
        "natural language processing": [
            "natural language processing",
            "nlp",
        ],
        "rest api": [
            "rest api",
            "restful api",
            "restful services",
            "rest services",
        ],
        "django rest framework": [
            "django rest framework",
            "drf",
        ],
        "object oriented programming": [
            "object oriented programming",
            "object-oriented programming",
            "oop",
        ],
    }

    @classmethod
    def extract(cls, text):
        if not text:
            return []

        normalized_text = cls._normalize_text(text)
        found_skills = []

        for skill in SKILLS:
            if cls._is_skill_present(skill, normalized_text):
                found_skills.append(skill)

        return sorted(set(found_skills), key=str.lower)

    @classmethod
    def _is_skill_present(cls, skill, normalized_text):
        skill_name = skill.strip()
        skill_key = skill_name.lower()

        aliases = cls.SKILL_ALIASES.get(skill_key, [skill_name])

        for alias in aliases:
            if cls._matches_alias(alias, normalized_text):
                return True

        return False

    @staticmethod
    def _normalize_text(text):
        text = text.lower()

        replacements = {
            "\u2013": "-",
            "\u2014": "-",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\n": " ",
            "\r": " ",
            "\t": " ",
        }

        for old_value, new_value in replacements.items():
            text = text.replace(old_value, new_value)

        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _matches_alias(alias, normalized_text):
        alias = alias.lower().strip()

        escaped_alias = re.escape(alias)

        # Spaces and hyphens are treated as interchangeable.
        escaped_alias = escaped_alias.replace(r"\ ", r"[\s\-]+")
        escaped_alias = escaped_alias.replace(r"\-", r"[\s\-]+")

        # Prevent substring matching:
        # Java should not match JavaScript.
        pattern = rf"(?<![a-zA-Z0-9]){escaped_alias}(?![a-zA-Z0-9])"

        return re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        ) is not None