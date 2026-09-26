import abstract_extract


def test_public_api_exposes_supported_symbols() -> None:
    expected = {
        "Article",
        "fetch_all_from_scopus",
        "fetch_from_scopus",
        "get_abstract_from_doi",
        "process_scopus_entries",
        "process_scopus_response",
    }

    assert set(abstract_extract.__all__) == expected
    for name in expected:
        assert hasattr(abstract_extract, name)
