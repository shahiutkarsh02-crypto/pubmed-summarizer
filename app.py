# app.py
# Streamlit web version of the PubMed + Claude summarizer.

import os
import streamlit as st
from dotenv import load_dotenv
from summarize import (
    search_pubmed,
    fetch_details,
    clean_abstract_text,
    summarize_with_claude,
    save_summary_as_pdf,
    build_vancouver_citations,
    client,
)

load_dotenv()
APP_PASSWORD = os.getenv("APP_PASSWORD")

st.set_page_config(page_title="PubMed AI Summarizer", page_icon="🔬")

# --- Custom dark theme styling ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #12121a 50%, #0a0a0f 100%);
        color: #e8e8ec;
    }

    h1, h2, h3 {
        color: #f5f5f7;
        font-weight: 600;
    }

    .stTextInput input, .stTextInput > div > div {
        background-color: #1a1a24 !important;
        color: #e8e8ec !important;
        border: 1px solid #2a2a38 !important;
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
        transition: all 0.25s ease;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
    }

    .stDownloadButton button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.25s ease;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
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
        opacity: 0.35;
        z-index: 0;
        pointer-events: none;
        animation: float 12s ease-in-out infinite;
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
        33% { transform: translate(20px, -30px) scale(1.08); }
        66% { transform: translate(-15px, 20px) scale(0.95); }
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

# --- Simple password gate ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 PubMed AI Summarizer")
    entered_password = st.text_input("Enter password to continue", type="password")
    if st.button("Enter"):
        if entered_password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()   

# --- Session search history ---
if "search_history" not in st.session_state:
    st.session_state.search_history = []

with st.sidebar:
    st.markdown("### 🕘 Search History")
    if not st.session_state.search_history:
        st.caption("Your past searches this session will appear here.")
    else:
        for i, entry in enumerate(reversed(st.session_state.search_history)):
            with st.expander(f"{entry['topic']} ({entry['num_papers']} papers)"):
                st.markdown(entry['summary'])

st.markdown("""
<div style="text-align:center; padding: 2rem 0 1rem 0;">
    <h1 style="font-size:2.8rem; margin-bottom:0.2rem;
               background: linear-gradient(135deg, #6366f1, #a855f7, #10b981);
               -webkit-background-clip: text;
               -webkit-text-fill-color: transparent;
               background-clip: text;">
        🔬 PubMed AI Summarizer
    </h1>
    <p style="color:#9999a8; font-size:1.05rem; max-width:520px; margin:0 auto;">
        Turn recent PubMed research into clear, structured, pharmacy-ready summaries — in seconds.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: rgba(26,26,36,0.6); border: 1px solid #2a2a38;
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
        import json
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

        # Save this search into session history
        st.session_state.search_history.append({
            "topic": topic,
            "num_papers": num_papers,
            "summary": summary,
        })

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