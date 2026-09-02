import streamlit as st


def render_categorized_regulations(regulations_by_category: dict):
    if not regulations_by_category:
        return

    st.subheader("Compliance Checklist by Category")
    for category, items in regulations_by_category.items():
        with st.expander(f"**{category}** ({len(items)} regulations detected)", expanded=True):
            for idx, item in enumerate(items):
                key = f"chk_{category}_{idx}_{item[:20]}"
                checked = st.session_state.get(key, False)
                st.checkbox(item, key=key, value=checked)

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
