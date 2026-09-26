"""Scopus search and normalization utilities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import requests
from dataexcept import DataLoadingError, wrapping

from abstract_extract.models import Article

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_PAGE_SIZE = 25


def _require_non_empty(value: str, *, name: str) -> str:
    """Validate and normalize a required string argument."""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _optional_str(value: object) -> str | None:
    """Return a string value when present, otherwise None."""
    return value if isinstance(value, str) else None


def _request_json(
    *,
    session: requests.Session,
    params: Mapping[str, str | int],
    api_key: str,
    timeout: float,
) -> dict[str, Any]:
    """Execute one Scopus search request and validate its JSON shape."""
    with wrapping(
        requests.RequestException, DataLoadingError, source=SCOPUS_SEARCH_URL
    ):
        response = session.get(
            SCOPUS_SEARCH_URL,
            headers={
                "Accept": "application/json",
                "X-ELS-APIKey": api_key,
            },
            params=dict(params),
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Scopus returned a non-object JSON response")
    return payload


def fetch_from_scopus(
    query: str,
    api_key: str,
    *,
    max_results: int = MAX_PAGE_SIZE,
    session: requests.Session | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Fetch one page of Scopus search results.

    Args:
        query: Scopus search expression. Leading and trailing whitespace is removed.
        api_key: Elsevier/Scopus API key.
        max_results: Number of results requested for the page. Must be between 1 and 25.
        session: Optional HTTP session for connection reuse or deterministic testing.
        timeout: Request timeout in seconds. Must be positive.

    Returns:
        The raw Scopus JSON response as a dictionary.

    Raises:
        ValueError: If required values are empty, the page size or timeout is invalid,
            or Scopus returns a non-object JSON response.
        DataLoadingError: If the HTTP request, status validation, or JSON decoding fails.
    """
    query = _require_non_empty(query, name="query")
    api_key = _require_non_empty(api_key, name="api_key")

    if not 1 <= max_results <= MAX_PAGE_SIZE:
        raise ValueError(f"max_results must be between 1 and {MAX_PAGE_SIZE}")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    owns_session = session is None
    client = session or requests.Session()
    try:
        return _request_json(
            session=client,
            params={"query": query, "count": max_results},
            api_key=api_key,
            timeout=timeout,
        )
    finally:
        if owns_session:
            client.close()


def fetch_all_from_scopus(
    query: str,
    api_key: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    author: str | None = None,
    session: requests.Session | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    """Fetch all Scopus entries reachable through cursor pagination.

    Args:
        query: Scopus search expression.
        api_key: Elsevier/Scopus API key.
        start_date: Optional lower date bound. Must be paired with `end_date`.
        end_date: Optional upper date bound. Must be paired with `start_date`.
        author: Optional author filter appended to the Scopus query.
        session: Optional HTTP session for connection reuse or deterministic testing.
        timeout: Request timeout in seconds. Must be positive.

    Returns:
        Raw Scopus entry dictionaries collected across all cursor pages.

    Raises:
        ValueError: If required values are empty, only one date bound is provided,
            the timeout is invalid, or a Scopus response has an unexpected shape.
        DataLoadingError: If a request, status validation, or JSON decoding operation
            fails on any page.
    """
    query = _require_non_empty(query, name="query")
    api_key = _require_non_empty(api_key, name="api_key")

    if (start_date is None) != (end_date is None):
        raise ValueError("start_date and end_date must be provided together")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    effective_query = query
    if author is not None:
        effective_query += f" AND AUTHOR({_require_non_empty(author, name='author')})"

    params: dict[str, str | int] = {
        "query": effective_query,
        "count": MAX_PAGE_SIZE,
        "cursor": "*",
    }
    if start_date is not None and end_date is not None:
        params["date"] = f"{start_date} to {end_date}"

    owns_session = session is None
    client = session or requests.Session()
    entries: list[dict[str, Any]] = []

    try:
        while True:
            payload = _request_json(
                session=client,
                params=params,
                api_key=api_key,
                timeout=timeout,
            )

            search_results = payload.get("search-results")
            if not isinstance(search_results, Mapping):
                raise ValueError("Scopus response is missing 'search-results'")

            page_entries = search_results.get("entry", [])
            if not isinstance(page_entries, list):
                raise ValueError("Scopus 'entry' field must be a list")

            entries.extend(entry for entry in page_entries if isinstance(entry, dict))

            cursor = search_results.get("cursor")
            next_cursor = cursor.get("@next") if isinstance(cursor, Mapping) else None
            if not isinstance(next_cursor, str) or not next_cursor:
                break
            params["cursor"] = next_cursor
    finally:
        if owns_session:
            client.close()

    return entries


def process_scopus_entries(
    entries: Iterable[Mapping[str, Any]],
) -> list[Article]:
    """Normalize raw Scopus entries into typed article objects.

    Args:
        entries: Iterable of raw Scopus entry mappings.

    Returns:
        One immutable :class:`Article` for each input entry.

    Notes:
        Missing optional metadata is represented by `None`. Invalid author objects are
        ignored rather than failing normalization.
    """
    articles: list[Article] = []

    for entry in entries:
        raw_authors = entry.get("author", [])
        authors: tuple[str, ...] = ()
        if isinstance(raw_authors, list):
            author_names: list[str] = []
            for author in raw_authors:
                if not isinstance(author, Mapping):
                    continue
                name = _optional_str(author.get("authname"))
                if name is not None:
                    author_names.append(name)
            authors = tuple(author_names)

        articles.append(
            Article(
                title=_optional_str(entry.get("dc:title")),
                abstract=_optional_str(entry.get("dc:description")),
                publication_date=_optional_str(entry.get("prism:coverDate")),
                authors=authors,
                doi=_optional_str(entry.get("prism:doi")),
            )
        )

    return articles


def process_scopus_response(payload: Mapping[str, Any]) -> list[Article]:
    """Normalize a complete single-page Scopus search response.

    Args:
        payload: Raw Scopus response containing `search-results.entry`.

    Returns:
        Normalized article records from the response.

    Raises:
        ValueError: If `search-results` is missing or `entry` is not a list.
    """
    search_results = payload.get("search-results")
    if not isinstance(search_results, Mapping):
        raise ValueError("Scopus response is missing 'search-results'")

    entries = search_results.get("entry", [])
    if not isinstance(entries, list):
        raise ValueError("Scopus 'entry' field must be a list")

    return process_scopus_entries(
        entry for entry in entries if isinstance(entry, Mapping)
    )
