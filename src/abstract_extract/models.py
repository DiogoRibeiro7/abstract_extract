"""Domain models exposed by :mod:`abstract_extract`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Article:
    """Normalized metadata for a scholarly article.

    Attributes:
        title: Article title when supplied by the upstream service.
        abstract: Article abstract when available.
        publication_date: Publication date as returned by the upstream service.
        authors: Author names in source order.
        doi: Digital Object Identifier when available.
    """

    title: str | None
    abstract: str | None
    publication_date: str | None
    authors: tuple[str, ...]
    doi: str | None
