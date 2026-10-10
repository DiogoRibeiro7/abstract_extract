"""OpenAlex works search and inverted-index abstract normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests
from dataexcept import DataLoadingError, wrapping

from abstract_extract.models import Article

OPENALEX_URL = "https://api.openalex.org/works"


def reconstruct_abstract(index: object) -> str | None:
    """Reconstruct an OpenAlex abstract from its inverted word index."""
    if index is None:
        return None
    if not isinstance(index, Mapping):
        raise ValueError("OpenAlex abstract_inverted_index must be an object")
    positions: dict[int, str] = {}
    for word, indices in index.items():
        if not isinstance(word, str) or not isinstance(indices, list):
            raise ValueError("Invalid OpenAlex inverted-index entry")
        for position in indices:
            if not isinstance(position, int) or isinstance(position, bool) or position < 0:
                raise ValueError("Invalid OpenAlex word position")
            if position in positions:
                raise ValueError("Duplicate OpenAlex word position")
            positions[position] = word
    if not positions:
        return None
    if sorted(positions) != list(range(len(positions))):
        raise ValueError("Non-contiguous OpenAlex word positions")
    return " ".join(positions[i] for i in range(len(positions)))


def search_openalex(
    query: str,
    *,
    max_results: int = 25,
    api_key: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> list[Article]:
    """Search OpenAlex works and return normalized article metadata.

    Args:
        query: Free-text works search.
        max_results: Number of works (1–100) from the first result page.
        api_key: Optional OpenAlex API key.
        session: Injectable HTTP session.
        timeout: Positive HTTP timeout in seconds.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= 100:
        raise ValueError("max_results must be between 1 and 100")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if api_key is not None and not api_key.strip():
        raise ValueError("api_key must not be empty")

    params: dict[str, str | int] = {"search": query.strip(), "per_page": max_results}
    if api_key is not None:
        params["api_key"] = api_key.strip()
    owns_session = session is None
    client = session if session is not None else requests.Session()
    try:
        with wrapping(requests.RequestException, DataLoadingError, source=OPENALEX_URL):
            response = client.get(OPENALEX_URL, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, Mapping) or not isinstance(payload.get("results"), list):
            raise ValueError("OpenAlex response must contain a results list")
        articles: list[Article] = []
        for item in payload["results"]:
            if not isinstance(item, Mapping):
                raise ValueError("OpenAlex work must be an object")
            authorships = item.get("authorships", [])
            if not isinstance(authorships, list):
                raise ValueError("OpenAlex authorships must be a list")
            authors: list[str] = []
            for authorship in authorships:
                if not isinstance(authorship, Mapping):
                    continue
                author = authorship.get("author")
                if isinstance(author, Mapping) and isinstance(author.get("display_name"), str):
                    authors.append(author["display_name"])
            raw_doi = item.get("doi")
            doi = raw_doi.removeprefix("https://doi.org/") if isinstance(raw_doi, str) else None
            articles.append(Article(
                title=item.get("title") if isinstance(item.get("title"), str) else None,
                abstract=reconstruct_abstract(item.get("abstract_inverted_index")),
                publication_date=item.get("publication_date") if isinstance(item.get("publication_date"), str) else None,
                authors=tuple(authors),
                doi=doi,
            ))
        return articles
    finally:
        if owns_session:
            client.close()
