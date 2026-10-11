"""Tests for professor and researcher workspaces."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import replace

import pytest

from abstract_extract.models import Article
from abstract_extract.search import SearchHit
from webapp.academic import (
    AppraisalEntry,
    ReviewProtocol,
    appraisal_csv,
    appraisal_json,
    assignment_markdown,
    blank_appraisal,
    protocol_markdown,
)


def _protocol() -> ReviewProtocol:
    return ReviewProtocol(
        title="Time-series reviews",
        question="Do change-point methods improve detection?",
        population="Health sensors",
        intervention="Detection algorithms",
        comparator="Baseline",
        outcomes="Detection delay",
        inclusion="Peer-reviewed studies",
        exclusion="No methods",
        databases="OpenAlex; PubMed",
        search_strategy="change-point detection",
        assessment_notes="Check bias and uncertainty",
    )


def test_protocol_and_assignment_exports() -> None:
    protocol = _protocol()
    assert "## Databases" in protocol_markdown(protocol)
    assert "OpenAlex; PubMed" in protocol_markdown(protocol)
    assert "Document every database" in assignment_markdown(protocol)


def test_protocol_rejects_missing_essential_fields() -> None:
    with pytest.raises(ValueError, match="title"):
        replace(_protocol(), question="")


def test_manual_appraisal_starts_ungraded() -> None:
    hit = SearchHit(
        Article("A paper", None, "2025", (), "10.1/example"),
        ("pubmed",),
        None,
    )
    entry = blank_appraisal(hit)
    assert entry.question == "not_assessed"
    assert entry.title == "A paper"
    assert entry.design == ""


def test_exports_preserve_appraisals_and_escape_formulas() -> None:
    entry = AppraisalEntry(
        doi="10.1/test",
        title="=SUM(1)",
        design="Survey",
        question="yes",
        methods="partly",
        bias="unclear",
        uncertainty="no",
        notes="+CMD",
    )
    rows = list(csv.reader(io.StringIO(appraisal_csv([entry]).decode("utf-8-sig"))))
    assert rows[1][0] == "'=SUM(1)"
    assert rows[1][-1] == "'+CMD"
    restored = json.loads(appraisal_json([entry]))
    assert restored["appraisals"][0]["bias"] == "unclear"


def test_invalid_appraisal_option_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        AppraisalEntry(
            doi=None,
            title=None,
            design="",
            question="excellent",
            methods="yes",
            bias="no",
            uncertainty="unclear",
        )
