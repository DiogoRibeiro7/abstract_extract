"""Crossref abstract retrieval utilities."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote

import requests

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
DEFAULT_TIMEOUT_SECONDS = 30.0


def get_abstract_from_doi(
    doi: str,
    *,
    session: requests.Session | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> str | None:
    """Retrieve an abstract from Crossref for a DOI.

    Returns None when Crossref has no abstract for the work.
    """
    normalized_doi = doi.strip()
    if not normalized_doi:
        raise ValueError("doi must not be empty")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    owns_session = session is None
    client = session or requests.Session()

    try:
        response = client.get(
            f"{CROSSREF_WORKS_URL}/{quote(normalized_doi, safe='')}",
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, Mapping):
            raise ValueError("Crossref returned a non-object JSON response")

        message = payload.get("message")
        if not isinstance(message, Mapping):
            raise ValueError("Crossref response is missing 'message'")

        abstract = message.get("abstract")
        return abstract if isinstance(abstract, str) else None
    finally:
        if owns_session:
            client.close()
