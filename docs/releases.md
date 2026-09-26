# Releases

The project follows Semantic Versioning.

## Release preparation

Before tagging a release:

1. move completed entries from `Unreleased` into a dated version section in `CHANGELOG.md`;
2. update the version in `pyproject.toml`;
3. merge the release preparation into `main`;
4. confirm CI is green on the exact release commit;
5. create a tag named `vX.Y.Z`.

## Automated release checks

A tag matching `v*.*.*` triggers the release workflow.

The workflow:

1. validates package metadata with `poetry check`;
2. verifies that the tag exactly matches the Poetry version;
3. installs dependencies;
4. runs Ruff linting and formatting checks;
5. runs strict mypy;
6. runs the tests and coverage gate;
7. builds the wheel and source distribution;
8. creates the GitHub release and attaches both artifacts.

## Current release

Version **0.1.0** was released from the repository's first professionalized package baseline.
