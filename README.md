# abstract-extract

[![CI](https://github.com/DiogoRibeiro7/abstract_extract/actions/workflows/ci.yml/badge.svg)](https://github.com/DiogoRibeiro7/abstract_extract/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Typed Python utilities for retrieving and normalizing scholarly article metadata and abstracts from **Scopus** and **Crossref**.

The package provides a small, explicit API for querying Scopus, following cursor-based pagination, converting raw Scopus records into typed `Article` objects, and retrieving abstracts from Crossref by DOI.

## Features

- Scopus search with explicit request timeouts.
- Cursor-based retrieval of complete Scopus result sets.
- Optional author and date-range filtering.
- Typed immutable `Article` model.
- Normalization of raw Scopus records.
- Crossref abstract lookup by DOI.
- Injectable HTTP sessions for testing and connection reuse.
- Strict static typing with mypy.
- Ruff linting and formatting.
- Deterministic unit tests with no live API calls.
- CI-enforced test coverage.

## Requirements

- Python 3.12
- Poetry
- A Scopus API key for Scopus requests

Crossref requests do not require a Scopus API key.

## Installation

Clone the repository and install the project with Poetry:

```bash
git clone https://github.com/DiogoRibeiro7/abstract_extract.git
cd abstract_extract
poetry install
```

The package can then be used inside the Poetry environment:

```bash
poetry run python
```

## Scopus credentials

Do not store API keys in source code.

Copy the example environment file:

```bash
cp .env.example .env
```

Set your Scopus key locally:

```text
SCOPUS_API_KEY=your-scopus-api-key
```

The package itself accepts the API key explicitly. Applications can load it from their preferred environment/configuration mechanism.

For example:

```python
import os

from abstract_extract import fetch_from_scopus

api_key = os.environ["SCOPUS_API_KEY"]

response = fetch_from_scopus(
    query="changepoint detection",
    api_key=api_key,
    max_results=10,
)
```

## Usage

### Fetch one page from Scopus

```python
from abstract_extract import fetch_from_scopus

response = fetch_from_scopus(
    query="bayesian changepoint detection",
    api_key="your-api-key",
    max_results=25,
)
```

`fetch_from_scopus` returns the raw Scopus JSON response as a dictionary.

### Fetch all Scopus results

```python
from abstract_extract import fetch_all_from_scopus

entries = fetch_all_from_scopus(
    query="time series forecasting",
    api_key="your-api-key",
    author="Jane Doe",
    start_date="2020-01-01",
    end_date="2026-01-01",
)
```

Pagination is handled automatically using the Scopus cursor returned by each page.

If a date range is used, both `start_date` and `end_date` must be supplied.

### Normalize Scopus entries

```python
from abstract_extract import process_scopus_entries

articles = process_scopus_entries(entries)

for article in articles:
    print(article.title)
    print(article.doi)
    print(article.authors)
```

Each item is returned as an immutable `Article`:

```python
from abstract_extract import Article

article = Article(
    title="Example paper",
    abstract="Example abstract",
    publication_date="2026-01-01",
    authors=("Alice Example", "Bob Example"),
    doi="10.1000/example",
)
```

### Normalize a single Scopus response

For a raw response returned by `fetch_from_scopus`:

```python
from abstract_extract import fetch_from_scopus, process_scopus_response

response = fetch_from_scopus(
    query="uncertainty quantification",
    api_key="your-api-key",
)

articles = process_scopus_response(response)
```

### Retrieve an abstract from Crossref

```python
from abstract_extract import get_abstract_from_doi

abstract = get_abstract_from_doi("10.1000/example")

if abstract is not None:
    print(abstract)
```

Crossref may return abstracts containing JATS/XML markup. The package currently returns that value unchanged.

## Public API

The supported top-level interface is:

```python
from abstract_extract import (
    Article,
    fetch_all_from_scopus,
    fetch_from_scopus,
    get_abstract_from_doi,
    process_scopus_entries,
    process_scopus_response,
)
```

HTTP and response-shape errors are intentionally propagated to callers rather than converted into sentinel values. This keeps failure handling explicit.

## Development

Install all dependencies:

```bash
poetry install
```

Run the same checks enforced by CI:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src
poetry run pytest --cov=abstract_extract --cov-report=term-missing
```

The coverage configuration enforces a minimum total coverage of 90%.

## Project structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── abstract_extract/
│       ├── __init__.py
│       ├── crossref.py
│       ├── models.py
│       └── scopus.py
├── tests/
├── .env.example
├── pyproject.toml
└── LICENSE
```

## Security

Credentials must be supplied at runtime and must not be committed to the repository.

If a credential is accidentally exposed in Git history, removing it from the current source tree is not sufficient. Revoke or rotate the credential at its provider.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
