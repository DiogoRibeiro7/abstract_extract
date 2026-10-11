"""Unit tests for the session-based student review workflow."""

from __future__ import annotations

import csv
import io
import json

import pytest

from abstract_extract.models import Article
from abstract_extract.search import SearchHit, SearchResponse
from webapp.review import (
    filter_entries,
    make_entries,
    review_bibtex,
    review_csv,
    review_json,
    selection_counts,
    update_entry,
)


def _entries() -> list:
    """Create two papers with different metadata and DOI availability."""
    a = SearchHit(
        Article("=Risk study", "Risk abstract", "2024-01-01", ("Ada",), "10.1/a"),
        ("openalex",),
        "openalex",
    )
    b = SearchHit(
        Article("Forecast", None, None, ("Bob",), None),
        ("pubmed",),
        None,
    )
    return make_entries(SearchResponse((a, b), ()))


def test_entry_identifiers_and_counts() -> None:
    entries = _entries()
    assert [e.key for e in entries] == ["paper-0", "paper-1"]
    assert selection_counts(entries)["unreviewed"] == 2


def test_screening_is_immutable_and_validated() -> None:
    entries = _entries()
    changed = update_entry(entries[0], decision="include", notes="Important")
    assert changed.decision == "include"
    assert changed.notes == "Important"
    assert entries[0].decision == "unreviewed"
    with pytest.raises(ValueError):
        update_entry(entries[0], decision="unknown", notes="")


def test_review_filters() -> None:
    entries = _entries()
    entries[0] = update_entry(entries[0], decision="include", notes="Useful")
    assert filter_entries(entries, decision="include") == [entries[0]]
    assert filter_entries(entries, query="useful") == [entries[0]]
    assert filter_entries(entries, query="forecast") == [entries[1]]
    assert filter_entries(entries, abstracts_only=True) == [entries[0]]
    assert filter_entries(entries, year_from=2023) == [entries[0]]
    assert filter_entries(entries, year_to=2023) == []
    with pytest.raises(ValueError):
        filter_entries(entries, decision="invalid")


def test_csv_json_and_bibtex_exports() -> None:
    entries = _entries()
    entries[0] = update_entry(entries[0], decision="include", notes="=SUM(A1)")
    csv_content = review_csv(entries).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(csv_content)))
    assert rows[1][0] == "'=Risk study"
    assert rows[1][-1] == "'=SUM(A1)"
    assert rows[1][-2] == "include"
    assert len(rows) == 3
    decoded = json.loads(review_json(entries))
    assert decoded["schema_version"] == 1
    assert decoded["articles"][0]["notes"] == "=SUM(A1)"
    bib = review_bibtex(entries)
    assert "@misc{article1," in bib
    assert "year = {2024}" in bib
    assert "doi = {10.1/a}" in bib
    assert "@misc{article2," in bib


def test_bibtex_escapes_control_characters() -> None:
    entries = _entries()
    modified = Article(r"A {title} & 50% of study", None, None, (), None)
    first = entries[0]
    replaced = SearchHit(modified, first.hit.sources, first.hit.abstract_source)
    from webapp.review import ReviewEntry

    bib = review_bibtex([ReviewEntry("x", replaced)])
    assert r"\{" in bib and r"\%" in bib and r"\&" in bib


def test_empty_exports() -> None:
    assert review_bibtex([]) == ""
    assert json.loads(review_json([]))["articles"] == []
    assert len(review_csv([])) > 0
