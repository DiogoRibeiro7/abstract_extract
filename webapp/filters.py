"""Pure, first-page search-result filters for the student interface.

Filtering is deliberately local: provider APIs have different query
languages and this module only filters the returned result window.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Literal

from abstract_extract.search import SearchHit, SearchSource
from webapp.viewmodel import readable_abstract

SortOrder = Literal[
    "discovery", "newest", "oldest", "title", "most_sources"
]

_YEAR = re.compile(r"^(\d{4})(?:\D|$)")


def article_year(date: str | None) -> int | None:
    """Extract the known publication year, without guessing missing dates."""
    if not isinstance(date, str):
        return None
    matched = _YEAR.match(date.strip())
    if matched is None:
        return None
    year = int(matched.group(1))
    return year if 1500 <= year <= 2100 else None


def filter_hits(
    hits: Sequence[SearchHit],
    *,
    text: str = "",
    source: SearchSource | None = None,
    abstracts_only: bool = False,
    year_from: int | None = None,
    year_to: int | None = None,
    order: SortOrder = "discovery",
) -> tuple[SearchHit, ...]:
    """Filter and sort only records already returned by the search adapters.

    Args:
        hits: The retrieved first-page results.
        text: Case-insensitive words in title, authors, DOI or abstract.
        source: Restrict results to records discovered by that provider.
        abstracts_only: Exclude papers with no human-readable abstract.
        year_from: Inclusive publication year (undated papers are excluded).
        year_to: Inclusive upper year.
        order: Discovery order, newest/oldest, title, or most source matches.

    Returns:
        A new tuple of hits; input order and data are not modified.
    """
    if year_from is not None and year_to is not None and year_from > year_to:
        raise ValueError("year_from must not exceed year_to")
    if order not in ("discovery", "newest", "oldest", "title", "most_sources"):
        raise ValueError(f"Unsupported sort order: {order}")
    required = text.casefold().strip()
    chosen: list[SearchHit] = []
    for hit in hits:
        article = hit.article
        if source is not None and source not in hit.sources:
            continue
        abstract = readable_abstract(article.abstract)
        if abstracts_only and abstract is None:
            continue
        year = article_year(article.publication_date)
        if (year_from is not None or year_to is not None) and year is None:
            continue
        if year_from is not None and year is not None and year < year_from:
            continue
        if year_to is not None and year is not None and year > year_to:
            continue
        if required:
            searchable = " ".join(
                (
                    article.title or "",
                    " ".join(article.authors),
                    article.doi or "",
                    abstract or "",
                )
            ).casefold()
            if required not in searchable:
                continue
        chosen.append(hit)
    if order == "newest":
        chosen.sort(
            key=lambda h: (
                article_year(h.article.publication_date) is None,
                -(article_year(h.article.publication_date) or 0),
            )
        )
    elif order == "oldest":
        chosen.sort(
            key=lambda h: (
                article_year(h.article.publication_date) is None,
                article_year(h.article.publication_date) or 0,
            )
        )
    elif order == "title":
        chosen.sort(key=lambda h: (h.article.title or "").casefold())
    elif order == "most_sources":
        chosen.sort(key=lambda h: -len(h.sources))
    return tuple(chosen)
