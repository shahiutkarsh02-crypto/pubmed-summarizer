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


def search_pubmed(topic, max_results=5):
    """Ask PubMed for the IDs of the most recent papers on 'topic'."""
    search_url = BASE_URL + "esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": topic,
        "retmax": max_results,
        "sort": "date",
        "retmode": "json"
    }
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
    prompt = f"""You are helping a pharmacy professional quickly understand
recent research. Below are the {num_papers} most recent PubMed abstracts on the topic
"{topic}".

For EACH paper, produce a short structured summary with these exact headings:
- Title (short version)
- Study Type & Size (e.g. retrospective cohort, 616 patients)
- Key Findings (2-3 bullet points, plain language)
- Relevance to "{topic}" (1 sentence)

Keep it concise and skip any paper that has no usable abstract text.

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