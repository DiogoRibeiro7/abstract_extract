import os
from typing import Dict, List, Optional

import requests
from requests.exceptions import HTTPError


def fetch_all_from_scopus(
    query: str,
    api_key: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    author: Optional[str] = None,
) -> Optional[List[Dict]]:
    """
    Fetches all articles from Scopus based on a query and additional conditions.

    Args:
    - query (str): Search query for Scopus.
    - api_key (str): Your Scopus API key.
    - start_date (str, optional): Start date for filtering articles. Format YYYY-MM-DD.
    - end_date (str, optional): End date for filtering articles. Format YYYY-MM-DD.
    - author (str, optional): Author name to filter articles.

    Returns:
    - List[Dict]: List of dictionaries containing fetched articles and metadata,
      or None in case of an error.
    """
    base_url = "https://api.elsevier.com/content/search/scopus"

    headers = {
        "Accept": "application/json",
        "X-ELS-APIKey": api_key,
    }

    params = {
        "query": query,
        "count": 25,
        "cursor": "*",
    }

    if start_date and end_date:
        params["date"] = f"{start_date} to {end_date}"

    if author:
        params["query"] += f" AND AUTHOR({author})"

    all_results = []

    try:
        while True:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()

            json_response = response.json()
            all_results.extend(
                json_response.get("search-results", {}).get("entry", [])
            )

            next_cursor = (
                json_response.get("search-results", {})
                .get("cursor", {})
                .get("@next")
            )
            if next_cursor:
                params["cursor"] = next_cursor
            else:
                break

        return all_results
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

    query = "Aldina Correia"
    author = "Aldina Correia"
    result = fetch_all_from_scopus(query, api_key, author=author)

    if result is None:
        return

    print(result)

    # Preserve the original workflow. This processing step will be refactored
    # separately because fetch_all_from_scopus returns a list of entries.
    processed_data = process_scopus_response(result)

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
