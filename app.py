# app.py
# Streamlit web version of the PubMed + AI summarizer.
# Supports two summarization engines: free NVIDIA Nemotron 3 Ultra,
# or paid Claude.

import os
import json
import streamlit as st
from dotenv import load_dotenv
from summarize import (
    search_pubmed,
    fetch_details,
    clean_abstract_text,
    summarize_with_claude,
    summarize_with_nemotron,
    save_summary_as_pdf,
    build_vancouver_citations,
    build_paper_badges,
    get_paper_titles,
    client,
    nvidia_client,
)
from db import (
    init_db,
    create_user,
    verify_user,
    save_search,
    get_user_history,
    save_paper,
    unsave_paper,
    get_saved_papers,
)

init_db()
load_dotenv()

st.set_page_config(page_title="Unipharma | PubMed AI Summarizer", page_icon="🔬")

# --- Custom theme styling: "Clinic Light" design system ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=Karla:wght@400;500;600;700&display=swap');

:root {
  --bg:        #F6F7F4;
  --card:      #FFFFFF;
  --border:    #E2E6DE;
  --ink:       #14262B;
  --muted:     #5F6F72;
  --primary:   #0E5A5E;
  --primary-d: #0A4448;
  --sage:      #C7D8C6;
  --sage-soft: #EDF2EC;
  --radius:    14px;
  --pill:      999px;
  --shadow-sm: 0 1px 2px rgba(20,38,43,.04), 0 2px 8px rgba(20,38,43,.05);
  --shadow-md: 0 2px 4px rgba(20,38,43,.05), 0 10px 24px -8px rgba(20,38,43,.12);
  --shadow-lift: 0 6px 18px -6px rgba(14,90,94,.38);
}

.stApp {
  background: var(--bg);
  color: var(--ink);
  font-family: 'Karla', system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.6;
}
.stApp .block-container { padding-top: 2.75rem; max-width: 1080px; }

.stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp [data-testid="stMarkdownContainer"] h1,
.stApp [data-testid="stMarkdownContainer"] h2,
.stApp [data-testid="stMarkdownContainer"] h3 {
  font-family: 'Instrument Sans', system-ui, sans-serif;
  color: var(--ink);
  font-weight: 600;
  letter-spacing: -.02em;
  line-height: 1.18;
  text-wrap: balance;
}
.stApp h1 { font-size: clamp(2rem, 4.4vw, 3.15rem); }
.stApp h2 { font-size: clamp(1.5rem, 2.6vw, 2rem); margin-top: .25rem; }
.stApp h3 { font-size: 1.2rem; }
.stApp p, .stApp li, .stApp label { color: var(--ink); }
.stApp a { color: var(--primary); text-underline-offset: 3px; }
.stApp hr { border-color: var(--border); }

.hero {
  padding: 2.5rem 0 2rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2.25rem;
  text-align: center;
}
.badge-pill {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  background: var(--sage-soft);
  border: 1px solid var(--sage);
  color: var(--primary-d);
  font-family: 'Instrument Sans', sans-serif;
  font-size: .69rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .14em;
  padding: .38rem .85rem;
  border-radius: var(--pill);
  margin-bottom: 1.1rem;
}
.badge-pill::before {
  content: "";
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--primary);
}
.hero-title { margin: 0 0 .75rem; }
.hero-sub {
  font-size: 1.09rem;
  color: var(--muted);
  max-width: 62ch;
  margin: 0 auto;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card);
  border-radius: var(--radius);
}
[data-testid="stVerticalBlockBorderWrapper"][style*="border"],
div[data-testid="stVerticalBlockBorderWrapper"] > div[style*="border"] {
  border-color: var(--border) !important;
  box-shadow: var(--shadow-sm);
}
.stApp [data-testid="stExpander"] details,
.stApp [data-testid="stForm"] {
  background: var(--card);
  border: 1px solid var(--border) !important;
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}
.stApp [data-testid="stExpander"] summary { font-weight: 600; color: var(--ink); }

.stButton button,
.stFormSubmitButton button,
.stDownloadButton button,
.stLinkButton a {
  font-family: 'Instrument Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: .94rem !important;
  border-radius: var(--pill) !important;
  padding: .58rem 1.5rem !important;
  border: 1px solid var(--primary) !important;
  background: var(--primary) !important;
  color: #FFFFFF !important;
  box-shadow: 0 1px 2px rgba(20,38,43,.08);
  transition: transform .16s ease, box-shadow .16s ease, background .16s ease;
}
.stButton button:hover,
.stFormSubmitButton button:hover,
.stDownloadButton button:hover,
.stLinkButton a:hover {
  background: var(--primary-d) !important;
  transform: translateY(-2px);
  box-shadow: var(--shadow-lift);
}
.stButton button:active,
.stFormSubmitButton button:active { transform: translateY(0); }
.stButton button:focus-visible,
.stTextInput input:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea,
div[data-baseweb="select"] > div {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--ink) !important;
  font-family: 'Karla', sans-serif !important;
  font-size: .95rem !important;
  box-shadow: none !important;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus,
div[data-baseweb="select"] > div:focus-within {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(14,90,94,.12) !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder { color: #9AA7A9 !important; }

.stApp label,
.stApp [data-testid="stWidgetLabel"] p {
  font-family: 'Instrument Sans', sans-serif !important;
  font-size: .82rem !important;
  font-weight: 500 !important;
  color: var(--muted) !important;
  letter-spacing: .01em;
}

div[data-baseweb="radio"] label,
div[data-baseweb="checkbox"] label {
  font-family: 'Karla', sans-serif !important;
  font-size: .95rem !important;
  color: var(--ink) !important;
  padding: .18rem 0;
  cursor: pointer;
}
div[data-baseweb="radio"] label:hover { color: var(--primary) !important; }
.stSlider [data-baseweb="slider"] [role="slider"] { border-color: var(--primary) !important; }

.stTabs [data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] {
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 500;
  color: var(--muted);
  border-radius: 8px 8px 0 0;
}
.stTabs [aria-selected="true"] { color: var(--primary) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--primary) !important; }

.step-label {
  font-family: 'Instrument Sans', sans-serif;
  font-size: .69rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .13em;
  color: var(--primary);
  margin: .4rem 0 .6rem 0;
}
.step-divider {
  height: 1px;
  background: var(--border);
  margin: 1.4rem 0 1rem 0;
}

.chip-row { display: flex; flex-wrap: wrap; gap: .45rem; margin: .6rem 0; }
.chip {
  display: inline-flex; align-items: center; gap: .35rem;
  background: var(--sage-soft);
  border: 1px solid var(--sage);
  color: var(--primary-d);
  font-family: 'Karla', sans-serif;
  font-size: .78rem; font-weight: 600;
  padding: .3rem .75rem;
  border-radius: var(--pill);
  white-space: nowrap;
}
.chip--neutral { background: #F1F3EF; border-color: var(--border); color: var(--muted); }

.stat-row {
  display: flex;
  flex-wrap: wrap;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  margin: 1.75rem 0;
}
.stat {
  flex: 1 1 160px;
  padding: 1.35rem 1.4rem;
  border-right: 1px solid var(--border);
  text-align: center;
}
.stat:last-child { border-right: 0; }
.stat-value {
  font-family: 'Instrument Sans', sans-serif;
  font-size: 1.95rem; font-weight: 600;
  letter-spacing: -.025em;
  color: var(--primary);
  line-height: 1.05;
}
.stat-label {
  font-size: .72rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: .12em;
  color: var(--muted);
  margin-top: .4rem;
}

.top-nav {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.7rem 1.2rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--pill);
  margin-bottom: 1.8rem;
  box-shadow: var(--shadow-sm);
}
.top-nav .brand {
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 700; letter-spacing: 0.12em; color: var(--ink); font-size: 0.85rem;
}
.top-nav .user-pill {
  background: var(--primary); color: #fff;
  padding: 0.4rem 1rem; border-radius: var(--pill);
  font-size: 0.85rem; font-weight: 600;
}

.stApp [data-testid="stAlert"] {
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}
.stApp [data-testid="stSidebar"] {
  background: #FFFFFF;
  border-right: 1px solid var(--border);
}
</style>
""", unsafe_allow_html=True)

# --- Real login / signup ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None

if st.session_state.user_id is None:
    st.markdown("""
    <div class="hero">
        <span class="badge-pill">⚡ Unipharma</span>
        <h1 class="hero-title">🔬 PubMed AI Summarizer</h1>
        <p class="hero-sub">Evidence-ready research summaries for pharmacy professionals — powered by free and premium AI.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Log In", "Sign Up"])

    with tab1:
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log In"):
            user_id, error_msg = verify_user(login_username, login_password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = login_username
                st.rerun()
            elif error_msg:
                st.error(error_msg)
            else:
                st.error("Incorrect username or password.")
    with tab2:
        signup_username = st.text_input("Choose a username", key="signup_username")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Choose a password", type="password", key="signup_password")
        if st.button("Sign Up"):
            if not signup_username.strip() or not signup_email.strip() or not signup_password.strip():
                st.warning("Please fill in all fields.")
            elif len(signup_password) < 8:
                st.warning("Password should be at least 8 characters.")
            else:
                success, error_msg = create_user(signup_username, signup_email, signup_password)
                if success:
                    st.success("Account created! Please log in using the Log In tab.")
                else:
                    st.error(error_msg)

    st.stop()

# --- Top navigation bar ---
st.markdown(f"""
<div class="top-nav">
    <div style="display:flex; align-items:center; gap:0.6rem;">
        <span style="font-size:1.2rem;">⚡</span>
        <span class="brand">UNIPHARMA</span>
    </div>
    <div style="display:flex; align-items:center; gap:0.8rem;">
        <span style="color:var(--muted); font-size:0.85rem;">PubMed AI Summarizer</span>
        <div class="user-pill">👤 {st.session_state.username}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Stats bar ---
stats_history_count = len(get_user_history(st.session_state.user_id))
stats_saved_count = len(get_saved_papers(st.session_state.user_id))

st.markdown(f"""
<div class="stat-row">
    <div class="stat">
        <div class="stat-value">{stats_history_count}</div>
        <div class="stat-label">Searches Run</div>
    </div>
    <div class="stat">
        <div class="stat-value">{stats_saved_count}</div>
        <div class="stat-label">Papers Saved</div>
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

    st.markdown("### 🔖 Saved Papers")
    saved = get_saved_papers(st.session_state.user_id)
    if not saved:
        st.caption("Papers you save will appear here.")
    else:
        for pmid, title, journal, year, saved_at in saved:
            with st.expander(title[:60] + ("..." if len(title) > 60 else "")):
                st.caption(f"{journal} · {year}")
                st.markdown(f"[View on PubMed](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
                if st.button("Remove", key=f"unsave_{pmid}"):
                    unsave_paper(st.session_state.user_id, pmid)
                    st.rerun()

    st.markdown("---")
    if st.button("Log Out"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()

st.markdown("""
<div class="hero">
    <span class="badge-pill">🔬 Clinical Research, Simplified</span>
    <h1 class="hero-title">PubMed AI Summarizer</h1>
    <p class="hero-sub">Turning the latest PubMed research into clear, evidence-ready insights for pharmacy professionals.</p>
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<p class="step-label">STEP 1 · WHAT ARE YOU RESEARCHING</p>', unsafe_allow_html=True)
    topic = st.text_input("💊 Medical topic or drug name", label_visibility="visible")

    st.markdown('<div class="step-divider"></div>', unsafe_allow_html=True)
    st.markdown('<p class="step-label">STEP 2 · CUSTOMIZE YOUR SEARCH</p>', unsafe_allow_html=True)

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

    st.markdown('<div class="step-divider"></div>', unsafe_allow_html=True)
    st.markdown('<p class="step-label">STEP 3 · CHOOSE YOUR AI</p>', unsafe_allow_html=True)

    # --- Model choice: free Nemotron vs paid Claude ---
    model_choice = st.radio(
        "Summarize with",
        options=["🆓 Free (Nemotron 3 Ultra)", "💎 Premium (Claude)"],
        horizontal=True,
        label_visibility="collapsed",
    )

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

        using_nemotron = model_choice.startswith("🆓")
        model_label = "Nemotron 3 Ultra" if using_nemotron else "Claude"

        with st.spinner(f"Asking {model_label} to summarize... (this takes a few seconds)"):
            try:
                if using_nemotron:
                    summary = summarize_with_nemotron(topic, papers_text, num_papers)
                else:
                    summary = summarize_with_claude(topic, papers_text, num_papers)
            except Exception as e:
                st.error(f"{model_label} API error: {e}")
                if using_nemotron:
                    st.info("Check that NVIDIA_API_KEY is set correctly in your .env file.")
                else:
                    st.info("This is often a billing issue — check console.anthropic.com > Billing")
                st.stop()

        st.markdown(f"### Summary — *{model_label}*")
        st.markdown(summary)

        # --- Copy to clipboard button ---
        summary_js_safe = json.dumps(summary)
        st.markdown(f"""
        <button onclick="navigator.clipboard.writeText({summary_js_safe})"
                style="background: var(--primary); color: white; border: none;
                       border-radius: 999px; padding: 0.5rem 1.2rem; font-weight: 600;
                       cursor: pointer; margin-bottom: 1rem; font-family: 'Instrument Sans', sans-serif;">
            📋 Copy Summary
        </button>
        """, unsafe_allow_html=True)

        # Save this search into the user's permanent history
        save_search(st.session_state.user_id, topic, num_papers, summary)

        st.markdown("### 🏷️ Evidence Overview")
        badges = build_paper_badges(id_list)
        chip_html = '<div class="chip-row">'
        for b in badges:
            peer_badge = "✅ Peer-Reviewed" if b["peer_reviewed"] else "⚠️ Preprint"
            chip_class = "chip" if b["peer_reviewed"] else "chip chip--neutral"
            chip_html += f'<span class="{chip_class}"><b>{b["evidence_type"]}</b> · {b["journal"]} · {b["year"]} · {peer_badge}</span>'
        chip_html += '</div>'
        st.markdown(chip_html, unsafe_allow_html=True)

        st.markdown("### 🔗 View Original Papers on PubMed")
        titles = get_paper_titles(id_list)
        badges_lookup = {b["pmid"]: b for b in badges}
        for pid in id_list:
            paper_title = titles.get(pid, "Untitled")
            journal = badges_lookup.get(pid, {}).get("journal", "")
            year = badges_lookup.get(pid, {}).get("year", "")
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.markdown(f"- [{paper_title}](https://pubmed.ncbi.nlm.nih.gov/{pid}/) — PMID {pid}")
            with col_b:
                if st.button("🔖 Save", key=f"save_{pid}"):
                    save_paper(st.session_state.user_id, pid, paper_title, journal, year)
                    st.success("Saved!")

        st.markdown("### 📖 References (Vancouver Style)")
        citations = build_vancouver_citations(id_list)
        for i, citation in enumerate(citations, start=1):
            st.markdown(f"{i}. {citation}")

        # --- PDF download button ---
        try:
            pdf_path = save_summary_as_pdf(topic, summary)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📄 Download as PDF",
                    data=f,
                    file_name=pdf_path.split("/")[-1],
                    mime="application/pdf",
                )
        except Exception as e:
            st.warning(f"PDF generation failed, but your summary above is still available. ({e})")

        # --- Follow-up question ---
        st.markdown("### 💬 Ask a follow-up question")
        followup = st.text_input("e.g. 'Which of these had the largest sample size?'", key=f"followup_{topic}")
        if st.button("Ask", key=f"ask_{topic}"):
            if followup.strip():
                with st.spinner("Thinking..."):
                    followup_prompt = f"""Based on this earlier summary of PubMed research on "{topic}":

{summary}

Answer this follow-up question concisely: {followup}"""
                    if using_nemotron:
                        followup_completion = nvidia_client.chat.completions.create(
                            model="nvidia/nemotron-3-ultra-550b-a55b",
                            messages=[{"role": "user", "content": followup_prompt}],
                            max_tokens=500,
                            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                        )
                        st.markdown(followup_completion.choices[0].message.content)
                    else:
                        followup_response = client.messages.create(
                            model="claude-sonnet-4-5",
                            max_tokens=500,
                            messages=[{"role": "user", "content": followup_prompt}]
                        )
                        st.markdown(followup_response.content[0].text)