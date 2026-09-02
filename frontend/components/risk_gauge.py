import streamlit as st
from ..utils.formatting import get_risk_gauge


def render_risk_gauge(score: int | None):
    if score is None:
        return

    st.subheader("Compliance Risk Assessment")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        gauge_label = get_risk_gauge(score)
        st.metric("Assessed Risk Level", f"{score}%", delta=gauge_label, delta_color="off")
        st.progress(score / 100.0)

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
