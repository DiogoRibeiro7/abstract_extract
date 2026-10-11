"""Offline, student-friendly literature review utilities."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from abstract_extract.search import SearchHit, SearchResponse

Decision = Literal["unreviewed", "include", "exclude", "maybe"]
_DECISIONS = frozenset(("unreviewed", "include", "exclude", "maybe"))


@dataclass(frozen=True, slots=True)
class ReviewEntry:
    """A reviewed work with a stable session identifier and personal notes."""

    key: str
    hit: SearchHit
    decision: Decision = "unreviewed"
    notes: str = ""


def make_entries(report: SearchResponse) -> list[ReviewEntry]:
    """Assign IDs in the original search order; DOI-less works remain distinct."""
    return [
        ReviewEntry(key=f"paper-{index}", hit=hit)
        for index, hit in enumerate(report.results)
    ]


def update_entry(
    entry: ReviewEntry, *, decision: Decision, notes: str
) -> ReviewEntry:
    """Validate user decisions and return a replacement immutable entry."""
    if decision not in _DECISIONS:
        raise ValueError("Unsupported review decision")
    if not isinstance(notes, str):
        raise TypeError("notes must be text")
    return ReviewEntry(
        key=entry.key, hit=entry.hit, decision=decision, notes=notes
    )


def filter_entries(
    entries: Sequence[ReviewEntry],
    *,
    query: str = "",
    decision: str = "all",
    year_from: int | None = None,
    year_to: int | None = None,
    abstracts_only: bool = False,
) -> list[ReviewEntry]:
    """Filter locally without making additional requests to any academic API."""
    if decision not in _DECISIONS | {"all"}:
        raise ValueError("Unsupported decision filter")
    search = query.casefold().strip()
    selected: list[ReviewEntry] = []
    for entry in entries:
        article = entry.hit.article
        year_text = (article.publication_date or "")[:4]
        year = int(year_text) if year_text.isdecimal() else None
        if decision != "all" and entry.decision != decision:
            continue
        if abstracts_only and not (article.abstract or "").strip():
            continue
        if year_from is not None and (year is None or year < year_from):
            continue
        if year_to is not None and (year is None or year > year_to):
            continue
        haystack = " ".join(
            (
                article.title or "",
                article.abstract or "",
                " ".join(article.authors),
                article.doi or "",
                entry.notes,
            )
        ).casefold()
        if search and search not in haystack:
            continue
        selected.append(entry)
    return selected


def _safe_csv(value: str) -> str:
    """Avoid spreadsheet formula evaluation for user/source text fields."""
    cleaned = value.replace("\x00", "")
    if cleaned.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + cleaned
    return cleaned


def review_csv(entries: Sequence[ReviewEntry]) -> bytes:
    """Export a review table with decisions, personal notes and provenance."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        (
            "Title", "Authors", "Year/date", "DOI", "Abstract",
            "Sources", "Decision", "Notes",
        )
    )
    for entry in entries:
        item = entry.hit.article
        writer.writerow(
            [
                _safe_csv(value)
                for value in (
                    item.title or "",
                    "; ".join(item.authors),
                    item.publication_date or "",
                    item.doi or "",
                    item.abstract or "",
                    "; ".join(entry.hit.sources),
                    entry.decision,
                    entry.notes,
                )
            ]
        )
    return stream.getvalue().encode("utf-8-sig")


def review_json(entries: Sequence[ReviewEntry]) -> bytes:
    """Export full results and decisions for reproducibility and later review."""
    result: list[dict[str, object]] = []
    for entry in entries:
        item = entry.hit.article
        result.append(
            {
                "key": entry.key,
                "title": item.title,
                "authors": list(item.authors),
                "date": item.publication_date,
                "doi": item.doi,
                "abstract": item.abstract,
                "sources": list(entry.hit.sources),
                "abstract_source": entry.hit.abstract_source,
                "decision": entry.decision,
                "notes": entry.notes,
            }
        )
    return json.dumps(
        {"schema_version": 1, "articles": result},
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def _bib_escape(value: str) -> str:
    """Escape BibTeX-sensitive input without creating arbitrary commands."""
    return (
        value.replace("\\", r"\textbackslash{}")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("%", r"\%")
        .replace("&", r"\&")
        .replace("#", r"\#")
        .replace("_", r"\_")
    )


def review_bibtex(entries: Sequence[ReviewEntry]) -> str:
    """Export selected articles as BibTeX with unique numeric citation keys."""
    records: list[str] = []
    for index, entry in enumerate(entries, start=1):
        item = entry.hit.article
        fields: list[tuple[str, str]] = []
        if item.title:
            fields.append(("title", item.title))
        if item.authors:
            fields.append(("author", " and ".join(item.authors)))
        if item.publication_date:
            year = item.publication_date[:4]
            if year.isdecimal():
                fields.append(("year", year))
        if item.doi:
            fields.append(("doi", item.doi))
        fields_text = ",\n".join(
            f"  {name} = {{{_bib_escape(value)}}}" for name, value in fields
        )
        records.append(f"@misc{{article{index},\n{fields_text}\n}}")
    return "\n\n".join(records) + ("\n" if records else "")


def selection_counts(entries: Sequence[ReviewEntry]) -> Mapping[str, int]:
    """Count each review decision for the screening dashboard."""
    return {
        option: sum(entry.decision == option for entry in entries)
        for option in ("unreviewed", "include", "exclude", "maybe")
    }
