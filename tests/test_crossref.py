from unittest.mock import MagicMock

import pytest
import requests

from abstract_extract.crossref import CROSSREF_WORKS_URL, get_abstract_from_doi


def _session_with_payload(payload: object) -> MagicMock:
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.json.return_value = payload
    session.get.return_value = response
    return session


def test_get_abstract_from_doi_encodes_doi_and_returns_abstract() -> None:
    session = _session_with_payload(
        {"message": {"abstract": "<jats:p>Example abstract</jats:p>"}}
    )

    result = get_abstract_from_doi(
        " 10.1000/example/path ",
        session=session,
        timeout=4.0,
    )

    assert result == "<jats:p>Example abstract</jats:p>"
    session.get.assert_called_once_with(
        f"{CROSSREF_WORKS_URL}/10.1000%2Fexample%2Fpath",
        headers={"Accept": "application/json"},
        timeout=4.0,
    )
    session.get.return_value.raise_for_status.assert_called_once()


def test_get_abstract_from_doi_returns_none_when_abstract_is_missing() -> None:
    session = _session_with_payload({"message": {}})

    assert get_abstract_from_doi("10.1000/example", session=session) is None


@pytest.mark.parametrize("doi", ["", "   "])
def test_get_abstract_from_doi_rejects_empty_doi(doi: str) -> None:
    with pytest.raises(ValueError, match="doi"):
        get_abstract_from_doi(doi)


def test_get_abstract_from_doi_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError, match="timeout"):
        get_abstract_from_doi("10.1000/example", timeout=0)


def test_get_abstract_from_doi_rejects_missing_message() -> None:
    session = _session_with_payload({})

    with pytest.raises(ValueError, match="message"):
        get_abstract_from_doi("10.1000/example", session=session)
