import requests

import requests

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
        "X-ELS-APIKey": api_key
    }
    
    params = {
        "query": query,
        "count": max_results
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()  # Ensure the request was successful
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching from Scopus: {e}")
        if response.status_code != 200:
            print(f"Response Code: {response.status_code}")
            print(response.text)  # This will print the error message from Scopus
        return None

# Example usage
api_key = "aa945f2068e32283437cea4dc191245b"
query = "machine learning in biomedical applications"
articles = fetch_from_scopus(query, api_key)


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

# Example: Print the details of the first article
for article in processed_data
first_article = processed_data[0]
print(f"Title: {first_article['title']}")
print(f"Abstract: {first_article['abstract']}")
print(f"Publication Date: {first_article['publication_date']}")
print(f"Authors: {', '.join(first_article['authors'])}")
print(f"Doi: {first_article['doi']}")

