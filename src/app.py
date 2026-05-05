import streamlit as st
import requests
import os
import json
import re

# Page config
st.set_page_config(
    page_title="RegLens AI",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state for checklists
if "compliance_checklist" not in st.session_state:
    st.session_state.compliance_checklist = {}
if "risk_score" not in st.session_state:
    st.session_state.risk_score = None
if "regulations_by_category" not in st.session_state:
    st.session_state.regulations_by_category = {}

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
        return "🟢 LOW RISK"
    elif score < 70:
        return "🟡 MEDIUM RISK"
    else:
        return "🔴 HIGH RISK"


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


# Header
st.markdown("""
    <h1 style='text-align: center; color: #1a1a2e;'>🔍 RegLens AI</h1>
    <h4 style='text-align: center; color: #16213e;'>AI-Powered Regulatory Compliance Assistant for Indian FinTechs & MSMEs</h4>
    <hr>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/law.png", width=80)
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
    - 🏦 RBI KYC & Payment Guidelines
    - 💰 NBFC & Digital Lending Rules
    - 🧾 GST & CGST Rules 2017
    - 🏭 MSME Udyam Registration
    - 📊 Income Tax TDS Provisions
    - 🌐 FEMA Compliance
    - 🏢 Companies Act 2013
    """)
    st.markdown("---")
    api_url = st.text_input("Backend API URL", "http://localhost:8000")
    st.caption("ET AI Hackathon 2026 — PS5")

# Main form
st.markdown("## 📋 Enter Your Business Profile")
st.markdown("Fill in your business details below. RegLens AI will analyze which regulations apply to you.")

col1, col2 = st.columns(2)

with col1:
    business_type = st.selectbox(
        "Business Type",
        ["Private Limited Company", "LLP", "Sole Proprietorship", "Partnership Firm", "OPC"]
    )

    industry = st.selectbox(
        "Industry",
        [
            "FinTech - Digital Payments",
            "FinTech - Lending / NBFC",
            "MSME - Manufacturing",
            "MSME - Services",
            "E-Commerce",
            "SaaS / Technology"
        ]
    )

    services = st.text_area(
        "Services / Products Offered",
        placeholder="e.g. Online payment gateway, wallet services, UPI transactions",
        height=100
    )

with col2:
    customer_type = st.selectbox(
        "Customer Type",
        ["Retail Consumers (B2C)", "Businesses (B2B)", "Both B2B and B2C", "Government (B2G)"]
    )

    transaction_type = st.selectbox(
        "Primary Transaction Type",
        [
            "Digital Payments / UPI",
            "Lending / Credit",
            "Investment / Wealth",
            "Insurance",
            "Product Sales",
            "Service Billing"
        ]
    )

    revenue = st.selectbox(
        "Annual Revenue",
        [
            "Under ₹1 Crore",
            "₹1 Crore – ₹5 Crore",
            "₹5 Crore – ₹25 Crore",
            "Above ₹25 Crore"
        ]
    )

st.markdown("---")

# Submit button
if st.button("🔍 Run Compliance Check", type="primary", use_container_width=True):
    if not services.strip():
        st.error("Please describe your services before running the compliance check.")
    else:
        business_profile = {
            "business_type": business_type,
            "industry": industry,
            "services": services,
            "customer_type": customer_type,
            "transaction_type": transaction_type,
            "revenue": revenue
        }

        with st.spinner("🔍 Analyzing regulations for your business... This may take 15–30 seconds."):
            try:
                endpoint = f"{api_url.rstrip('/')}/api/compliance-check"
                response = requests.post(endpoint, json=business_profile, timeout=120)
                response.raise_for_status()
                result = response.json().get("result", "No result returned from backend.")

                st.session_state.risk_score = parse_risk_level(result)
                st.session_state.regulations_by_category = extract_regulations_by_category(result)
                
                st.markdown("---")
                st.markdown("## 📊 Compliance Analysis Report")
                
                # Risk Gauge Section
                st.subheader("🎯 Compliance Risk Assessment")
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
                
                # Categorized Regulations Section
                if st.session_state.regulations_by_category:
                    st.subheader("📋 Compliance Checklist by Category")
                    
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
                
                # Full Report
                st.subheader("📄 Detailed Compliance Analysis")
                st.markdown(result)
                
                st.markdown("---")
                st.success("✅ Analysis complete. This report is based on official government documents only.")
                st.warning("⚠️ This tool provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions.")

            except requests.exceptions.RequestException as re:
                st.error(f"Backend request failed: {re}")
            except Exception as e:
                st.error(f"Error running compliance check: {str(e)}")

# Display saved analysis if it exists
if st.session_state.risk_score is not None:
    st.markdown("---")
    st.subheader("📈 Your Latest Compliance Dashboard")
    
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

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
RegLens AI — Built for ET AI Hackathon 2026 | Powered by LLaMA 3.3 70B + RAG on RBI, GST, SEBI, MCA Documents
</div>
""", unsafe_allow_html=True)