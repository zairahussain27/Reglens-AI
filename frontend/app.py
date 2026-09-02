import os
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st

# Setup python path for frontend modules
FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from components.topbar import render_topbar, render_page_header
from components.compliance_form import render_compliance_form
from components.result_cards import render_top_metric_cards
from components.risk_gauge import render_risk_gauge
from components.findings import render_categorized_regulations
from components.timeline import render_timeline
from components.sources import render_source_documents
from components.history import render_audit_history
from services.api import submit_compliance_check, request_pdf_export
from utils.formatting import (
    validate_business_profile,
    parse_risk_level,
    extract_regulations_by_category,
    build_compliance_timeline,
    parse_source_documents,
    build_markdown_report,
)

# 1. Page Configuration
logo_path = FRONTEND_DIR / "assets" / "reglens_logo.png"
st.set_page_config(
    page_title="RegLens AI — Regulatory Compliance Assistant",
    page_icon=str(logo_path) if logo_path.exists() else "⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Session State Initialization
if "risk_score" not in st.session_state:
    st.session_state.risk_score = None
if "regulations_by_category" not in st.session_state:
    st.session_state.regulations_by_category = {}
if "compliance_timeline" not in st.session_state:
    st.session_state.compliance_timeline = {}
if "latest_result_text" not in st.session_state:
    st.session_state.latest_result_text = None
if "latest_source_documents" not in st.session_state:
    st.session_state.latest_source_documents = []
if "latest_business_profile" not in st.session_state:
    st.session_state.latest_business_profile = None

# 3. Sidebar
with st.sidebar:
    st.title("⚖️ RegLens AI")
    st.caption("AI-Powered Compliance for Indian FinTechs & MSMEs")
    st.markdown("---")

    backend_api_url = st.text_input(
        "Backend API URL",
        value=os.getenv("BACKEND_API_URL", "http://localhost:8000"),
        help="FastAPI backend URL (Render or Local)",
    )

    st.markdown("### 📚 Statutory Coverage")
    st.markdown(
        """
        - **RBI:** KYC, Payment Aggregators, Digital Lending, NBFC
        - **GST:** CGST Rules 2017 & Invoicing
        - **MSME:** Udyam Registration & Compliance
        - **FEMA:** Basic Cross-Border Compliance
        - **Companies Act:** Statutory Filings
        """
    )
    st.markdown("---")
    st.caption("Engine: Google Gemini | Vectors: Qdrant Cloud")

# 4. Topbar & Header
render_topbar()

is_post_check = st.session_state.risk_score is not None
page_title = "Compliance Analysis Report" if is_post_check else "Compliance Analysis"
page_description = (
    "AI-assisted compliance findings grounded in official government regulations."
    if is_post_check
    else "Enter your business details to receive an audit-ready compliance analysis."
)
render_page_header(page_title, page_description)

# 5. Top Metric Cards
render_top_metric_cards(
    score=st.session_state.risk_score,
    regulations_by_category=st.session_state.regulations_by_category,
    timeline=st.session_state.compliance_timeline,
)

# 6. Main Form & Submission
col_form, col_summary = st.columns([1.1, 0.9], gap="large")

with col_form:
    submitted, profile = render_compliance_form(is_post_check=is_post_check)

with col_summary:
    st.markdown("### 📋 Executive Summary")
    if st.session_state.latest_result_text:
        render_risk_gauge(st.session_state.risk_score)
    else:
        st.info("Submit your business profile to trigger automated regulatory analysis.")

# 7. Handling Form Submission
if submitted:
    is_valid, validation_msg = validate_business_profile(profile)
    if not is_valid:
        st.error(f"**Input Validation Error:**\n{validation_msg}")
    else:
        with st.spinner("Analyzing official regulations with Google Gemini and Qdrant Cloud..."):
            success, response_data = submit_compliance_check(profile, api_url=backend_api_url)

            if not success:
                error_type = response_data.get("error_type", "error")
                error_detail = response_data.get("detail", "Analysis failed")
                st.error(f"**Error ({error_type}):** {error_detail}")
            else:
                result_text = response_data.get("result", "")
                source_documents = parse_source_documents(response_data.get("source_documents", []))

                st.session_state.risk_score = parse_risk_level(result_text)
                st.session_state.regulations_by_category = extract_regulations_by_category(result_text)
                st.session_state.compliance_timeline = build_compliance_timeline(result_text)
                st.session_state.latest_result_text = result_text
                st.session_state.latest_source_documents = source_documents
                st.session_state.latest_business_profile = profile

                st.rerun()

# 8. Render Results View (when analysis is available)
if st.session_state.latest_result_text:
    st.markdown("---")

    # A. Compliance Timeline
    if st.session_state.compliance_timeline:
        render_timeline(st.session_state.compliance_timeline)

    # B. Categorized Regulations
    if st.session_state.regulations_by_category:
        render_categorized_regulations(st.session_state.regulations_by_category)

    # C. Source Documents
    render_source_documents(st.session_state.latest_source_documents)

    # D. Full Analysis Report
    st.subheader("Detailed Compliance Analysis")
    st.markdown(st.session_state.latest_result_text)

    # E. Export Report Buttons
    st.markdown("---")
    st.subheader("📥 Export Compliance Report")
    dcol1, dcol2 = st.columns(2)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
    md_report = build_markdown_report(
        business_profile=st.session_state.latest_business_profile or {},
        result_text=st.session_state.latest_result_text,
        risk_score=st.session_state.risk_score or 50,
        timeline=st.session_state.compliance_timeline,
        source_documents=st.session_state.latest_source_documents,
    )

    with dcol1:
        st.download_button(
            "📄 Download Markdown Report (.md)",
            data=md_report,
            file_name=f"reglens_report_{timestamp_str}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with dcol2:
        pdf_payload = {
            "business_profile": st.session_state.latest_business_profile or {},
            "result_text": st.session_state.latest_result_text,
            "risk_score": st.session_state.risk_score or 50,
            "timeline": st.session_state.compliance_timeline,
            "source_documents": st.session_state.latest_source_documents,
        }
        pdf_success, pdf_data = request_pdf_export(pdf_payload, api_url=backend_api_url)
        if pdf_success and isinstance(pdf_data, bytes):
            st.download_button(
                "📑 Download PDF Report (.pdf)",
                data=pdf_data,
                file_name=f"reglens_report_{timestamp_str}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("📑 PDF Export Unavailable", disabled=True, use_container_width=True)

    st.success("✅ Analysis complete. Grounded in official statutory documents.")
    st.caption("Disclaimer: AI-assisted guidance only. Consult a qualified compliance professional.")

# 9. Audit History
render_audit_history(api_url=backend_api_url)
