"""Offline contract tests for the literature search providers."""

from unittest.mock import MagicMock

import pytest
import requests
from dataexcept import DataLoadingError

from abstract_extract import search_openalex, search_pubmed, search_semantic_scholar
from abstract_extract.openalex import OPENALEX_URL, reconstruct_abstract
from abstract_extract.pubmed import EFETCH_URL, ESEARCH_URL
from abstract_extract.semantic_scholar import SEMANTIC_SCHOLAR_URL


def _response(*, payload: object = None, content: bytes = b"") -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.content = content
    return response


def test_openalex_reconstructs_abstract_and_normalizes_doi() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"results": [{
        "title": "Study", "doi": "https://doi.org/10.1234/study",
        "publication_date": "2025-02-10",
        "abstract_inverted_index": {"A": [0], "study": [1], "today": [2]},
        "authorships": [{"author": {"display_name": "Ada"}}],
    }]})
    articles = search_openalex("  statistical inference ", session=session, max_results=10)
    assert len(articles) == 1
    assert articles[0].abstract == "A study today"
    assert articles[0].doi == "10.1234/study"
    assert articles[0].authors == ("Ada",)
    session.get.assert_called_once_with(
        OPENALEX_URL, params={"search": "statistical inference", "per_page": 10},
        timeout=30.0,
    )


@pytest.mark.parametrize("index", [{ "a": [1] }, {"a": [0], "b": [0]}, {"a": [-1]}, "bad"])
def test_openalex_rejects_invalid_indices(index: object) -> None:
    with pytest.raises(ValueError):
        reconstruct_abstract(index)


def test_semantic_scholar_maps_abstract_and_year() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"data": [{
        "title": "Paper", "abstract": "Findings", "year": 2024,
        "authors": [{"name": "Alice"}], "externalIds": {"DOI": "10.42/paper"},
    }]})
    articles = search_semantic_scholar("causal inference", session=session, api_key=" secret ")
    assert articles[0].abstract == "Findings"
    assert articles[0].publication_date == "2024"
    assert articles[0].doi == "10.42/paper"
    args, kwargs = session.get.call_args
    assert args == (SEMANTIC_SCHOLAR_URL,)
    assert kwargs["headers"]["x-api-key"] == "secret"


def test_pubmed_search_and_efetch_xml() -> None:
    xml = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><Article>
    <ArticleTitle>Clinical <i>study</i></ArticleTitle>
    <Abstract><AbstractText Label="METHODS">Data <b>collection</b>.</AbstractText>
    <AbstractText Label="RESULTS">Significant effects.</AbstractText></Abstract>
    <AuthorList><Author><ForeName>Ada</ForeName><LastName>Jones</LastName></Author></AuthorList>
    <Journal><JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue></Journal>
    </Article></MedlineCitation><PubmedData><ArticleIdList>
    <ArticleId IdType="doi">10.42/clinical</ArticleId>
    </ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = [
        _response(payload={"esearchresult": {"idlist": ["111"]}}),
        _response(content=xml),
    ]
    articles = search_pubmed("time series", session=session, email="contact@example.org")
    assert articles[0].title == "Clinical study"
    assert articles[0].abstract == "METHODS: Data collection. RESULTS: Significant effects."
    assert articles[0].authors == ("Ada Jones",)
    assert articles[0].doi == "10.42/clinical"
    assert session.get.call_args_list[0].args == (ESEARCH_URL,)
    assert session.get.call_args_list[1].args == (EFETCH_URL,)


def test_pubmed_empty_results_does_not_efetch() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"esearchresult": {"idlist": []}})
    assert search_pubmed("none", session=session) == []
    session.get.assert_called_once()


@pytest.mark.parametrize("search", [search_openalex, search_semantic_scholar, search_pubmed])
def test_providers_reject_empty_query(search: object) -> None:
    assert callable(search)
    with pytest.raises(ValueError, match="query"):
        search(" ")


@pytest.mark.parametrize("search", [search_openalex, search_semantic_scholar, search_pubmed])
def test_providers_reject_nonpositive_timeout(search: object) -> None:
    assert callable(search)
    with pytest.raises(ValueError, match="timeout"):
        search("query", timeout=0)


@pytest.mark.parametrize("search", [search_openalex, search_semantic_scholar, search_pubmed])
def test_providers_reject_invalid_result_count(search: object) -> None:
    assert callable(search)
    with pytest.raises(ValueError, match="max_results"):
        search("query", max_results=101)


@pytest.mark.parametrize("search,endpoint", [
    (search_openalex, OPENALEX_URL),
    (search_semantic_scholar, SEMANTIC_SCHOLAR_URL),
    (search_pubmed, ESEARCH_URL),
])
def test_provider_http_errors_preserve_source(search: object, endpoint: str) -> None:
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = requests.Timeout("timeout")
    with pytest.raises(DataLoadingError) as caught:
        search("query", session=session)
    assert caught.value.source == endpoint


def test_pubmed_rejects_malformed_xml() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = [
        _response(payload={"esearchresult": {"idlist": ["1"]}}),
        _response(content=b"<invalid"),
    ]
    with pytest.raises(ValueError, match="XML"):
        search_pubmed("query", session=session)
