# Contributing

Contributions are welcome. Please keep changes focused, reproducible, and easy to review.

## Development setup

Clone the repository and install the development dependencies:

```bash
git clone https://github.com/DiogoRibeiro7/abstract_extract.git
cd abstract_extract
poetry install
```

The project targets Python 3.12.

## Workflow

1. Create a branch from `main`.
2. Make one focused change.
3. Add or update tests when behavior changes.
4. Run the local quality checks.
5. Open a pull request against `main`.
6. Do not merge until the pull request has been reviewed and CI is green.

Prefer small pull requests over broad refactors that mix unrelated concerns.

## Quality checks

Run the same checks enforced by CI:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src
poetry run pytest --cov=abstract_extract --cov-report=term-missing
```

The repository currently enforces a minimum total test coverage of 90%.

## Code guidelines

- Use type annotations for public functions and non-trivial internal interfaces.
- Keep strict mypy compatibility.
- Prefer explicit validation and explicit failure modes.
- Do not swallow HTTP or parsing errors unless the API contract explicitly requires it.
- Keep network access injectable where practical so tests remain deterministic.
- Avoid live external API calls in unit tests.
- Keep public API changes deliberate and document them.
- Do not commit credentials, tokens, local environment files, or generated artifacts.
- Follow Ruff for linting and formatting rather than introducing competing style tools.

## Tests

Behavioral changes should include tests that cover the relevant success and failure paths.

Tests should be deterministic and should not depend on:

- a live Scopus API key;
- external network availability;
- mutable third-party data;
- execution order.

Mock external HTTP boundaries rather than internal implementation details when possible.

## Documentation

Update the README when a change affects:

- installation;
- configuration;
- public API usage;
- required credentials;
- development commands;
- externally visible behavior.

## Pull requests

A pull request should explain:

- what changed;
- why the change is needed;
- how it was tested;
- whether it changes the public API.

Keep commit and pull-request descriptions factual and specific to the change.
