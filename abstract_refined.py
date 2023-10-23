import requests

from requests.exceptions import HTTPError
from typing import Optional, Dict


import requests
from typing import Optional, Dict, List

def fetch_all_from_scopus(query: str, api_key: str, start_date: Optional[str] = None,
                          end_date: Optional[str] = None, author: Optional[str] = None) -> Optional[List[Dict]]:
    """
    Fetches all articles from Scopus based on a query and additional conditions.
    
    Args:
    - query (str): Search query for Scopus.
    - api_key (str): Your Scopus API key.
    - start_date (str, optional): Start date for filtering articles. Format YYYY-MM-DD. Defaults to None.
    - end_date (str, optional): End date for filtering articles. Format YYYY-MM-DD. Defaults to None.
    - author (str, optional): Author name to filter articles. Defaults to None.
    
    Returns:
    - List[Dict]: List of dictionaries containing fetched articles and metadata, or None in case of an error.
    """
    # Base URL for the Scopus API
    base_url = "https://api.elsevier.com/content/search/scopus"
    
    # Headers for the API request
    headers = {
        "Accept": "application/json",
        "X-ELS-APIKey": api_key
    }
    
    # Basic parameters for the API request
    params = {
        "query": query,
        "count": 25,  # Maximum allowed per request
        "cursor": "*"  # Initialize cursor
    }
    
    # Add date range to the query if specified
    if start_date and end_date:
        params["date"] = f"{start_date} to {end_date}"
        
    # Add author to the query if specified
    if author:
        params["query"] += f" AND AUTHOR({author})"
        
    all_results = []  # To store all fetched articles
    
    try:
        while True:
            # Make the API request
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()  # Check if the request was successful
            
            json_response = response.json()
            all_results.extend(json_response.get("search-results", {}).get("entry", []))
            
            next_cursor = json_response.get("search-results", {}).get("cursor", {}).get("@next")
            if next_cursor:
                params["cursor"] = next_cursor  # Update cursor for the next iteration
            else:
                break  # Exit loop if there's no more data to fetch
                
        return all_results
    except requests.RequestException as e:
        print(f"Error fetching from Scopus: {e}")
        if response.status_code != 200:
            print(f"Response Code: {response.status_code}")
            print(response.text)  # Print the error message from Scopus
        return None



# Example usage
api_key = "aa945f2068e32283437cea4dc191245b"
# The query you want to perform
query = "Aldina Correia"

# Optionally, specify a date range and author
# start_date = "2010-01-01"
# end_date = "2023-01-01"
# author = "Aldina Correia"

# Call the function
result = fetch_all_from_scopus(query, api_key, author=author)


print(result)


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
        # Extracting key details
        title = article.get("dc:title", None)
        abstract = article.get("dc:description", None)
        publication_date = article.get("prism:coverDate", None)

        # Extracting author details
        authors = article.get("author", [])
        author_names = [author.get("authname", "") for author in authors]
        doi = article.get("prism:doi", None)

        # Append the processed article details to the list
        processed_articles.append({
            "title": title,
            "abstract": abstract,
            "publication_date": publication_date,
            "authors": author_names,
            "doi": doi
        })

    return processed_articles


# Process the fetched articles
processed_data = process_scopus_response(articles)


def get_abstract_from_doi(doi):
    # Define the CrossRef API endpoint
    url = f"https://api.crossref.org/works/{doi}"

    try:
        # Make the API request
        response = requests.get(url)

        # Raise an HTTPError if the HTTP request returned an unsuccessful status code
        response.raise_for_status()

    except HTTPError as http_err:
        # Handle HTTPError
        print(f"HTTP error occurred: {http_err}")
        return "HTTP Error"

    except Exception as err:
        # Handle other exceptions
        print(f"An error occurred: {err}")
        return "Error"

    data = response.json()

    # Extract the abstract, if available
    abstract = data['message'].get('abstract', 'Abstract not available.')

    return abstract


# Example
for article in processed_data:
    first_article = article
    print(f"Doi: {first_article['doi']}")
    doi = first_article['doi']
    if doi:
        print(get_abstract_from_doi(doi))
        first_article['abstract'] = get_abstract_from_doi(doi)


# Example: Print the details of the first article
for article in processed_data:
    first_article = article
    print(f"Title: {first_article['title']}")
    print(f"Abstract: {first_article['abstract']}")
    print(f"Publication Date: {first_article['publication_date']}")
    print(f"Authors: {', '.join(first_article['authors'])}")
    print(f"Doi: {first_article['doi']}")
