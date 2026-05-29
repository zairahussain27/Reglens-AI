import streamlit as st
import requests
import os
import json
import re
import textwrap
from datetime import datetime
from xml.sax.saxutils import escape
# Optional dependency: only needed for PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    _REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    colors = None
    letter = None
    getSampleStyleSheet = None
    ParagraphStyle = None
    inch = None
    SimpleDocTemplate = Paragraph = Spacer = Table = TableStyle = PageBreak = None
    _REPORTLAB_AVAILABLE = False

from io import BytesIO

# Page config
st.set_page_config(
    page_title="RegLens AI",
    page_icon="RL",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    with open("main.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
# Initialize session state for checklists
if "compliance_checklist" not in st.session_state:
    st.session_state.compliance_checklist = {}
if "risk_score" not in st.session_state:
    st.session_state.risk_score = None
if "regulations_by_category" not in st.session_state:
    st.session_state.regulations_by_category = {}
if "compliance_timeline" not in st.session_state:
    st.session_state.compliance_timeline = {}
if "latest_report_markdown" not in st.session_state:
    st.session_state.latest_report_markdown = None
if "latest_report_pdf" not in st.session_state:
    st.session_state.latest_report_pdf = None
if "latest_business_profile" not in st.session_state:
    st.session_state.latest_business_profile = None
if "latest_source_documents" not in st.session_state:
    st.session_state.latest_source_documents = []
if "latest_result_text" not in st.session_state:
    st.session_state.latest_result_text = None

# Input validation functions
def sanitize_input(value: str) -> str:
    """Remove potentially malicious content from input strings"""
    if not isinstance(value, str):
        return value
    
    # Remove newlines and tabs
    value = value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Remove multiple spaces
    value = re.sub(r'\s+', ' ', value)
    
    # Remove URLs
    value = re.sub(r'https?://\S+', '', value)
    
    # Remove email addresses
    value = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', value)
    
    return value.strip()


def validate_services(services: str) -> tuple[bool, str]:
    """Validate services field"""
    services = sanitize_input(services)
    
    if not services:
        return False, "Services field cannot be empty"
    if len(services) < 5:
        return False, "Services must be at least 5 characters long"
    if len(services) > 2000:
        return False, "Services description is too long (max 2000 characters)"
    
    return True, "Services validation passed"


def validate_business_profile(profile: dict) -> tuple[bool, str]:
    """Validate entire business profile"""
    is_valid = True
    errors = []
    
    # Check services specifically
    services_valid, services_msg = validate_services(profile.get("services", ""))
    if not services_valid:
        errors.append(services_msg)
        is_valid = False
    
    # Check other required fields
    for field in ["business_type", "industry", "customer_type", "transaction_type", "revenue"]:
        value = profile.get(field, "").strip()
        if not value:
            errors.append(f"{field.replace('_', ' ').title()} is required")
            is_valid = False
        elif len(value) > 100:
            errors.append(f"{field.replace('_', ' ').title()} is too long")
            is_valid = False
    
    if not is_valid:
        return False, "\n".join(errors)
    
    return True, "All validations passed"


def parse_source_documents(value) -> list[str]:
    """Normalize API/DB source document payloads into a list of strings."""
    if isinstance(value, list):
        return [str(source).strip() for source in value if str(source).strip()]

    if not value:
        return []

    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = None

        if isinstance(decoded, list):
            return [str(source).strip() for source in decoded if str(source).strip()]

        return [
            source.strip()
            for source in re.split(r"[\n,]", value)
            if source.strip()
        ]

    return [str(value).strip()]


def fetch_audit_history(api_url: str) -> tuple[list[dict], str | None]:
    """Fetch recent compliance requests from the backend audit endpoint."""
    try:
        endpoint = f"{api_url.rstrip('/')}/api/history"
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as exc:
        return [], str(exc)


def render_source_documents(source_documents: list[str]) -> None:
    """Render source links/files for the current report or audit records."""
    if not source_documents:
        st.caption("No source documents captured.")
        return

    for source in source_documents:
        if source.startswith("http"):
            st.markdown(f"- [{source}]({source})")
        else:
            st.markdown(f"- {source}")


def render_audit_history(api_url: str) -> None:
    """Show recent compliance checks with persisted source document metadata."""
    st.markdown("---")
    st.subheader("Audit History")
    history_items, history_error = fetch_audit_history(api_url)

    if history_error:
        st.info(f"Audit history is unavailable: {history_error}")
        return

    if not history_items:
        st.caption("No compliance requests have been logged yet.")
        return

    st.caption(f"Showing {min(len(history_items), 10)} of {len(history_items)} recent requests.")

    for item in history_items[:10]:
        timestamp = item.get("timestamp", "")
        industry = item.get("industry", "Unknown industry")
        status = item.get("status", "unknown").upper()
        title = f"#{item.get('id')} - {status} - {industry} - {timestamp}"

        with st.expander(title, expanded=False):
            st.markdown(
                f"**Business Type:** {item.get('business_type', '')}  \n"
                f"**Customer Type:** {item.get('customer_type', '')}  \n"
                f"**Transaction Type:** {item.get('transaction_type', '')}  \n"
                f"**Revenue:** {item.get('revenue', '')}"
            )

            st.markdown("**Source Documents**")
            render_source_documents(parse_source_documents(item.get("source_documents")))

            result_preview = (item.get("result_text") or "").strip()
            if result_preview:
                st.text_area(
                    "Result Snapshot",
                    value=result_preview[:2000],
                    height=180,
                    disabled=True,
                    key=f"audit_result_{item.get('id')}",
                )


# Helper functions
def parse_risk_level(result_text: str) -> int:
    """Extract risk score from compliance result (0-100)"""
    if "HIGH" in result_text.upper() or "CRITICAL" in result_text.upper():
        return 80
    elif "MEDIUM" in result_text.upper() or "MODERATE" in result_text.upper():
        return 50
    elif "LOW" in result_text.upper() or "MINIMAL" in result_text.upper():
        return 20
    else:
        return 50  # default to medium


def get_risk_gauge(score: int) -> str:
    """Return emoji gauge based on risk score"""
    if score < 30:
        return "LOW RISK"
    elif score < 70:
        return "MEDIUM RISK"
    else:
        return "HIGH RISK"


def extract_regulations_by_category(result_text: str) -> dict:
    """Parse compliance result and categorize regulations"""
    categories = {
        "RBI": [],
        "GST": [],
        "MSME": [],
        "SEBI": [],
        "Companies Act": [],
        "FEMA": [],
        "Other": []
    }
    
    lines = result_text.split("\n")
    current_category = "Other"
    
    for line in lines:
        line_upper = line.upper()
        if "RBI" in line_upper:
            current_category = "RBI"
        elif "GST" in line_upper or "CGST" in line_upper:
            current_category = "GST"
        elif "MSME" in line_upper or "UDYAM" in line_upper:
            current_category = "MSME"
        elif "SEBI" in line_upper:
            current_category = "SEBI"
        elif "COMPANIES ACT" in line_upper or "MCA" in line_upper:
            current_category = "Companies Act"
        elif "FEMA" in line_upper:
            current_category = "FEMA"
        
        # Add non-empty lines as regulations
        if line.strip() and not any(cat in line_upper for cat in ["RBI", "GST", "MSME", "SEBI", "COMPANIES", "FEMA"]):
            if len(line.strip()) > 10:  # Skip very short lines
                categories[current_category].append(line.strip())
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def clean_report_line(line: str) -> str:
    """Normalize markdown checklist/list lines for display and exports."""
    line = line.strip()
    line = re.sub(r"^[-*]\s+\[[ xX]\]\s*", "", line)
    line = re.sub(r"^[-*]\s+", "", line)
    line = re.sub(r"^\d+\.\s+", "", line)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    return line.strip()


def extract_action_items(result_text: str) -> list[str]:
    """Extract checklist and next-step items from the model report."""
    items = []
    in_next_steps = False

    for raw_line in result_text.splitlines():
        line = raw_line.strip()
        line_lower = line.lower()

        if "recommended next steps" in line_lower:
            in_next_steps = True
            continue
        if line.startswith("##") and in_next_steps:
            in_next_steps = False

        is_checklist_item = bool(re.match(r"^[-*]\s+\[[ xX]\]\s+", line))
        is_next_step = in_next_steps and bool(re.match(r"^\d+\.\s+", line))

        if is_checklist_item or is_next_step:
            cleaned = clean_report_line(line)
            if cleaned and cleaned not in items:
                items.append(cleaned)

    return items


def assign_timeline_bucket(item: str) -> str:
    """Place an action item into a practical compliance timeline bucket."""
    item_lower = item.lower()

    setup_keywords = [
        "register", "obtain", "apply", "license", "kyc", "verify", "disclose",
        "appoint", "before", "prior", "immediate", "urgent", "must"
    ]
    general_immediate_keywords = [
        "file", "submit", "ensure", "comply"
    ]
    monthly_keywords = [
        "invoice", "payment", "return", "reconcile",
        "monitor", "review transactions", "deduct", "deposit"
    ]
    quarterly_keywords = [
        "board", "audit", "statement",
        "inspection", "reporting"
    ]
    annual_keywords = [
        "renew", "financial statement",
        "income tax", "roc", "mca", "audit report"
    ]

    if any(keyword in item_lower for keyword in setup_keywords):
        return "Immediate"
    if any(keyword in item_lower for keyword in ["annual", "yearly", "year"]):
        return "Annual"
    if any(keyword in item_lower for keyword in ["quarterly", "quarter"]):
        return "Quarterly"
    if any(keyword in item_lower for keyword in ["monthly", "month"]):
        return "Monthly"
    if any(keyword in item_lower for keyword in annual_keywords):
        return "Annual"
    if any(keyword in item_lower for keyword in quarterly_keywords):
        return "Quarterly"
    if any(keyword in item_lower for keyword in monthly_keywords):
        return "Monthly"
    if any(keyword in item_lower for keyword in general_immediate_keywords):
        return "Immediate"
    return "Immediate"


def build_compliance_timeline(result_text: str) -> dict[str, list[str]]:
    """Convert report checklist items into Immediate/Monthly/Quarterly/Annual buckets."""
    timeline = {
        "Immediate": [],
        "Monthly": [],
        "Quarterly": [],
        "Annual": []
    }

    for item in extract_action_items(result_text):
        bucket = assign_timeline_bucket(item)
        timeline[bucket].append(item)

    return {bucket: items for bucket, items in timeline.items() if items}


def build_markdown_report(
    business_profile: dict,
    result_text: str,
    risk_score: int,
    timeline: dict[str, list[str]],
    source_documents: list[str] | None = None,
) -> str:
    """Build a downloadable Markdown compliance report."""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# RegLens AI Compliance Report",
        "",
        f"Generated: {generated_at}",
        "",
        "## Business Profile",
        ""
    ]

    for label, value in business_profile.items():
        lines.append(f"- **{label.replace('_', ' ').title()}:** {value}")

    lines.extend([
        "",
        "## Risk Snapshot",
        "",
        f"- **Risk Score:** {risk_score}%",
        f"- **Risk Level:** {get_risk_gauge(risk_score)}",
        "",
        "## Compliance Timeline",
        ""
    ])

    if timeline:
        for bucket, items in timeline.items():
            lines.append(f"### {bucket}")
            for item in items:
                lines.append(f"- [ ] {item}")
            lines.append("")
    else:
        lines.append("No checklist items were detected in the report.")
        lines.append("")

    lines.extend([
        "## Source Documents",
        ""
    ])

    if source_documents:
        for source in source_documents:
            lines.append(f"- {source}")
        lines.append("")
    else:
        lines.append("No source documents were captured.")
        lines.append("")

    lines.extend([
        "## Detailed Compliance Analysis",
        "",
        result_text,
        "",
        "---",
        "This report provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions."
    ])

    return "\n".join(lines)


def build_pdf_report(
    business_profile: dict,
    result_text: str,
    risk_score: int,
    timeline: dict[str, list[str]],
    source_documents: list[str] | None = None,
) -> bytes:
    """Create a professional PDF report using ReportLab."""
    if not _REPORTLAB_AVAILABLE:
        raise ModuleNotFoundError(
            "reportlab is required for PDF generation. Install it or disable PDF generation."
        )

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )

    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=15,
        textColor=colors.darkgreen
    )

    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 14

    # Build the story (content)
    story = []

    # Title
    story.append(Paragraph("RegLens AI Compliance Report", title_style))
    story.append(Spacer(1, 12))

    # Generation timestamp
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"Generated: {generated_at}", normal_style))
    story.append(Spacer(1, 20))

    # Business Profile Section
    story.append(Paragraph("Business Profile", section_style))

    # Create business profile table
    profile_data = [["Field", "Value"]]
    for label, value in business_profile.items():
        display_label = label.replace('_', ' ').title()
        profile_data.append([display_label, value])

    profile_table = Table(profile_data, colWidths=[2*inch, 4*inch])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 20))

    # Risk Snapshot Section
    story.append(Paragraph("Risk Snapshot", section_style))

    risk_level = get_risk_gauge(risk_score)
    risk_color = colors.red if risk_score >= 70 else colors.orange if risk_score >= 40 else colors.green

    risk_data = [
        ["Risk Score", f"{risk_score}%"],
        ["Risk Level", risk_level]
    ]

    risk_table = Table(risk_data, colWidths=[2*inch, 4*inch])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (1, 1), (1, 1), risk_color),
        ('FONTNAME', (1, 1), (1, 1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 20))

    # Compliance Timeline Section
    story.append(Paragraph("Compliance Timeline", section_style))

    if timeline:
        for bucket, items in timeline.items():
            story.append(Paragraph(bucket, styles['Heading3']))
            for item in items:
                story.append(Paragraph(f"- {item}", normal_style))
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("No checklist items were detected in the report.", normal_style))
        story.append(Spacer(1, 20))

    # Source Documents Section
    story.append(Paragraph("Source Documents", section_style))
    if source_documents:
        for source in source_documents:
            story.append(Paragraph(escape(source), normal_style))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No source documents were captured.", normal_style))
    story.append(Spacer(1, 20))

    # Detailed Analysis Section
    story.append(PageBreak())  # Start new page for detailed analysis
    story.append(Paragraph("Detailed Compliance Analysis", section_style))

    # Clean and format the result text
    cleaned_result = result_text.replace('#', '').replace('*', '').strip()
    paragraphs = cleaned_result.split('\n\n')

    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip(), normal_style))
            story.append(Spacer(1, 10))

    # Footer disclaimer
    story.append(Spacer(1, 30))
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=normal_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    story.append(Paragraph(
        "This report provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions.",
        disclaimer_style
    ))

    # Build the PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def render_topbar() -> None:
    updated = datetime.now().strftime("%d %b %Y")
    st.markdown(
        f"""
        <div class="rl-topbar">
            <div class="rl-brand">
                <div class="rl-logo">RL</div>
                <div>RegLens AI</div>
            </div>
            <div class="rl-nav">
                <span class="active">Compliance Check</span>
                <span>Regulatory Updates</span>
                <span>About</span>
            </div>
            <div class="rl-meta">
                <span>Last updated: {updated}</span>
                <div class="rl-avatar">RG</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="rl-page-title">
            <h1>{escape(title)}</h1>
            <p>{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_metric_cards() -> None:
    score = st.session_state.risk_score if st.session_state.risk_score is not None else 0
    regulations_count = sum(len(items) for items in st.session_state.regulations_by_category.values())
    pending_actions = sum(len(items) for items in st.session_state.compliance_timeline.values())
    upcoming_filings = len(st.session_state.compliance_timeline.get("Monthly", [])) + len(
        st.session_state.compliance_timeline.get("Quarterly", [])
    )

    cards = [
        ("Compliance Score", f"{score}%", "Your current compliance risk score."),
        ("Applicable Regulations", str(regulations_count), "Laws and regulations that apply."),
        ("Pending Actions", str(pending_actions), "Tasks that require your attention."),
        ("Upcoming Filings", str(upcoming_filings), "Filings you should complete soon."),
    ]

    metrics_html = "".join(
        f"""
        <div class=\"rl-stat-card\">
            <div class=\"metric-label\">{escape(title)}</div>
            <div class=\"metric-value\">{escape(value)}</div>
            <div class=\"metric-note\">{escape(note)}</div>
        </div>
        """
        for title, value, note in cards
    )

    st.markdown(
        f"""
        <div class="top-card-grid">{metrics_html}</div>
        """,
        unsafe_allow_html=True,
    )


def render_business_profile_card(is_post_check: bool) -> None:
    status_html = (
        '<span class="rl-status pending">Submitted</span>'
        if is_post_check else ""
    )

    intro_text = (
        "Provide accurate details to get relevant compliance obligations."
        if not is_post_check
        else "Your latest profile has been submitted and the report has been generated."
    )

    st.markdown(
        f"""
        <div class="rl-section-head">
            <div class="rl-title-left">
                <div class="rl-icon">BP</div>
                <h2>Business Profile</h2>
            </div>
            {status_html}
        </div>
        <p class="rl-help">{intro_text}</p>
        """,
        unsafe_allow_html=True,
    )

def risk_label(score: int | None) -> str:
    if score is None:
        return "Not assessed"
    if score < 30:
        return "Low"
    if score < 70:
        return "Medium"
    return "High"


def audit_readiness_label(score: int | None) -> str:
    if score is None:
        return "Pending"
    if score < 30:
        return "High"
    if score < 70:
        return "Moderate"
    return "Needs review"


def flatten_timeline_items(limit: int = 4) -> list[tuple[str, str]]:
    rows = []
    for bucket, items in st.session_state.compliance_timeline.items():
        for item in items:
            rows.append((bucket, item))
            if len(rows) >= limit:
                return rows
    return rows


def render_summary_card() -> None:
    score = st.session_state.risk_score
    display_score = 0 if score is None else score
    label = risk_label(score)
    regulations_count = sum(len(items) for items in st.session_state.regulations_by_category.values())
    pending_actions = sum(len(items) for items in st.session_state.compliance_timeline.values())
    upcoming_filings = len(st.session_state.compliance_timeline.get("Monthly", [])) + len(
        st.session_state.compliance_timeline.get("Quarterly", [])
    )
    status_class = "pending" if score is None else "good"
    status_text = "Ready" if score is None else label
    assessed = "Not assessed yet" if score is None else datetime.now().strftime("Last assessed: %d %b %Y")

    st.markdown(
        f"""
        <div class="rl-card">
            <div class="rl-section-head">
                <h2>Compliance Summary</h2>
                <span class="rl-status {status_class}"><span class="rl-dot"></span>{status_text}</span>
            </div>
            <div class="rl-divider"></div>
            <div class="rl-summary-grid">
                <div>
                    <h3 style="text-align:center; margin-bottom:0.3rem;">Compliance Score</h3>
                    <div class="rl-score-ring" style="--score:{display_score}%;">
                        <div><strong>{display_score}%</strong><span>{escape(label)}</span></div>
                    </div>
                    <div class="rl-score-caption">{assessed}</div>
                </div>
                <div class="rl-stats">
                    <h3>Key Stats</h3>
                    <div class="rl-stat-row">
                        <div class="rl-row-left"><span class="rl-mini-icon">R</span><span>Applicable Regulations</span></div>
                        <span class="rl-row-value">{regulations_count}</span>
                    </div>
                    <div class="rl-stat-row">
                        <div class="rl-row-left"><span class="rl-mini-icon">A</span><span>Pending Actions</span></div>
                        <span class="rl-row-value">{pending_actions}</span>
                    </div>
                    <div class="rl-stat-row">
                        <div class="rl-row-left"><span class="rl-mini-icon">F</span><span>Upcoming Filings</span></div>
                        <span class="rl-row-value">{upcoming_filings}</span>
                    </div>
                    <div class="rl-stat-row">
                        <div class="rl-row-left"><span class="rl-mini-icon">AR</span><span>Audit Readiness</span></div>
                        <span class="rl-row-value">{escape(audit_readiness_label(score))}</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_regulations_card() -> None:
    rows = []
    for category, regulations in st.session_state.regulations_by_category.items():
        for regulation in regulations[:2]:
            rows.append((category, clean_report_line(regulation)))
            if len(rows) >= 5:
                break
        if len(rows) >= 5:
            break

    if not rows:
        rows = [
            ("RBI", "RBI KYC Master Directions, 2016"),
            ("GST", "GST Act, 2017"),
            ("MCA", "Companies Act, 2013"),
            ("MSME", "MSME Udyam Registration"),
            ("FEMA", "FEMA Basic Compliance"),
        ]

    rows_html = "\n".join(
        f"""
        <div class="rl-list-row">
            <div class="rl-row-left">
                <span class="rl-mini-icon">{escape(category[:2].upper())}</span>
                <span class="rl-row-title">{escape(title[:90])}</span>
            </div>
            <span class="rl-status good">Applicable</span>
        </div>
        """
        for category, title in rows
    )
    st.markdown(
        f"""
        <div class="rl-card">
            <div class="rl-section-head">
                <h3>Top Applicable Regulations</h3>
                <span class="rl-view">View all</span>
            </div>
            {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_actions_card() -> None:
    rows = flatten_timeline_items()
    if not rows:
        rows = [
            ("Pending", "Complete KYC Policy Review"),
            ("Pending", "Update Privacy Policy"),
            ("Upcoming", "Annual IT Security Audit"),
            ("Upcoming", "Board Resolution Update"),
        ]

    rows_html = ""
    for bucket, item in rows:
        status_class = "pending" if bucket in {"Immediate", "Pending"} else "upcoming"
        due_text = {
            "Immediate": "Due now",
            "Monthly": "Due this month",
            "Quarterly": "Due this quarter",
            "Annual": "Due this year",
            "Pending": "Due soon",
            "Upcoming": "Upcoming",
        }.get(bucket, "Upcoming")
        rows_html += f"""
        <div class="rl-action-row">
            <div class="rl-row-left">
                <span class="rl-mini-icon">A</span>
                <div>
                    <div class="rl-row-title">{escape(clean_report_line(item)[:85])}</div>
                    <div class="rl-row-sub">{due_text}</div>
                </div>
            </div>
            <span class="rl-status {status_class}">{escape(bucket)}</span>
        </div>
        """

    st.markdown(
        f"""
        <div class="rl-card">
            <div class="rl-section-head">
                <h3>Required Actions</h3>
                <span class="rl-view">View all</span>
            </div>
            {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_coverage_card() -> None:
    coverage = [
        ("RBI", "Reserve Bank of India"),
        ("MCA", "Ministry of Corporate Affairs"),
        ("CBDT", "Income Tax Department"),
        ("GSTN", "Goods and Services Tax"),
        ("MeitY", "Electronics and IT"),
        ("+6 More", "Regulatory Bodies"),
    ]
    items = "\n".join(
        f"""
        <div class="rl-coverage-item">
            <span class="rl-mini-icon">{escape(name[:2])}</span>
            <div>
                <div class="rl-coverage-name">{escape(name)}</div>
                <div class="rl-coverage-sub">{escape(subtitle)}</div>
            </div>
        </div>
        """
        for name, subtitle in coverage
    )
    st.markdown(
        f"""
        <div class="rl-card" style="margin-top:1.05rem;">
            <div class="rl-section-head">
                <div class="rl-title-left">
                    <div class="rl-icon">C</div>
                    <h2>Regulatory Coverage</h2>
                </div>
            </div>
            <div class="rl-coverage-grid">{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Header
render_topbar()

is_post_check = st.session_state.risk_score is not None
page_title = "Compliance Check Results" if is_post_check else "Compliance Check"
page_description = (
    "Based on the information provided, here is your compliance overview and actionable insights."
    if is_post_check
    else "Enter your business details and get an audit-ready compliance checklist."
)
render_page_header(page_title, page_description)

render_top_metric_cards()

# Legacy header markup remains below but is hidden by CSS to avoid changing workflow state.
st.markdown(
    """
    <div class='app-card hero-card'>
        <h1 style='text-align: center; margin-bottom: 0.15rem;'>RegLens AI</h1>
        <p style='text-align: center; font-size: 1.05rem; opacity: 0.86; margin-top: 0; max-width: 860px; margin-left: auto; margin-right: auto;'>
            AI-powered regulatory compliance assistant for Indian FinTechs & MSMEs.
            Enter a strong business profile and get a regulation-aware compliance checklist with audit-ready reasoning.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.markdown("### RegLens AI")
    st.caption("Compliance workspace")
    st.markdown("---")
    st.markdown("### About RegLens AI")
    st.markdown("""
    RegLens AI reads **real government regulations** and tells you exactly:
    - Which laws apply to your business
    - Why they apply
    - What you must do
    - Your compliance risk level
    """)
    st.markdown("---")
    st.markdown("**Regulatory Coverage:**")
    st.markdown("""
    - RBI KYC & Payment Guidelines
    - NBFC & Digital Lending Rules
    - GST & CGST Rules 2017
    - MSME Udyam Registration
    - Income Tax TDS Provisions
    - FEMA Compliance
    - Companies Act 2013
    """)
    st.markdown("---")
    default_api_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    api_url = st.text_input("Backend API URL", default_api_url)

# Main form
main_left, main_right = st.columns([1.15, 1.15], gap="medium")

with main_left:
    st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
    render_business_profile_card(is_post_check)

    with st.form("business_profile_form"):
        col1, col2 = st.columns([1, 1], gap="medium")

        with col1:
            business_type = st.selectbox(
                "Business Type",
                ["Private Limited Company", "LLP", "Sole Proprietorship", "Partnership Firm", "OPC"],
                index=None,
                placeholder="Select business type",
                help="Choose the legal business entity that matches your company.",
            )

            industry = st.selectbox(
                "Industry",
                [
                    "FinTech - Digital Payments",
                    "FinTech - Lending / NBFC",
                    "MSME - Manufacturing",
                    "MSME - Services",
                    "E-Commerce",
                    "SaaS / Technology",
                ],
                index=None,
                placeholder="Select industry",
                help="Select the industry category closest to your operations.",
            )

            services = st.text_area(
                "Services / Products Offered",
                
                placeholder="Enter services or products",
                height=110,
                help="Describe the key services or products your business offers.",
            )

        with col2:
            customer_type = st.selectbox(
                "Customer Type",
                ["Retail Consumers (B2C)", "Businesses (B2B)", "Both B2B and B2C", "Government (B2G)"],
                index=None,
                placeholder="Select customer type",
                help="Choose the main customer segment your business serves.",
            )

            transaction_type = st.selectbox(
                "Primary Transaction Type",
                [
                    "Digital Payments / UPI",
                    "Lending / Credit",
                    "Investment / Wealth",
                    "Insurance",
                    "Product Sales",
                    "Service Billing",
                ],
                index=None,
                placeholder="Select transaction type",
                help="Select the transaction type that best represents your business model.",
            )

            revenue = st.selectbox(
                "Annual Revenue",
                [
                    "Under ₹1 Crore",
                    "₹1 Crore - ₹5 Crore",
                    "₹5 Crore - ₹25 Crore",
                    "Above ₹25 Crore",
                ],
                index=None,
                placeholder="Select annual revenue",
                help="Choose the closest annual revenue band for your business.",
            )

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        submitted = st.form_submit_button(
            "Run Compliance Check",
            use_container_width=True
        )

        st.caption("Your data is secure and used only for compliance analysis.")
with main_right:
    render_summary_card()
    reg_col, action_col = st.columns(2, gap="medium")
    with reg_col:
        render_regulations_card()
    with action_col:
        render_actions_card()

render_coverage_card()
if submitted:
    business_profile = {
        "business_type": business_type,
        "industry": industry,
        "services": services,
        "customer_type": customer_type,
        "transaction_type": transaction_type,
        "revenue": revenue
    }
    
    # Run client-side validation
    is_valid, validation_message = validate_business_profile(business_profile)
    
    if not is_valid:
        st.error(validation_message)
    else:
        with st.spinner("Analyzing regulations for your business... This may take 15-30 seconds."):
            try:
                endpoint = f"{api_url.rstrip('/')}/api/compliance-check"
                response = requests.post(endpoint, json=business_profile, timeout=120)
                
                if response.status_code == 422:
                    # Handle validation errors from backend
                    error_data = response.json()
                    st.error("**Input Validation Error**")
                    if "errors" in error_data:
                        for error in error_data.get("errors", []):
                            st.error(error)
                    else:
                        st.error(error_data.get("detail", "Invalid input provided"))
                    st.stop()
                else:
                    response.raise_for_status()
                    response_payload = response.json()
                    result = response_payload.get("result", "No result returned from backend.")
                    source_documents = parse_source_documents(response_payload.get("source_documents", []))

                    st.session_state.risk_score = parse_risk_level(result)
                    st.session_state.regulations_by_category = extract_regulations_by_category(result)
                    st.session_state.compliance_timeline = build_compliance_timeline(result)
                    st.session_state.latest_business_profile = business_profile
                    st.session_state.latest_source_documents = source_documents
                    st.session_state.latest_result_text = result
                    st.session_state.latest_report_markdown = build_markdown_report(
                        business_profile,
                        result,
                        st.session_state.risk_score,
                        st.session_state.compliance_timeline,
                        source_documents,
                    )
                    st.session_state.latest_report_pdf = build_pdf_report(
                        business_profile,
                        result,
                        st.session_state.risk_score,
                        st.session_state.compliance_timeline,
                        source_documents,
                    )
                
                st.markdown("---")
                st.markdown("## Compliance Analysis Report")
                
                # Risk Gauge Section
                st.subheader("Compliance Risk Assessment")
                risk_col1, risk_col2, risk_col3 = st.columns([1, 2, 1])
                
                with risk_col2:
                    risk_gauge = get_risk_gauge(st.session_state.risk_score)
                    st.metric(
                        "Risk Level",
                        f"{st.session_state.risk_score}%",
                        delta=risk_gauge,
                        delta_color="off"
                    )
                    
                    # Progress bar visualization
                    st.progress(st.session_state.risk_score / 100)
                
                st.markdown("---")

                # Compliance Timeline Section
                st.subheader("Compliance Timeline")
                if st.session_state.compliance_timeline:
                    timeline_columns = st.columns(4)
                    timeline_order = ["Immediate", "Monthly", "Quarterly", "Annual"]

                    for column, bucket in zip(timeline_columns, timeline_order):
                        with column:
                            items = st.session_state.compliance_timeline.get(bucket, [])
                            st.markdown(f"**{bucket}**")
                            if items:
                                for item in items[:6]:
                                    checkbox_key = f"timeline_{bucket}_{item[:30]}"
                                    checked = st.checkbox(
                                        item[:90] + ("..." if len(item) > 90 else ""),
                                        key=checkbox_key,
                                        value=st.session_state.compliance_checklist.get(checkbox_key, False)
                                    )
                                    st.session_state.compliance_checklist[checkbox_key] = checked
                                if len(items) > 6:
                                    st.caption(f"+ {len(items) - 6} more")
                            else:
                                st.caption("No items detected")
                else:
                    st.info("No checklist items were detected for timeline generation.")

                st.markdown("---")

                # Downloadable Reports Section
                st.subheader("Download Compliance Report")
                download_col1, download_col2 = st.columns(2)
                file_stamp = datetime.now().strftime("%Y%m%d_%H%M")

                with download_col1:
                    st.download_button(
                        "Download Markdown Report",
                        data=st.session_state.latest_report_markdown or "",
                        file_name=f"reglens_compliance_report_{file_stamp}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

                with download_col2:
                    st.download_button(
                        "Download PDF Report",
                        data=st.session_state.latest_report_pdf or b"",
                        file_name=f"reglens_compliance_report_{file_stamp}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

                st.markdown("---")
                
                # Categorized Regulations Section
                if st.session_state.regulations_by_category:
                    st.subheader("Compliance Checklist by Category")
                    
                    for category, regulations in st.session_state.regulations_by_category.items():
                        with st.expander(f"**{category}** ({len(regulations)} items)", expanded=True):
                            for idx, regulation in enumerate(regulations[:5]):  # Show first 5
                                checkbox_key = f"{category}_{idx}_{regulation[:20]}"
                                checked = st.checkbox(
                                    regulation[:100] + ("..." if len(regulation) > 100 else ""),
                                    key=checkbox_key,
                                    value=st.session_state.compliance_checklist.get(checkbox_key, False)
                                )
                                st.session_state.compliance_checklist[checkbox_key] = checked
                            
                            if len(regulations) > 5:
                                st.caption(f"... and {len(regulations) - 5} more regulations")
                
                st.markdown("---")
                
                # Source Documents Section
                st.subheader("Source Documents")
                render_source_documents(st.session_state.latest_source_documents)

                st.markdown("---")
                
                # Full Report
                st.subheader("Detailed Compliance Analysis")
                st.markdown(result)
                
                st.markdown("---")
                st.success("Analysis complete. This report is based on official government documents only.")
                st.warning("This tool provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions.")

            except requests.exceptions.Timeout:
                st.error("**Request Timeout**: The server took too long to respond. Please try again.")
            except requests.exceptions.RequestException as re:
                st.error(f"**Backend Error**: {str(re)}")
            except Exception as e:
                st.error(f"**Error**: {str(e)}")

# Display saved analysis if it exists
if st.session_state.risk_score is not None:
    st.markdown("---")
    st.subheader("Your Latest Compliance Dashboard")
    
    dashboard_col1, dashboard_col2 = st.columns([1, 2])
    
    with dashboard_col1:
        risk_gauge = get_risk_gauge(st.session_state.risk_score)
        st.metric("Risk Score", f"{st.session_state.risk_score}%")
        st.write(risk_gauge)
    
    with dashboard_col2:
        if st.session_state.compliance_checklist:
            total_items = len(st.session_state.compliance_checklist)
            checked_items = sum(st.session_state.compliance_checklist.values())
            progress_pct = (checked_items / total_items * 100) if total_items > 0 else 0
            st.metric("Progress", f"{int(progress_pct)}%", f"{checked_items}/{total_items} items")
            st.progress(progress_pct / 100)

render_audit_history(api_url)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
RegLens AI - Powered by LLaMA 3.3 70B + RAG on Official Government Documents
</div>
""", unsafe_allow_html=True)

