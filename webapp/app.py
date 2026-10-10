"""Browser-based scientific article search for students.

Run from the repository root:
    poetry install --with ui
    poetry run streamlit run webapp/app.py
"""

from __future__ import annotations

import logging
import os
from html import escape

import streamlit as st

from abstract_extract import SearchResponse, search_articles
from webapp.viewmodel import (
    api_keys_from_environment,
    available_sources,
    doi_link,
    readable_abstract,
    report_to_csv,
)

_LOGGER = logging.getLogger(__name__)

st.set_page_config(
    page_title="Article Finder",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("Article Finder")
st.write(
    "Find scientific papers, read available abstracts, and save your results. "
    "No programming required."
)
st.caption(
    "Start with OpenAlex. For a broader search, choose additional databases "
    "under Search options."
)

configured_sources = available_sources(os.environ)

with st.form("article_search"):
    query = st.text_input(
        "What topic are you researching?",
        placeholder="For example: machine learning for sleep monitoring",
        key="research_query",
    )

    with st.expander("Search options", expanded=False):
        selected_labels = st.multiselect(
            "Databases to search",
            options=list(configured_sources),
            default=["OpenAlex"],
            help=(
                "Different databases cover different publications. "
                "Some may limit how often they can be searched."
            ),
        )
        max_results = st.slider(
            "Maximum results from each database",
            min_value=5,
            max_value=25,
            value=10,
            step=5,
            help="The final number can be smaller after duplicate articles are merged.",
        )
        enrich = st.checkbox(
            "Try to find missing abstracts using Crossref",
            value=False,
            help=(
                "Crossref may have additional abstracts. "
                "Enrichment can take longer and some papers have no abstract."
            ),
        )

    submitted = st.form_submit_button("Search articles", type="primary")

if submitted:
    # Never show credentials or raw HTTP exception messages to students.
    st.session_state.pop("search_report", None)
    if not query.strip():
        st.warning("Enter a research topic to start your search.")
    elif not selected_labels:
        st.warning("Select at least one database.")
    else:
        sources = tuple(configured_sources[label] for label in selected_labels)
        with st.spinner("Searching scientific databases…"):
            try:
                result = search_articles(
                    query,
                    sources=sources,
                    max_results=max_results,
                    api_keys=api_keys_from_environment(os.environ),
                    email=os.environ.get("NCBI_EMAIL", "").strip() or None,
                    enrich_abstracts=enrich,
                    on_error="collect",
                    timeout=15.0,
                )
            except Exception as error:
                # The UI boundary gives a generic message; the package API
                # retains detailed errors for researchers and developers.
                _LOGGER.error(
                    "Student search failed unexpectedly (%s)",
                    type(error).__name__,
                )
                st.error(
                    "The search could not be completed. "
                    "Try again or contact your instructor."
                )
            else:
                st.session_state["search_report"] = result
                st.session_state["last_query"] = query.strip()

report = st.session_state.get("search_report")
if isinstance(report, SearchResponse):
    st.divider()
    st.subheader("Search results")
    st.caption(f"Topic: {st.session_state.get('last_query', '')}")

    if report.failures:
        names = ", ".join(sorted({failure.source for failure in report.failures}))
        st.warning(
            "Some databases or abstract lookups could not be reached: "
            f"{names}. Available results are shown below."
        )

    if not report.results:
        if report.failures:
            st.error(
                "No articles could be retrieved. "
                "Some databases were unavailable; please try again later."
            )
        else:
            st.info(
                "No articles found. Try a shorter search phrase "
                "or search another database."
            )
    else:
        found_with_abstract = sum(
            readable_abstract(hit.article.abstract) is not None
            for hit in report.results
        )
        metric_one, metric_two = st.columns(2)
        metric_one.metric("Unique articles", len(report.results))
        metric_two.metric("With abstracts", found_with_abstract)

        st.download_button(
            "Download results (CSV)",
            data=report_to_csv(report),
            file_name="article-finder-results.csv",
            mime="text/csv",
            help="Open the file in a spreadsheet program.",
        )

        source_names = {
            key: label for label, key in configured_sources.items()
        }
        for number, hit in enumerate(report.results, start=1):
            article = hit.article
            with st.container(border=True):
                title = article.title or "Untitled publication"
                st.markdown(f"**{number}. {escape(title)}**")
                byline = " · ".join(
                    part
                    for part in (
                        ", ".join(article.authors) if article.authors else "",
                        article.publication_date or "",
                    )
                    if part
                )
                if byline:
                    st.caption(byline)
                source_text = ", ".join(
                    source_names.get(source, source) for source in hit.sources
                )
                st.caption(f"Found in: {source_text}")
                link = doi_link(article.doi)
                if link is not None:
                    st.markdown(f"[Open article using DOI]({link})")
                with st.expander("Read abstract"):
                    abstract = readable_abstract(article.abstract)
                    if abstract is None:
                        st.caption("No abstract available for this article.")
                    else:
                        st.write(abstract)
                        st.caption(
                            "Abstract supplied by: "
                            f"{hit.abstract_source or 'Unknown source'}"
                        )

st.divider()
st.caption(
    "Results come from external academic databases. Check article details "
    "and publication information before citing. This tool does not generate "
    "or summarize abstracts with AI."
)
