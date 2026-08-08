# pubmed_search.py
# This script searches PubMed for the 5 most recent papers on a topic
# and prints their titles and abstracts.

import requests

# This is the base address of PubMed's free public API (E-utilities).
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def search_pubmed(topic, max_results=5):
    """
    Step A: Ask PubMed for the IDs of the most recent papers on 'topic'.
    PubMed doesn't give us full papers right away - first it gives us
    a list of ID numbers, which we use in Step B to get full details.
    """
    search_url = BASE_URL + "esearch.fcgi"
    params = {
        "db": "pubmed",          # search the PubMed database
        "term": topic,           # our search term
        "retmax": max_results,   # how many results we want
        "sort": "date",          # newest first
        "retmode": "json"        # give us the answer as JSON (structured data)
    }

    response = requests.get(search_url, params=params)
    data = response.json()

    id_list = data["esearchresult"]["idlist"]
    return id_list


def fetch_details(id_list):
    """
    Step B: Given a list of PubMed IDs, fetch the actual title and
    abstract text for each paper.
    """
    fetch_url = BASE_URL + "efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),   # PubMed wants IDs joined by commas
        "rettype": "abstract",
        "retmode": "text"
    }

    response = requests.get(fetch_url, params=params)
    return response.text


def main():
    topic = input("Enter a medical topic or drug name to search PubMed: ")

    print(f"\nSearching PubMed for the 5 most recent papers on '{topic}'...\n")

    id_list = search_pubmed(topic, max_results=5)

    if not id_list:
        print("No results found. Try a different search term.")
        return

    print(f"Found {len(id_list)} paper(s). Fetching details...\n")

    details_text = fetch_details(id_list)

    print("=" * 80)
    print(details_text)
    print("=" * 80)


if __name__ == "__main__":
    main()