"""Public package interface for abstract-extract."""

from abstract_extract.crossref import get_abstract_from_doi
from abstract_extract.models import Article
from abstract_extract.openalex import search_openalex
from abstract_extract.pubmed import search_pubmed
from abstract_extract.scopus import (
    fetch_all_from_scopus,
    fetch_from_scopus,
    process_scopus_entries,
    process_scopus_response,
)
from abstract_extract.search import (
    SearchFailure,
    SearchHit,
    SearchResponse,
    normalize_doi,
    search_articles,
)
from abstract_extract.semantic_scholar import search_semantic_scholar

__all__ = [
    "Article",
    "SearchFailure",
    "SearchHit",
    "SearchResponse",
    "fetch_all_from_scopus",
    "fetch_from_scopus",
    "get_abstract_from_doi",
    "normalize_doi",
    "process_scopus_entries",
    "process_scopus_response",
    "search_articles",
    "search_openalex",
    "search_pubmed",
    "search_semantic_scholar",
]
