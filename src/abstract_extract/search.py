"""Unified scholarly search, DOI deduplication, and optional enrichment."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal
from urllib.parse import unquote

import requests
from dataexcept import DataLoadingError

from abstract_extract.crossref import get_abstract_from_doi
from abstract_extract.models import Article
from abstract_extract.openalex import search_openalex
from abstract_extract.pubmed import search_pubmed
from abstract_extract.scopus import fetch_from_scopus, process_scopus_response
from abstract_extract.semantic_scholar import search_semantic_scholar

SearchSource = Literal["openalex", "semantic_scholar", "pubmed", "scopus"]
AbstractSource = SearchSource | Literal["crossref"]
ErrorMode = Literal["raise", "collect"]

_SUPPORTED_SOURCES: tuple[SearchSource, ...] = (
    "openalex",
    "semantic_scholar",
    "pubmed",
    "scopus",
)
_DOI_PREFIX = re.compile(
    r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """An article with matching providers and the source of its abstract.

    Attributes:
        article: Normalized and DOI-canonicalized article.
        sources: Providers that returned this DOI, in requested source order.
        abstract_source: Source whose abstract was retained, if any. Crossref
            enrichment does not count as a search hit in sources.
    """

    article: Article
    sources: tuple[SearchSource, ...]
    abstract_source: AbstractSource | None


@dataclass(frozen=True, slots=True)
class SearchFailure:
    """An isolated provider/enrichment failure in collect mode."""

    source: AbstractSource
    error: Exception
    doi: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResponse:
    """Result records and any failures from a federated search.

    Failures is empty in successful runs, including when a source legitimately
    returns no records. In collect mode, consult failures before treating an
    empty result tuple as evidence of no matching publications.
    """

    results: tuple[SearchHit, ...]
    failures: tuple[SearchFailure, ...]


def normalize_doi(value: str | None) -> str | None:
    """Normalize a DOI for exact-match deduplication and Crossref requests.

    Decode percent-encoding, strip common DOI resolver/label prefixes and
    case-fold the identifier. Do not remove DOI punctuation or infer missing
    identifiers from titles. This is normalization, not full DOI validation.
    """
    if value is None:
        return None
    identifier = unquote(value.strip())
    while True:
        candidate = _DOI_PREFIX.sub("", identifier, count=1).strip()
        if candidate == identifier:
            break
        identifier = candidate
    return identifier.casefold() or None


def _nonempty(value: str | None) -> str | None:
    """Preserve a nonblank value exactly as given by its source."""
    return value if value is not None and value.strip() else None


def _merge(existing: SearchHit, incoming: Article, source: SearchSource) -> SearchHit:
    """Merge matching DOIs; keep first nonempty field in source priority order."""
    current = existing.article
    current_abstract = _nonempty(current.abstract)
    incoming_abstract = _nonempty(incoming.abstract)
    merged = Article(
        title=_nonempty(current.title) or _nonempty(incoming.title),
        abstract=current_abstract or incoming_abstract,
        publication_date=(
            _nonempty(current.publication_date)
            or _nonempty(incoming.publication_date)
        ),
        authors=current.authors or incoming.authors,
        doi=current.doi,
    )
    abstract_source = (
        existing.abstract_source
        if current_abstract is not None
        else source if incoming_abstract is not None else None
    )
    sources = (
        existing.sources
        if source in existing.sources
        else (*existing.sources, source)
    )
    return SearchHit(
        article=merged,
        sources=sources,
        abstract_source=abstract_source,
    )


def _fetch_from_source(
    source: SearchSource,
    query: str,
    max_results: int,
    api_keys: Mapping[str, str],
    email: str | None,
    session: requests.Session,
    timeout: float,
) -> list[Article]:
    """Delegate one page to the existing provider adapter."""
    if source == "openalex":
        return search_openalex(
            query,
            max_results=max_results,
            api_key=api_keys.get(source),
            session=session,
            timeout=timeout,
        )
    if source == "semantic_scholar":
        return search_semantic_scholar(
            query,
            max_results=max_results,
            api_key=api_keys.get(source),
            session=session,
            timeout=timeout,
        )
    if source == "pubmed":
        return search_pubmed(
            query,
            max_results=max_results,
            email=email,
            api_key=api_keys.get(source),
            session=session,
            timeout=timeout,
        )
    raw = fetch_from_scopus(
        query,
        api_key=api_keys["scopus"],
        max_results=max_results,
        session=session,
        timeout=timeout,
    )
    return process_scopus_response(raw)


def _validate(
    query: str,
    sources: Sequence[SearchSource],
    max_results: int,
    api_keys: Mapping[str, str] | None,
    email: str | None,
    on_error: ErrorMode,
    timeout: float,
) -> dict[str, str]:
    """Reject configuration errors before making any HTTP requests."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if isinstance(sources, str) or not sources:
        raise ValueError("sources must be a non-empty sequence")
    seen: set[SearchSource] = set()
    for source in sources:
        if source not in _SUPPORTED_SOURCES:
            raise ValueError(f"Unsupported search source: {source}")
        if source in seen:
            raise ValueError(f"Duplicate search source: {source}")
        seen.add(source)
    if (
        not isinstance(max_results, int)
        or isinstance(max_results, bool)
        or not 1 <= max_results <= 100
    ):
        raise ValueError("max_results must be between 1 and 100")
    if "scopus" in seen and max_results > 25:
        raise ValueError("Scopus supports at most 25 results per page")
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite positive number")
    if on_error not in ("raise", "collect"):
        raise ValueError("on_error must be 'raise' or 'collect'")
    if email is not None and (
        not isinstance(email, str) or not email.strip()
    ):
        raise ValueError("email must be a non-empty string")
    keys = dict(api_keys) if api_keys is not None else {}
    for provider, key in keys.items():
        if provider not in _SUPPORTED_SOURCES:
            raise ValueError(f"Unknown API key provider: {provider}")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"API key for {provider} must not be empty")
    if "scopus" in seen and "scopus" not in keys:
        raise ValueError("A Scopus API key is required when selecting scopus")
    return keys


def search_articles(
    query: str,
    *,
    sources: Sequence[SearchSource] = (
        "openalex",
        "semantic_scholar",
        "pubmed",
    ),
    max_results: int = 25,
    api_keys: Mapping[str, str] | None = None,
    email: str | None = None,
    enrich_abstracts: bool = False,
    on_error: ErrorMode = "raise",
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> SearchResponse:
    """Search selected services, deduplicate by DOI, and optionally enrich.

    Args:
        query: Search string passed unchanged to each selected provider except
            for trimming whitespace; query syntax differs between providers.
        sources: Ordered provider priority. Defaults to OpenAlex, Semantic
            Scholar, and PubMed. Include Scopus explicitly with an API key.
        max_results: First-page maximum per provider, 1-100 (Scopus: 1-25).
        api_keys: Optional mapping from provider names to API credentials.
        email: Optional NCBI email for PubMed requests.
        enrich_abstracts: Query Crossref only for deduplicated records missing
            abstracts and having DOIs. JATS/XML from Crossref is kept intact.
        on_error: 'raise' aborts on a provider/Crossref error; 'collect' records
            data-loading and response-shape errors and continues.
        session: Optional injectable HTTP session; never closed when supplied.
        timeout: Positive, finite HTTP timeout in seconds.

    Returns:
        Immutable search results in first-seen order, with provider provenance
        and explicit partial failures. Records without DOIs are never collapsed.

    Notes:
        For duplicate DOIs, the earliest selected source with a nonblank value
        wins each field; missing values are filled from later providers. Authors
        use the first nonempty author list. Source rankings are not calibrated.
    """
    keys = _validate(
        query, sources, max_results, api_keys, email, on_error, timeout
    )
    owns_session = session is None
    client = session if session is not None else requests.Session()
    hits: list[SearchHit] = []
    positions: dict[str, int] = {}
    failures: list[SearchFailure] = []
    try:
        for source in sources:
            try:
                articles = _fetch_from_source(
                    source, query.strip(), max_results, keys, email, client, timeout
                )
            except (DataLoadingError, ValueError) as error:
                if on_error == "raise":
                    raise
                failures.append(SearchFailure(source=source, error=error))
                continue
            for article in articles:
                doi = normalize_doi(article.doi)
                article = replace(
                    article, doi=doi, abstract=_nonempty(article.abstract)
                )
                index = positions.get(doi) if doi is not None else None
                if index is not None:
                    hits[index] = _merge(hits[index], article, source)
                    continue
                if doi is not None:
                    positions[doi] = len(hits)
                hits.append(
                    SearchHit(
                        article=article,
                        sources=(source,),
                        abstract_source=(
                            source if article.abstract is not None else None
                        ),
                    )
                )
        if enrich_abstracts:
            for index, hit in enumerate(hits):
                if hit.article.abstract is not None or hit.article.doi is None:
                    continue
                try:
                    abstract = get_abstract_from_doi(
                        hit.article.doi, session=client, timeout=timeout
                    )
                except (DataLoadingError, ValueError) as error:
                    if on_error == "raise":
                        raise
                    failures.append(
                        SearchFailure(
                            source="crossref", doi=hit.article.doi, error=error
                        )
                    )
                    continue
                if _nonempty(abstract) is not None:
                    hits[index] = replace(
                        hit,
                        article=replace(hit.article, abstract=abstract),
                        abstract_source="crossref",
                    )
        return SearchResponse(results=tuple(hits), failures=tuple(failures))
    finally:
        if owns_session:
            client.close()
