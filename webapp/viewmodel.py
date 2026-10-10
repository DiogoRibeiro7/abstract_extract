"""Presentation helpers for the student-facing literature search app.

Pure functions live here so CSV export, credentials, links, and display
formatting can be tested without installing or running Streamlit.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping
from html.parser import HTMLParser
from urllib.parse import quote

from abstract_extract.search import SearchResponse, SearchSource, normalize_doi

SOURCE_LABELS: dict[str, SearchSource] = {
    "OpenAlex": "openalex",
    "Semantic Scholar": "semantic_scholar",
    "PubMed": "pubmed",
    "Scopus": "scopus",
}

_CREDENTIAL_NAMES = {
    "openalex": "OPENALEX_API_KEY",
    "semantic_scholar": "SEMANTIC_SCHOLAR_API_KEY",
    "pubmed": "NCBI_API_KEY",
    "scopus": "SCOPUS_API_KEY",
}
_DOI_FORMAT = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)
_BLOCK_TAGS = frozenset(
    {"p", "jats:p", "br", "jats:br", "sec", "jats:sec", "title", "jats:title"}
)


def api_keys_from_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """Read configured server-side credentials without exposing them in the UI."""
    return {
        name: value
        for name, key in _CREDENTIAL_NAMES.items()
        if (value := environ.get(key, "").strip())
    }


def available_sources(environ: Mapping[str, str]) -> dict[str, SearchSource]:
    """Hide Scopus until its mandatory API key is configured on the server."""
    sources = dict(SOURCE_LABELS)
    if not environ.get("SCOPUS_API_KEY", "").strip():
        sources.pop("Scopus")
    return sources


def doi_link(doi: str | None) -> str | None:
    """Create an HTTPS DOI resolver link only for plausibly valid identifiers."""
    normalized = normalize_doi(doi)
    if normalized is None or _DOI_FORMAT.fullmatch(normalized) is None:
        return None
    return f"https://doi.org/{quote(normalized, safe='/')}"


class _AbstractTextParser(HTMLParser):
    """Extract human-readable text from JATS and other lightweight markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        """Retain text content, including text inside inline emphasis tags."""
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Add whitespace at block boundaries, not around inline markup."""
        if tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        """Keep adjacent paragraphs from running together."""
        if tag in _BLOCK_TAGS:
            self.parts.append(" ")


def readable_abstract(value: str | None) -> str | None:
    """Present abstracts as text, stripping markup without rendering raw HTML."""
    if value is None or not value.strip():
        return None
    parser = _AbstractTextParser()
    parser.feed(value)
    result = " ".join("".join(parser.parts).split())
    return result or None


def _spreadsheet_safe(value: str) -> str:
    """Prevent spreadsheet formula execution in downloaded CSV cells."""
    cleaned = value.replace("\x00", "")
    if cleaned.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + cleaned
    return cleaned


def report_to_csv(report: SearchResponse) -> bytes:
    """Serialize a search report to UTF-8 CSV with provenance columns.

    Uses a UTF-8 BOM for compatibility with common spreadsheet programs.
    Text fields are formula-escaped. Network credentials and failures are
    deliberately not serialized.
    """
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Title",
            "Authors",
            "Publication date",
            "DOI",
            "Abstract",
            "Found in",
            "Abstract source",
        ]
    )
    for hit in report.results:
        article = hit.article
        fields = (
            article.title or "",
            "; ".join(article.authors),
            article.publication_date or "",
            article.doi or "",
            readable_abstract(article.abstract) or "",
            "; ".join(hit.sources),
            hit.abstract_source or "",
        )
        writer.writerow([_spreadsheet_safe(field) for field in fields])
    return output.getvalue().encode("utf-8-sig")
