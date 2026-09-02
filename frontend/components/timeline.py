import streamlit as st


def render_timeline(timeline: dict):
    if not timeline:
        return

    st.subheader("Compliance Timeline")
    cols = st.columns(4)
    buckets = ["Immediate", "Monthly", "Quarterly", "Annual"]

    for col, bucket in zip(cols, buckets):
        with col:
            items = timeline.get(bucket, [])
            st.markdown(f"### {bucket}")
            if items:
                for idx, it in enumerate(items[:5]):
                    key = f"time_{bucket}_{idx}_{it[:20]}"
                    checked = st.session_state.get(key, False)
                    st.checkbox(it[:80] + ("..." if len(it) > 80 else ""), key=key, value=checked)
                if len(items) > 5:
                    st.caption(f"+ {len(items) - 5} more")
            else:
                st.caption("No action items")

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
