from unittest.mock import MagicMock

import pytest
import requests

from abstract_extract.models import Article
from abstract_extract.scopus import (
    MAX_PAGE_SIZE,
    SCOPUS_SEARCH_URL,
    fetch_all_from_scopus,
    fetch_from_scopus,
    process_scopus_entries,
    process_scopus_response,
)


def _session_with_payloads(*payloads: object) -> MagicMock:
    session = MagicMock(spec=requests.Session)
    responses = []

    for payload in payloads:
        response = MagicMock()
        response.json.return_value = payload
        responses.append(response)

    session.get.side_effect = responses
    return session


def test_fetch_from_scopus_builds_expected_request() -> None:
    payload = {"search-results": {"entry": []}}
    session = _session_with_payloads(payload)

    result = fetch_from_scopus(
        "  changepoint detection  ",
        "  secret-key  ",
        max_results=10,
        session=session,
        timeout=5.0,
    )

    assert result == payload
    session.get.assert_called_once_with(
        SCOPUS_SEARCH_URL,
        headers={
            "Accept": "application/json",
            "X-ELS-APIKey": "secret-key",
        },
        params={"query": "changepoint detection", "count": 10},
        timeout=5.0,
    )
    session.get.return_value.raise_for_status.assert_called_once()


@pytest.mark.parametrize("max_results", [0, MAX_PAGE_SIZE + 1])
def test_fetch_from_scopus_rejects_invalid_page_size(max_results: int) -> None:
    with pytest.raises(ValueError, match="max_results"):
        fetch_from_scopus("query", "key", max_results=max_results)


@pytest.mark.parametrize(
    ("query", "api_key"),
    [
        ("", "key"),
        ("   ", "key"),
        ("query", ""),
        ("query", "   "),
    ],
)
def test_fetch_from_scopus_rejects_empty_required_values(
    query: str,
    api_key: str,
) -> None:
    with pytest.raises(ValueError):
        fetch_from_scopus(query, api_key)


def test_fetch_all_from_scopus_follows_cursor_pagination() -> None:
    first_entry = {"dc:title": "First"}
    second_entry = {"dc:title": "Second"}

    session = _session_with_payloads(
        {
            "search-results": {
                "entry": [first_entry],
                "cursor": {"@next": "cursor-2"},
            }
        },
        {
            "search-results": {
                "entry": [second_entry],
                "cursor": {},
            }
        },
    )

    result = fetch_all_from_scopus(
        "topic",
        "key",
        author="Ada Lovelace",
        start_date="2020-01-01",
        end_date="2026-01-01",
        session=session,
        timeout=7.5,
    )

    assert result == [first_entry, second_entry]
    assert session.get.call_count == 2

    first_call = session.get.call_args_list[0]
    assert first_call.kwargs["params"] == {
        "query": "topic AND AUTHOR(Ada Lovelace)",
        "count": MAX_PAGE_SIZE,
        "cursor": "*",
        "date": "2020-01-01 to 2026-01-01",
    }

    second_call = session.get.call_args_list[1]
    assert second_call.kwargs["params"]["cursor"] == "cursor-2"


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        ("2020-01-01", None),
        (None, "2026-01-01"),
    ],
)
def test_fetch_all_requires_complete_date_range(
    start_date: str | None,
    end_date: str | None,
) -> None:
    with pytest.raises(ValueError, match="provided together"):
        fetch_all_from_scopus(
            "query",
            "key",
            start_date=start_date,
            end_date=end_date,
        )


def test_fetch_all_rejects_missing_search_results() -> None:
    session = _session_with_payloads({})

    with pytest.raises(ValueError, match="search-results"):
        fetch_all_from_scopus("query", "key", session=session)


def test_process_scopus_entries_normalizes_article_metadata() -> None:
    articles = process_scopus_entries(
        [
            {
                "dc:title": "Paper",
                "dc:description": "Abstract",
                "prism:coverDate": "2026-02-03",
                "prism:doi": "10.1000/paper",
                "author": [
                    {"authname": "Alice"},
                    {"authname": "Bob"},
                    {"unexpected": "value"},
                    "invalid",
                ],
            }
        ]
    )

    assert articles == [
        Article(
            title="Paper",
            abstract="Abstract",
            publication_date="2026-02-03",
            authors=("Alice", "Bob"),
            doi="10.1000/paper",
        )
    ]


def test_process_scopus_response_handles_empty_entries() -> None:
    assert process_scopus_response({"search-results": {"entry": []}}) == []


def test_process_scopus_response_rejects_invalid_entries_shape() -> None:
    with pytest.raises(ValueError, match="entry"):
        process_scopus_response({"search-results": {"entry": {}}})
