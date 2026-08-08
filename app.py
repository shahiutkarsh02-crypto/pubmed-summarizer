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
)

load_dotenv()
APP_PASSWORD = os.getenv("APP_PASSWORD")

st.set_page_config(page_title="PubMed AI Summarizer", page_icon="🔬")

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

st.title("🔬 PubMed AI Summarizer")
st.write(
    "Enter a medical topic or drug name to get an AI-generated summary "
    "of the most recent PubMed research."
)

topic = st.text_input("Medical topic or drug name")
num_papers = st.slider("How many recent papers?", min_value=1, max_value=10, value=5)

if st.button("Search and Summarize"):
    if not topic.strip():
        st.warning("Please enter a topic first.")
    else:
        with st.spinner(f"Searching PubMed for {num_papers} papers on '{topic}'..."):
            try:
                id_list = search_pubmed(topic, max_results=num_papers)
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