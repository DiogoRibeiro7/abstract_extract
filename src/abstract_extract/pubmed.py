"""PubMed E-utilities search followed by XML abstract retrieval."""

from __future__ import annotations

from xml.etree import ElementTree

import requests
from dataexcept import DataLoadingError, wrapping

from abstract_extract.models import Article

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def search_pubmed(
    query: str,
    *,
    max_results: int = 25,
    email: str | None = None,
    api_key: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> list[Article]:
    """Retrieve PubMed abstracts for the first matching identifiers.

    Args:
        query: PubMed search expression.
        max_results: Number of identifiers to retrieve (1-100).
        email: Optional contact email used by NCBI E-utilities.
        api_key: Optional NCBI API key.
        session: Injectable HTTP session.
        timeout: Positive HTTP timeout in seconds.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if (
        not isinstance(max_results, int)
        or isinstance(max_results, bool)
        or not 1 <= max_results <= 100
    ):
        raise ValueError("max_results must be between 1 and 100")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    for name, value in (("email", email), ("api_key", api_key)):
        if value is not None and not value.strip():
            raise ValueError(f"{name} must not be empty")
    params: dict[str, str | int] = {
        "db": "pubmed",
        "term": query.strip(),
        "retmode": "json",
        "retmax": max_results,
    }
    if email is not None:
        params["email"] = email.strip()
    if api_key is not None:
        params["api_key"] = api_key.strip()
    owns_session = session is None
    client = session if session is not None else requests.Session()
    try:
        with wrapping(requests.RequestException, DataLoadingError, source=ESEARCH_URL):
            response = client.get(ESEARCH_URL, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(
            payload.get("esearchresult"), dict
        ):
            raise ValueError("PubMed search response is missing esearchresult")
        identifiers = payload["esearchresult"].get("idlist")
        if not isinstance(identifiers, list) or any(
            not isinstance(identifier, str) for identifier in identifiers
        ):
            raise ValueError("PubMed idlist must be a list of strings")
        if not identifiers:
            return []
        fetch_params: dict[str, str] = {
            "db": "pubmed",
            "id": ",".join(identifiers),
            "retmode": "xml",
        }
        if email is not None:
            fetch_params["email"] = email.strip()
        if api_key is not None:
            fetch_params["api_key"] = api_key.strip()
        with wrapping(requests.RequestException, DataLoadingError, source=EFETCH_URL):
            response = client.get(EFETCH_URL, params=fetch_params, timeout=timeout)
            response.raise_for_status()
            raw_xml = response.content
        try:
            root = ElementTree.fromstring(raw_xml)
        except ElementTree.ParseError as exc:
            raise ValueError("Invalid PubMed EFetch XML response") from exc
        articles: list[Article] = []
        for record in root.findall(".//PubmedArticle"):
            element = record.find("./MedlineCitation/Article")
            if element is None:
                continue
            title = _xml_text(element.find("ArticleTitle"))
            abstract_parts: list[str] = []
            for part in element.findall("./Abstract/AbstractText"):
                content = _xml_text(part)
                if content is not None:
                    label = part.get("Label")
                    abstract_parts.append(f"{label}: {content}" if label else content)
            authors: list[str] = []
            for author in element.findall("./AuthorList/Author"):
                collective = _xml_text(author.find("CollectiveName"))
                individual = " ".join(
                    piece
                    for piece in (
                        _xml_text(author.find("ForeName")),
                        _xml_text(author.find("LastName")),
                    )
                    if piece
                )
                if collective or individual:
                    authors.append(collective or individual)
            doi: str | None = None
            for identifier in record.findall("./PubmedData/ArticleIdList/ArticleId"):
                if identifier.get("IdType") == "doi":
                    doi = _xml_text(identifier)
                    break
            date = _xml_text(element.find("./ArticleDate/Year"))
            if date is None:
                date = _xml_text(element.find("./Journal/JournalIssue/PubDate/Year"))
            articles.append(
                Article(
                    title=title,
                    abstract=" ".join(abstract_parts) if abstract_parts else None,
                    publication_date=date,
                    authors=tuple(authors),
                    doi=doi,
                )
            )
        return articles
    finally:
        if owns_session:
            client.close()


def _xml_text(element: ElementTree.Element | None) -> str | None:
    """Read text including inline XML nodes without discarding words."""
    if element is None:
        return None
    content = "".join(element.itertext()).strip()
    return content or None
