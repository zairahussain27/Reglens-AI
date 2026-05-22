import streamlit as st
import requests
import os
import json
import re
import textwrap
from datetime import datetime
from xml.sax.saxutils import escape
# Optional dependency: only needed for PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    _REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    colors = None
    letter = None
    getSampleStyleSheet = None
    ParagraphStyle = None
    inch = None
    SimpleDocTemplate = Paragraph = Spacer = Table = TableStyle = PageBreak = None
    _REPORTLAB_AVAILABLE = False

from io import BytesIO

# Page config
st.set_page_config(
    page_title="RegLens AI",
    page_icon="RL",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .app-card {
        padding: 1.8rem 2rem;
        border-radius: 22px;
        background: var(--background-color, #ffffff);
        box-shadow: 0 28px 60px rgba(15, 23, 42, 0.09);
        transition: box-shadow 180ms ease, transform 180ms ease;
    }
    .app-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 34px 80px rgba(15, 23, 42, 0.14);
    }
    .hero-card {
        border: 1px solid rgba(148, 163, 184, 0.14);
        background: rgba(15, 118, 255, 0.06);
    }
    .section-label {
        color: var(--text-color-secondary, #64748b);
        font-weight: 600;
    }
    .stButton>button {
        border-radius: 14px;
        padding: 0.85rem 1.4rem;
        font-weight: 700;
    }
    
    @media (prefers-color-scheme: dark) {
        .app-card { box-shadow: 0 28px 60px rgba(0, 0, 0, 0.40); }
        .hero-card { background: rgba(10, 54, 108, 0.22); border-color: rgba(148, 163, 184, 0.20); }
        .section-label { color: #cbd5e1; }
    }
    label[data-testid="stWidgetLabel"] p {
        font-size: 0.78rem !important;
        letter-spacing: -0.1px;
    }

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background: #fcfcfd !important;
    }

    

    div[data-testid="stForm"] hr {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    /* SELECTBOX FIX */

    div[data-baseweb="select"] > div {
        height: 44px !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        border-radius: 10px !important;
        border: 1px solid #d1d5db !important;
        background: white !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        padding: 0 10px !important;
        box-shadow: none !important;
    }

    div[data-baseweb="select"] span {
        font-size: 14px !important;
        color: #111827 !important;
        line-height: normal !important;
        display: flex !important;
        align-items: center !important;
    }

    /* DROPDOWN */

    ul[role="listbox"] {
        border-radius: 10px !important;
        border: 1px solid #e5e7eb !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08) !important;
    }

    /* TEXTAREA */

    .stTextArea textarea {
        border-radius: 10px !important;
        padding-top: 12px !important;
        line-height: 1.5 !important;
        resize: none !important;
    }

    /* LABELS */

    label[data-testid="stWidgetLabel"] p {
        font-size: 14px !important;
        font-weight: 600 !important;
        margin-bottom: 6px !important;
        color: #111827 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    :root {
        --rl-bg: #f8fafc;
        --rl-card: #ffffff;
        --rl-line: #e2e8f0;
        --rl-soft-line: #edf2f7;
        --rl-text: #0f172a;
        --rl-muted: #64748b;
        --rl-blue: #0f5bff;
        --rl-green: #16a34a;
        --rl-orange: #f97316;
    }
    .stApp { background: var(--rl-bg); color: var(--rl-text); }
    .block-container { max-width: 1480px; padding-top: 1.1rem; padding-bottom: 1.5rem; }
    /* Remove reserved Streamlit header/chrome space (fixes blank top bar) */
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    #MainMenu,
    footer,
    .stApp header {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    /* Also remove any accidental top padding/margin on main container */
    .block-container { padding-top: 0.2rem !important; }
    .rl-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.2rem 0 1rem;
        border-bottom: 1px solid var(--rl-line);
        margin-bottom: 1.8rem;
    }
    .rl-brand, .rl-nav, .rl-meta, .rl-title-left, .rl-row-left, .rl-section-head {
        display: flex;
        align-items: center;
    }
    .rl-brand { gap: 0.75rem; font-size: 1.25rem; font-weight: 800; color: var(--rl-text); }
    .rl-logo, .rl-icon, .rl-mini-icon {
        display: grid;
        place-items: center;
        font-weight: 800;
        flex: 0 0 auto;
    }
    .rl-logo {
        width: 2rem;
        height: 2rem;
        border-radius: 8px;
        color: #ffffff;
        background: linear-gradient(135deg, #2563eb, #4f46e5);
        font-size: 0.82rem;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.22);
    }
    .rl-nav { gap: 1.8rem; color: #475569; font-size: 0.9rem; white-space: nowrap; }
    .rl-nav .active {
        color: var(--rl-blue);
        font-weight: 700;
        border-bottom: 2px solid var(--rl-blue);
        padding-bottom: 1.45rem;
        margin-bottom: -1.45rem;
    }
    .rl-meta {
        justify-content: flex-end;
        gap: 0.9rem;
        color: #475569;
        font-size: 0.85rem;
        white-space: nowrap;
    }
    .rl-avatar {
        width: 2.25rem;
        height: 2.25rem;
        border-radius: 50%;
        background: #e2e8f0;
        color: var(--rl-text);
        display: grid;
        place-items: center;
        font-weight: 800;
    }
    .rl-page-title h1 {
        font-size: 1.8rem;
        line-height: 1.15;
        margin: 0;
        font-weight: 800;
        color: var(--rl-text);
    }
    .rl-page-title p { margin: 0.55rem 0 1.5rem; color: var(--rl-muted); font-size: 0.98rem; }
    .rl-card {
        background: var(--rl-card);
        border: 1px solid var(--rl-line);
        border-radius: 8px;
        padding: 1.15rem 1.25rem;
        min-height: 100%;
    }
    .rl-section-head { justify-content: space-between; gap: 0.7rem; margin-bottom: 0.95rem; }
    .rl-title-left { gap: 0.75rem; }
    .rl-icon {
        width: 2rem;
        height: 2rem;
        border-radius: 8px;
        background: #eff6ff;
        color: var(--rl-blue);
        border: 1px solid #dbeafe;
        font-size: 0.78rem;
    }
    .rl-card h2, .rl-card h3 { margin: 0; color: var(--rl-text); font-weight: 800; }
    .rl-card h2 { font-size: 1.15rem; }
    .rl-card h3 { font-size: 1rem; }
    .rl-help { margin: 0.2rem 0 1.25rem; color: var(--rl-muted); font-size: 0.9rem; }
    .rl-status {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.35rem 0.65rem;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .rl-status.good { background: #dcfce7; color: #15803d; }
    .rl-status.pending { background: #ffedd5; color: #c2410c; }
    .rl-status.upcoming { background: #dbeafe; color: #1d4ed8; }
    .rl-dot { width: 0.45rem; height: 0.45rem; border-radius: 50%; background: currentColor; }
    .rl-divider { height: 1px; background: var(--rl-line); margin: 1.05rem 0; }
    .rl-summary-grid {
        display: grid;
        grid-template-columns: minmax(170px, 0.9fr) minmax(220px, 1.1fr);
        gap: 1.25rem;
        align-items: center;
    }
    .rl-score-ring {
        width: 9rem;
        height: 9rem;
        border-radius: 50%;
        display: grid;
        place-items: center;
        margin: 0.3rem auto 0.7rem;
        background:
            radial-gradient(circle at center, #ffffff 0 56%, transparent 57%),
            conic-gradient(var(--rl-green) var(--score, 0%), #e5e7eb 0);
    }
    .rl-score-ring strong { display: block; font-size: 1.7rem; line-height: 1; color: var(--rl-text); text-align: center; }
    .rl-score-ring span {
        display: block;
        color: var(--rl-green);
        font-size: 0.78rem;
        font-weight: 800;
        margin-top: 0.35rem;
        text-align: center;
    }
    .rl-score-caption { text-align: center; color: var(--rl-muted); font-size: 0.8rem; }
    .rl-stats { border-left: 1px solid var(--rl-line); padding-left: 1.25rem; }
    .rl-stat-row, .rl-list-row, .rl-action-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.66rem 0;
        border-bottom: 1px solid var(--rl-soft-line);
        font-size: 0.88rem;
    }
    .rl-stat-row:last-child, .rl-list-row:last-child, .rl-action-row:last-child { border-bottom: 0; }
    .rl-row-left { gap: 0.7rem; min-width: 0; }
    .rl-mini-icon {
        width: 1.35rem;
        height: 1.35rem;
        border-radius: 6px;
        border: 1px solid #cbd5e1;
        color: #64748b;
        font-size: 0.68rem;
    }
    .rl-row-title { color: var(--rl-text); font-weight: 650; overflow-wrap: anywhere; }
    .rl-row-sub { color: var(--rl-muted); font-size: 0.78rem; margin-top: 0.15rem; }
    .rl-row-value { color: var(--rl-text); font-weight: 800; white-space: nowrap; }
    .rl-view { color: var(--rl-blue); font-size: 0.82rem; font-weight: 700; }
    .rl-coverage-grid {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 0.85rem;
    }
    .rl-coverage-item {
        border: 1px solid var(--rl-line);
        border-radius: 8px;
        padding: 0.85rem;
        min-height: 4.3rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        background: #ffffff;
    }
    .rl-coverage-name { font-weight: 800; color: var(--rl-text); font-size: 0.9rem; }
    .rl-coverage-sub { color: var(--rl-muted); font-size: 0.76rem; margin-top: 0.15rem; }
    .rl-footer {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: 1.6rem 0 0.4rem;
        color: #475569;
        font-size: 0.8rem;
        border-top: 1px solid var(--rl-line);
        margin-top: 1.5rem;
    }
    .hero-card { display: none; }
    div[data-testid="stForm"] { border: 0; padding: 0; }
    .stButton>button {
        border-radius: 8px;
        padding: 0.78rem 1.15rem;
        font-weight: 700;
        background: var(--rl-blue);
        color: #ffffff;
        border: 1px solid var(--rl-blue);
    }
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div>div>div {
        border-radius: 8px;
        border-color: var(--rl-line);
        min-height: 2.9rem;
    }
    label[data-testid="stWidgetLabel"] p {
        font-weight: 700;
        color: var(--rl-text);
        font-size: 0.85rem;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --rl-bg: #0f172a;
            --rl-card: #111827;
            --rl-line: #334155;
            --rl-soft-line: #1f2937;
            --rl-text: #f8fafc;
            --rl-muted: #cbd5e1;
        }
        .rl-score-ring {
            background:
                radial-gradient(circle at center, #111827 0 56%, transparent 57%),
                conic-gradient(var(--rl-green) var(--score, 0%), #334155 0);
        }
        .rl-coverage-item { background: #111827; }
    }
    @media (max-width: 900px) {
        .rl-topbar { align-items: flex-start; flex-direction: column; }
        .rl-nav, .rl-meta { width: 100%; justify-content: flex-start; flex-wrap: wrap; }
        .rl-nav .active { padding-bottom: 0.2rem; margin-bottom: 0; }
        .rl-summary-grid, .rl-coverage-grid { grid-template-columns: 1fr; }
        .rl-stats { border-left: 0; border-top: 1px solid var(--rl-line); padding-left: 0; padding-top: 1rem; }
        .rl-footer { flex-direction: column; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    /* Final enterprise light-theme layer. Keep this after legacy styles. */
    :root {
        --rl-bg: #f6f8fb;
        --rl-card: #ffffff;
        --rl-line: #e5e7eb;
        --rl-soft-line: #f0f2f5;
        --rl-text: #111827;
        --rl-muted: #6b7280;
        --rl-blue: #2563eb;
        --rl-green: #16a34a;
        --rl-orange: #d97706;
    }
    html, body, .stApp {
        background: #f6f8fb !important;
        color: #111827 !important;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .block-container {
        max-width: 1360px;
        padding: 1rem 2rem 1.25rem;
    }
    section[data-testid="stSidebar"] {
        width: auto !important;
        max-width: 250px !important;
        min-width: 0 !important;
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
        transition: width 180ms ease;
    }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width: auto !important;
        min-width: 72px !important;
    }
    section[data-testid="stSidebar"] > div {
        padding: 1.25rem 1rem;
    }
    section[data-testid="stSidebar"] img {
        width: 42px !important;
        margin-bottom: 0.25rem;
    }
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] li {
        color: #4b5563;
        font-size: 0.84rem;
        line-height: 1.45;
    }
    section[data-testid="stSidebar"] h3 {
        color: #111827;
        font-size: 0.95rem;
        font-weight: 700;
    }
    .rl-topbar {
        min-height: 48px;
        padding: 0 0 0.75rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid #e5e7eb;
    }
    .rl-brand {
        font-size: 1rem;
        font-weight: 750;
        letter-spacing: 0;
    }
    .rl-logo {
        width: 1.8rem;
        height: 1.8rem;
        border-radius: 7px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1d4ed8;
        box-shadow: none;
    }
    .rl-nav {
        gap: 1.4rem;
        font-size: 0.82rem;
        color: #6b7280;
    }
    .rl-nav .active {
        color: #1d4ed8;
        border-bottom: 2px solid #2563eb;
        padding-bottom: 1.05rem;
        margin-bottom: -1.05rem;
    }
    .rl-meta {
        font-size: 0.78rem;
        color: #6b7280;
    }
    .rl-avatar {
        width: 1.9rem;
        height: 1.9rem;
        background: #f3f4f6;
        border: 1px solid #e5e7eb;
        font-size: 0.76rem;
    }
    .rl-page-title h1 {
        font-size: 1.65rem;
        font-weight: 750;
        letter-spacing: 0;
    }
    .rl-page-title p {
        margin: 0.4rem 0 1.1rem;
        color: #6b7280;
        font-size: 0.92rem;
    }
    .rl-card,
    .rl-panel-heading,
    div[data-testid="stForm"] {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.035) !important;
    }
    .rl-card {
        padding: 1rem 1.05rem;
    }
    .rl-panel-heading {
        padding: 1rem 1.05rem;
        margin-bottom: 0.75rem;
    }
    div[data-testid="stForm"] {
        padding: 1rem 1.05rem 0.9rem;
    }
    .rl-section-head {
        margin-bottom: 0.7rem;
    }
    .rl-card h2,
    .rl-card h3 {
        font-weight: 720;
        color: #111827;
        letter-spacing: 0;
    }
    .rl-card h2 { font-size: 1rem; }
    .rl-card h3 { font-size: 0.92rem; }
    .rl-help {
        color: #6b7280;
        font-size: 0.84rem;
        margin-bottom: 0.65rem;
    }
    .rl-icon,
    .rl-mini-icon {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        color: #64748b;
        box-shadow: none;
    }
    .rl-icon {
        width: 1.7rem;
        height: 1.7rem;
        border-radius: 7px;
    }
    .rl-mini-icon {
        width: 1.3rem;
        height: 1.3rem;
        border-radius: 6px;
        font-size: 0.64rem;
    }
    .rl-summary-grid {
        grid-template-columns: minmax(150px, 0.8fr) minmax(230px, 1.2fr);
        gap: 1rem;
    }
    .rl-score-ring {
        width: 7.4rem;
        height: 7.4rem;
        margin: 0.2rem auto 0.55rem;
        background:
            radial-gradient(circle at center, #ffffff 0 58%, transparent 59%),
            conic-gradient(#22c55e var(--score, 0%), #edf2f7 0);
    }
    .rl-score-ring strong {
        font-size: 1.45rem;
        font-weight: 760;
    }
    .rl-score-ring span {
        color: #16a34a;
        font-size: 0.72rem;
    }
    .rl-score-caption {
        font-size: 0.74rem;
        color: #6b7280;
    }
    .rl-stats {
        padding-left: 1rem;
        border-left: 1px solid #e5e7eb;
    }
    .rl-stat-row,
    .rl-list-row,
    .rl-action-row {
        padding: 0.54rem 0;
        gap: 0.75rem;
        font-size: 0.82rem;
        border-bottom: 1px solid #f0f2f5;
    }
    .rl-row-title {
        font-size: 0.82rem;
        font-weight: 620;
        color: #111827;
    }
    .rl-row-sub {
        font-size: 0.72rem;
        color: #6b7280;
    }
    .rl-row-value {
        font-size: 0.82rem;
        font-weight: 720;
    }
    .rl-status {
        padding: 0.22rem 0.5rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 650;
    }
    .rl-status.good {
        background: #ecfdf3;
        color: #067647;
    }
    .rl-status.pending {
        background: #fff7ed;
        color: #b45309;
    }
    .rl-status.upcoming {
        background: #eff6ff;
        color: #1d4ed8;
    }
    .rl-view {
        color: #2563eb;
        font-size: 0.76rem;
        font-weight: 650;
    }
    .rl-coverage-grid {
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 0.75rem;
    }
    .rl-coverage-item {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 9px;
        min-height: 3.75rem;
        padding: 0.72rem;
    }
    .rl-coverage-name {
        font-size: 0.82rem;
        font-weight: 700;
    }
    .rl-coverage-sub {
        font-size: 0.7rem;
        color: #6b7280;
    }
    .top-card-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1rem;
        margin-bottom: 1.25rem;
    }
    .rl-stat-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 1rem 1.1rem;
        min-height: 128px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 0.5rem;
    }
    .rl-stat-card .metric-label {
        font-size: 0.78rem;
        font-weight: 700;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .rl-stat-card .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #111827;
    }
    .rl-stat-card .metric-note {
        font-size: 0.82rem;
        color: #6b7280;
    }
    .rl-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        background: #ecfdf5;
        color: #15803d;
    }
    .rl-status-pill.pending {
        background: #ffedd5;
        color: #b45309;
    }
    .rl-status-pill.upcoming {
        background: #eff6ff;
        color: #1d4ed8;
    }
    .stButton > button {
        width: 100% !important;
        min-width: 0;
        min-height: 2.45rem;
        border-radius: 8px;
        background: #2563eb !important;
        border: 1px solid #2563eb !important;
        color: #ffffff !important;
        font-weight: 650;
        font-size: 0.84rem;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.18);
    }
    .stButton > button:hover {
        background: #1d4ed8 !important;
        border-color: #1d4ed8 !important;
    }
    /* Form styling */
    div[data-testid="stForm"] {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 12px !important;
        padding: 2rem 1.5rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        margin-top: 2rem !important;
        margin-bottom: 2rem !important;
    }
    /* Columns alignment */
    
    /* Vertical spacing for form fields */
    .stSelectbox,
    .stTextArea {
        margin-bottom: 0.7rem !important;
    }
    .stTextInput,
    .stTextArea,
    .stSelectbox {
        margin-bottom: 1.2rem !important;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px !important;
        color: #111827 !important;
        box-shadow: none !important;
        padding: 0.75rem 0.875rem !important;
        font-size: 0.92rem !important;
        min-height: 2.5rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
    }
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #9ca3af !important;
        opacity: 1;
    }
    
    
    label[data-testid="stWidgetLabel"] {
        margin-bottom: 0.35rem !important;
    }
    label[data-testid="stWidgetLabel"] p {
        color: #111827 !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        margin-bottom: 0.25rem !important;
    }
    /* Two-column form layout */
    .stColumns > div > div {
        padding: 0 0.5rem !important;
    }
    .stColumns > div > div:first-child {
        padding-left: 0 !important;
    }
    .stColumns > div > div:last-child {
        padding-right: 0 !important;
    }
    .stMarkdown hr {
        margin: 0.75rem 0;
        border-color: #edf2f7;
    }
    .app-card,
    .hero-card {
        display: none !important;
    }
    @media (prefers-color-scheme: dark) {
        html, body, .stApp {
            background: #f6f8fb !important;
            color: #111827 !important;
        }
        .rl-card,
        div[data-testid="stForm"],
        .rl-coverage-item,
        section[data-testid="stSidebar"] {
            background: #ffffff !important;
            color: #111827 !important;
        }
        .rl-score-ring {
            background:
                radial-gradient(circle at center, #ffffff 0 58%, transparent 59%),
                conic-gradient(#22c55e var(--score, 0%), #edf2f7 0) !important;
        }
    }
    @media (max-width: 1100px) {
        .rl-coverage-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }
    }
    @media (max-width: 760px) {
        .block-container {
            padding: 0.75rem 1rem 1rem;
        }
        .rl-summary-grid,
        .rl-coverage-grid {
            grid-template-columns: 1fr;
        }
        .rl-stats {
            border-left: 0;
            border-top: 1px solid #e5e7eb;
            padding-left: 0;
            padding-top: 0.8rem;
        }
        div[data-testid="stForm"] {
        padding: 1.2rem 1.2rem 0.6rem 1.2rem !important;
        }
    }
    /* Additional form enhancements */
    div[data-testid="stForm"] .stSelectbox {
        position: relative;
    }
    div[data-testid="stForm"] .stSelectbox > div > div > div > div > div > svg {
        color: #2563eb !important;
    }
    .stForm fieldset {
        border: none !important;
        padding: 0 !important;
    }
    /* Help text styling */
    div[data-baseweb="popover"] {
        background: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state for checklists
if "compliance_checklist" not in st.session_state:
    st.session_state.compliance_checklist = {}
if "risk_score" not in st.session_state:
    st.session_state.risk_score = None
if "regulations_by_category" not in st.session_state:
    st.session_state.regulations_by_category = {}
if "compliance_timeline" not in st.session_state:
    st.session_state.compliance_timeline = {}
if "latest_report_markdown" not in st.session_state:
    st.session_state.latest_report_markdown = None
if "latest_report_pdf" not in st.session_state:
    st.session_state.latest_report_pdf = None
if "latest_business_profile" not in st.session_state:
    st.session_state.latest_business_profile = None
if "latest_source_documents" not in st.session_state:
    st.session_state.latest_source_documents = []
if "latest_result_text" not in st.session_state:
    st.session_state.latest_result_text = None

# Input validation functions
def sanitize_input(value: str) -> str:
    """Remove potentially malicious content from input strings"""
    if not isinstance(value, str):
        return value
    
    # Remove newlines and tabs
    value = value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Remove multiple spaces
    value = re.sub(r'\s+', ' ', value)
    
    # Remove URLs
    value = re.sub(r'https?://\S+', '', value)
    
    # Remove email addresses
    value = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', value)
    
    return value.strip()


def validate_services(services: str) -> tuple[bool, str]:
    """Validate services field"""
    services = sanitize_input(services)
    
    if not services:
        return False, "Services field cannot be empty"
    if len(services) < 5:
        return False, "Services must be at least 5 characters long"
    if len(services) > 2000:
        return False, "Services description is too long (max 2000 characters)"
    
    return True, "Services validation passed"


def validate_business_profile(profile: dict) -> tuple[bool, str]:
    """Validate entire business profile"""
    is_valid = True
    errors = []
    
    # Check services specifically
    services_valid, services_msg = validate_services(profile.get("services", ""))
    if not services_valid:
        errors.append(services_msg)
        is_valid = False
    
    # Check other required fields
    for field in ["business_type", "industry", "customer_type", "transaction_type", "revenue"]:
        value = profile.get(field, "").strip()
        if not value:
            errors.append(f"{field.replace('_', ' ').title()} is required")
            is_valid = False
        elif len(value) > 100:
            errors.append(f"{field.replace('_', ' ').title()} is too long")
            is_valid = False
    
    if not is_valid:
        return False, "\n".join(errors)
    
    return True, "All validations passed"


def parse_source_documents(value) -> list[str]:
    """Normalize API/DB source document payloads into a list of strings."""
    if isinstance(value, list):
        return [str(source).strip() for source in value if str(source).strip()]

    if not value:
        return []

    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = None

        if isinstance(decoded, list):
            return [str(source).strip() for source in decoded if str(source).strip()]

        return [
            source.strip()
            for source in re.split(r"[\n,]", value)
            if source.strip()
        ]

    return [str(value).strip()]


def fetch_audit_history(api_url: str) -> tuple[list[dict], str | None]:
    """Fetch recent compliance requests from the backend audit endpoint."""
    try:
        endpoint = f"{api_url.rstrip('/')}/api/history"
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as exc:
        return [], str(exc)


def render_source_documents(source_documents: list[str]) -> None:
    """Render source links/files for the current report or audit records."""
    if not source_documents:
        st.caption("No source documents captured.")
        return

    for source in source_documents:
        if source.startswith("http"):
            st.markdown(f"- [{source}]({source})")
        else:
            st.markdown(f"- {source}")


def render_audit_history(api_url: str) -> None:
    """Show recent compliance checks with persisted source document metadata."""
    st.markdown("---")
    st.subheader("Audit History")
    history_items, history_error = fetch_audit_history(api_url)

    if history_error:
        st.info(f"Audit history is unavailable: {history_error}")
        return

    if not history_items:
        st.caption("No compliance requests have been logged yet.")
        return

    st.caption(f"Showing {min(len(history_items), 10)} of {len(history_items)} recent requests.")

    for item in history_items[:10]:
        timestamp = item.get("timestamp", "")
        industry = item.get("industry", "Unknown industry")
        status = item.get("status", "unknown").upper()
        title = f"#{item.get('id')} - {status} - {industry} - {timestamp}"

        with st.expander(title, expanded=False):
            st.markdown(
                f"**Business Type:** {item.get('business_type', '')}  \n"
                f"**Customer Type:** {item.get('customer_type', '')}  \n"
                f"**Transaction Type:** {item.get('transaction_type', '')}  \n"
                f"**Revenue:** {item.get('revenue', '')}"
            )

            st.markdown("**Source Documents**")
            render_source_documents(parse_source_documents(item.get("source_documents")))

            result_preview = (item.get("result_text") or "").strip()
            if result_preview:
                st.text_area(
                    "Result Snapshot",
                    value=result_preview[:2000],
                    height=180,
                    disabled=True,
                    key=f"audit_result_{item.get('id')}",
                )


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
        return "LOW RISK"
    elif score < 70:
        return "MEDIUM RISK"
    else:
        return "HIGH RISK"


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


def clean_report_line(line: str) -> str:
    """Normalize markdown checklist/list lines for display and exports."""
    line = line.strip()
    line = re.sub(r"^[-*]\s+\[[ xX]\]\s*", "", line)
    line = re.sub(r"^[-*]\s+", "", line)
    line = re.sub(r"^\d+\.\s+", "", line)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    return line.strip()


def extract_action_items(result_text: str) -> list[str]:
    """Extract checklist and next-step items from the model report."""
    items = []
    in_next_steps = False

    for raw_line in result_text.splitlines():
        line = raw_line.strip()
        line_lower = line.lower()

        if "recommended next steps" in line_lower:
            in_next_steps = True
            continue
        if line.startswith("##") and in_next_steps:
            in_next_steps = False

        is_checklist_item = bool(re.match(r"^[-*]\s+\[[ xX]\]\s+", line))
        is_next_step = in_next_steps and bool(re.match(r"^\d+\.\s+", line))

        if is_checklist_item or is_next_step:
            cleaned = clean_report_line(line)
            if cleaned and cleaned not in items:
                items.append(cleaned)

    return items


def assign_timeline_bucket(item: str) -> str:
    """Place an action item into a practical compliance timeline bucket."""
    item_lower = item.lower()

    setup_keywords = [
        "register", "obtain", "apply", "license", "kyc", "verify", "disclose",
        "appoint", "before", "prior", "immediate", "urgent", "must"
    ]
    general_immediate_keywords = [
        "file", "submit", "ensure", "comply"
    ]
    monthly_keywords = [
        "invoice", "payment", "return", "reconcile",
        "monitor", "review transactions", "deduct", "deposit"
    ]
    quarterly_keywords = [
        "board", "audit", "statement",
        "inspection", "reporting"
    ]
    annual_keywords = [
        "renew", "financial statement",
        "income tax", "roc", "mca", "audit report"
    ]

    if any(keyword in item_lower for keyword in setup_keywords):
        return "Immediate"
    if any(keyword in item_lower for keyword in ["annual", "yearly", "year"]):
        return "Annual"
    if any(keyword in item_lower for keyword in ["quarterly", "quarter"]):
        return "Quarterly"
    if any(keyword in item_lower for keyword in ["monthly", "month"]):
        return "Monthly"
    if any(keyword in item_lower for keyword in annual_keywords):
        return "Annual"
    if any(keyword in item_lower for keyword in quarterly_keywords):
        return "Quarterly"
    if any(keyword in item_lower for keyword in monthly_keywords):
        return "Monthly"
    if any(keyword in item_lower for keyword in general_immediate_keywords):
        return "Immediate"
    return "Immediate"


def build_compliance_timeline(result_text: str) -> dict[str, list[str]]:
    """Convert report checklist items into Immediate/Monthly/Quarterly/Annual buckets."""
    timeline = {
        "Immediate": [],
        "Monthly": [],
        "Quarterly": [],
        "Annual": []
    }

    for item in extract_action_items(result_text):
        bucket = assign_timeline_bucket(item)
        timeline[bucket].append(item)

    return {bucket: items for bucket, items in timeline.items() if items}


def build_markdown_report(
    business_profile: dict,
    result_text: str,
    risk_score: int,
    timeline: dict[str, list[str]],
    source_documents: list[str] | None = None,
) -> str:
    """Build a downloadable Markdown compliance report."""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# RegLens AI Compliance Report",
        "",
        f"Generated: {generated_at}",
        "",
        "## Business Profile",
        ""
    ]

    for label, value in business_profile.items():
        lines.append(f"- **{label.replace('_', ' ').title()}:** {value}")

    lines.extend([
        "",
        "## Risk Snapshot",
        "",
        f"- **Risk Score:** {risk_score}%",
        f"- **Risk Level:** {get_risk_gauge(risk_score)}",
        "",
        "## Compliance Timeline",
        ""
    ])

    if timeline:
        for bucket, items in timeline.items():
            lines.append(f"### {bucket}")
            for item in items:
                lines.append(f"- [ ] {item}")
            lines.append("")
    else:
        lines.append("No checklist items were detected in the report.")
        lines.append("")

    lines.extend([
        "## Source Documents",
        ""
    ])

    if source_documents:
        for source in source_documents:
            lines.append(f"- {source}")
        lines.append("")
    else:
        lines.append("No source documents were captured.")
        lines.append("")

    lines.extend([
        "## Detailed Compliance Analysis",
        "",
        result_text,
        "",
        "---",
        "This report provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions."
    ])

    return "\n".join(lines)


def build_pdf_report(
    business_profile: dict,
    result_text: str,
    risk_score: int,
    timeline: dict[str, list[str]],
    source_documents: list[str] | None = None,
) -> bytes:
    """Create a professional PDF report using ReportLab."""
    if not _REPORTLAB_AVAILABLE:
        raise ModuleNotFoundError(
            "reportlab is required for PDF generation. Install it or disable PDF generation."
        )

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )

    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=15,
        textColor=colors.darkgreen
    )

    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 14

    # Build the story (content)
    story = []

    # Title
    story.append(Paragraph("RegLens AI Compliance Report", title_style))
    story.append(Spacer(1, 12))

    # Generation timestamp
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"Generated: {generated_at}", normal_style))
    story.append(Spacer(1, 20))

    # Business Profile Section
    story.append(Paragraph("Business Profile", section_style))

    # Create business profile table
    profile_data = [["Field", "Value"]]
    for label, value in business_profile.items():
        display_label = label.replace('_', ' ').title()
        profile_data.append([display_label, value])

    profile_table = Table(profile_data, colWidths=[2*inch, 4*inch])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 20))

    # Risk Snapshot Section
    story.append(Paragraph("Risk Snapshot", section_style))

    risk_level = get_risk_gauge(risk_score)
    risk_color = colors.red if risk_score >= 70 else colors.orange if risk_score >= 40 else colors.green

    risk_data = [
        ["Risk Score", f"{risk_score}%"],
        ["Risk Level", risk_level]
    ]

    risk_table = Table(risk_data, colWidths=[2*inch, 4*inch])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (1, 1), (1, 1), risk_color),
        ('FONTNAME', (1, 1), (1, 1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 20))

    # Compliance Timeline Section
    story.append(Paragraph("Compliance Timeline", section_style))

    if timeline:
        for bucket, items in timeline.items():
            story.append(Paragraph(bucket, styles['Heading3']))
            for item in items:
                story.append(Paragraph(f"- {item}", normal_style))
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("No checklist items were detected in the report.", normal_style))
        story.append(Spacer(1, 20))

    # Source Documents Section
    story.append(Paragraph("Source Documents", section_style))
    if source_documents:
        for source in source_documents:
            story.append(Paragraph(escape(source), normal_style))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No source documents were captured.", normal_style))
    story.append(Spacer(1, 20))

    # Detailed Analysis Section
    story.append(PageBreak())  # Start new page for detailed analysis
    story.append(Paragraph("Detailed Compliance Analysis", section_style))

    # Clean and format the result text
    cleaned_result = result_text.replace('#', '').replace('*', '').strip()
    paragraphs = cleaned_result.split('\n\n')

    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip(), normal_style))
            story.append(Spacer(1, 10))

    # Footer disclaimer
    story.append(Spacer(1, 30))
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=normal_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    story.append(Paragraph(
        "This report provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions.",
        disclaimer_style
    ))

    # Build the PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def render_topbar() -> None:
    updated = datetime.now().strftime("%d %b %Y")
    st.markdown(
        f"""
        <div class="rl-topbar">
            <div class="rl-brand">
                <div class="rl-logo">RL</div>
                <div>RegLens AI</div>
            </div>
            <div class="rl-nav">
                <span class="active">Compliance Check</span>
                <span>Regulatory Updates</span>
                <span>About</span>
            </div>
            <div class="rl-meta">
                <span>Last updated: {updated}</span>
                <div class="rl-avatar">RG</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="rl-page-title">
            <h1>{escape(title)}</h1>
            <p>{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_metric_cards() -> None:
    score = st.session_state.risk_score if st.session_state.risk_score is not None else 0
    regulations_count = sum(len(items) for items in st.session_state.regulations_by_category.values())
    pending_actions = sum(len(items) for items in st.session_state.compliance_timeline.values())
    upcoming_filings = len(st.session_state.compliance_timeline.get("Monthly", [])) + len(
        st.session_state.compliance_timeline.get("Quarterly", [])
    )

    cards = [
        ("Compliance Score", f"{score}%", "Your current compliance risk score."),
        ("Applicable Regulations", str(regulations_count), "Laws and regulations that apply."),
        ("Pending Actions", str(pending_actions), "Tasks that require your attention."),
        ("Upcoming Filings", str(upcoming_filings), "Filings you should complete soon."),
    ]

    metrics_html = "".join(
        f"""
        <div class=\"rl-stat-card\">
            <div class=\"metric-label\">{escape(title)}</div>
            <div class=\"metric-value\">{escape(value)}</div>
            <div class=\"metric-note\">{escape(note)}</div>
        </div>
        """
        for title, value, note in cards
    )

    st.markdown(
        f"""
        <div class="top-card-grid">{metrics_html}</div>
        """,
        unsafe_allow_html=True,
    )


def render_business_profile_card(is_post_check: bool) -> None:
    status_html = (
        '<span class="rl-status-pill">Submitted</span>'
        if is_post_check else ""
    )

    intro_text = (
        "Provide accurate details to get relevant compliance obligations."
        if not is_post_check
        else "Your latest profile has been submitted and the report has been generated."
    )

    st.markdown(
        f"""
        <div class="rl-card">
            <div class="rl-section-head">
                <div class="rl-title-left">
                    <div class="rl-icon">BP</div>
                    <h2>Business Profile</h2>
                </div>
                {status_html}

            
        
        """,
        unsafe_allow_html=True,
    )

def risk_label(score: int | None) -> str:
    if score is None:
        return "Not assessed"
    if score < 30:
        return "Low"
    if score < 70:
        return "Medium"
    return "High"


def audit_readiness_label(score: int | None) -> str:
    if score is None:
        return "Pending"
    if score < 30:
        return "High"
    if score < 70:
        return "Moderate"
    return "Needs review"


def flatten_timeline_items(limit: int = 4) -> list[tuple[str, str]]:
    rows = []
    for bucket, items in st.session_state.compliance_timeline.items():
        for item in items:
            rows.append((bucket, item))
            if len(rows) >= limit:
                return rows
    return rows


def render_summary_card() -> None:
    score = st.session_state.risk_score
    display_score = 0 if score is None else score
    label = risk_label(score)
    regulations_count = sum(len(items) for items in st.session_state.regulations_by_category.values())
    pending_actions = sum(len(items) for items in st.session_state.compliance_timeline.values())
    upcoming_filings = len(st.session_state.compliance_timeline.get("Monthly", [])) + len(
        st.session_state.compliance_timeline.get("Quarterly", [])
    )
    status_class = "pending" if score is None else "good"
    status_text = "Ready" if score is None else label
    assessed = "Not assessed yet" if score is None else datetime.now().strftime("Last assessed: %d %b %Y")

    st.markdown(
        f"""
        <div class="rl-card">
            <div class="rl-section-head">
                <h2>Compliance Summary</h2>
                <span class="rl-status {status_class}"><span class="rl-dot"></span>{status_text}</span>
            </div>
            <div class="rl-divider"></div>
            <div class="rl-summary-grid">
                <div>
                    <h3 style="text-align:center; margin-bottom:0.3rem;">Compliance Score</h3>
                    <div class="rl-score-ring" style="--score:{display_score}%;">
                        <div><strong>{display_score}%</strong><span>{escape(label)}</span></div>
                    </div>
                    <div class="rl-score-caption">{assessed}</div>
                </div>
                <div class="rl-stats">
                    <h3>Key Stats</h3>
                    <div class="rl-stat-row">
                        <div class="rl-row-left"><span class="rl-mini-icon">R</span><span>Applicable Regulations</span></div>
                        <span class="rl-row-value">{regulations_count}</span>
                    </div>
                    <div class="rl-stat-row">
                        <div class="rl-row-left"><span class="rl-mini-icon">A</span><span>Pending Actions</span></div>
                        <span class="rl-row-value">{pending_actions}</span>
                    </div>
                    <div class="rl-stat-row">
                        <div class="rl-row-left"><span class="rl-mini-icon">F</span><span>Upcoming Filings</span></div>
                        <span class="rl-row-value">{upcoming_filings}</span>
                    </div>
                    <div class="rl-stat-row">
                        <div class="rl-row-left"><span class="rl-mini-icon">AR</span><span>Audit Readiness</span></div>
                        <span class="rl-row-value">{escape(audit_readiness_label(score))}</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_regulations_card() -> None:
    rows = []
    for category, regulations in st.session_state.regulations_by_category.items():
        for regulation in regulations[:2]:
            rows.append((category, clean_report_line(regulation)))
            if len(rows) >= 5:
                break
        if len(rows) >= 5:
            break

    if not rows:
        rows = [
            ("RBI", "RBI KYC Master Directions, 2016"),
            ("GST", "GST Act, 2017"),
            ("MCA", "Companies Act, 2013"),
            ("MSME", "MSME Udyam Registration"),
            ("FEMA", "FEMA Basic Compliance"),
        ]

    rows_html = "\n".join(
        f"""
        <div class="rl-list-row">
            <div class="rl-row-left">
                <span class="rl-mini-icon">{escape(category[:2].upper())}</span>
                <span class="rl-row-title">{escape(title[:90])}</span>
            </div>
            <span class="rl-status good">Applicable</span>
        </div>
        """
        for category, title in rows
    )
    st.markdown(
        f"""
        <div class="rl-card">
            <div class="rl-section-head">
                <h3>Top Applicable Regulations</h3>
                <span class="rl-view">View all</span>
            </div>
            {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_actions_card() -> None:
    rows = flatten_timeline_items()
    if not rows:
        rows = [
            ("Pending", "Complete KYC Policy Review"),
            ("Pending", "Update Privacy Policy"),
            ("Upcoming", "Annual IT Security Audit"),
            ("Upcoming", "Board Resolution Update"),
        ]

    rows_html = ""
    for bucket, item in rows:
        status_class = "pending" if bucket in {"Immediate", "Pending"} else "upcoming"
        due_text = {
            "Immediate": "Due now",
            "Monthly": "Due this month",
            "Quarterly": "Due this quarter",
            "Annual": "Due this year",
            "Pending": "Due soon",
            "Upcoming": "Upcoming",
        }.get(bucket, "Upcoming")
        rows_html += f"""
        <div class="rl-action-row">
            <div class="rl-row-left">
                <span class="rl-mini-icon">A</span>
                <div>
                    <div class="rl-row-title">{escape(clean_report_line(item)[:85])}</div>
                    <div class="rl-row-sub">{due_text}</div>
                </div>
            </div>
            <span class="rl-status {status_class}">{escape(bucket)}</span>
        </div>
        """

    st.markdown(
        f"""
        <div class="rl-card">
            <div class="rl-section-head">
                <h3>Required Actions</h3>
                <span class="rl-view">View all</span>
            </div>
            {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_coverage_card() -> None:
    coverage = [
        ("RBI", "Reserve Bank of India"),
        ("MCA", "Ministry of Corporate Affairs"),
        ("CBDT", "Income Tax Department"),
        ("GSTN", "Goods and Services Tax"),
        ("MeitY", "Electronics and IT"),
        ("+6 More", "Regulatory Bodies"),
    ]
    items = "\n".join(
        f"""
        <div class="rl-coverage-item">
            <span class="rl-mini-icon">{escape(name[:2])}</span>
            <div>
                <div class="rl-coverage-name">{escape(name)}</div>
                <div class="rl-coverage-sub">{escape(subtitle)}</div>
            </div>
        </div>
        """
        for name, subtitle in coverage
    )
    st.markdown(
        f"""
        <div class="rl-card" style="margin-top:1.05rem;">
            <div class="rl-section-head">
                <div class="rl-title-left">
                    <div class="rl-icon">C</div>
                    <h2>Regulatory Coverage</h2>
                </div>
            </div>
            <div class="rl-coverage-grid">{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Header
render_topbar()

is_post_check = st.session_state.risk_score is not None
page_title = "Compliance Check Results" if is_post_check else "Compliance Check"
page_description = (
    "Based on the information provided, here is your compliance overview and actionable insights."
    if is_post_check
    else "Enter your business details and get an audit-ready compliance checklist."
)
render_page_header(page_title, page_description)

render_top_metric_cards()

# Legacy header markup remains below but is hidden by CSS to avoid changing workflow state.
st.markdown(
    """
    <div class='app-card hero-card'>
        <h1 style='text-align: center; margin-bottom: 0.15rem;'>RegLens AI</h1>
        <p style='text-align: center; font-size: 1.05rem; opacity: 0.86; margin-top: 0; max-width: 860px; margin-left: auto; margin-right: auto;'>
            AI-powered regulatory compliance assistant for Indian FinTechs & MSMEs.
            Enter a strong business profile and get a regulation-aware compliance checklist with audit-ready reasoning.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.markdown("### RegLens AI")
    st.caption("Compliance workspace")
    st.markdown("---")
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
    - RBI KYC & Payment Guidelines
    - NBFC & Digital Lending Rules
    - GST & CGST Rules 2017
    - MSME Udyam Registration
    - Income Tax TDS Provisions
    - FEMA Compliance
    - Companies Act 2013
    """)
    st.markdown("---")
    default_api_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    api_url = st.text_input("Backend API URL", default_api_url)

# Main form
main_left, main_right = st.columns([0.8, 1.2], gap="large")

with main_left:
    st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
    render_business_profile_card(is_post_check)

    with st.form("business_profile_form"):
        col1, col2 = st.columns([1, 1], gap="medium")

        with col1:
            business_type = st.selectbox(
                "Business Type",
                ["Private Limited Company", "LLP", "Sole Proprietorship", "Partnership Firm", "OPC"],
                index=0,
                placeholder="Select business type",
                help="Choose the legal business entity that matches your company.",
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
                placeholder="Select industry",
                help="Select the industry category closest to your operations.",
            )

            services = st.text_area(
                "Services / Products Offered",
                value="Online payment gateway and UPI transaction processing for retail consumers.",
                placeholder="Enter services or products",
                height=68,
                help="Describe the key services or products your business offers.",
            )

        with col2:
            customer_type = st.selectbox(
                "Customer Type",
                ["Retail Consumers (B2C)", "Businesses (B2B)", "Both B2B and B2C", "Government (B2G)"],
                index=0,
                placeholder="Select customer type",
                help="Choose the main customer segment your business serves.",
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
                placeholder="Select transaction type",
                help="Select the transaction type that best represents your business model.",
            )

            revenue = st.selectbox(
                "Annual Revenue",
                [
                    "Under ₹1 Crore",
                    "₹1 Crore - ₹5 Crore",
                    "₹5 Crore - ₹25 Crore",
                    "Above ₹25 Crore",
                ],
                index=1,
                placeholder="Select annual revenue",
                help="Choose the closest annual revenue band for your business.",
            )

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        submitted = st.form_submit_button(
            "Run Compliance Check",
            use_container_width=True
        )

        st.caption("Your data is secure and used only for compliance analysis.")
with main_right:
    render_summary_card()
    reg_col, action_col = st.columns(2, gap="medium")
    with reg_col:
        render_regulations_card()
    with action_col:
        render_actions_card()

render_coverage_card()
if submitted:
    business_profile = {
        "business_type": business_type,
        "industry": industry,
        "services": services,
        "customer_type": customer_type,
        "transaction_type": transaction_type,
        "revenue": revenue
    }
    
    # Run client-side validation
    is_valid, validation_message = validate_business_profile(business_profile)
    
    if not is_valid:
        st.error(validation_message)
    else:
        with st.spinner("Analyzing regulations for your business... This may take 15-30 seconds."):
            try:
                endpoint = f"{api_url.rstrip('/')}/api/compliance-check"
                response = requests.post(endpoint, json=business_profile, timeout=120)
                
                if response.status_code == 422:
                    # Handle validation errors from backend
                    error_data = response.json()
                    st.error("**Input Validation Error**")
                    if "errors" in error_data:
                        for error in error_data.get("errors", []):
                            st.error(error)
                    else:
                        st.error(error_data.get("detail", "Invalid input provided"))
                    st.stop()
                else:
                    response.raise_for_status()
                    response_payload = response.json()
                    result = response_payload.get("result", "No result returned from backend.")
                    source_documents = parse_source_documents(response_payload.get("source_documents", []))

                    st.session_state.risk_score = parse_risk_level(result)
                    st.session_state.regulations_by_category = extract_regulations_by_category(result)
                    st.session_state.compliance_timeline = build_compliance_timeline(result)
                    st.session_state.latest_business_profile = business_profile
                    st.session_state.latest_source_documents = source_documents
                    st.session_state.latest_result_text = result
                    st.session_state.latest_report_markdown = build_markdown_report(
                        business_profile,
                        result,
                        st.session_state.risk_score,
                        st.session_state.compliance_timeline,
                        source_documents,
                    )
                    st.session_state.latest_report_pdf = build_pdf_report(
                        business_profile,
                        result,
                        st.session_state.risk_score,
                        st.session_state.compliance_timeline,
                        source_documents,
                    )
                
                st.markdown("---")
                st.markdown("## Compliance Analysis Report")
                
                # Risk Gauge Section
                st.subheader("Compliance Risk Assessment")
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

                # Compliance Timeline Section
                st.subheader("Compliance Timeline")
                if st.session_state.compliance_timeline:
                    timeline_columns = st.columns(4)
                    timeline_order = ["Immediate", "Monthly", "Quarterly", "Annual"]

                    for column, bucket in zip(timeline_columns, timeline_order):
                        with column:
                            items = st.session_state.compliance_timeline.get(bucket, [])
                            st.markdown(f"**{bucket}**")
                            if items:
                                for item in items[:6]:
                                    checkbox_key = f"timeline_{bucket}_{item[:30]}"
                                    checked = st.checkbox(
                                        item[:90] + ("..." if len(item) > 90 else ""),
                                        key=checkbox_key,
                                        value=st.session_state.compliance_checklist.get(checkbox_key, False)
                                    )
                                    st.session_state.compliance_checklist[checkbox_key] = checked
                                if len(items) > 6:
                                    st.caption(f"+ {len(items) - 6} more")
                            else:
                                st.caption("No items detected")
                else:
                    st.info("No checklist items were detected for timeline generation.")

                st.markdown("---")

                # Downloadable Reports Section
                st.subheader("Download Compliance Report")
                download_col1, download_col2 = st.columns(2)
                file_stamp = datetime.now().strftime("%Y%m%d_%H%M")

                with download_col1:
                    st.download_button(
                        "Download Markdown Report",
                        data=st.session_state.latest_report_markdown or "",
                        file_name=f"reglens_compliance_report_{file_stamp}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

                with download_col2:
                    st.download_button(
                        "Download PDF Report",
                        data=st.session_state.latest_report_pdf or b"",
                        file_name=f"reglens_compliance_report_{file_stamp}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

                st.markdown("---")
                
                # Categorized Regulations Section
                if st.session_state.regulations_by_category:
                    st.subheader("Compliance Checklist by Category")
                    
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
                
                # Source Documents Section
                st.subheader("Source Documents")
                render_source_documents(st.session_state.latest_source_documents)

                st.markdown("---")
                
                # Full Report
                st.subheader("Detailed Compliance Analysis")
                st.markdown(result)
                
                st.markdown("---")
                st.success("Analysis complete. This report is based on official government documents only.")
                st.warning("This tool provides AI-assisted guidance only. Consult a qualified compliance professional for legal decisions.")

            except requests.exceptions.Timeout:
                st.error("**Request Timeout**: The server took too long to respond. Please try again.")
            except requests.exceptions.RequestException as re:
                st.error(f"**Backend Error**: {str(re)}")
            except Exception as e:
                st.error(f"**Error**: {str(e)}")

# Display saved analysis if it exists
if st.session_state.risk_score is not None:
    st.markdown("---")
    st.subheader("Your Latest Compliance Dashboard")
    
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

render_audit_history(api_url)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
RegLens AI - Powered by LLaMA 3.3 70B + RAG on Official Government Documents
</div>
""", unsafe_allow_html=True)

