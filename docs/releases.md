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
8. creates the GitHub release and attaches both artifacts;
9. downloads those exact release artifacts in a separate trusted-publishing job;
10. publishes them to PyPI using OpenID Connect, without a stored PyPI API token.

## PyPI trusted publishing

PyPI publishing uses the GitHub environment named `pypi` and requires `id-token: write` only in the publishing job.

Configure the PyPI trusted publisher with:

- **PyPI project:** `abstract-extract`
- **GitHub owner:** `DiogoRibeiro7`
- **Repository:** `abstract_extract`
- **Workflow:** `release.yml`
- **Environment:** `pypi`

For the first publication, use PyPI's pending trusted publisher flow if the project does not yet exist.

The GitHub `pypi` environment can also be protected with deployment approval rules if desired.

## Publishing an existing GitHub release

The release workflow supports manual dispatch with a release tag. This is intended for publishing an already-created GitHub release, such as `v0.1.0`, after trusted publishing has been configured.

The manual workflow checks out the specified tag, validates that its package version matches, reruns the quality and build checks, verifies that the GitHub release exists, and publishes the artifacts already attached to that release.

## Current release

Version **0.1.0** was released from the repository's first professionalized package baseline and is available on [PyPI](https://pypi.org/project/abstract-extract/0.1.0/).

Install it with:

```bash
pip install abstract-extract==0.1.0
```
