# abstract-extract

**abstract-extract** is a small typed Python package for retrieving and normalizing scholarly metadata from Scopus and Crossref.

It focuses on a narrow set of tasks:

- search Scopus with explicit timeouts;
- follow Scopus cursor pagination;
- normalize records into immutable `Article` objects;
- retrieve abstracts from Crossref by DOI;
- expose a typed API that is straightforward to test.

The package targets Python 3.12 and is distributed with typing information.

## Design principles

The library deliberately keeps transport and transformation logic simple.

- **Explicit failures.** HTTP and response-shape errors propagate to callers.
- **Deterministic tests.** Unit tests mock HTTP boundaries rather than calling live services.
- **Typed public API.** Public functions and data models are type annotated and checked with strict mypy.
- **Small dependency surface.** Runtime dependencies are kept minimal.
- **Credential hygiene.** Scopus credentials are supplied at runtime and never embedded in source code.

## Current release

The current release is **0.1.0**.

See the [release guide](releases.md) for versioning and release mechanics.
