import logging
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

logger = logging.getLogger(__name__)


def get_risk_gauge_label(score: int) -> str:
    if score < 30:
        return "LOW RISK"
    elif score < 70:
        return "MEDIUM RISK"
    return "HIGH RISK"


def build_pdf_report(
    business_profile: dict,
    result_text: str,
    risk_score: int = 50,
    timeline: dict[str, list[str]] | None = None,
    source_documents: list[str] | None = None,
) -> bytes:
    """Create a professional PDF compliance report using ReportLab."""
    if timeline is None:
        timeline = {}
    if source_documents is None:
        source_documents = []

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=22,
        spaceAfter=15,
        alignment=1,  # Center
        textColor=colors.HexColor("#0f5bff"),
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor("#16a34a"),
    )

    normal_style = ParagraphStyle(
        "ReportNormal",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )

    story = []

    # Title & Timestamp
    story.append(Paragraph("RegLens AI Compliance Report", title_style))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"Generated: {generated_at}", normal_style))
    story.append(Spacer(1, 15))

    # Business Profile Section
    story.append(Paragraph("Business Profile", section_style))
    profile_data = [["Field", "Value"]]
    for label, value in business_profile.items():
        display_label = label.replace("_", " ").title()
        profile_data.append([display_label, str(value)])

    profile_table = Table(profile_data, colWidths=[2.2 * inch, 4.3 * inch])
    profile_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    story.append(profile_table)
    story.append(Spacer(1, 15))

    # Risk Snapshot Section
    story.append(Paragraph("Risk Snapshot", section_style))
    risk_level = get_risk_gauge_label(risk_score)
    risk_color = (
        colors.red if risk_score >= 70 else colors.orange if risk_score >= 40 else colors.green
    )

    risk_data = [
        ["Risk Score", f"{risk_score}%"],
        ["Risk Level", risk_level],
    ]

    risk_table = Table(risk_data, colWidths=[2.2 * inch, 4.3 * inch])
    risk_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("TEXTCOLOR", (1, 1), (1, 1), risk_color),
                ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    story.append(risk_table)
    story.append(Spacer(1, 15))

    # Compliance Timeline Section
    story.append(Paragraph("Compliance Timeline", section_style))
    if timeline:
        for bucket, items in timeline.items():
            story.append(Paragraph(f"<b>{bucket}</b>", styles["Heading4"]))
            for item in items:
                story.append(Paragraph(f"• {escape(item)}", normal_style))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No checklist items detected in the report.", normal_style))
    story.append(Spacer(1, 15))

    # Source Documents Section
    story.append(Paragraph("Source Documents", section_style))
    if source_documents:
        for source in source_documents:
            story.append(Paragraph(f"• {escape(str(source))}", normal_style))
    else:
        story.append(Paragraph("No source documents were captured.", normal_style))
    story.append(Spacer(1, 15))

    # Detailed Analysis Section
    story.append(PageBreak())
    story.append(Paragraph("Detailed Compliance Analysis", section_style))

    cleaned_result = result_text.replace("#", "").replace("*", "").strip()
    paragraphs = cleaned_result.split("\n\n")

    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(escape(para.strip()), normal_style))
            story.append(Spacer(1, 8))

    # Footer Disclaimer
    story.append(Spacer(1, 20))
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=normal_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
    )
    story.append(
        Paragraph(
            "This report provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions.",
            disclaimer_style,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
