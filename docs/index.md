<div class="abstract-hero" markdown="1">

# Scholarly metadata, without the API clutter

Retrieve and normalize article metadata from Scopus, enrich abstracts from Crossref, and keep the result in a small typed Python API.

[Get started](getting-started.md){ .md-button .md-button--primary }
[Explore the API](api.md){ .md-button }

</div>

<div class="abstract-cards" markdown="1">

<div markdown="1">

### Query Scopus cleanly

Use explicit timeouts, cursor pagination, optional author filters, and date ranges without mixing transport details into application code.

</div>

<div markdown="1">

### Normalize once

Convert raw Scopus entries into immutable `Article` objects with a stable typed interface.

</div>

<div markdown="1">

### Enrich from Crossref

Retrieve abstracts by DOI while keeping HTTP failures explicit and testable.

</div>

</div>

## What it provides

- Scopus search with explicit request timeouts.
- Cursor-based retrieval of complete result sets.
- Optional author and date-range filtering.
- Typed immutable `Article` records.
- Crossref abstract lookup by DOI.
- Injectable HTTP sessions for deterministic tests.
- Strict mypy, Ruff, pytest, and package smoke tests in CI.

## Design principles

- **Explicit failures.** Network and decoding errors remain visible to callers.
- **Deterministic tests.** Unit tests mock the external HTTP boundary.
- **Typed public API.** Public functions and models are checked with strict mypy.
- **Small runtime surface.** Runtime dependencies stay minimal.
- **Credential hygiene.** Scopus keys are supplied at runtime and never embedded in source.

## Install

```bash
pip install abstract-extract
```

The current release is **0.1.0**. See [Getting started](getting-started.md) for configuration and [Releases](releases.md) for the release process.
