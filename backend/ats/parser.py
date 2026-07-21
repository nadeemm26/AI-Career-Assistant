import pdfplumber
from docx import Document


class ResumeParser:

    @staticmethod
    def extract_text(file_path):

        if file_path.endswith(".pdf"):
            return ResumeParser._extract_pdf(file_path)

        elif file_path.endswith(".docx"):
            return ResumeParser._extract_docx(file_path)

        return ""

    @staticmethod
    def _extract_pdf(file_path):

        text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"

        return text

    @staticmethod
    def _extract_docx(file_path):

        document = Document(file_path)

        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

        return text