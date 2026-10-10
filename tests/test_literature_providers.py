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
    session.get.return_value = _response(
        payload={
            "results": [
                {
                    "title": "Study",
                    "doi": "https://doi.org/10.1234/study",
                    "publication_date": "2025-02-10",
                    "abstract_inverted_index": {
                        "A": [0],
                        "study": [1],
                        "today": [2],
                    },
                    "authorships": [{"author": {"display_name": "Ada"}}],
                }
            ]
        }
    )
    articles = search_openalex(
        "  statistical inference ", session=session, max_results=10
    )
    assert len(articles) == 1
    assert articles[0].abstract == "A study today"
    assert articles[0].doi == "10.1234/study"
    assert articles[0].authors == ("Ada",)
    session.get.assert_called_once_with(
        OPENALEX_URL,
        params={"search": "statistical inference", "per_page": 10},
        timeout=30.0,
    )


@pytest.mark.parametrize(
    "index", [{"a": [1]}, {"a": [0], "b": [0]}, {"a": [-1]}, "bad"]
)
def test_openalex_rejects_invalid_indices(index: object) -> None:
    with pytest.raises(ValueError):
        reconstruct_abstract(index)


def test_semantic_scholar_maps_abstract_and_year() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(
        payload={
            "data": [
                {
                    "title": "Paper",
                    "abstract": "Findings",
                    "year": 2024,
                    "authors": [{"name": "Alice"}],
                    "externalIds": {"DOI": "10.42/paper"},
                }
            ]
        }
    )
    articles = search_semantic_scholar(
        "causal inference", session=session, api_key=" secret "
    )
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
    articles = search_pubmed(
        "time series", session=session, email="contact@example.org"
    )
    assert articles[0].title == "Clinical study"
    assert articles[0].abstract == (
        "METHODS: Data collection. RESULTS: Significant effects."
    )
    assert articles[0].authors == ("Ada Jones",)
    assert articles[0].doi == "10.42/clinical"
    assert session.get.call_args_list[0].args == (ESEARCH_URL,)
    assert session.get.call_args_list[1].args == (EFETCH_URL,)


def test_pubmed_empty_results_does_not_efetch() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"esearchresult": {"idlist": []}})
    assert search_pubmed("none", session=session) == []
    session.get.assert_called_once()


@pytest.mark.parametrize(
    "search", [search_openalex, search_semantic_scholar, search_pubmed]
)
def test_providers_reject_empty_query(search: object) -> None:
    assert callable(search)
    with pytest.raises(ValueError, match="query"):
        search(" ")


@pytest.mark.parametrize(
    "search", [search_openalex, search_semantic_scholar, search_pubmed]
)
def test_providers_reject_nonpositive_timeout(search: object) -> None:
    assert callable(search)
    with pytest.raises(ValueError, match="timeout"):
        search("query", timeout=0)


@pytest.mark.parametrize(
    "search", [search_openalex, search_semantic_scholar, search_pubmed]
)
def test_providers_reject_invalid_result_count(search: object) -> None:
    assert callable(search)
    with pytest.raises(ValueError, match="max_results"):
        search("query", max_results=101)


@pytest.mark.parametrize(
    ("search", "endpoint"),
    [
        (search_openalex, OPENALEX_URL),
        (search_semantic_scholar, SEMANTIC_SCHOLAR_URL),
        (search_pubmed, ESEARCH_URL),
    ],
)
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


def test_openalex_empty_abstract_and_missing_metadata() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(
        payload={"results": [{"abstract_inverted_index": None, "authorships": []}]}
    )
    items = search_openalex("topic", session=session)
    assert len(items) == 1
    assert items[0].abstract is None
    assert items[0].title is None
    assert items[0].authors == ()
    assert items[0].doi is None


def test_openalex_rejects_nonobject_result() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"results": [42]})
    with pytest.raises(ValueError, match="work"):
        search_openalex("topic", session=session)


def test_openalex_rejects_invalid_authorships() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(
        payload={"results": [{"authorships": "invalid"}]}
    )
    with pytest.raises(ValueError, match="authorships"):
        search_openalex("topic", session=session)


def test_openalex_rejects_invalid_payload() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={})
    with pytest.raises(ValueError, match="results"):
        search_openalex("topic", session=session)


def test_openalex_reconstructs_empty_index() -> None:
    assert reconstruct_abstract({}) is None


def test_openalex_rejects_nonlist_positions() -> None:
    with pytest.raises(ValueError, match="inverted-index"):
        reconstruct_abstract({"word": 5})


def test_semantic_scholar_rejects_invalid_payload() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"data": {}})
    with pytest.raises(ValueError, match="data"):
        search_semantic_scholar("topic", session=session)


def test_semantic_scholar_rejects_nonobject_paper() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"data": [None]})
    with pytest.raises(ValueError, match="paper"):
        search_semantic_scholar("topic", session=session)


def test_semantic_scholar_rejects_invalid_authors() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"data": [{"authors": None}]})
    with pytest.raises(ValueError, match="authors"):
        search_semantic_scholar("topic", session=session)


def test_semantic_scholar_missing_abstract_is_none() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(
        payload={"data": [{"title": "No abstract", "authors": []}]}
    )
    result = search_semantic_scholar("topic", session=session)
    assert result[0].abstract is None
    assert result[0].doi is None


def test_pubmed_rejects_invalid_search_response() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={})
    with pytest.raises(ValueError, match="esearchresult"):
        search_pubmed("topic", session=session)


def test_pubmed_rejects_invalid_identifier_list() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(payload={"esearchresult": {"idlist": [12]}})
    with pytest.raises(ValueError, match="idlist"):
        search_pubmed("topic", session=session)


def test_pubmed_skips_records_without_article() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = [
        _response(payload={"esearchresult": {"idlist": ["12"]}}),
        _response(content=b"<PubmedArticleSet><PubmedArticle/></PubmedArticleSet>"),
    ]
    assert search_pubmed("topic", session=session) == []


def test_pubmed_returns_none_for_missing_abstract() -> None:
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = [
        _response(payload={"esearchresult": {"idlist": ["12"]}}),
        _response(
            content=(
                b"<PubmedArticleSet><PubmedArticle><MedlineCitation>"
                b"<Article><ArticleTitle>Title</ArticleTitle></Article>"
                b"</MedlineCitation></PubmedArticle></PubmedArticleSet>"
            )
        ),
    ]
    items = search_pubmed("topic", session=session)
    assert items[0].title == "Title"
    assert items[0].abstract is None
    assert items[0].publication_date is None
    assert items[0].authors == ()


@pytest.mark.parametrize(
    ("provider", "options"),
    [
        (search_openalex, {"api_key": " "}),
        (search_semantic_scholar, {"api_key": " "}),
        (search_pubmed, {"api_key": " "}),
        (search_pubmed, {"email": " "}),
    ],
)
def test_provider_rejects_blank_optional_credentials(
    provider: object, options: dict[str, str]
) -> None:
    assert callable(provider)
    with pytest.raises(ValueError, match="empty"):
        provider("topic", **options)


@pytest.mark.parametrize(
    "provider", [search_openalex, search_semantic_scholar, search_pubmed]
)
def test_providers_close_owned_sessions(
    provider: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = requests.Timeout("offline")
    monkeypatch.setattr(requests, "Session", lambda: session)
    with pytest.raises(DataLoadingError):
        provider("topic")
    session.close.assert_called_once_with()
