# Development

## Install development dependencies

```bash
poetry install
```

## Quality gates

Run the same checks as CI:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src
poetry run pytest --cov=abstract_extract --cov-report=term-missing
poetry run mkdocs build --strict
```

The test suite enforces a minimum total coverage of 90%.

## Testing rules

Unit tests should remain deterministic.

Avoid dependencies on:

- live Scopus credentials;
- external network availability;
- mutable third-party data;
- test execution order.

Mock the external HTTP boundary rather than internal helper functions where practical.

## Documentation

Serve the documentation locally with:

```bash
poetry run mkdocs serve
```

A strict production build is:

```bash
poetry run mkdocs build --strict
```

Warnings fail the CI documentation step.

## Contribution workflow

Create a focused branch from `main`, add tests for behavioral changes, run all quality checks, and open a pull request.

See `CONTRIBUTING.md` in the repository for the complete contribution policy.
