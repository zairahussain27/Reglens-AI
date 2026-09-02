import streamlit as st
from ..services.api import fetch_audit_history
from ..utils.formatting import parse_source_documents


def render_audit_history(api_url: str):
    st.markdown("---")
    st.subheader("Audit History Log")
    records, error = fetch_audit_history(api_url)

    if error:
        st.info(f"Audit history unavailable: {error}")
        return

    if not records:
        st.caption("No previous compliance requests logged in SQLite.")
        return

    st.caption(f"Showing recent {min(len(records), 10)} of {len(records)} logged checks:")

    for item in records[:10]:
        rec_id = item.get("id")
        status = (item.get("status") or "UNKNOWN").upper()
        industry = item.get("industry") or "Unknown"
        ts = item.get("timestamp") or ""
        header = f"#{rec_id} — {status} — {industry} — {ts[:19]}"

        with st.expander(header, expanded=False):
            st.markdown(
                f"**Business Type:** {item.get('business_type')} | "
                f"**Customer Type:** {item.get('customer_type')} | "
                f"**Revenue:** {item.get('revenue')}"
            )
            sources = parse_source_documents(item.get("source_documents"))
            if sources:
                st.markdown(f"**Sources:** {', '.join(sources)}")

            res_snippet = (item.get("result_text") or "")[:500]
            if res_snippet:
                st.text_area("Analysis Snapshot", res_snippet, height=100, disabled=True, key=f"hist_{rec_id}")
