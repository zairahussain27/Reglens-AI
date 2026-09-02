import streamlit as st
from datetime import datetime
from xml.sax.saxutils import escape


def render_topbar():
    updated = datetime.now().strftime("%d %b %Y")
    st.markdown(
        f"""
        <div class="rl-topbar" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding: 0.5rem 0 1rem; margin-bottom:1.5rem;">
            <div style="display:flex; align-items:center; gap:0.75rem; font-size:1.3rem; font-weight:800; color:#0f172a;">
                <div style="width:2.2rem; height:2.2rem; border-radius:8px; background:linear-gradient(135deg, #2563eb, #4f46e5); display:grid; place-items:center; color:white; font-size:0.9rem; font-weight:bold;">RL</div>
                <span>RegLens AI</span>
            </div>
            <div style="display:flex; align-items:center; gap:1.5rem; color:#475569; font-size:0.9rem;">
                <span style="color:#0f5bff; font-weight:700; border-bottom:2px solid #0f5bff; padding-bottom:0.3rem;">Compliance Analysis</span>
                <span>Powered by Gemini & Qdrant</span>
            </div>
            <div style="color:#64748b; font-size:0.85rem;">
                <span>Updated: {updated}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div style="margin-bottom:1.5rem;">
            <h1 style="font-size:1.8rem; font-weight:800; color:#0f172a; margin-bottom:0.2rem;">{escape(title)}</h1>
            <p style="color:#64748b; font-size:1rem; margin-top:0;">{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
