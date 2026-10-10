"""Portable in-session reading lists, notes and citation exports."""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from abstract_extract.search import SearchHit
from webapp.viewmodel import readable_abstract

MAX_BOOKMARKS = 300
MAX_NOTE_LENGTH = 4000
_KEY_RE = re.compile(r"[^A-Za-z0-9]+")
_TEX_SPECIAL = re.compile(r"([\\{}%$&#_])")


@dataclass(frozen=True, slots=True)
class Bookmark:
    """A selected article with a student's private reading notes."""

    key: str
    title: str
    authors: tuple[str, ...]
    publication_date: str | None
    doi: str | None
    abstract: str | None
    sources: tuple[str, ...]
    note: str = ""
    status: str = "To read"


def bookmark_key(hit: SearchHit) -> str:
    """Prefer DOI; fall back to a stable, non-identifying record fingerprint."""
    import hashlib

    article = hit.article
    if article.doi:
        return "doi:" + article.doi.casefold()
    payload = json.dumps(
        [article.title, article.authors, article.publication_date],
        ensure_ascii=False,
    )
    return "record:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def from_hit(hit: SearchHit) -> Bookmark:
    """Preserve provenance and bibliographic data without fabricating fields."""
    article = hit.article
    return Bookmark(
        key=bookmark_key(hit),
        title=article.title or "Untitled publication",
        authors=article.authors,
        publication_date=article.publication_date,
        doi=article.doi,
        abstract=readable_abstract(article.abstract),
        sources=hit.sources,
    )


def update_bookmark(
    item: Bookmark, *, note: str | None = None, status: str | None = None
) -> Bookmark:
    """Validate and update one student's reading item."""
    from dataclasses import replace

    new_note = item.note if note is None else note
    new_status = item.status if status is None else status
    if len(new_note) > MAX_NOTE_LENGTH:
        raise ValueError("Notes must contain no more than 4000 characters")
    if new_status not in ("To read", "Reading", "Reviewed", "Excluded"):
        raise ValueError("Unknown reading status")
    return replace(item, note=new_note, status=new_status)


def export_library(items: Sequence[Bookmark]) -> bytes:
    """Produce a portable UTF-8 JSON file, without search credentials."""
    payload = {"format": "abstract-extract-reading-list", "version": 1,
               "articles": [asdict(item) for item in items]}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def import_library(raw: bytes) -> tuple[Bookmark, ...]:
    """Restore a bounded student library from its explicitly validated format."""
    if len(raw) > 2_000_000:
        raise ValueError("Reading-list file is too large")
    try:
        payload: Any = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid reading-list JSON") from exc
    if not isinstance(payload, dict) or payload.get("format") != (
        "abstract-extract-reading-list"
    ) or payload.get("version") != 1:
        raise ValueError("Unsupported reading-list format")
    articles = payload.get("articles")
    if not isinstance(articles, list) or len(articles) > MAX_BOOKMARKS:
        raise ValueError("Invalid number of articles")
    restored: list[Bookmark] = []
    seen: set[str] = set()
    for value in articles:
        if not isinstance(value, Mapping):
            raise ValueError("Invalid article entry")
        scalar_fields = ("key", "title", "note", "status")
        if any(not isinstance(value.get(name), str) for name in scalar_fields):
            raise ValueError("Missing article text field")
        if any(
            value.get(name) is not None and not isinstance(value.get(name), str)
            for name in ("doi", "abstract", "publication_date")
        ):
            raise ValueError("Invalid optional article field")
        authors = value.get("authors")
        sources = value.get("sources")
        if not isinstance(authors, list) or not all(
            isinstance(x, str) for x in authors
        ):
            raise ValueError("Invalid authors list")
        if not isinstance(sources, list) or not all(
            isinstance(x, str) for x in sources
        ):
            raise ValueError("Invalid source list")
        item = Bookmark(
            key=value["key"], title=value["title"],
            authors=tuple(authors), publication_date=value.get("publication_date"),
            doi=value.get("doi"), abstract=value.get("abstract"),
            sources=tuple(sources), note=value["note"], status=value["status"],
        )
        item = update_bookmark(item)
        if not item.key or item.key in seen:
            raise ValueError("Duplicate or empty bookmark identifier")
        seen.add(item.key)
        restored.append(item)
    return tuple(restored)


def _safe_cell(value: str) -> str:
    """Escape spreadsheet formula prefixes, including after leading whitespace."""
    result = value.replace("\x00", "")
    return "'" + result if result.lstrip().startswith(("=", "+", "-", "@")) else result


def library_csv(items: Sequence[Bookmark]) -> bytes:
    """Export an annotated reading matrix for a spreadsheet."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        ["Title", "Authors", "Date", "DOI", "Abstract", "Sources",
         "Reading status", "Notes"]
    )
    for item in items:
        writer.writerow([
            _safe_cell(value) for value in (
                item.title, "; ".join(item.authors),
                item.publication_date or "", item.doi or "",
                item.abstract or "", "; ".join(item.sources),
                item.status, item.note,
            )
        ])
    return output.getvalue().encode("utf-8-sig")


def _latex(value: str) -> str:
    """Escape common TeX special characters in citation fields."""
    return _TEX_SPECIAL.sub(lambda match: "\\" + match.group(1), value)


def library_bibtex(items: Sequence[Bookmark]) -> bytes:
    """Export provisional BibTeX records: users must verify publication details."""
    records: list[str] = []
    for index, item in enumerate(items, start=1):
        year_match = re.match(r"^\d{4}", item.publication_date or "")
        year = year_match.group(0) if year_match else ""
        key_title = _KEY_RE.sub("", item.authors[0] if item.authors else "paper")
        citekey = f"{key_title[:18]}{year or 'undated'}_{index}"
        fields = [f"  title = {{{_latex(item.title)}}}"]
        if item.authors:
            fields.append(f"  author = {{{_latex(' and '.join(item.authors))}}}")
        if year:
            fields.append(f"  year = {{{year}}}")
        if item.doi:
            fields.append(f"  doi = {{{_latex(item.doi)}}}")
        records.append("@misc{" + citekey + ",\n" + ",\n".join(fields) + "\n}")
    return ("\n\n".join(records) + ("\n" if records else "")).encode("utf-8")
