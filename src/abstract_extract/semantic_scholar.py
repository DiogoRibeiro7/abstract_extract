"""Semantic Scholar Graph API search adapter."""

from __future__ import annotations

from collections.abc import Mapping

import requests
from dataexcept import DataLoadingError, wrapping

from abstract_extract.models import Article

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search_semantic_scholar(
    query: str,
    *,
    max_results: int = 25,
    api_key: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> list[Article]:
    """Search one page of papers, optionally authenticating with an API key."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if (
        not isinstance(max_results, int)
        or isinstance(max_results, bool)
        or not 1 <= max_results <= 100
    ):
        raise ValueError("max_results must be between 1 and 100")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if api_key is not None and not api_key.strip():
        raise ValueError("api_key must not be empty")

    headers = {"Accept": "application/json"}
    if api_key is not None:
        headers["x-api-key"] = api_key.strip()
    params: dict[str, str | int] = {
        "query": query.strip(),
        "limit": max_results,
        "fields": "title,abstract,publicationDate,year,authors,externalIds",
    }
    owns_session = session is None
    client = session if session is not None else requests.Session()
    try:
        with wrapping(
            requests.RequestException, DataLoadingError, source=SEMANTIC_SCHOLAR_URL
        ):
            response = client.get(
                SEMANTIC_SCHOLAR_URL,
                headers=headers,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, Mapping) or not isinstance(
            payload.get("data"), list
        ):
            raise ValueError("Semantic Scholar response must contain a data list")
        articles: list[Article] = []
        for item in payload["data"]:
            if not isinstance(item, Mapping):
                raise ValueError("Semantic Scholar paper must be an object")
            raw_authors = item.get("authors", [])
            if not isinstance(raw_authors, list):
                raise ValueError("Semantic Scholar authors must be a list")
            names = tuple(
                author["name"]
                for author in raw_authors
                if isinstance(author, Mapping) and isinstance(author.get("name"), str)
            )
            ids = item.get("externalIds")
            doi = ids.get("DOI") if isinstance(ids, Mapping) else None
            date = item.get("publicationDate")
            year = item.get("year")
            if (
                not isinstance(date, str)
                and isinstance(year, int)
                and not isinstance(year, bool)
            ):
                date = str(year)
            title = item.get("title")
            abstract = item.get("abstract")
            articles.append(
                Article(
                    title=title if isinstance(title, str) else None,
                    abstract=abstract if isinstance(abstract, str) else None,
                    publication_date=date if isinstance(date, str) else None,
                    authors=names,
                    doi=doi if isinstance(doi, str) else None,
                )
            )
        return articles
    finally:
        if owns_session:
            client.close()
