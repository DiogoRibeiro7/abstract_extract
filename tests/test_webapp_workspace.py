"""Offline tests for student research workspace utilities."""

from __future__ import annotations

import csv
import io
import json

import pytest

from abstract_extract.models import Article
from abstract_extract.search import SearchHit
from webapp.filters import article_year, filter_hits
from webapp.library import (
    bookmark_key,
    export_library,
    from_hit,
    import_library,
    library_bibtex,
    library_csv,
    update_bookmark,
)


def _hit(
    doi: str | None = "10.1234/example",
    *,
    title: str = "Paper",
    date: str | None = "2025-01-01",
    abstract: str | None = "Summary",
    sources: tuple[str, ...] = ("openalex",),
) -> SearchHit:
    return SearchHit(
        article=Article(
            title=title,
            abstract=abstract,
            publication_date=date,
            authors=("A. Researcher",),
            doi=doi,
        ),
        sources=sources,
        abstract_source="openalex" if abstract else None,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2025-09-30", 2025),
        ("2024", 2024),
        ("unknown", None),
        (None, None),
        ("1499-01-01", None),
    ],
)
def test_article_year(value: str | None, expected: int | None) -> None:
    assert article_year(value) == expected


def test_filters_combine_source_year_text_and_abstract() -> None:
    hits = (
        _hit(title="Sleep methods", sources=("openalex", "pubmed")),
        _hit("10.1/other", title="Sleep theory", date="2020", abstract=None),
        _hit("10.1/third", title="Causal models", date=None),
    )
    selected = filter_hits(
        hits,
        text="sleep",
        source="pubmed",
        abstracts_only=True,
        year_from=2023,
        year_to=2026,
    )
    assert len(selected) == 1
    assert selected[0].article.title == "Sleep methods"


def test_filters_keep_undated_papers_without_date_bounds() -> None:
    hits = (_hit(date=None),)
    assert filter_hits(hits) == hits
    assert filter_hits(hits, year_from=2020) == ()


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        ("newest", ["Newest", "Older", "Undated"]),
        ("oldest", ["Older", "Newest", "Undated"]),
        ("title", ["Newest", "Older", "Undated"]),
        ("most_sources", ["Newest", "Older", "Undated"]),
    ],
)
def test_filters_sort(order: str, expected: list[str]) -> None:
    hits = (
        _hit(title="Older", date="2018"),
        _hit("10.1/new", title="Newest", date="2025", sources=("openalex", "pubmed")),
        _hit("10.1/unknown", title="Undated", date=None),
    )
    assert [hit.article.title for hit in filter_hits(hits, order=order)] == expected


def test_invalid_filter_arguments() -> None:
    with pytest.raises(ValueError):
        filter_hits((), year_from=2030, year_to=2020)
    with pytest.raises(ValueError):
        filter_hits((), order="unknown")


def test_reading_list_roundtrip_preserves_notes() -> None:
    item = update_bookmark(
        from_hit(_hit()), note="Check sample size", status="Reviewed"
    )
    raw = export_library((item,))
    recovered = import_library(raw)
    assert recovered == (item,)
    assert b"Check sample size" in raw


def test_missing_doi_has_stable_fingerprint() -> None:
    first = _hit(None)
    assert bookmark_key(first).startswith("record:")
    assert bookmark_key(first) == bookmark_key(first)


@pytest.mark.parametrize(
    "input_bytes",
    [
        b"invalid",
        b"{}",
        b"[]",
        b'{"format":"wrong"}',
        b'{"format":"abstract-extract-reading-list","version":1,"articles":[3]}',
    ],
)
def test_invalid_restore_rejected(input_bytes: bytes) -> None:
    with pytest.raises(ValueError):
        import_library(input_bytes)


def test_restore_rejects_duplicate_keys() -> None:
    item = from_hit(_hit())
    payload = json.loads(export_library((item,)))
    payload["articles"].append(payload["articles"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        import_library(json.dumps(payload).encode())


def test_restore_rejects_oversized_data() -> None:
    with pytest.raises(ValueError):
        import_library(b" " * 2_000_001)


def test_notes_validation() -> None:
    item = from_hit(_hit())
    with pytest.raises(ValueError):
        update_bookmark(item, note="a" * 4001)
    with pytest.raises(ValueError):
        update_bookmark(item, status="Made up")


def test_exports_citations_and_matrix() -> None:
    item = update_bookmark(
        from_hit(_hit(title="Data & statistics")), note="=HYPERLINK(1)"
    )
    bib = library_bibtex((item,)).decode()
    assert "@misc{" in bib
    assert "10.1234/example" in bib
    assert r"Data \& statistics" in bib
    rows = list(csv.reader(io.StringIO(library_csv((item,)).decode("utf-8-sig"))))
    assert rows[1][-1] == "'=HYPERLINK(1)"
    assert rows[1][-2] == "To read"
