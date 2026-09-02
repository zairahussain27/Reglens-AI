import streamlit as st


def render_compliance_form(is_post_check: bool = False) -> tuple[bool, dict]:
    """Render the business profile submission form.

    Returns:
        tuple (submitted, profile_dict)
    """
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
            <div style="width:1.8rem; height:1.8rem; border-radius:6px; background:#eff6ff; color:#2563eb; display:grid; place-items:center; font-weight:bold; font-size:0.8rem;">BP</div>
            <h3 style="margin:0; font-size:1.25rem;">Business Profile</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("business_profile_form"):
        col1, col2 = st.columns(2, gap="medium")

        with col1:
            business_type = st.selectbox(
                "Business Type",
                ["Private Limited Company", "LLP", "Sole Proprietorship", "Partnership Firm", "OPC"],
                index=0,
                help="Legal structure of your business entity.",
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
                index=0,
                help="Industry domain closest to your operations.",
            )

            services = st.text_area(
                "Services / Products Offered",
                placeholder="Describe your core products, services, wallets, lending apps, or merchant gateways...",
                height=110,
                help="Detailed description of products and business model.",
            )

        with col2:
            customer_type = st.selectbox(
                "Customer Type",
                ["Retail Consumers (B2C)", "Businesses (B2B)", "Both B2B and B2C", "Government (B2G)"],
                index=0,
                help="Primary customer segment served.",
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
                index=0,
                help="Main transactional mechanism.",
            )

            revenue = st.selectbox(
                "Annual Revenue",
                [
                    "Under ₹1 Crore",
                    "₹1 Crore - ₹5 Crore",
                    "₹5 Crore - ₹25 Crore",
                    "Above ₹25 Crore",
                ],
                index=0,
                help="Approximate annual turnover.",
            )

        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Run Compliance Analysis", use_container_width=True)

        profile = {
            "business_type": business_type,
            "industry": industry,
            "services": services,
            "customer_type": customer_type,
            "transaction_type": transaction_type,
            "revenue": revenue,
        }

        return submitted, profile
