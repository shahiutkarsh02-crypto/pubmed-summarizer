# app.py
# Streamlit web version of the PubMed + Claude summarizer.

import os
import json
import streamlit as st
from dotenv import load_dotenv
from summarize import (
    search_pubmed,
    fetch_details,
    clean_abstract_text,
    summarize_with_claude,
    save_summary_as_pdf,
    build_vancouver_citations,
    build_paper_badges,
    client,
)
from db import init_db, create_user, verify_user, save_search, get_user_history

init_db()
load_dotenv()

st.set_page_config(page_title="Unipharma | PubMed AI Summarizer", page_icon="🔬")

# --- Custom theme styling ---
st.markdown("""
<style>
    * {
        cursor: default;
    }
    button, a, .stButton button, .stDownloadButton button, [role="button"] {
        cursor: pointer !important;
    }

    .stApp {
        background: linear-gradient(180deg, #17171d 0%, #202028 50%, #17171d 100%);
        color: #e8e8ec;
    }

    h1, h2, h3 {
        color: #f5f5f7;
        font-weight: 600;
    }

    .stTextInput input, .stTextInput > div > div {
        background-color: #24242e !important;
        color: #e8e8ec !important;
        border: 1px solid #34343f !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }
    .stTextInput input:focus {
        border: 1px solid #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }

    .stButton button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.15s ease;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
    }
    .stButton button:active {
        transform: translateY(1px) scale(0.97);
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
    }

    .stDownloadButton button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
    }
    .stDownloadButton button:active {
        transform: translateY(1px) scale(0.97);
    }

    [data-testid="stMarkdownContainer"] {
        animation: fadeIn 0.6s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stAlert {
        border-radius: 8px !important;
        animation: fadeIn 0.4s ease-in;
    }

    div[data-baseweb="slider"] {
        padding-top: 10px;
    }

    .orb {
        position: fixed;
        border-radius: 50%;
        filter: blur(60px);
        opacity: 0.3;
        z-index: 0;
        pointer-events: none;
        animation: float 14s ease-in-out infinite;
    }
    .orb1 {
        width: 350px; height: 350px;
        background: radial-gradient(circle, #6366f1, transparent 70%);
        top: -100px; left: -80px;
        animation-delay: 0s;
    }
    .orb2 {
        width: 280px; height: 280px;
        background: radial-gradient(circle, #a855f7, transparent 70%);
        bottom: -60px; right: -60px;
        animation-delay: 3s;
    }
    .orb3 {
        width: 220px; height: 220px;
        background: radial-gradient(circle, #10b981, transparent 70%);
        top: 40%; right: 10%;
        animation-delay: 6s;
    }

    @keyframes float {
        0%, 100% { transform: translate(0, 0) scale(1); }
        33% { transform: translate(25px, -35px) scale(1.1); }
        66% { transform: translate(-20px, 25px) scale(0.92); }
    }

    .gradient-text {
        background: linear-gradient(90deg, #6366f1, #a855f7, #10b981, #6366f1);
        background-size: 300% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: shimmer 6s linear infinite;
    }

    @keyframes shimmer {
        0% { background-position: 0% center; }
        100% { background-position: 300% center; }
    }

    .block-container {
        position: relative;
        z-index: 1;
    }
</style>

<div class="orb orb1"></div>
<div class="orb orb2"></div>
<div class="orb orb3"></div>
""", unsafe_allow_html=True)

# --- Real login / signup ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None

if st.session_state.user_id is None:
    st.markdown("""
    <div style="text-align:center; padding: 2rem 0 1rem 0;">
        <p style="color:#a78bfa; font-size:0.95rem; letter-spacing:0.25em;
                  text-transform:uppercase; margin-bottom:0.5rem; font-weight:800;">
            ⚡ UNIPHARMA
        </p>
        <h1 class="gradient-text" style="font-size:2.4rem;">
            🔬 PubMed AI Summarizer
        </h1>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Log In", "Sign Up"])

    with tab1:
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log In"):
            user_id = verify_user(login_username, login_password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = login_username
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    with tab2:
        signup_username = st.text_input("Choose a username", key="signup_username")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Choose a password", type="password", key="signup_password")
        if st.button("Sign Up"):
            if not signup_username.strip() or not signup_email.strip() or not signup_password.strip():
                st.warning("Please fill in all fields.")
            elif len(signup_password) < 6:
                st.warning("Password should be at least 6 characters.")
            else:
                success, error_msg = create_user(signup_username, signup_email, signup_password)
                if success:
                    st.success("Account created! Please log in using the Log In tab.")
                else:
                    st.error(error_msg)

    st.stop()

# --- Top navigation bar ---
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center;
            padding:0.7rem 1.2rem; background:#1c1c24;
            border-radius:999px; margin-bottom:1.8rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.3);">
    <div style="display:flex; align-items:center; gap:0.6rem;">
        <span style="font-size:1.2rem;">⚡</span>
        <span style="font-weight:800; letter-spacing:0.12em; color:#f5f5f7; font-size:0.85rem;">
            UNIPHARMA
        </span>
    </div>
    <div style="display:flex; align-items:center; gap:0.8rem;">
        <span style="color:#6b6b78; font-size:0.85rem;">PubMed AI Summarizer</span>
        <div style="background:linear-gradient(135deg, #6366f1, #8b5cf6); color:white;
                    padding:0.4rem 1rem; border-radius:999px; font-size:0.85rem; font-weight:600;">
            👤 {st.session_state.username}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Sidebar: search history ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")

    st.markdown("### 🕘 Search History")
    history = get_user_history(st.session_state.user_id)
    if not history:
        st.caption("Your past searches will appear here.")
    else:
        for topic_h, num_papers_h, summary_h, created_at_h in history:
            with st.expander(f"{topic_h} ({num_papers_h} papers)"):
                st.caption(created_at_h)
                st.markdown(summary_h)

    st.markdown("---")
    if st.button("Log Out"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()

st.markdown("""
<div style="text-align:center; padding: 1rem 0 1rem 0;">
    <h1 class="gradient-text" style="font-size:2.6rem; margin-bottom:0.6rem;">
        🔬 PubMed AI Summarizer
    </h1>
    <p style="color:#9999a8; font-size:1.05rem; max-width:480px; margin:0 auto;
              line-height:1.6;">
        Turning the latest PubMed research into clear,<br>evidence-ready insights for pharmacy professionals.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: rgba(36,36,46,0.6); border: 1px solid #34343f;
            border-radius: 14px; padding: 1.5rem 1.5rem 0.5rem 1.5rem;
            margin-bottom: 1.5rem; backdrop-filter: blur(10px);">
""", unsafe_allow_html=True)

topic = st.text_input("💊 Medical topic or drug name")

col1, col2 = st.columns(2)
with col1:
    num_papers = st.slider("📚 How many recent papers?", min_value=1, max_value=10, value=5)
with col2:
    date_filter = st.selectbox(
        "📅 Publication date range",
        options=["Any time", "Last 1 year", "Last 2 years", "Last 5 years"],
    )

sort_choice = st.selectbox(
    "🔀 Sort results by",
    options=["Most recent", "Most relevant", "First author", "Journal"],
)

sort_map = {
    "Most recent": "date",
    "Most relevant": "relevance",
    "First author": "author",
    "Journal": "journal",
}
sort_by = sort_map[sort_choice]

st.markdown("</div>", unsafe_allow_html=True)

years_back_map = {
    "Any time": None,
    "Last 1 year": 1,
    "Last 2 years": 2,
    "Last 5 years": 5,
}
years_back = years_back_map[date_filter]


if st.button("Search and Summarize"):
    if not topic.strip():
        st.warning("Please enter a topic first.")
    else:
        with st.spinner(f"Searching PubMed for {num_papers} papers on '{topic}'..."):
            try:
                id_list = search_pubmed(topic, max_results=num_papers, years_back=years_back, sort_by=sort_by)
            except Exception as e:
                st.error(f"Could not reach PubMed: {e}")
                st.stop()

        if not id_list:
            st.warning("No results found. Try a different search term.")
            st.stop()

        st.success(f"Found {len(id_list)} paper(s).")

        with st.spinner("Fetching and cleaning paper details..."):
            papers_text = fetch_details(id_list)
            papers_text = clean_abstract_text(papers_text)

        with st.spinner("Asking Claude to summarize... (this takes a few seconds)"):
            try:
                summary = summarize_with_claude(topic, papers_text, num_papers)
            except Exception as e:
                st.error(f"Claude API error: {e}")
                st.info("This is often a billing issue — check console.anthropic.com > Billing")
                st.stop()

        st.markdown("### Summary")
        st.markdown(summary)

        # --- Copy to clipboard button ---
        summary_js_safe = json.dumps(summary)
        st.markdown(f"""
        <button onclick="navigator.clipboard.writeText({summary_js_safe})"
                style="background: linear-gradient(135deg, #6366f1, #8b5cf6);
                       color: white; border: none; border-radius: 8px;
                       padding: 0.5rem 1.2rem; font-weight: 600; cursor: pointer;
                       margin-bottom: 1rem;">
            📋 Copy Summary
        </button>
        """, unsafe_allow_html=True)

        # Save this search into the user's permanent history
        save_search(st.session_state.user_id, topic, num_papers, summary)

        st.markdown("### 🏷️ Evidence Overview")
        badges = build_paper_badges(id_list)
        for b in badges:
            peer_badge = "✅ Peer-Reviewed" if b["peer_reviewed"] else "⚠️ Preprint"
            st.markdown(
                f"""<div style="display:inline-block; background:#24242e; border:1px solid #34343f;
                border-radius:20px; padding:0.4rem 1rem; margin:0.2rem 0.3rem 0.2rem 0;
                font-size:0.85rem;">
                <b>{b['evidence_type']}</b> · {b['journal']} · {b['year']} · {peer_badge}
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("### 🔗 View Original Papers on PubMed")
        for pid in id_list:
            st.markdown(f"- [PMID {pid}](https://pubmed.ncbi.nlm.nih.gov/{pid}/)")

        st.markdown("### 📖 References (Vancouver Style)")
        citations = build_vancouver_citations(id_list)
        for i, citation in enumerate(citations, start=1):
            st.markdown(f"{i}. {citation}")

        # --- PDF download button ---
        pdf_path = save_summary_as_pdf(topic, summary)
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📄 Download as PDF",
                data=f,
                file_name=pdf_path.split("/")[-1],
                mime="application/pdf",
            )

        # --- Follow-up question ---
        st.markdown("### 💬 Ask a follow-up question")
        followup = st.text_input("e.g. 'Which of these had the largest sample size?'", key=f"followup_{topic}")
        if st.button("Ask Claude", key=f"ask_{topic}"):
            if followup.strip():
                with st.spinner("Thinking..."):
                    followup_prompt = f"""Based on this earlier summary of PubMed research on "{topic}":

{summary}

Answer this follow-up question concisely: {followup}"""
                    followup_response = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=500,
                        messages=[{"role": "user", "content": followup_prompt}]
                    )
                    st.markdown(followup_response.content[0].text)