# summarize.py
# This script searches PubMed, then asks Claude (Anthropic AI) to
# produce a structured summary of the results.

import os
import re
import requests
from dotenv import load_dotenv
import anthropic

# Load the secret key from our .env file into memory
load_dotenv()

# Create a "client" - this is our connection to Claude's API
client = anthropic.Anthropic()  # it automatically reads ANTHROPIC_API_KEY

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def search_pubmed(topic, max_results=5, years_back=None, sort_by="date"):
    """
    Ask PubMed for the IDs of the most recent papers on 'topic'.
    If years_back is given (e.g. 2), only papers published in the
    last N years are included. sort_by controls result ordering
    (PubMed values: "date", "relevance", "author", "journal").
    """
    search_url = BASE_URL + "esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": topic,
        "retmax": max_results,
        "sort": sort_by,
        "retmode": "json"
    }

    if years_back:
        import datetime
        end_date = datetime.date.today()
        start_date = end_date.replace(year=end_date.year - years_back)
        params["datetype"] = "pdat"  # filter by publication date
        params["mindate"] = start_date.strftime("%Y/%m/%d")
        params["maxdate"] = end_date.strftime("%Y/%m/%d")

    response = requests.get(search_url, params=params)
    data = response.json()
    return data["esearchresult"]["idlist"]


def fetch_details(id_list):
    """Given PubMed IDs, fetch the title/abstract text for each paper."""
    fetch_url = BASE_URL + "efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "rettype": "abstract",
        "retmode": "text"
    }
    response = requests.get(fetch_url, params=params)
    return response.text
def get_paper_titles(id_list):
    """Fetches just the titles for a list of PubMed IDs, as a {pmid: title} dict."""
    fetch_url = BASE_URL + "esummary.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "json"
    }
    response = requests.get(fetch_url, params=params)
    data = response.json()

    titles = {}
    for pid in id_list:
        try:
            titles[pid] = data["result"][pid].get("title", "Untitled")
        except KeyError:
            titles[pid] = "Untitled"
    return titles


def build_paper_badges(id_list):
    """
    Fetches publication metadata (journal, year, publication type) for
    each paper to build small trust/credibility badges - evidence type,
    journal, year, and whether it's peer-reviewed or a preprint.
    """
    fetch_url = BASE_URL + "esummary.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "json"
    }
    response = requests.get(fetch_url, params=params)
    data = response.json()

    badges = []
    preprint_servers = ["biorxiv", "medrxiv", "preprints.org", "ssrn"]

    for pid in id_list:
        try:
            item = data["result"][pid]
            journal = item.get("source", "Unknown journal")
            pub_date = item.get("pubdate", "")
            year = pub_date.split(" ")[0] if pub_date else "Unknown year"
            pub_types = item.get("pubtype", [])

            # Pick the most informative evidence type PubMed gives us
            evidence_type = "Journal Article"
            priority = ["Randomized Controlled Trial", "Meta-Analysis",
                        "Systematic Review", "Review", "Case Reports",
                        "Clinical Trial", "Observational Study"]
            for p in priority:
                if p in pub_types:
                    evidence_type = p
                    break

            is_preprint = any(server in journal.lower() for server in preprint_servers)

            badges.append({
                "pmid": pid,
                "journal": journal,
                "year": year,
                "evidence_type": evidence_type,
                "peer_reviewed": not is_preprint,
            })
        except KeyError:
            badges.append({
                "pmid": pid,
                "journal": "Unknown",
                "year": "Unknown",
                "evidence_type": "Unknown",
                "peer_reviewed": True,
            })

    return badges


def build_vancouver_citations(id_list):
    """
    Fetches basic citation info (authors, title, journal, year) for
    each paper and formats them as Vancouver-style references —
    the citation style most commonly used in medical/pharmacy writing.
    """
    fetch_url = BASE_URL + "esummary.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "json"
    }
    response = requests.get(fetch_url, params=params)
    data = response.json()

    citations = []
    for pid in id_list:
        try:
            item = data["result"][pid]
            authors_list = item.get("authors", [])
            author_names = ", ".join(a["name"] for a in authors_list[:3])
            if len(authors_list) > 3:
                author_names += ", et al"

            title = item.get("title", "").rstrip(".")
            journal = item.get("source", "")
            pub_date = item.get("pubdate", "")
            year = pub_date.split(" ")[0] if pub_date else ""

            citation = f"{author_names}. {title}. {journal}. {year}. PMID: {pid}."
            citations.append(citation)
        except KeyError:
            citations.append(f"[Citation unavailable for PMID {pid}]")

    return citations


def clean_abstract_text(raw_text):
    """
    Removes clutter from PubMed's raw text - author affiliation lists,
    conflict-of-interest statements, copyright notices, and DOI/PMID
    lines - keeping mainly the title, journal info, and abstract itself.
    """
    lines = raw_text.split("\n")
    cleaned_lines = []
    skip_block = False

    for line in lines:
        stripped = line.strip()

        if (stripped.startswith("Author information:") or
                stripped.startswith("Conflict of interest statement:") or
                stripped.startswith("Declaration of") or
                stripped.startswith("Copyright") or
                stripped.startswith("©")):
            skip_block = True
            continue

        if skip_block and stripped == "":
            skip_block = False
            continue

        if skip_block:
            continue

        if stripped.startswith("DOI:") or stripped.startswith("PMID:"):
            continue

        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text.strip()


def summarize_with_claude(topic, papers_text, num_papers):
    """
    Send the raw PubMed text to Claude and ask for a clean,
    structured summary.
    """
    prompt = f"""You are a clinical pharmacy research assistant helping a pharmacy
professional quickly evaluate recent research. Below are the {num_papers} most
recent PubMed abstracts on the topic "{topic}".

For EACH paper, produce a structured summary with these EXACT headings, in this order:

- **Title** (short version)
- **Evidence Level** (e.g. RCT, retrospective cohort, case report, systematic review, animal/in-vitro study — state clearly which)
- **Study Size & Population** (number of patients/subjects, key population details like age range, comorbidities, if mentioned)
- **Key Findings** (2-3 bullet points, plain language, include actual numbers/statistics where available)
- **Adverse Events / Safety Signals** (mention any side effects, safety concerns, or drug interactions noted — write "None reported" if the abstract doesn't mention any)
- **Study Limitations** (note anything that weakens confidence: small sample size, no control group, industry funding, single-center, short follow-up — write "Not stated" if the abstract gives no info on this)
- **Relevance to "{topic}"** (1 sentence, practical takeaway for a pharmacy professional)

If a paper has no usable abstract text, skip it and note "Abstract not available" instead of guessing.

Here are the raw abstracts:

{papers_text}
"""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def save_summary(topic, summary):
    """
    Saves the summary to a text file inside a folder called 'summaries'.
    The filename includes the topic and today's date/time so old
    searches don't get overwritten.
    """
    import datetime

    os.makedirs("summaries", exist_ok=True)

    safe_topic = "".join(c if c.isalnum() or c == " " else "" for c in topic)
    safe_topic = safe_topic.strip().replace(" ", "_")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"summaries/{safe_topic}_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Topic: {topic}\n")
        f.write(f"Generated: {timestamp}\n")
        f.write("=" * 80 + "\n")
        f.write(summary)

    print(f"\nSummary also saved to: {filename}")


def save_summary_as_pdf(topic, summary):
    """
    Saves the summary as a clean, readable PDF file inside the
    'summaries' folder, alongside the .txt version.
    """
    from fpdf import FPDF
    import datetime

    os.makedirs("summaries", exist_ok=True)

    safe_topic = "".join(c if c.isalnum() or c == " " else "" for c in topic)
    safe_topic = safe_topic.strip().replace(" ", "_")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"summaries/{safe_topic}_{timestamp}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, "PubMed AI Summary")

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 8, f"Topic: {topic}")
    pdf.multi_cell(0, 8, f"Generated: {timestamp}")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    safe_summary = summary.encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 7, safe_summary)

    pdf.output(filename)
    return filename


def main():
    try:
        topic = input("Enter a medical topic or drug name to search PubMed: ").strip()

        if topic == "":
            print("You didn't type anything. Please run the tool again and enter a topic.")
            return

        num_papers_input = input("How many recent papers do you want? (press Enter for 5): ")
        if num_papers_input.strip() == "":
            num_papers = 5
        else:
            try:
                num_papers = int(num_papers_input)
                if num_papers <= 0:
                    print("Please enter a positive number. Defaulting to 5.")
                    num_papers = 5
            except ValueError:
                print("That wasn't a valid number. Defaulting to 5.")
                num_papers = 5

        print(f"\nSearching PubMed for the {num_papers} most recent papers on '{topic}'...\n")

        try:
            id_list = search_pubmed(topic, max_results=num_papers)
        except requests.exceptions.ConnectionError:
            print("Could not connect to PubMed. Please check your internet connection and try again.")
            return
        except requests.exceptions.RequestException as e:
            print(f"Something went wrong while contacting PubMed: {e}")
            return

        if not id_list:
            print("No results found. Try a different search term.")
            return

        print(f"Found {len(id_list)} paper(s). Fetching details...\n")

        try:
            papers_text = fetch_details(id_list)
        except requests.exceptions.RequestException as e:
            print(f"Something went wrong while fetching paper details: {e}")
            return

        print("Cleaning up text before sending to Claude...\n")
        papers_text = clean_abstract_text(papers_text)

        print("Sending papers to Claude for summarization... (this takes a few seconds)\n")

        try:
            summary = summarize_with_claude(topic, papers_text, num_papers)
        except anthropic.AuthenticationError:
            print("There's a problem with your API key. Please check your .env file.")
            return
        except anthropic.APIError as e:
            print(f"Claude API error: {e}")
            print("(This is often a billing issue - check console.anthropic.com > Billing)")
            return

        print("=" * 80)
        print(summary)
        print("=" * 80)

        save_summary(topic, summary)

    except KeyboardInterrupt:
        print("\n\nCancelled. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error happened: {e}")
        print("If this keeps happening, note down this message and we can fix it together.")


if __name__ == "__main__":
    main()