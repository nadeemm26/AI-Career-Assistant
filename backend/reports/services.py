from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ats.models import ATSScore
from resume.models import Resume

from .models import Report


class ScoreGauge(Flowable):
    """
    Circular ATS score indicator drawn directly on the PDF canvas.
    """

    def __init__(self, score, label, width=42 * mm, height=42 * mm):
        super().__init__()

        self.score = max(0, min(float(score or 0), 100))
        self.label = label
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv

        center_x = self.width / 2
        center_y = self.height / 2
        radius = min(self.width, self.height) / 2 - 5

        canvas.saveState()

        canvas.setLineCap(1)
        canvas.setLineWidth(8)

        canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
        canvas.circle(
            center_x,
            center_y,
            radius,
            stroke=1,
            fill=0,
        )

        if self.score >= 80:
            score_color = colors.HexColor("#16A34A")
        elif self.score >= 60:
            score_color = colors.HexColor("#0284C7")
        elif self.score >= 40:
            score_color = colors.HexColor("#D97706")
        else:
            score_color = colors.HexColor("#DC2626")

        canvas.setStrokeColor(score_color)

        canvas.arc(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            startAng=90,
            extent=-(360 * self.score / 100),
        )

        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.setFont("Helvetica-Bold", 19)

        canvas.drawCentredString(
            center_x,
            center_y + 2,
            f"{self.score:.0f}%",
        )

        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.setFont("Helvetica-Bold", 7)

        canvas.drawCentredString(
            center_x,
            center_y - 12,
            self.label.upper(),
        )

        canvas.restoreState()


class HorizontalProgressBar(Flowable):
    """
    Reusable horizontal progress bar.
    """

    def __init__(
        self,
        value,
        width=115 * mm,
        height=7 * mm,
        foreground="#4F46E5",
        background="#E5E7EB",
    ):
        super().__init__()

        self.value = max(0, min(float(value or 0), 100))
        self.width = width
        self.height = height
        self.foreground = colors.HexColor(foreground)
        self.background = colors.HexColor(background)

    def draw(self):
        canvas = self.canv

        canvas.saveState()

        radius = self.height / 2

        canvas.setFillColor(self.background)
        canvas.roundRect(
            0,
            0,
            self.width,
            self.height,
            radius,
            stroke=0,
            fill=1,
        )

        filled_width = self.width * self.value / 100

        if filled_width > 0:
            canvas.setFillColor(self.foreground)
            canvas.roundRect(
                0,
                0,
                filled_width,
                self.height,
                min(radius, filled_width / 2),
                stroke=0,
                fill=1,
            )

        canvas.restoreState()


class PDFReportService:
    PRIMARY = colors.HexColor("#4F46E5")
    PRIMARY_DARK = colors.HexColor("#3730A3")
    SECONDARY = colors.HexColor("#7C3AED")

    SUCCESS = colors.HexColor("#16A34A")
    SUCCESS_DARK = colors.HexColor("#166534")
    SUCCESS_LIGHT = colors.HexColor("#DCFCE7")

    DANGER = colors.HexColor("#DC2626")
    DANGER_DARK = colors.HexColor("#991B1B")
    DANGER_LIGHT = colors.HexColor("#FEE2E2")

    WARNING = colors.HexColor("#D97706")
    WARNING_LIGHT = colors.HexColor("#FEF3C7")

    INFO = colors.HexColor("#0284C7")
    INFO_LIGHT = colors.HexColor("#E0F2FE")

    DARK = colors.HexColor("#111827")
    TEXT = colors.HexColor("#374151")
    MUTED = colors.HexColor("#6B7280")

    BACKGROUND = colors.HexColor("#F4F7FB")
    LIGHT_BACKGROUND = colors.HexColor("#F8FAFC")
    BORDER = colors.HexColor("#E5E7EB")
    WHITE = colors.white

    @classmethod
    @transaction.atomic
    def generate(cls, user, resume_id):
        resume = (
            Resume.objects
            .select_related("user")
            .filter(
                id=resume_id,
                user=user,
            )
            .first()
        )

        if not resume:
            raise ValueError("Resume not found.")

        selected_score = (
            ATSScore.objects
            .filter(resume=resume)
            .select_related(
                "job_role",
                "resume",
                "resume__user",
            )
            .prefetch_related(
                "missing_skills__skill",
                "recommendations",
                "course_recommendations__course__skill",
                "job_role__required_skills__skill",
            )
            .order_by("-score")
            .first()
        )

        if not selected_score:
            raise ValueError(
                "ATS analysis is not available for this resume."
            )

        report = Report.objects.create(
            user=user,
            resume=resume,
            report_type="pdf",
            status="pending",
        )

        try:
            pdf_bytes = cls._build_pdf(
                report=report,
                resume=resume,
                ats_score=selected_score,
            )

            safe_name = (
                slugify(
                    Path(resume.original_filename).stem
                )
                or f"resume-{resume.id}"
            )

            filename = (
                f"{safe_name}-premium-ats-report-"
                f"{timezone.now():%Y%m%d-%H%M%S}.pdf"
            )

            report.report_file.save(
                filename,
                ContentFile(pdf_bytes),
                save=False,
            )

            report.status = "generated"
            report.generated_at = timezone.now()

            report.save(
                update_fields=[
                    "report_file",
                    "status",
                    "generated_at",
                ]
            )

            return report

        except Exception:
            report.status = "failed"

            report.save(
                update_fields=["status"]
            )

            raise

    @classmethod
    def _build_pdf(
        cls,
        report,
        resume,
        ats_score,
    ):
        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=16 * mm,
            bottomMargin=18 * mm,
            title="AI Career Assistant - Premium ATS Report",
            author="AI Career Assistant",
            subject="ATS Resume Analysis Report",
        )

        styles = cls._get_styles()
        story = []

        analysis = getattr(
            resume,
            "analysis",
            None,
        )

        extracted_skills = []

        if analysis:
            extracted_skills = list(
                analysis.extracted_skills
                .select_related("skill")
                .order_by("skill__name")
            )

        missing_skills = list(
            ats_score.missing_skills
            .select_related("skill")
            .order_by("skill__name")
        )

        recommendations = list(
            ats_score.recommendations
            .all()
            .order_by("priority")
        )

        course_recommendations = list(
            ats_score.course_recommendations
            .select_related(
                "course",
                "course__skill",
            )
            .filter(
                course__is_active=True
            )
            .order_by(
                "priority",
                "course__title",
            )
        )

        required_skills = list(
            ats_score.job_role.required_skills
            .select_related("skill")
            .order_by("skill__name")
        )

        extracted_skill_ids = {
            item.skill_id
            for item in extracted_skills
        }

        matched_count = sum(
            1
            for required_skill in required_skills
            if required_skill.skill_id in extracted_skill_ids
        )

        required_count = len(required_skills)

        skill_match_percent = (
            round(
                matched_count
                / required_count
                * 100
            )
            if required_count
            else 0
        )

        score = float(
            ats_score.score or 0
        )

        score_label = cls._get_score_label(
            score
        )

        verdict = cls._get_verdict(
            score=score,
            missing_skills=missing_skills,
        )

        cls._add_cover_header(
            story=story,
            styles=styles,
            report=report,
            resume=resume,
            ats_score=ats_score,
        )

        cls._add_candidate_information(
            story=story,
            styles=styles,
            report=report,
            resume=resume,
            ats_score=ats_score,
        )

        cls._add_executive_summary(
            story=story,
            styles=styles,
            score=score,
            score_label=score_label,
            verdict=verdict,
            extracted_count=len(extracted_skills),
            missing_count=len(missing_skills),
            matched_count=matched_count,
            required_count=required_count,
            skill_match_percent=skill_match_percent,
        )

        cls._add_score_breakdown(
            story=story,
            styles=styles,
            score=score,
            skill_match_percent=skill_match_percent,
            extracted_count=len(extracted_skills),
            required_count=required_count,
        )

        cls._add_skill_cards(
            story=story,
            styles=styles,
            title="Detected Technical Skills",
            subtitle=(
                "Technical skills successfully identified "
                "from the uploaded resume."
            ),
            skills=[
                item.skill.name
                for item in extracted_skills
            ],
            found=True,
        )

        cls._add_skill_cards(
            story=story,
            styles=styles,
            title="Priority Skill Gaps",
            subtitle=(
                "Skills required for the selected role but "
                "not identified in the resume."
            ),
            skills=[
                item.skill.name
                for item in missing_skills
            ],
            found=False,
        )

        cls._add_skill_comparison(
            story=story,
            styles=styles,
            required_skills=required_skills,
            extracted_skill_ids=extracted_skill_ids,
        )

        story.append(PageBreak())

        cls._add_improvement_plan(
            story=story,
            styles=styles,
            recommendations=recommendations,
            missing_skills=missing_skills,
            score=score,
        )

        cls._add_courses(
            story=story,
            styles=styles,
            course_recommendations=course_recommendations,
        )

        cls._add_final_verdict(
            story=story,
            styles=styles,
            score=score,
            score_label=score_label,
            verdict=verdict,
            missing_skills=missing_skills,
        )

        cls._add_disclaimer(
            story=story,
            styles=styles,
            report=report,
        )

        document.build(
            story,
            onFirstPage=cls._draw_page_footer,
            onLaterPages=cls._draw_page_footer,
        )

        pdf_value = buffer.getvalue()
        buffer.close()

        return pdf_value

    @classmethod
    def _get_styles(cls):
        styles = getSampleStyleSheet()

        styles.add(
            ParagraphStyle(
                name="BrandSmall",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#DDD6FE"),
                alignment=TA_CENTER,
                spaceAfter=4,
            )
        )

        styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=23,
                leading=29,
                textColor=cls.WHITE,
                alignment=TA_CENTER,
                spaceAfter=7,
            )
        )

        styles.add(
            ParagraphStyle(
                name="ReportSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=14,
                textColor=colors.HexColor("#EDE9FE"),
                alignment=TA_CENTER,
            )
        )

        styles.add(
            ParagraphStyle(
                name="SectionTitle",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=15,
                leading=19,
                textColor=cls.PRIMARY_DARK,
                spaceBefore=13,
                spaceAfter=5,
            )
        )

        styles.add(
            ParagraphStyle(
                name="SectionSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8.5,
                leading=13,
                textColor=cls.MUTED,
                spaceAfter=10,
            )
        )

        styles.add(
            ParagraphStyle(
                name="Body",
                parent=styles["BodyText"],
                fontName="Helvetica",
                fontSize=9,
                leading=14,
                textColor=cls.TEXT,
            )
        )

        styles.add(
            ParagraphStyle(
                name="BodyBold",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=14,
                textColor=cls.DARK,
            )
        )

        styles.add(
            ParagraphStyle(
                name="Small",
                parent=styles["BodyText"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=11,
                textColor=cls.MUTED,
            )
        )

        styles.add(
            ParagraphStyle(
                name="SmallBold",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=11,
                textColor=cls.TEXT,
            )
        )

        styles.add(
            ParagraphStyle(
                name="TableHeader",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=11,
                textColor=cls.WHITE,
            )
        )

        styles.add(
            ParagraphStyle(
                name="CenteredMetric",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                textColor=cls.PRIMARY,
                alignment=TA_CENTER,
            )
        )

        styles.add(
            ParagraphStyle(
                name="CenteredLabel",
                parent=styles["BodyText"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=10,
                textColor=cls.MUTED,
                alignment=TA_CENTER,
            )
        )

        styles.add(
            ParagraphStyle(
                name="WhiteBold",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=13,
                textColor=cls.WHITE,
            )
        )

        styles.add(
            ParagraphStyle(
                name="VerdictTitle",
                parent=styles["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=17,
                textColor=cls.PRIMARY_DARK,
            )
        )

        return styles

    @classmethod
    def _add_cover_header(
        cls,
        story,
        styles,
        report,
        resume,
        ats_score,
    ):
        generated_date = timezone.localtime().strftime(
            "%d %b %Y, %I:%M %p"
        )

        report_code = cls._report_code(
            report
        )

        content = [
            [
                Paragraph(
                    "AI CAREER ASSISTANT",
                    styles["BrandSmall"],
                )
            ],
            [
                Paragraph(
                    "Premium ATS Resume Analysis Report",
                    styles["ReportTitle"],
                )
            ],
            [
                Paragraph(
                    (
                        f"{escape(resume.original_filename)}"
                        f" &nbsp; | &nbsp; "
                        f"{escape(ats_score.job_role.title)}"
                    ),
                    styles["ReportSubtitle"],
                )
            ],
            [
                Paragraph(
                    (
                        f"Report ID: {report_code}"
                        f" &nbsp; | &nbsp; "
                        f"Generated: {generated_date}"
                    ),
                    styles["ReportSubtitle"],
                )
            ],
        ]

        table = Table(
            content,
            colWidths=[178 * mm],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        cls.PRIMARY,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, 0),
                        13,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, -1),
                        (-1, -1),
                        13,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        14,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        14,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0,
                        cls.PRIMARY,
                    ),
                ]
            )
        )

        story.append(table)
        story.append(Spacer(1, 11))

    @classmethod
    def _add_candidate_information(
        cls,
        story,
        styles,
        report,
        resume,
        ats_score,
    ):
        user = resume.user

        phone_number = (
            user.phone_number
            if getattr(user, "phone_number", "")
            else "Not provided"
        )

        candidate_data = [
            [
                Paragraph(
                    "Candidate Profile",
                    styles["WhiteBold"],
                ),
                "",
            ],
            [
                Paragraph(
                    "<b>Candidate Name</b>",
                    styles["Small"],
                ),
                Paragraph(
                    escape(user.full_name),
                    styles["Body"],
                ),
            ],
            [
                Paragraph(
                    "<b>Email Address</b>",
                    styles["Small"],
                ),
                Paragraph(
                    escape(user.email),
                    styles["Body"],
                ),
            ],
            [
                Paragraph(
                    "<b>Phone Number</b>",
                    styles["Small"],
                ),
                Paragraph(
                    escape(phone_number),
                    styles["Body"],
                ),
            ],
        ]

        report_data = [
            [
                Paragraph(
                    "Analysis Information",
                    styles["WhiteBold"],
                ),
                "",
            ],
            [
                Paragraph(
                    "<b>Target Job Role</b>",
                    styles["Small"],
                ),
                Paragraph(
                    escape(ats_score.job_role.title),
                    styles["Body"],
                ),
            ],
            [
                Paragraph(
                    "<b>Resume File</b>",
                    styles["Small"],
                ),
                Paragraph(
                    escape(resume.original_filename),
                    styles["Body"],
                ),
            ],
            [
                Paragraph(
                    "<b>Report Type</b>",
                    styles["Small"],
                ),
                Paragraph(
                    "Premium ATS PDF",
                    styles["Body"],
                ),
            ],
        ]

        left_table = Table(
            candidate_data,
            colWidths=[
                35 * mm,
                48 * mm,
            ],
        )

        right_table = Table(
            report_data,
            colWidths=[
                35 * mm,
                48 * mm,
            ],
        )

        for table in [left_table, right_table]:
            table.setStyle(
                TableStyle(
                    [
                        (
                            "SPAN",
                            (0, 0),
                            (1, 0),
                        ),
                        (
                            "BACKGROUND",
                            (0, 0),
                            (1, 0),
                            cls.PRIMARY_DARK,
                        ),
                        (
                            "BACKGROUND",
                            (0, 1),
                            (-1, -1),
                            cls.LIGHT_BACKGROUND,
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.7,
                            cls.BORDER,
                        ),
                        (
                            "INNERGRID",
                            (0, 1),
                            (-1, -1),
                            0.4,
                            cls.BORDER,
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            7,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            7,
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                    ]
                )
            )

        wrapper = Table(
            [[left_table, right_table]],
            colWidths=[
                86 * mm,
                86 * mm,
            ],
            hAlign="CENTER",
        )

        wrapper.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                ]
            )
        )

        story.append(wrapper)
        story.append(Spacer(1, 9))

    @classmethod
    def _add_executive_summary(
        cls,
        story,
        styles,
        score,
        score_label,
        verdict,
        extracted_count,
        missing_count,
        matched_count,
        required_count,
        skill_match_percent,
    ):
        story.append(
            Paragraph(
                "Executive Summary",
                styles["SectionTitle"],
            )
        )

        story.append(
            Paragraph(
                (
                    "A high-level overview of the resume's ATS "
                    "compatibility and skill alignment."
                ),
                styles["SectionSubtitle"],
            )
        )

        gauge = ScoreGauge(
            score=score,
            label=score_label,
        )

        summary_metrics = Table(
            [
                [
                    Paragraph(
                        str(extracted_count),
                        styles["CenteredMetric"],
                    ),
                    Paragraph(
                        str(missing_count),
                        styles["CenteredMetric"],
                    ),
                    Paragraph(
                        (
                            f"{matched_count}/{required_count}"
                            if required_count
                            else "0/0"
                        ),
                        styles["CenteredMetric"],
                    ),
                ],
                [
                    Paragraph(
                        "Skills Detected",
                        styles["CenteredLabel"],
                    ),
                    Paragraph(
                        "Missing Skills",
                        styles["CenteredLabel"],
                    ),
                    Paragraph(
                        "Required Skills Matched",
                        styles["CenteredLabel"],
                    ),
                ],
            ],
            colWidths=[
                34 * mm,
                34 * mm,
                42 * mm,
            ],
        )

        summary_metrics.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        cls.LIGHT_BACKGROUND,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        cls.BORDER,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        cls.BORDER,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, 0),
                        12,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 1),
                        (-1, 1),
                        11,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                ]
            )
        )

        verdict_box = Table(
            [
                [
                    Paragraph(
                        escape(score_label),
                        styles["VerdictTitle"],
                    )
                ],
                [
                    Paragraph(
                        escape(verdict),
                        styles["Body"],
                    )
                ],
                [
                    Paragraph(
                        (
                            f"Required skill alignment: "
                            f"<b>{skill_match_percent}%</b>"
                        ),
                        styles["Body"],
                    )
                ],
            ],
            colWidths=[56 * mm],
        )

        verdict_box.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        cls.INFO_LIGHT,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        colors.HexColor("#BAE6FD"),
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                ]
            )
        )

        layout = Table(
            [
                [
                    gauge,
                    summary_metrics,
                    verdict_box,
                ]
            ],
            colWidths=[
                45 * mm,
                72 * mm,
                61 * mm,
            ],
        )

        layout.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        story.append(layout)
        story.append(Spacer(1, 8))

    @classmethod
    def _add_score_breakdown(
        cls,
        story,
        styles,
        score,
        skill_match_percent,
        extracted_count,
        required_count,
    ):
        story.append(
            Paragraph(
                "ATS Performance Breakdown",
                styles["SectionTitle"],
            )
        )

        story.append(
            Paragraph(
                (
                    "Visual indicators showing ATS compatibility "
                    "and required skill coverage."
                ),
                styles["SectionSubtitle"],
            )
        )

        ats_bar = HorizontalProgressBar(
            value=score,
            width=105 * mm,
            foreground=cls._score_hex(score),
        )

        skill_bar = HorizontalProgressBar(
            value=skill_match_percent,
            width=105 * mm,
            foreground="#4F46E5",
        )

        rows = [
            [
                Paragraph(
                    "<b>Overall ATS Compatibility</b>",
                    styles["Body"],
                ),
                ats_bar,
                Paragraph(
                    f"<b>{score:.0f}%</b>",
                    styles["Body"],
                ),
            ],
            [
                Paragraph(
                    "<b>Required Skill Match</b>",
                    styles["Body"],
                ),
                skill_bar,
                Paragraph(
                    f"<b>{skill_match_percent}%</b>",
                    styles["Body"],
                ),
            ],
            [
                Paragraph(
                    "<b>Technical Skills Detected</b>",
                    styles["Body"],
                ),
                Paragraph(
                    (
                        f"{extracted_count} skills were identified "
                        f"from the uploaded resume."
                    ),
                    styles["Small"],
                ),
                Paragraph(
                    (
                        f"<b>{required_count}</b> required"
                        if required_count
                        else "<b>0</b> required"
                    ),
                    styles["Body"],
                ),
            ],
        ]

        table = Table(
            rows,
            colWidths=[
                45 * mm,
                108 * mm,
                24 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        cls.LIGHT_BACKGROUND,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        cls.BORDER,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        cls.BORDER,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                ]
            )
        )

        story.append(table)

    @classmethod
    def _add_skill_cards(
        cls,
        story,
        styles,
        title,
        subtitle,
        skills,
        found,
    ):
        story.append(
            Paragraph(
                escape(title),
                styles["SectionTitle"],
            )
        )

        story.append(
            Paragraph(
                escape(subtitle),
                styles["SectionSubtitle"],
            )
        )

        if not skills:
            message = (
                "No technical skills were detected."
                if found
                else "No required skills are missing."
            )

            cls._add_empty_box(
                story=story,
                styles=styles,
                message=message,
            )

            return

        rows = []

        for index in range(
            0,
            len(skills),
            3,
        ):
            row_skills = skills[
                index:index + 3
            ]

            cells = []

            for skill in row_skills:
                status_text = (
                    "FOUND"
                    if found
                    else "MISSING"
                )

                cell = Paragraph(
                    (
                        f"<b>{status_text}</b><br/>"
                        f"{escape(skill)}"
                    ),
                    styles["Body"],
                )

                cells.append(cell)

            while len(cells) < 3:
                cells.append("")

            rows.append(cells)

        table = Table(
            rows,
            colWidths=[
                59 * mm,
                59 * mm,
                59 * mm,
            ],
        )

        background = (
            cls.SUCCESS_LIGHT
            if found
            else cls.DANGER_LIGHT
        )

        text_color = (
            cls.SUCCESS_DARK
            if found
            else cls.DANGER_DARK
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        background,
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, -1),
                        text_color,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.6,
                        cls.WHITE,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        3,
                        cls.WHITE,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                ]
            )
        )

        story.append(table)

    @classmethod
    def _add_skill_comparison(
        cls,
        story,
        styles,
        required_skills,
        extracted_skill_ids,
    ):
        story.append(
            Paragraph(
                "Required Skill Comparison",
                styles["SectionTitle"],
            )
        )

        story.append(
            Paragraph(
                (
                    "A detailed comparison between the target role "
                    "requirements and detected resume skills."
                ),
                styles["SectionSubtitle"],
            )
        )

        if not required_skills:
            cls._add_empty_box(
                story=story,
                styles=styles,
                message=(
                    "No required skills are configured "
                    "for this job role."
                ),
            )

            return

        data = [
            [
                Paragraph(
                    "Required Skill",
                    styles["TableHeader"],
                ),
                Paragraph(
                    "Match Status",
                    styles["TableHeader"],
                ),
                Paragraph(
                    "Recommendation",
                    styles["TableHeader"],
                ),
            ]
        ]

        for required_skill in required_skills:
            is_found = (
                required_skill.skill_id
                in extracted_skill_ids
            )

            status = (
                "<font color='#166534'><b>Found</b></font>"
                if is_found
                else (
                    "<font color='#991B1B'>"
                    "<b>Missing</b></font>"
                )
            )

            recommendation = (
                "Maintain and highlight this skill in projects."
                if is_found
                else (
                    "Add this skill after gaining practical "
                    "knowledge or project experience."
                )
            )

            data.append(
                [
                    Paragraph(
                        escape(
                            required_skill.skill.name
                        ),
                        styles["Body"],
                    ),
                    Paragraph(
                        status,
                        styles["Body"],
                    ),
                    Paragraph(
                        recommendation,
                        styles["Small"],
                    ),
                ]
            )

        table = Table(
            data,
            colWidths=[
                50 * mm,
                35 * mm,
                92 * mm,
            ],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        cls.PRIMARY_DARK,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        cls.BORDER,
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            cls.WHITE,
                            cls.LIGHT_BACKGROUND,
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                ]
            )
        )

        story.append(table)

    @classmethod
    def _add_improvement_plan(
        cls,
        story,
        styles,
        recommendations,
        missing_skills,
        score,
    ):
        story.append(
            Paragraph(
                "Personalized Improvement Plan",
                styles["SectionTitle"],
            )
        )

        story.append(
            Paragraph(
                (
                    "Actionable recommendations designed to improve "
                    "resume quality and ATS compatibility."
                ),
                styles["SectionSubtitle"],
            )
        )

        improvement_items = []

        for recommendation in recommendations:
            improvement_items.append(
                (
                    recommendation.title,
                    recommendation.description,
                )
            )

        if missing_skills:
            missing_names = ", ".join(
                item.skill.name
                for item in missing_skills[:5]
            )

            improvement_items.append(
                (
                    "Develop Missing Technical Skills",
                    (
                        f"Prioritize practical learning in "
                        f"{missing_names}. Add these skills only "
                        f"after completing exercises or projects."
                    ),
                )
            )

        if score < 80:
            improvement_items.append(
                (
                    "Strengthen Project Descriptions",
                    (
                        "Use measurable results, clear responsibilities "
                        "and relevant technologies when describing projects."
                    ),
                )
            )

            improvement_items.append(
                (
                    "Improve ATS Keywords",
                    (
                        "Use role-specific keywords naturally in the "
                        "summary, skills and project sections."
                    ),
                )
            )

        if not improvement_items:
            improvement_items.append(
                (
                    "Maintain Resume Quality",
                    (
                        "Your resume demonstrates strong alignment. "
                        "Keep skills, projects and experience updated."
                    ),
                )
            )

        for index, (
            title,
            description,
        ) in enumerate(
            improvement_items,
            start=1,
        ):
            number_box = Table(
                [
                    [
                        Paragraph(
                            str(index),
                            ParagraphStyle(
                                name=f"PlanNumber{index}",
                                parent=styles["BodyBold"],
                                textColor=cls.WHITE,
                                alignment=TA_CENTER,
                            ),
                        )
                    ]
                ],
                colWidths=[11 * mm],
                rowHeights=[11 * mm],
            )

            number_box.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            cls.PRIMARY,
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),
                    ]
                )
            )

            content = Table(
                [
                    [
                        Paragraph(
                            escape(title),
                            styles["BodyBold"],
                        )
                    ],
                    [
                        Paragraph(
                            escape(description),
                            styles["Body"],
                        )
                    ],
                ],
                colWidths=[158 * mm],
            )

            card = Table(
                [[number_box, content]],
                colWidths=[
                    14 * mm,
                    162 * mm,
                ],
            )

            card.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (1, 0),
                            (1, 0),
                            cls.LIGHT_BACKGROUND,
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.6,
                            cls.BORDER,
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                        (
                            "TOPPADDING",
                            (1, 0),
                            (1, 0),
                            8,
                        ),
                        (
                            "BOTTOMPADDING",
                            (1, 0),
                            (1, 0),
                            8,
                        ),
                        (
                            "LEFTPADDING",
                            (1, 0),
                            (1, 0),
                            9,
                        ),
                        (
                            "RIGHTPADDING",
                            (1, 0),
                            (1, 0),
                            9,
                        ),
                    ]
                )
            )

            story.append(
                KeepTogether(
                    [
                        card,
                        Spacer(1, 6),
                    ]
                )
            )

    @classmethod
    def _add_courses(
        cls,
        story,
        styles,
        course_recommendations,
    ):
        story.append(
            Paragraph(
                "Recommended Learning Resources",
                styles["SectionTitle"],
            )
        )

        story.append(
            Paragraph(
                (
                    "Courses selected according to missing skills "
                    "for the best-matching job role."
                ),
                styles["SectionSubtitle"],
            )
        )

        if not course_recommendations:
            cls._add_empty_box(
                story=story,
                styles=styles,
                message=(
                    "No course recommendations are currently "
                    "available for this analysis."
                ),
            )

            return

        data = [
            [
                Paragraph(
                    "Course",
                    styles["TableHeader"],
                ),
                Paragraph(
                    "Skill",
                    styles["TableHeader"],
                ),
                Paragraph(
                    "Provider",
                    styles["TableHeader"],
                ),
                Paragraph(
                    "Level",
                    styles["TableHeader"],
                ),
                Paragraph(
                    "Type",
                    styles["TableHeader"],
                ),
            ]
        ]

        for item in course_recommendations:
            course = item.course

            data.append(
                [
                    Paragraph(
                        escape(course.title),
                        styles["BodyBold"],
                    ),
                    Paragraph(
                        escape(course.skill.name),
                        styles["Body"],
                    ),
                    Paragraph(
                        escape(course.provider),
                        styles["Body"],
                    ),
                    Paragraph(
                        escape(
                            course.get_level_display()
                        ),
                        styles["Body"],
                    ),
                    Paragraph(
                        (
                            "<font color='#166534'><b>Free</b></font>"
                            if course.is_free
                            else (
                                "<font color='#92400E'>"
                                "<b>Paid</b></font>"
                            )
                        ),
                        styles["Body"],
                    ),
                ]
            )

        table = Table(
            data,
            colWidths=[
                64 * mm,
                28 * mm,
                38 * mm,
                29 * mm,
                18 * mm,
            ],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        cls.PRIMARY_DARK,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        cls.BORDER,
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            cls.WHITE,
                            cls.LIGHT_BACKGROUND,
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                ]
            )
        )

        story.append(table)

    @classmethod
    def _add_final_verdict(
        cls,
        story,
        styles,
        score,
        score_label,
        verdict,
        missing_skills,
    ):
        story.append(
            Paragraph(
                "Final Assessment",
                styles["SectionTitle"],
            )
        )

        improvement_text = ""

        if missing_skills:
            missing_names = ", ".join(
                item.skill.name
                for item in missing_skills[:4]
            )

            improvement_text = (
                f" Priority areas include {missing_names}."
            )

        content = [
            [
                Paragraph(
                    f"{score:.0f}%",
                    ParagraphStyle(
                        name="FinalScore",
                        parent=styles["CenteredMetric"],
                        fontSize=24,
                        leading=28,
                        textColor=cls.PRIMARY,
                    ),
                ),
                Paragraph(
                    (
                        f"<b>{escape(score_label)}</b><br/>"
                        f"{escape(verdict)}"
                        f"{escape(improvement_text)}"
                    ),
                    styles["Body"],
                ),
            ]
        ]

        table = Table(
            content,
            colWidths=[
                35 * mm,
                142 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, 0),
                        cls.INFO_LIGHT,
                    ),
                    (
                        "BACKGROUND",
                        (1, 0),
                        (1, 0),
                        cls.LIGHT_BACKGROUND,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.8,
                        cls.BORDER,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        12,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        12,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                ]
            )
        )

        story.append(table)

    @classmethod
    def _add_disclaimer(
        cls,
        story,
        styles,
        report,
    ):
        story.append(Spacer(1, 14))

        report_code = cls._report_code(
            report
        )

        disclaimer = Table(
            [
                [
                    Paragraph(
                        "<b>Important Notice</b>",
                        styles["SmallBold"],
                    )
                ],
                [
                    Paragraph(
                        (
                            "This report was automatically generated "
                            "by AI Career Assistant. ATS scores and "
                            "recommendations are intended to support "
                            "resume improvement and do not guarantee "
                            "job selection or recruitment outcomes."
                        ),
                        styles["Small"],
                    )
                ],
                [
                    Paragraph(
                        (
                            f"Report Reference: {report_code} "
                            f"| Version 1.0"
                        ),
                        styles["Small"],
                    )
                ],
            ],
            colWidths=[177 * mm],
        )

        disclaimer.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        cls.WARNING_LIGHT,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        colors.HexColor("#FDE68A"),
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                ]
            )
        )

        story.append(disclaimer)

    @classmethod
    def _add_empty_box(
        cls,
        story,
        styles,
        message,
    ):
        table = Table(
            [
                [
                    Paragraph(
                        escape(message),
                        styles["Body"],
                    )
                ]
            ],
            colWidths=[177 * mm],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        cls.LIGHT_BACKGROUND,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        cls.BORDER,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        11,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        11,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                ]
            )
        )

        story.append(table)

    @classmethod
    def _draw_page_footer(
        cls,
        canvas,
        document,
    ):
        canvas.saveState()

        page_width, page_height = A4

        canvas.setStrokeColor(cls.BORDER)
        canvas.setLineWidth(0.6)

        canvas.line(
            16 * mm,
            13 * mm,
            page_width - 16 * mm,
            13 * mm,
        )

        canvas.setFont(
            "Helvetica-Bold",
            7,
        )
        canvas.setFillColor(
            cls.PRIMARY_DARK
        )

        canvas.drawString(
            16 * mm,
            8 * mm,
            "AI Career Assistant",
        )

        canvas.setFont(
            "Helvetica",
            7,
        )
        canvas.setFillColor(
            cls.MUTED
        )

        canvas.drawCentredString(
            page_width / 2,
            8 * mm,
            "Confidential ATS Analysis Report",
        )

        canvas.drawRightString(
            page_width - 16 * mm,
            8 * mm,
            f"Page {document.page}",
        )

        canvas.restoreState()

    @staticmethod
    def _get_score_label(score):
        score = float(score or 0)

        if score >= 85:
            return "Excellent Match"

        if score >= 70:
            return "Strong Match"

        if score >= 55:
            return "Good Match"

        if score >= 40:
            return "Fair Match"

        return "Needs Improvement"

    @staticmethod
    def _get_verdict(
        score,
        missing_skills,
    ):
        score = float(score or 0)
        missing_count = len(
            missing_skills
        )

        if score >= 85:
            return (
                "The resume demonstrates excellent alignment "
                "with the selected job role and contains most "
                "of the required technical skills."
            )

        if score >= 70:
            return (
                "The resume shows strong compatibility with "
                "the selected job role. Addressing the remaining "
                "skill gaps can further strengthen the profile."
            )

        if score >= 55:
            return (
                "The resume has a good technical foundation, "
                "but improving missing skills and role-specific "
                "keywords can significantly increase compatibility."
            )

        if score >= 40:
            return (
                "The resume partially matches the selected role. "
                "More relevant skills, projects and ATS keywords "
                "should be added."
            )

        if missing_count:
            return (
                "The resume requires significant improvement "
                "before targeting this role. Focus on missing "
                "skills, relevant projects and clear technical content."
            )

        return (
            "The resume requires stronger role-specific content "
            "and improved ATS keyword alignment."
        )

    @staticmethod
    def _score_hex(score):
        score = float(score or 0)

        if score >= 80:
            return "#16A34A"

        if score >= 60:
            return "#0284C7"

        if score >= 40:
            return "#D97706"

        return "#DC2626"

    @staticmethod
    def _report_code(report):
        created_date = (
            report.created_at
            if report.created_at
            else timezone.now()
        )

        return (
            f"ATS-"
            f"{created_date:%Y%m%d}-"
            f"{report.id:05d}"
        )