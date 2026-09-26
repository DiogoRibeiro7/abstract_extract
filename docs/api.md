# API reference

The reference below is generated directly from the package source. Function signatures,
type annotations, parameter descriptions, return values, and documented exceptions stay
synchronized with the code through `mkdocstrings`.

## Article model

::: abstract_extract.models.Article
    options:
      members_order: source

## Scopus

### fetch_from_scopus

::: abstract_extract.scopus.fetch_from_scopus

### fetch_all_from_scopus

::: abstract_extract.scopus.fetch_all_from_scopus

### process_scopus_entries

::: abstract_extract.scopus.process_scopus_entries

### process_scopus_response

::: abstract_extract.scopus.process_scopus_response

## Crossref

### get_abstract_from_doi

::: abstract_extract.crossref.get_abstract_from_doi

## Error behavior

Network failures, HTTP errors, and JSON decoding failures from Scopus and Crossref are
wrapped as `dataexcept.DataLoadingError`. Invalid input and malformed response shapes
raise `ValueError`.
