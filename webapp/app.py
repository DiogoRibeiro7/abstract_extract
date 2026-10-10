"""Student research workspace: discover, filter, annotate, compare and export."""

from __future__ import annotations

import logging
import os
from html import escape

import streamlit as st

from abstract_extract import SearchResponse, search_articles
from webapp.filters import article_year, filter_hits
from webapp.library import (
    Bookmark,
    bookmark_key,
    export_library,
    from_hit,
    import_library,
    library_bibtex,
    library_csv,
    update_bookmark,
)
from webapp.viewmodel import (
    api_keys_from_environment,
    available_sources,
    doi_link,
    readable_abstract,
    report_to_csv,
)

_LOGGER = logging.getLogger(__name__)
st.set_page_config(page_title="Article Finder", page_icon="📚", layout="wide")
st.title("Article Finder")
st.caption(
    "Your academic research workspace: discover papers, screen abstracts, "
    "build a reading list, compare studies, and export references."
)

if "library" not in st.session_state:
    st.session_state["library"] = {}
configured = available_sources(os.environ)
search_tab, library_tab, compare_tab, guide_tab = st.tabs(
    ["Discover papers", "My reading list", "Compare papers", "Research guide"]
)

with search_tab:
    st.subheader("Discover scientific literature")
    with st.form("article_search"):
        query = st.text_input(
            "What are you researching?",
            placeholder="e.g. sleep monitoring with wearable sensors",
            key="research_query",
        )
        with st.expander("Advanced search options"):
            labels = st.multiselect(
                "Academic databases",
                list(configured),
                default=["OpenAlex"],
            )
            max_results = st.slider(
                "Results per database (first page)", 5, 25, 15, step=5
            )
            enrich = st.checkbox(
                "Find missing abstracts using Crossref", value=False
            )
        submitted = st.form_submit_button("Search papers", type="primary")

    if submitted:
        st.session_state.pop("search_report", None)
        if not query.strip():
            st.warning("Enter a research topic.")
        elif not labels:
            st.warning("Choose at least one database.")
        else:
            with st.spinner("Searching academic databases…"):
                try:
                    report = search_articles(
                        query,
                        sources=tuple(configured[label] for label in labels),
                        max_results=max_results,
                        enrich_abstracts=enrich,
                        api_keys=api_keys_from_environment(os.environ),
                        email=os.environ.get("NCBI_EMAIL", "").strip() or None,
                        on_error="collect",
                        timeout=15.0,
                    )
                except Exception as error:
                    _LOGGER.error("Search failed: %s", type(error).__name__)
                    st.error("Search unavailable. Try again or ask your instructor.")
                else:
                    st.session_state["search_report"] = report
                    st.session_state["last_query"] = query.strip()
    report = st.session_state.get("search_report")
    if isinstance(report, SearchResponse):
        if report.failures:
            names = ", ".join(sorted({x.source for x in report.failures}))
            st.warning(
                f"Some sources failed ({names}). Results may be incomplete."
            )
        total = len(report.results)
        abstracts = sum(
            readable_abstract(x.article.abstract) is not None
            for x in report.results
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("Unique papers", total)
        m2.metric("With abstract", abstracts)
        m3.metric("Saved to reading list", len(st.session_state["library"]))
        st.caption(
            "Results cover only the first page from each selected database; "
            "absence here is not evidence that a paper does not exist."
        )
        st.download_button(
            "Export search results (CSV)", report_to_csv(report),
            "search-results.csv", "text/csv",
        )
        if total:
            with st.expander("Filter and sort results", expanded=True):
                text = st.text_input(
                    "Search within these results", key="filter_text"
                )
                c1, c2, c3 = st.columns(3)
                sources = sorted({s for h in report.results for s in h.sources})
                chosen_source = c1.selectbox(
                    "Database", ["All"] + sources, key="filter_source"
                )
                abstracts_only = c2.checkbox(
                    "Abstract available", key="filter_abstract"
                )
                sort = c3.selectbox(
                    "Sort",
                    ["discovery", "newest", "oldest", "title", "most_sources"],
                    key="filter_order",
                )
                years = [
                    y for hit in report.results
                    if (y := article_year(hit.article.publication_date)) is not None
                ]
                if years:
                    dates = st.slider(
                        "Publication year",
                        min_value=min(years), max_value=max(years),
                        value=(min(years), max(years)),
                        key="filter_years",
                    )
                else:
                    dates = None
            filtered = filter_hits(
                report.results,
                text=text,
                source=None if chosen_source == "All" else chosen_source,
                abstracts_only=abstracts_only,
                year_from=dates[0] if dates else None,
                year_to=dates[1] if dates else None,
                order=sort,
            )
            st.write(f"Showing {len(filtered)} of {total} unique papers.")
            page_size = 10
            page_count = max(1, (len(filtered) + page_size - 1) // page_size)
            page = st.number_input(
                "Results page", 1, page_count, 1, key="results_page"
            )
            first = (page - 1) * page_size
            for number, hit in enumerate(
                filtered[first:first + page_size], start=first + 1
            ):
                a = hit.article
                saved_key = bookmark_key(hit)
                with st.container(border=True):
                    st.markdown(f"**{number}. {escape(a.title or 'Untitled paper')}**")
                    st.caption(
                        f"{', '.join(a.authors) or 'Authors not provided'} · "
                        f"{a.publication_date or 'Date unknown'}"
                    )
                    st.caption("Discovered via: " + ", ".join(hit.sources))
                    link = doi_link(a.doi)
                    if link:
                        st.markdown(f"[Open publication]({link})")
                    with st.expander("Read abstract and provenance"):
                        st.write(
                            readable_abstract(a.abstract)
                            or "Abstract not available from the selected databases."
                        )
                        st.caption(
                            "Abstract from: " + (hit.abstract_source or "Unknown")
                        )
                    if saved_key in st.session_state["library"]:
                        if st.button("Remove from reading list", key=f"remove_{number}"):
                            del st.session_state["library"][saved_key]
                            st.rerun()
                    elif st.button("Save paper", key=f"save_{number}"):
                        if len(st.session_state["library"]) >= 300:
                            st.error("The reading list is limited to 300 papers.")
                        else:
                            st.session_state["library"][saved_key] = from_hit(hit)
                            st.rerun()
        elif not report.failures:
            st.info("No papers found. Try a shorter query or another database.")

with library_tab:
    st.subheader("My reading list")
    st.caption(
        "Keep notes and track reading decisions. This list is temporary; "
        "export your project file to save your work between sessions."
    )
    upload = st.file_uploader("Import saved reading list (JSON)", type=["json"])
    if upload is not None and st.button("Restore reading list"):
        try:
            restored = import_library(upload.getvalue())
        except ValueError:
            st.error("The reading-list file is invalid or unsupported.")
        else:
            st.session_state["library"] = {item.key: item for item in restored}
            st.rerun()

    library: dict[str, Bookmark] = st.session_state["library"]
    items = tuple(library.values())
    st.metric("Papers saved", len(items))
    if items:
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "Save project (JSON)", export_library(items),
            "reading-list.json", "application/json",
        )
        c2.download_button(
            "Annotated matrix (CSV)", library_csv(items),
            "reading-matrix.csv", "text/csv",
        )
        c3.download_button(
            "BibTeX references", library_bibtex(items),
            "references.bib", "text/plain",
        )
        st.info(
            "BibTeX entries are provisional. Verify titles, authors, "
            "publication venues and dates against the original papers."
        )
        for index, item in enumerate(items):
            with st.expander(
                f"{index + 1}. {item.title} — {item.status}"
            ):
                st.caption(", ".join(item.authors) or "Authors unavailable")
                st.write(item.abstract or "No abstract provided.")
                updated_status = st.selectbox(
                    "Reading status",
                    ["To read", "Reading", "Reviewed", "Excluded"],
                    index=["To read", "Reading", "Reviewed", "Excluded"].index(
                        item.status
                    ),
                    key=f"status_{item.key}",
                )
                note = st.text_area(
                    "Your notes: methods, strengths, limitations, relevance",
                    value=item.note, max_chars=4000, key=f"notes_{item.key}",
                )
                left, right = st.columns(2)
                if left.button("Save notes", key=f"update_{item.key}"):
                    library[item.key] = update_bookmark(
                        item, note=note, status=updated_status
                    )
                    st.success("Notes saved for this session.")
                if right.button("Remove paper", key=f"delete_{item.key}"):
                    del library[item.key]
                    st.rerun()
    else:
        st.info("Save papers from Discover to start a reading list.")

with compare_tab:
    st.subheader("Compare papers")
    library = st.session_state["library"]
    st.caption(
        "Compare up to three selected articles side by side. "
        "This displays available metadata, not an automatic quality judgment."
    )
    ids = st.multiselect(
        "Choose saved papers",
        list(library),
        format_func=lambda key: library[key].title,
        max_selections=3,
    )
    if ids:
        columns = st.columns(len(ids))
        for column, key in zip(columns, ids, strict=True):
            item = library[key]
            with column:
                st.markdown(f"**{escape(item.title)}**")
                st.caption(
                    f"{item.publication_date or 'Unknown year'} · {item.status}"
                )
                st.write("Authors:", ", ".join(item.authors) or "Unknown")
                st.write("DOI:", item.doi or "Not available")
                st.write("Sources:", ", ".join(item.sources))
                st.write("Abstract:", item.abstract or "Not provided")
                st.write("Notes:", item.note or "No notes yet.")

with guide_tab:
    st.subheader("Research workflow")
    st.markdown(
        "1. **Define a question.** Write down the problem, population, "
        "method and outcome you are studying.\n"
        "2. **Search broadly.** Try synonyms and more than one database.\n"
        "3. **Screen abstracts.** Save relevant papers, noting inclusion "
        "and exclusion reasons.\n"
        "4. **Read critically.** Record methods, sample sizes, assumptions "
        "and limitations in your reading list.\n"
        "5. **Compare evidence.** Do not treat every paper as equally reliable.\n"
        "6. **Verify and cite.** Open the original publication, check its "
        "details and revise exported references."
    )
    st.warning(
        "This application does not automatically assess study quality, "
        "produce systematic reviews, or download paywalled publications."
    )

st.divider()
st.caption(
    "Article Finder · External sources may be incomplete or rate-limited. "
    "Student notes remain in this browser session unless exported."
)
