import argparse
import csv
import logging
import re
import sys
from typing import List, Dict, Optional
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

Paper = Dict[str, Optional[str]]

def fetch_pubmed_ids(query: str) -> List[str]:
    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': 20,
        'retmode': 'json'
    }
    response = requests.get(PUBMED_API_URL, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get('esearchresult', {}).get('idlist', [])

def fetch_paper_details(paper_ids: List[str]) -> List[Paper]:
    ids = ",".join(paper_ids)
    params = {
        'db': 'pubmed',
        'id': ids,
        'retmode': 'json'
    }
    response = requests.get(PUBMED_SUMMARY_URL, params=params)
    response.raise_for_status()
    summaries = response.json().get('result', {})

    papers = []
    for pid in paper_ids:
        summary = summaries.get(pid, {})
        title = summary.get('title')
        pubdate = summary.get('pubdate')
        authors = summary.get('authors', [])

        non_academic_authors = []
        companies = []
        email = summary.get('elocationid', '')

        for author in authors:
            name = author.get('name', '')
            affiliation = author.get('affiliation', '')
            if not re.search(r'university|college|institute|lab|school', affiliation, re.I):
                non_academic_authors.append(name)
                companies.append(affiliation)

        papers.append({
            'PubmedID': pid,
            'Title': title,
            'Publication Date': pubdate,
            'Non-academic Author(s)': "; ".join(non_academic_authors) or None,
            'Company Affiliation(s)': "; ".join(companies) or None,
            'Corresponding Author Email': email or None
        })

    return papers

def save_to_csv(papers: List[Paper], filename: str) -> None:
    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=papers[0].keys())
        writer.writeheader()
        writer.writerows(papers)

def main():
    parser = argparse.ArgumentParser(description='Fetch PubMed papers based on query.')
    parser.add_argument('query', type=str, help='PubMed search query')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('-f', '--file', type=str, help='Output CSV filename')

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        logger.info(f"Fetching PubMed IDs for query: {args.query}")
        ids = fetch_pubmed_ids(args.query)
        logger.debug(f"Found PubMed IDs: {ids}")

        logger.info("Fetching paper details...")
        papers = fetch_paper_details(ids)

        if not papers:
            logger.warning("No papers found.")
            sys.exit(0)

        if args.file:
            logger.info(f"Saving results to {args.file}")
            save_to_csv(papers, args.file)
        else:
            for paper in papers:
                print(paper)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
