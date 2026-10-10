# API reference

The reference below is generated directly from package source using `mkdocstrings`.

## Article model

::: abstract_extract.models.Article
    options:
      members_order: source

## Scopus

::: abstract_extract.scopus.fetch_from_scopus

::: abstract_extract.scopus.fetch_all_from_scopus

::: abstract_extract.scopus.process_scopus_entries

::: abstract_extract.scopus.process_scopus_response

## Crossref

::: abstract_extract.crossref.get_abstract_from_doi

## OpenAlex

::: abstract_extract.openalex.search_openalex

::: abstract_extract.openalex.reconstruct_abstract

## Semantic Scholar

::: abstract_extract.semantic_scholar.search_semantic_scholar

## PubMed

::: abstract_extract.pubmed.search_pubmed

## Error behavior

HTTP and decoding errors are wrapped as `dataexcept.DataLoadingError`. Invalid input and malformed response shapes raise `ValueError`.
