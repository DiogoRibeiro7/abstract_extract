# Literature search providers

The package now supports **OpenAlex**, **Semantic Scholar**, and **PubMed**, alongside existing Scopus searches and Crossref DOI abstract lookups.

Each search adapter returns a `list[Article]` and fetches at most one page (up to 100 records). Provider-specific query languages and relevance rankings differ, so results are not interchangeable. Abstracts may be unavailable and will then be `None`.

## OpenAlex

```python
from abstract_extract import search_openalex

articles = search_openalex("causal inference", max_results=20)
for article in articles:
    print(article.title, article.abstract)
```

OpenAlex abstracts are reconstructed from the API's inverted-index representation. Depending on your API access, supply `api_key="..."`; check the provider's current access requirements.

## Semantic Scholar

```python
from abstract_extract import search_semantic_scholar

articles = search_semantic_scholar(
    "gaussian process regression",
    max_results=20,
    api_key="your-optional-key",
)
```

An API key may improve access or quotas; unauthenticated access can be limited. Rate limits and usage requirements are governed by the provider.

## PubMed

```python
from abstract_extract import search_pubmed

articles = search_pubmed(
    "change point detection[Title/Abstract]",
    max_results=20,
    email="researcher@example.org",
)
```

PubMed uses ESearch to retrieve identifiers, then EFetch to read article metadata and abstracts. Set `email` and optionally `api_key` for NCBI-compliant usage. Publication dates are currently returned as a year if available.

## Reliability

All adapters accept a `requests.Session` and an explicit request `timeout`. HTTP and JSON failures raise `dataexcept.DataLoadingError`; structurally invalid responses raise `ValueError`. API credentials must not be committed to the repository.

Current scope deliberately excludes pagination across large result sets, cross-provider de-duplication, and rate-limit retries. These are tracked in separate GitHub issues.
