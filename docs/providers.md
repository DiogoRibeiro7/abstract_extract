# Literature search providers

The package now supports **OpenAlex**, **Semantic Scholar**, and **PubMed**, alongside existing Scopus searches and Crossref DOI abstract lookups.

Each search adapter returns a `list[Article]` and fetches at most one page (up to 100 records). Provider-specific query languages and relevance rankings differ, so results are not interchangeable. Abstracts may be unavailable and will then be `None`.

## Unified cross-provider search

A federated search combines the selected providers, merges exact DOI matches, and
optionally asks Crossref for any still-missing abstracts. The public result model
retains provider provenance and isolated failures.

```python
from abstract_extract import search_articles

report = search_articles(
    "bayesian change point detection",
    sources=("openalex", "semantic_scholar", "pubmed"),
    max_results=20,
    enrich_abstracts=True,
    on_error="collect",
)

for hit in report.results:
    print(hit.article.title, hit.article.doi)
    print("Found in:", hit.sources)
    print("Abstract from:", hit.abstract_source)

for failure in report.failures:
    print(failure.source, type(failure.error).__name__)
```

**Matching and conflicts.** DOI normalization removes common resolver prefixes,
decodes percent-encoding and compares without case sensitivity. The first selected
provider containing a nonblank value determines each field; later providers fill
missing fields only. Authors are taken from the first nonempty author list.
Records **without a DOI are never deduplicated by title** to avoid false merges.
The output preserves first-seen order rather than attempting to combine
incomparable relevance rankings.

**Error behavior.** The default `on_error="raise"` propagates transport and
malformed-response errors. Use `on_error="collect"` for partial results with
`report.failures` recording the provider, exception, and DOI when the
failed request was a Crossref lookup. Programming errors are not suppressed.
An empty result with nonempty failures **does not prove** that no articles exist.

**Scope.** `max_results` is per provider and limited to the first page,
not a global cap. All provider query syntaxes remain different, and public API
rate limits apply. Crossref fallback is opt-in, requires a DOI, and may return
JATS/XML markup unmodified; it is not counted as a discovery source.

To include Scopus, select it explicitly and provide a key; its page-size limit
is 25, including when other sources are selected:

```python
report = search_articles(
    "TITLE-ABS-KEY(causal inference)",
    sources=("scopus",),
    api_keys={"scopus": "your-scopus-api-key"},
    max_results=25,
)
```

For OpenAlex, Semantic Scholar and PubMed, keys use the same mapping keys
(`"openalex"`, `"semantic_scholar"`, `"pubmed"`). The `email` parameter supplies
NCBI contact information for PubMed. All HTTP requests can share an injected
`requests.Session`.

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

Current scope deliberately excludes pagination across large result sets, rate-limit retries, and bulk export. These are tracked separately.
