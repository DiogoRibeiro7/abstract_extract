# Usage

## Fetch one Scopus page

```python
from abstract_extract import fetch_from_scopus

response = fetch_from_scopus(
    query="bayesian changepoint detection",
    api_key="your-api-key",
    max_results=25,
)
```

This returns the raw Scopus JSON object as a Python dictionary.

## Fetch all Scopus pages

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

Cursor pagination is handled automatically.

When filtering by date, both `start_date` and `end_date` must be provided.

## Normalize Scopus records

```python
from abstract_extract import process_scopus_entries

articles = process_scopus_entries(entries)

for article in articles:
    print(article.title, article.doi)
```

The normalized result is a list of immutable `Article` objects.

## Normalize a single Scopus response

```python
from abstract_extract import fetch_from_scopus, process_scopus_response

response = fetch_from_scopus(
    query="uncertainty quantification",
    api_key="your-api-key",
)

articles = process_scopus_response(response)
```

## Retrieve an abstract from Crossref

```python
from abstract_extract import get_abstract_from_doi

abstract = get_abstract_from_doi("10.1000/example")
```

The return value is `str | None`.

Crossref may return JATS/XML markup in the abstract field. Version 0.1.0 returns that value unchanged.

## HTTP sessions

The request functions accept an optional `requests.Session`. This supports connection reuse in applications and deterministic substitution in tests.
