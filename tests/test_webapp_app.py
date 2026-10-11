"""Streamlit smoke test - no HTTP calls on the initial page."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_student_app_starts_without_network_or_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A student must see the search form without supplying API credentials."""
    testing = pytest.importorskip("streamlit.testing.v1")
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_API_KEY", raising=False)
    entrypoint = Path(__file__).resolve().parents[1] / "webapp" / "app.py"
    app_test = testing.AppTest.from_file(entrypoint).run()
    assert len(app_test.exception) == 0
    assert app_test.title[0].value == "Article Finder"
    assert len(app_test.tabs) == 4
    assert len(app_test.text_input) >= 1
    assert len(app_test.multiselect) == 1
