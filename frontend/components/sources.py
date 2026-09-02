import streamlit as st


def render_source_documents(source_documents: list):
    st.subheader("Source Regulatory Documents")
    if not source_documents:
        st.caption("No source documents captured.")
        return

    st.markdown("Ground truth documents retrieved from Qdrant Cloud:")
    for source in source_documents:
        if source.startswith("http"):
            st.markdown(f"- 📄 [{source}]({source})")
        else:
            st.markdown(f"- 📄 `{source}`")

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
