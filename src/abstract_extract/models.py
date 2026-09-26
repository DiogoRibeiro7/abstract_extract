"""Domain models exposed by abstract_extract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Article:
    """Normalized metadata for a scholarly article."""

    title: str | None
    abstract: str | None
    publication_date: str | None
    authors: tuple[str, ...]
    doi: str | None
