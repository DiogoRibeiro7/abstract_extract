# API reference

The supported top-level API is exported from `abstract_extract`.

## `Article`

```python
@dataclass(frozen=True, slots=True)
class Article:
    title: str | None
    abstract: str | None
    publication_date: str | None
    authors: tuple[str, ...]
    doi: str | None
```

A normalized immutable scholarly article record.

## `fetch_from_scopus`

```python
fetch_from_scopus(
    query: str,
    api_key: str,
    *,
    max_results: int = 25,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]
```

Fetches one Scopus search page.

The function validates non-empty `query` and `api_key`, requires `max_results` between 1 and 25, and rejects non-positive timeouts.

## `fetch_all_from_scopus`

```python
fetch_all_from_scopus(
    query: str,
    api_key: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    author: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> list[dict[str, Any]]
```

Fetches all Scopus entries available through cursor pagination.

Date bounds must be supplied together.

## `process_scopus_entries`

```python
process_scopus_entries(
    entries: Iterable[Mapping[str, Any]],
) -> list[Article]
```

Converts raw Scopus entry mappings into `Article` objects.

## `process_scopus_response`

```python
process_scopus_response(
    payload: Mapping[str, Any],
) -> list[Article]
```

Extracts the `search-results.entry` collection from a single Scopus response and normalizes it.

## `get_abstract_from_doi`

```python
get_abstract_from_doi(
    doi: str,
    *,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> str | None
```

Retrieves the Crossref abstract field for a DOI.

Returns `None` when Crossref provides no abstract. HTTP failures and malformed response shapes are propagated rather than converted into sentinel strings.
