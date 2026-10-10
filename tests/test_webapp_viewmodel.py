"""Pure student-interface helpers are tested without network or Streamlit."""

from __future__ import annotations

import csv
import io

import pytest

from webapp.viewmodel import (
    api_keys_from_environment,
    available_sources,
    doi_link,
    readable_abstract,
    report_to_csv,
)

from abstract_extract.models import Article
from abstract_extract.search import SearchHit, SearchResponse


def _sample_report(
    *,
    title: str = "Example",
    abstract: str | None = "<jats:p>First <i>result</i>.</jats:p>",
) -> SearchResponse:
    """Build the smallest useful search response fixture."""
    return SearchResponse(
        results=(
            SearchHit(
                article=Article(
                    title=title,
                    abstract=abstract,
                    publication_date="2025-03-01",
                    authors=("Alice Example", "Bob Example"),
                    doi="10.1234/example",
                ),
                sources=("openalex", "pubmed"),
                abstract_source="pubmed",
            ),
        ),
        failures=(),
    )


def test_openalex_accessible_without_credential() -> None:
    """Casual OpenAlex access and optional providers need no student key."""
    sources = available_sources({})
    assert sources == {
        "OpenAlex": "openalex",
        "Semantic Scholar": "semantic_scholar",
        "PubMed": "pubmed",
    }
    assert "Scopus" not in sources


def test_scopus_visible_only_when_server_has_key() -> None:
    assert "Scopus" not in available_sources({"SCOPUS_API_KEY": "  "})
    assert available_sources({"SCOPUS_API_KEY": " server-key "})["Scopus"] == (
        "scopus"
    )


def test_keys_are_stripped_and_only_supported_names_exported() -> None:
    keys = api_keys_from_environment(
        {
            "OPENALEX_API_KEY": "  oa-key  ",
            "SEMANTIC_SCHOLAR_API_KEY": "ss-key",
            "NCBI_API_KEY": "",
            "SCOPUS_API_KEY": "  ",
            "SECRET_PASSWORD": "not-a-provider-key",
        }
    )
    assert keys == {"openalex": "oa-key", "semantic_scholar": "ss-key"}
    assert "SECRET_PASSWORD" not in keys


@pytest.mark.parametrize(
    ("doi", "expected"),
    [
        ("10.1234/ABC", "https://doi.org/10.1234/abc"),
        (
            "https://doi.org/10.5555/intro%2Fstudy",
            "https://doi.org/10.5555/intro/study",
        ),
        (None, None),
        ("", None),
        ("not a DOI", None),
        ("javascript:alert(1)", None),
        ("10.1234/a b", None),
        ("10.1234/text?x=1", "https://doi.org/10.1234/text%3Fx%3D1"),
    ],
)
def test_doi_link(doi: str | None, expected: str | None) -> None:
    assert doi_link(doi) == expected


@pytest.mark.parametrize(
    ("abstract", "expected"),
    [
        (None, None),
        ("   ", None),
        ("Ordinary text.", "Ordinary text."),
        ("<jats:p>Alpha <italic>beta</italic>.</jats:p>", "Alpha beta."),
        ("A <jats:sec><jats:p>B</jats:p></jats:sec> C", "A B C"),
        ("One &amp; two", "One & two"),
        ("3 < 5", "3 < 5"),
        ("<p>First.</p><p>Second.</p>", "First. Second."),
        ("<script>do_bad_thing()</script>", "do_bad_thing()"),
    ],
)
def test_readable_abstract(abstract: str | None, expected: str | None) -> None:
    assert readable_abstract(abstract) == expected


def test_csv_contains_metadata_and_provenance() -> None:
    content = report_to_csv(_sample_report())
    assert content.startswith(b"\xef\xbb\xbf")
    decoded = content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(decoded)))
    assert rows[0] == [
        "Title",
        "Authors",
        "Publication date",
        "DOI",
        "Abstract",
        "Found in",
        "Abstract source",
    ]
    assert rows[1] == [
        "Example",
        "Alice Example; Bob Example",
        "2025-03-01",
        "10.1234/example",
        "First result.",
        "openalex; pubmed",
        "pubmed",
    ]


@pytest.mark.parametrize("formula", ["=1+1", "+SUM(A1)", "-2+3", "@X", "  =A1"])
def test_csv_blocks_spreadsheet_formula_injection(formula: str) -> None:
    data = report_to_csv(_sample_report(title=formula))
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    assert rows[1][0] == "'" + formula


def test_csv_quotes_commas_and_newlines() -> None:
    report = _sample_report(title="A, quoted\npaper")
    rows = list(
        csv.reader(io.StringIO(report_to_csv(report).decode("utf-8-sig")))
    )
    assert rows[1][0] == "A, quoted\npaper"


def test_empty_report_can_be_downloaded() -> None:
    report = SearchResponse(results=(), failures=())
    rows = list(
        csv.reader(io.StringIO(report_to_csv(report).decode("utf-8-sig")))
    )
    assert len(rows) == 1


def test_missing_abstract_exports_empty_cell() -> None:
    report = _sample_report(abstract=None)
    rows = list(
        csv.reader(io.StringIO(report_to_csv(report).decode("utf-8-sig")))
    )
    assert rows[1][4] == ""
