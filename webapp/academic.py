"""Academic protocol and manual appraisal helpers for teaching and research."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Literal

from abstract_extract.search import SearchHit

Appraisal = Literal["not_assessed", "yes", "partly", "no", "unclear"]


@dataclass(frozen=True, slots=True)
class ReviewProtocol:
    """A research plan, not a claim of systematic-review compliance."""

    title: str
    question: str
    population: str
    intervention: str
    comparator: str
    outcomes: str
    inclusion: str
    exclusion: str
    databases: str
    search_strategy: str
    assessment_notes: str

    def __post_init__(self) -> None:
        """Guard the mandatory fields before producing a protocol."""
        if not self.title.strip() or not self.question.strip():
            raise ValueError("A title and research question are required")


@dataclass(frozen=True, slots=True)
class AppraisalEntry:
    """Manual appraisal; answers remain attributable to a paper."""

    doi: str | None
    title: str | None
    design: str
    question: Appraisal
    methods: Appraisal
    bias: Appraisal
    uncertainty: Appraisal
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate controlled responses without inventing a score."""
        permitted = {"not_assessed", "yes", "partly", "no", "unclear"}
        if any(
            response not in permitted
            for response in (
                self.question, self.methods, self.bias, self.uncertainty
            )
        ):
            raise ValueError("Invalid appraisal response")


def protocol_markdown(protocol: ReviewProtocol) -> str:
    """Export an editable research protocol with explicit missing fields."""
    fields = (
        ("Research question", protocol.question),
        ("Population or context", protocol.population),
        ("Intervention or exposure", protocol.intervention),
        ("Comparison", protocol.comparator),
        ("Outcomes", protocol.outcomes),
        ("Inclusion criteria", protocol.inclusion),
        ("Exclusion criteria", protocol.exclusion),
        ("Databases", protocol.databases),
        ("Search strategy", protocol.search_strategy),
        ("Appraisal plan", protocol.assessment_notes),
    )
    sections = "\n\n".join(
        f"## {label}\n\n{value.strip() or '*Not specified*'}"
        for label, value in fields
    )
    return f"# {protocol.title.strip()}\n\n{sections}\n"


def assignment_markdown(protocol: ReviewProtocol) -> str:
    """Build a student assignment outline from the professor's protocol."""
    return (
        f"# Literature review assignment: {protocol.title.strip()}\n\n"
        f"## Research question\n\n{protocol.question.strip()}\n\n"
        f"## Inclusion criteria\n\n{protocol.inclusion or 'To be defined'}\n\n"
        f"## Exclusion criteria\n\n{protocol.exclusion or 'To be defined'}\n\n"
        "## Tasks\n\n"
        "1. Document every database and search phrase used.\n"
        "2. Read the primary literature and record eligibility decisions.\n"
        "3. Compare methods, limitations, and reported uncertainty.\n"
        "4. Verify DOI and citation metadata before submission.\n"
        "5. Submit an annotated reading list and a critical synthesis.\n\n"
        "## Instructor notes\n\n"
        f"{protocol.assessment_notes or 'Discuss appraisal methods in class.'}\n"
    )


def blank_appraisal(hit: SearchHit) -> AppraisalEntry:
    """Create a neutral, ungraded manual appraisal for a retrieved paper."""
    return AppraisalEntry(
        doi=hit.article.doi,
        title=hit.article.title,
        design="",
        question="not_assessed",
        methods="not_assessed",
        bias="not_assessed",
        uncertainty="not_assessed",
    )


def appraisal_csv(entries: list[AppraisalEntry]) -> bytes:
    """Export manual appraisals as spreadsheet-safe UTF-8 CSV."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([
        "Title", "DOI", "Study design", "Clear question",
        "Methods appropriate", "Bias assessed",
        "Uncertainty reported", "Notes",
    ])
    for entry in entries:
        values = (
            entry.title or "", entry.doi or "", entry.design,
            entry.question, entry.methods, entry.bias,
            entry.uncertainty, entry.notes,
        )
        writer.writerow([
            "'" + value if value.lstrip().startswith(("=", "+", "-", "@"))
            else value for value in values
        ])
    return stream.getvalue().encode("utf-8-sig")


def appraisal_json(entries: list[AppraisalEntry]) -> bytes:
    """Preserve unscored qualitative appraisals for future processing."""
    from dataclasses import asdict

    return json.dumps(
        {"version": 1, "appraisals": [asdict(x) for x in entries]},
        ensure_ascii=False, indent=2,
    ).encode("utf-8")
