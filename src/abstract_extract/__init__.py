"""Public package interface for abstract-extract."""

from abstract_extract.crossref import get_abstract_from_doi
from abstract_extract.models import Article
from abstract_extract.scopus import (
    fetch_all_from_scopus,
    fetch_from_scopus,
    process_scopus_entries,
    process_scopus_response,
)

__all__ = [
    "Article",
    "fetch_all_from_scopus",
    "fetch_from_scopus",
    "get_abstract_from_doi",
    "process_scopus_entries",
    "process_scopus_response",
]
