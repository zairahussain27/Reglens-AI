import streamlit as st


def render_top_metric_cards(
    score: int | None,
    regulations_by_category: dict,
    timeline: dict,
):
    display_score = f"{score}%" if score is not None else "0%"
    regulations_count = sum(len(v) for v in regulations_by_category.values())
    pending_actions = sum(len(v) for v in timeline.values())
    upcoming_filings = len(timeline.get("Monthly", [])) + len(timeline.get("Quarterly", []))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Compliance Risk Score", display_score, "Assessed by Gemini")
    with c2:
        st.metric("Applicable Regulations", str(regulations_count), "Statutory Acts identified")
    with c3:
        st.metric("Pending Action Items", str(pending_actions), "Checklist tasks")
    with c4:
        st.metric("Upcoming Filings", str(upcoming_filings), "Monthly / Quarterly")

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
