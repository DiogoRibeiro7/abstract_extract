import os

import requests
from requests.exceptions import HTTPError


def fetch_from_scopus(query, api_key, max_results=25):
    """
    Fetches articles from Scopus based on a query.

    Args:
    - query (str): Search query for Scopus.
    - api_key (str): Your Scopus API key.
    - max_results (int): Maximum number of articles to fetch.

    Returns:
    - dict: Dictionary containing fetched articles and metadata.
    """
    base_url = "https://api.elsevier.com/content/search/scopus"

    headers = {
        "Accept": "application/json",
        "X-ELS-APIKey": api_key,
    }

    params = {
        "query": query,
        "count": max_results,
    }

    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print(f"Error fetching from Scopus: {exc}")
        return None


def process_scopus_response(articles):
    """
    Processes the Scopus API response to extract key article details.

    Args:
    - articles (list): List of dictionaries containing articles from Scopus.

    Returns:
    - list: List of dictionaries containing processed article details.
    """
    processed_articles = []

    for article in articles["search-results"]["entry"]:
        title = article.get("dc:title", None)
        abstract = article.get("dc:description", None)
        publication_date = article.get("prism:coverDate", None)

        authors = article.get("author", [])
        author_names = [author.get("authname", "") for author in authors]
        doi = article.get("prism:doi", None)

        processed_articles.append(
            {
                "title": title,
                "abstract": abstract,
                "publication_date": publication_date,
                "authors": author_names,
                "doi": doi,
            }
        )

    return processed_articles


def get_abstract_from_doi(doi):
    """Fetch an abstract from Crossref for a DOI."""
    url = f"https://api.crossref.org/works/{doi}"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return "HTTP Error"
    except Exception as err:
        print(f"An error occurred: {err}")
        return "Error"

    data = response.json()
    return data["message"].get("abstract", "Abstract not available.")


def main():
    """Run the original example without embedding credentials in source code."""
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "SCOPUS_API_KEY is not set. Export it in your environment before running this script."
        )

    query = "aldina correia"
    articles = fetch_from_scopus(query, api_key)
    if not articles:
        return

    processed_data = process_scopus_response(articles)

    for article in processed_data:
        doi = article["doi"]
        print(f"Doi: {doi}")
        if doi:
            article["abstract"] = get_abstract_from_doi(doi)

    for article in processed_data:
        print(f"Title: {article['title']}")
        print(f"Abstract: {article['abstract']}")
        print(f"Publication Date: {article['publication_date']}")
        print(f"Authors: {', '.join(article['authors'])}")
        print(f"Doi: {article['doi']}")


if __name__ == "__main__":
    main()
