# Changelog

All notable changes to this project will be documented in this file.

The project follows Semantic Versioning. Changes are grouped under an `Unreleased`
section until a version is tagged.

## Unreleased

### Added

- Added PyPI trusted publishing through the release workflow, using OIDC instead of stored API tokens.

### Changed

- Restricted the supported Python range to 3.12–3.14, matching the versions exercised in CI.

## 0.1.0 - 2026-09-26

### Added

- Typed Python package layout under `src/abstract_extract`.
- Scopus search and cursor-pagination utilities.
- Crossref abstract retrieval by DOI.
- Immutable `Article` model.
- Deterministic unit tests with a 90% coverage floor.
- Ruff, strict mypy, and pytest quality gates in CI.
- Project, contribution, security, and issue-reporting documentation.
- Conservative Dependabot configuration.
- Tag-driven GitHub release workflow.
- Distribution metadata and a `py.typed` marker.

### Security

- Removed hard-coded Scopus credentials from the public source tree.
- Added explicit guidance for credential handling and vulnerability reporting.

## Release convention

Before creating a release:

1. Move relevant entries from `Unreleased` into a versioned section.
2. Update the version in `pyproject.toml`.
3. Merge the release preparation into `main`.
4. Create and push a tag named `vX.Y.Z` that exactly matches the project version.

The release workflow verifies the tag/version match, runs all quality gates, builds the
source distribution and wheel, and creates the GitHub release only if every step passes.
