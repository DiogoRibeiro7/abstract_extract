"""Offline contract tests for unified scholarly search."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

import abstract_extract.search as search_module
from abstract_extract.models import Article
from abstract_extract.search import normalize_doi, search_articles


def _article(
    doi: str | None = "10.1234/example",
    *,
    title: str | None = "Title",
    abstract: str | None = None,
    publication_date: str | None = None,
    authors: tuple[str, ...] = (),
) -> Article:
    """Make a complete immutable article fixture."""
    return Article(
        title=title,
        abstract=abstract,
        publication_date=publication_date,
        authors=authors,
        doi=doi,
    )


def _provider(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    result: list[Article] | Exception,
) -> MagicMock:
    """Replace a selected adapter with a deterministic mock."""
    mock = MagicMock()
    if isinstance(result, Exception):
        mock.side_effect = result
    else:
        mock.return_value = result
    attr = {
        "openalex": "search_openalex",
        "semantic_scholar": "search_semantic_scholar",
        "pubmed": "search_pubmed",
    }[name]
    monkeypatch.setattr(search_module, attr, mock)
    return mock


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (" ", None),
        (" 10.1234/XYz ", "10.1234/xyz"),
        ("DOI: 10.1234/AbC", "10.1234/abc"),
        ("https://doi.org/10.1234/Foo%2FBar", "10.1234/foo/bar"),
        ("http://dx.doi.org/10.1234/Q", "10.1234/q"),
        ("doi: https://doi.org/10.1234/XYZ", "10.1234/xyz"),
    ],
)
def test_normalize_doi(value: str | None, expected: str | None) -> None:
    assert normalize_doi(value) == expected


def test_dedup_preserves_first_source_and_fills_missing_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata conflicts use source order, not whichever provider ran last."""
    _provider(
        monkeypatch,
        "openalex",
        [
            _article(
                "doi: https://doi.org/10.1111/TEST",
                title="Original title",
                abstract=" ",
            )
        ],
    )
    _provider(
        monkeypatch,
        "semantic_scholar",
        [
            _article(
                "10.1111/test",
                title="Conflicting title",
                abstract="Provider abstract",
                publication_date="2025-02-03",
                authors=("Second Author",),
            )
        ],
    )
    _provider(
        monkeypatch,
        "pubmed",
        [
            _article(
                "https://doi.org/10.1111/Test",
                title="Another title",
                abstract="Another abstract",
                publication_date="2024",
                authors=("Third Author",),
            )
        ],
    )
    result = search_articles("test", session=MagicMock(spec=requests.Session))

    assert result.failures == ()
    assert len(result.results) == 1
    hit = result.results[0]
    assert hit.sources == ("openalex", "semantic_scholar", "pubmed")
    assert hit.abstract_source == "semantic_scholar"
    assert hit.article.doi == "10.1111/test"
    assert hit.article.title == "Original title"
    assert hit.article.abstract == "Provider abstract"
    assert hit.article.authors == ("Second Author",)
    assert hit.article.publication_date == "2025-02-03"


def test_reversed_priority_changes_metadata_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(
        monkeypatch, "openalex", [_article(title="First source", abstract="A")]
    )
    _provider(
        monkeypatch, "pubmed", [_article(title="First requested", abstract="B")]
    )
    result = search_articles(
        "topic",
        sources=("pubmed", "openalex"),
        session=MagicMock(spec=requests.Session),
    )
    assert result.results[0].article.title == "First requested"
    assert result.results[0].article.abstract == "B"
    assert result.results[0].abstract_source == "pubmed"
    assert result.results[0].sources == ("pubmed", "openalex")


def test_repeated_doi_in_same_source_keeps_unique_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(
        monkeypatch,
        "openalex",
        [_article(title=None), _article(title="Backfill title", abstract="Text")],
    )
    result = search_articles(
        "topic", sources=("openalex",), session=MagicMock(spec=requests.Session)
    )
    assert len(result.results) == 1
    assert result.results[0].sources == ("openalex",)
    assert result.results[0].abstract_source == "openalex"
    assert result.results[0].article.title == "Backfill title"


def test_records_without_doi_are_never_collapsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(monkeypatch, "openalex", [_article(None), _article("  ")])
    _provider(monkeypatch, "pubmed", [_article(None)])
    result = search_articles(
        "topic",
        sources=("openalex", "pubmed"),
        session=MagicMock(spec=requests.Session),
    )
    assert len(result.results) == 3
    assert all(hit.article.doi is None for hit in result.results)


def test_results_preserve_first_seen_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(
        monkeypatch,
        "openalex",
        [_article("10.1/one"), _article("10.1/two")],
    )
    _provider(
        monkeypatch,
        "pubmed",
        [_article("10.1/two"), _article("10.1/three")],
    )
    report = search_articles(
        "topic",
        sources=("openalex", "pubmed"),
        session=MagicMock(spec=requests.Session),
    )
    assert [hit.article.doi for hit in report.results] == [
        "10.1/one",
        "10.1/two",
        "10.1/three",
    ]


def test_default_sources_and_forwarded_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openalex = _provider(monkeypatch, "openalex", [])
    semantic = _provider(monkeypatch, "semantic_scholar", [])
    pubmed = _provider(monkeypatch, "pubmed", [])
    session = MagicMock(spec=requests.Session)

    result = search_articles(
        "  causal inference ",
        max_results=8,
        api_keys={
            "openalex": "oa-key",
            "semantic_scholar": "ss-key",
            "pubmed": "ncbi-key",
        },
        email="author@example.org",
        session=session,
        timeout=7.5,
    )
    assert result.results == ()
    assert result.failures == ()
    openalex.assert_called_once_with(
        "causal inference",
        max_results=8,
        api_key="oa-key",
        session=session,
        timeout=7.5,
    )
    semantic.assert_called_once_with(
        "causal inference",
        max_results=8,
        api_key="ss-key",
        session=session,
        timeout=7.5,
    )
    pubmed.assert_called_once_with(
        "causal inference",
        max_results=8,
        email="author@example.org",
        api_key="ncbi-key",
        session=session,
        timeout=7.5,
    )
    session.close.assert_not_called()


def test_explicit_scopus_uses_existing_normalizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = {"search-results": {"entry": [{"dc:title": "Scopus record"}]}}
    fetch = MagicMock(return_value=raw)
    monkeypatch.setattr(search_module, "fetch_from_scopus", fetch)
    session = MagicMock(spec=requests.Session)
    result = search_articles(
        "observational study",
        sources=("scopus",),
        api_keys={"scopus": "secret"},
        max_results=12,
        session=session,
    )
    assert [hit.article.title for hit in result.results] == ["Scopus record"]
    assert result.results[0].sources == ("scopus",)
    fetch.assert_called_once_with(
        "observational study",
        api_key="secret",
        max_results=12,
        session=session,
        timeout=30.0,
    )


def test_crossref_enriches_only_missing_abstracts_after_dedup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(
        monkeypatch,
        "openalex",
        [
            _article("10.20/MISSING", title="Missing"),
            _article("10.20/present", abstract="Already available"),
            _article(None, abstract=None),
        ],
    )
    _provider(
        monkeypatch,
        "pubmed",
        [_article("https://doi.org/10.20/missing", title="Duplicate")],
    )
    crossref = MagicMock(return_value="<jats:p>Crossref text</jats:p>")
    monkeypatch.setattr(search_module, "get_abstract_from_doi", crossref)
    session = MagicMock(spec=requests.Session)

    result = search_articles(
        "topic",
        sources=("openalex", "pubmed"),
        enrich_abstracts=True,
        session=session,
        timeout=4.0,
    )

    assert len(result.results) == 3
    assert result.failures == ()
    hit = result.results[0]
    assert hit.article.abstract == "<jats:p>Crossref text</jats:p>"
    assert hit.abstract_source == "crossref"
    assert hit.sources == ("openalex", "pubmed")
    assert result.results[1].abstract_source == "openalex"
    assert result.results[2].abstract_source is None
    crossref.assert_called_once_with(
        "10.20/missing", session=session, timeout=4.0
    )


@pytest.mark.parametrize("abstract", [None, " ", ""])
def test_crossref_absence_is_not_a_hit(
    monkeypatch: pytest.MonkeyPatch,
    abstract: str | None,
) -> None:
    _provider(monkeypatch, "openalex", [_article()])
    crossref = MagicMock(return_value=abstract)
    monkeypatch.setattr(search_module, "get_abstract_from_doi", crossref)
    result = search_articles(
        "topic",
        sources=("openalex",),
        enrich_abstracts=True,
        session=MagicMock(spec=requests.Session),
    )
    assert result.results[0].article.abstract is None
    assert result.results[0].abstract_source is None


def test_crossref_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _provider(monkeypatch, "openalex", [_article()])
    crossref = MagicMock(side_effect=AssertionError("Unexpected Crossref call"))
    monkeypatch.setattr(search_module, "get_abstract_from_doi", crossref)
    search_articles(
        "topic", sources=("openalex",), session=MagicMock(spec=requests.Session)
    )
    crossref.assert_not_called()


def test_collect_provider_failure_continues_and_returns_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken = ValueError("invalid payload")
    _provider(monkeypatch, "openalex", broken)
    _provider(monkeypatch, "pubmed", [_article()])
    result = search_articles(
        "topic",
        sources=("openalex", "pubmed"),
        on_error="collect",
        session=MagicMock(spec=requests.Session),
    )
    assert len(result.results) == 1
    assert result.results[0].sources == ("pubmed",)
    assert len(result.failures) == 1
    assert result.failures[0].source == "openalex"
    assert result.failures[0].error is broken
    assert result.failures[0].doi is None


def test_all_sources_failed_is_not_equivalent_to_no_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(monkeypatch, "openalex", ValueError("unavailable"))
    report = search_articles(
        "topic",
        sources=("openalex",),
        on_error="collect",
        session=MagicMock(spec=requests.Session),
    )
    assert report.results == ()
    assert len(report.failures) == 1


def test_default_error_policy_is_fail_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(monkeypatch, "openalex", ValueError("invalid response"))
    later = _provider(monkeypatch, "pubmed", [_article()])
    with pytest.raises(ValueError, match="invalid response"):
        search_articles(
            "topic",
            sources=("openalex", "pubmed"),
            session=MagicMock(spec=requests.Session),
        )
    later.assert_not_called()


def test_collect_crossref_error_leaves_article_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(
        monkeypatch,
        "openalex",
        [_article("10.1/error"), _article("10.1/works")],
    )
    error = ValueError("Malformed Crossref data")
    crossref = MagicMock(side_effect=[error, "Recovered"])
    monkeypatch.setattr(search_module, "get_abstract_from_doi", crossref)
    report = search_articles(
        "topic",
        sources=("openalex",),
        enrich_abstracts=True,
        on_error="collect",
        session=MagicMock(spec=requests.Session),
    )
    assert report.results[0].article.abstract is None
    assert report.results[1].article.abstract == "Recovered"
    assert report.results[1].abstract_source == "crossref"
    assert len(report.failures) == 1
    assert report.failures[0].source == "crossref"
    assert report.failures[0].doi == "10.1/error"
    assert report.failures[0].error is error


def test_crossref_fail_fast_propagates_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(monkeypatch, "openalex", [_article()])
    monkeypatch.setattr(
        search_module,
        "get_abstract_from_doi",
        MagicMock(side_effect=ValueError("Crossref invalid")),
    )
    with pytest.raises(ValueError, match="Crossref invalid"):
        search_articles(
            "topic",
            sources=("openalex",),
            enrich_abstracts=True,
            session=MagicMock(spec=requests.Session),
        )


def test_unexpected_programming_error_is_not_silenced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(monkeypatch, "openalex", RuntimeError("programming defect"))
    with pytest.raises(RuntimeError, match="programming defect"):
        search_articles(
            "topic",
            sources=("openalex",),
            on_error="collect",
            session=MagicMock(spec=requests.Session),
        )


def test_owned_session_closed_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _provider(monkeypatch, "openalex", [])
    session = MagicMock(spec=requests.Session)
    monkeypatch.setattr(requests, "Session", lambda: session)
    result = search_articles("topic", sources=("openalex",))
    assert result.results == ()
    session.close.assert_called_once_with()


def test_owned_session_closed_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _provider(monkeypatch, "openalex", ValueError("service error"))
    session = MagicMock(spec=requests.Session)
    monkeypatch.setattr(requests, "Session", lambda: session)
    with pytest.raises(ValueError, match="service error"):
        search_articles("topic", sources=("openalex",))
    session.close.assert_called_once_with()


@pytest.mark.parametrize(
    ("options", "error_text"),
    [
        ({"sources": ()}, "sources"),
        ({"sources": "openalex"}, "sources"),
        ({"sources": ("unknown",)}, "Unsupported"),
        ({"sources": ("openalex", "openalex")}, "Duplicate"),
        ({"max_results": 0}, "max_results"),
        ({"max_results": 101}, "max_results"),
        ({"max_results": True}, "max_results"),
        ({"sources": ("scopus",)}, "Scopus API key"),
        (
            {
                "sources": ("scopus",),
                "api_keys": {"scopus": "valid"},
                "max_results": 26,
            },
            "Scopus supports",
        ),
        ({"api_keys": {"unknown": "secret"}}, "Unknown API"),
        ({"api_keys": {"openalex": " "}}, "API key"),
        ({"email": " "}, "email"),
        ({"timeout": 0}, "timeout"),
        ({"timeout": float("nan")}, "timeout"),
        ({"timeout": float("inf")}, "timeout"),
        ({"on_error": "ignore"}, "on_error"),
    ],
)
def test_invalid_options_fail_before_opening_session(
    options: dict[str, object],
    error_text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock(spec=requests.Session)
    constructor = MagicMock(return_value=session)
    monkeypatch.setattr(requests, "Session", constructor)
    with pytest.raises(ValueError, match=error_text):
        search_articles("topic", **options)
    constructor.assert_not_called()


@pytest.mark.parametrize("query", ["", " ", None])
def test_invalid_query_fails_early(
    query: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    constructor = MagicMock()
    monkeypatch.setattr(requests, "Session", constructor)
    with pytest.raises(ValueError, match="query"):
        search_articles(query)
    constructor.assert_not_called()
