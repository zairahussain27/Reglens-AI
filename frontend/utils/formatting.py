import json
import re
from datetime import datetime
from typing import Dict, List, Tuple


def sanitize_input(value: str) -> str:
    """Normalize input strings and strip potential injections."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)

    value = value.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "", value)
    return value.strip()


def validate_business_profile(profile: dict) -> Tuple[bool, str]:
    """Validate client-side business profile values before submitting."""
    errors = []
    services = sanitize_input(profile.get("services", ""))

    if not services:
        errors.append("Services / Products Offered field cannot be empty.")
    elif len(services) < 5:
        errors.append("Services description must be at least 5 characters long.")
    elif len(services) > 2000:
        errors.append("Services description must not exceed 2000 characters.")

    for field in ["business_type", "industry", "customer_type", "transaction_type", "revenue"]:
        val = sanitize_input(profile.get(field, ""))
        display_name = field.replace("_", " ").title()
        if not val:
            errors.append(f"{display_name} is required.")
        elif len(val) > 100:
            errors.append(f"{display_name} must not exceed 100 characters.")

    if errors:
        return False, "\n".join(errors)
    return True, ""


def parse_risk_level(result_text: str) -> int:
    """Extract risk score (0-100) from compliance analysis."""
    if not result_text:
        return 50

    # Strategy 1: Look for emojis (🔴 High, 🟡 Medium, 🟢 Low)
    if re.search(r"🔴|🔻|🟔|\bHIGH\s+RISK\b|\bCRITICAL\b", result_text, re.IGNORECASE):
        return 80
    elif re.search(r"🟡|\bMEDIUM\s+RISK\b|\bMODERATE\b", result_text, re.IGNORECASE):
        return 50
    elif re.search(r"🟢|\bLOW\s+RISK\b|\bMINIMAL\b", result_text, re.IGNORECASE):
        return 20

    # Strategy 2: Look for explicit Risk Level section
    risk_section = re.search(
        r"(?:##\s*)?(?:Overall\s+)?Compliance\s+Risk[:\s]*([A-Za-z]+)",
        result_text,
        re.IGNORECASE,
    )
    if risk_section:
        word = risk_section.group(1).upper()
        if "HIGH" in word or "CRITICAL" in word:
            return 80
        elif "LOW" in word or "MINIMAL" in word:
            return 20
        return 50

    return 50


def get_risk_gauge(score: int) -> str:
    """Return text label for risk score."""
    if score < 30:
        return "LOW RISK"
    elif score < 70:
        return "MEDIUM RISK"
    return "HIGH RISK"


def clean_report_line(line: str) -> str:
    """Clean markdown checkbox/numbered prefix."""
    line = line.strip()
    line = re.sub(r"^[-*]\s+\[[ xX]\]\s*", "", line)
    line = re.sub(r"^[-*]\s+", "", line)
    line = re.sub(r"^\d+\.\s+", "", line)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    return line.strip()


def extract_regulations_by_category(result_text: str) -> Dict[str, List[str]]:
    """Group detected regulations into authority categories (RBI, GST, MSME, etc.)."""
    categories = {
        "RBI": [],
        "GST": [],
        "MSME": [],
        "SEBI": [],
        "Companies Act": [],
        "FEMA": [],
        "Income Tax": [],
        "Other": [],
    }

    matches = re.finditer(
        r"^###\s+\d+\.\s+(.+?)(?:\s+[—-]\s+Source:|\s+Source:|$)",
        result_text,
        re.MULTILINE,
    )

    for match in matches:
        reg_name = match.group(1).strip()
        reg_upper = reg_name.upper()
        if "RBI" in reg_upper or "PAYMENT" in reg_upper or "LENDING" in reg_upper:
            cat = "RBI"
        elif "GST" in reg_upper or "CGST" in reg_upper:
            cat = "GST"
        elif "MSME" in reg_upper or "UDYAM" in reg_upper:
            cat = "MSME"
        elif "SEBI" in reg_upper:
            cat = "SEBI"
        elif "COMPANIES ACT" in reg_upper or "MCA" in reg_upper:
            cat = "Companies Act"
        elif "FEMA" in reg_upper:
            cat = "FEMA"
        elif "TAX" in reg_upper or "TDS" in reg_upper:
            cat = "Income Tax"
        else:
            cat = "Other"

        if reg_name and len(reg_name) > 3:
            categories[cat].append(reg_name)

    return {k: v for k, v in categories.items() if v}


def extract_action_items(result_text: str) -> List[str]:
    """Extract action checklist items from the report."""
    items = []
    checklist_pattern = r"[-*]\s+\[[xX ]\]\s+(.+?)(?=\n|$)"
    for match in re.finditer(checklist_pattern, result_text):
        item = clean_report_line(match.group(1))
        if item and len(item) > 5 and item not in items:
            items.append(item)

    next_steps = re.search(
        r"(?:Recommended Next Steps|RECOMMENDED NEXT STEPS)(.*?)(?=\n## |\Z)",
        result_text,
        re.DOTALL,
    )
    if next_steps:
        for match in re.finditer(r"^\s*\d+\.\s+(.+?)(?=\n\s*\d+\.|$)", next_steps.group(1), re.MULTILINE):
            item = clean_report_line(match.group(1))
            if item and len(item) > 5 and item not in items:
                items.append(item)

    return items


def assign_timeline_bucket(item: str) -> str:
    """Categorize an action item into a frequency timeline bucket."""
    item_lower = item.lower()
    if any(k in item_lower for k in ["register", "obtain", "license", "kyc", "immediate", "urgent", "prior", "before"]):
        return "Immediate"
    if any(k in item_lower for k in ["annual", "yearly", "year", "roc", "audit report"]):
        return "Annual"
    if any(k in item_lower for k in ["quarterly", "quarter", "statement", "board"]):
        return "Quarterly"
    if any(k in item_lower for k in ["monthly", "month", "return", "reconcile", "invoice", "deposit", "deduct"]):
        return "Monthly"
    return "Immediate"


def build_compliance_timeline(result_text: str) -> Dict[str, List[str]]:
    timeline = {"Immediate": [], "Monthly": [], "Quarterly": [], "Annual": []}
    for item in extract_action_items(result_text):
        bucket = assign_timeline_bucket(item)
        timeline[bucket].append(item)
    return {k: v for k, v in timeline.items() if v}


def parse_source_documents(value: Any) -> List[str]:
    """Normalize source documents to a clean list of strings."""
    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]
    if not value:
        return []
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, list):
                return [str(s).strip() for s in decoded if str(s).strip()]
        except json.JSONDecodeError:
            pass
        return [s.strip() for s in re.split(r"[\n,]", value) if s.strip()]
    return [str(value).strip()]


def build_markdown_report(
    business_profile: dict,
    result_text: str,
    risk_score: int,
    timeline: dict,
    source_documents: list,
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# RegLens AI Compliance Report",
        "",
        f"Generated: {generated_at}",
        "",
        "## Business Profile",
        "",
    ]
    for label, val in business_profile.items():
        lines.append(f"- **{label.replace('_', ' ').title()}:** {val}")

    lines.extend([
        "",
        "## Risk Snapshot",
        "",
        f"- **Risk Score:** {risk_score}%",
        f"- **Risk Level:** {get_risk_gauge(risk_score)}",
        "",
        "## Compliance Timeline",
        "",
    ])

    if timeline:
        for bucket, items in timeline.items():
            lines.append(f"### {bucket}")
            for it in items:
                lines.append(f"- [ ] {it}")
            lines.append("")
    else:
        lines.append("No checklist items detected.")
        lines.append("")

    lines.extend(["## Source Documents", ""])
    if source_documents:
        for src in source_documents:
            lines.append(f"- {src}")
    else:
        lines.append("No source documents captured.")

    lines.extend([
        "",
        "## Detailed Compliance Analysis",
        "",
        result_text,
        "",
        "---",
        "*This report provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions.*",
    ])
    return "\n".join(lines)
