"""Interactive student research workspace built on the typed search API."""

from __future__ import annotations

import logging
import os
from typing import cast

import streamlit as st

from abstract_extract import search_articles
from webapp.academic import (
    Appraisal,
    AppraisalEntry,
    ReviewProtocol,
    appraisal_csv,
    appraisal_json,
    assignment_markdown,
    blank_appraisal,
    protocol_markdown,
)
from webapp.review import (
    Decision,
    ReviewEntry,
    filter_entries,
    make_entries,
    review_bibtex,
    review_csv,
    review_json,
    selection_counts,
    update_entry,
)
from webapp.viewmodel import (
    api_keys_from_environment,
    available_sources,
    doi_link,
    readable_abstract,
)

_LOGGER = logging.getLogger(__name__)
st.set_page_config(page_title="Article Finder", page_icon="📚", layout="wide")
st.title("Article Finder")
st.write("Discover, screen, teach and evaluate scholarly literature without coding.")
st.caption(
    "Workflow: search → filter → read → mark relevant papers → take notes → export."
)

sources_available = available_sources(os.environ)
if "review_entries" not in st.session_state:
    st.session_state["review_entries"] = []
if "last_query" not in st.session_state:
    st.session_state["last_query"] = ""

search_tab, review_tab, faculty_tab, help_tab = st.tabs(
    ["Discover", "Reading list", "Teaching & research", "Guide"]
)

with search_tab:
    with st.form("article_search"):
        query = st.text_input(
            "Research topic",
            placeholder="For example: wearable sensors and sleep quality",
            key="research_query",
        )
        with st.expander("Search options"):
            selected = st.multiselect(
                "Scientific databases",
                options=list(sources_available),
                default=["OpenAlex"],
            )
            max_results = st.slider(
                "Results per database", min_value=5, max_value=25, value=10, step=5
            )
            enrich = st.checkbox("Find missing abstracts with Crossref")
        submitted = st.form_submit_button("Search articles", type="primary")

    if submitted:
        if not query.strip() or not selected:
            st.warning("Enter a research topic and select a database.")
        else:
            st.session_state["review_entries"] = []
            st.session_state["search_failures"] = ()
            with st.spinner("Searching academic databases…"):
                try:
                    response = search_articles(
                        query.strip(),
                        sources=tuple(sources_available[name] for name in selected),
                        max_results=max_results,
                        api_keys=api_keys_from_environment(os.environ),
                        email=os.environ.get("NCBI_EMAIL", "").strip() or None,
                        enrich_abstracts=enrich,
                        on_error="collect",
                        timeout=15.0,
                    )
                except Exception as error:
                    _LOGGER.error("Search error: %s", type(error).__name__)
                    st.error("The search failed. Try again or ask your instructor.")
                else:
                    st.session_state["review_entries"] = make_entries(response)
                    st.session_state["search_failures"] = response.failures
                    st.session_state["last_query"] = query.strip()
                    st.success(
                        f"Found {len(response.results)} unique article records. "
                        "Open My reading list to screen them."
                    )

with review_tab:
    entries: list[ReviewEntry] = st.session_state["review_entries"]
    failures = st.session_state.get("search_failures", ())
    if failures:
        st.warning(
            "Some databases failed: "
            + ", ".join(sorted({failure.source for failure in failures}))
            + ". Results may be incomplete."
        )
    if not entries:
        st.info("Search for articles first. Your reading list will appear here.")
    else:
        st.caption(f"Research question: {st.session_state['last_query']}")
        counts = selection_counts(entries)
        total, included, maybe, screened = st.columns(4)
        total.metric("Found", len(entries))
        included.metric("Included", counts["include"])
        maybe.metric("Maybe", counts["maybe"])
        screened.metric("Reviewed", len(entries) - counts["unreviewed"])

        with st.expander("Filter your reading list", expanded=True):
            phrase = st.text_input(
                "Search within results",
                placeholder="Filter title, abstract, authors, DOI or notes",
            )
            status = st.selectbox(
                "Screening decision",
                ["all", "unreviewed", "include", "maybe", "exclude"],
            )
            year_filter = st.checkbox("Limit publication years")
            start_year, end_year = (None, None)
            if year_filter:
                start_year = st.number_input(
                    "From year", min_value=1900, max_value=2100, value=2015
                )
                end_year = st.number_input(
                    "To year", min_value=1900, max_value=2100, value=2026
                )
            abstracts_only = st.checkbox("Only papers with abstracts")
        filtered = filter_entries(
            entries,
            query=phrase,
            decision=status,
            year_from=start_year,
            year_to=end_year,
            abstracts_only=abstracts_only,
        )
        st.caption(f"Showing {len(filtered)} of {len(entries)} papers")
        chosen = st.radio(
            "Export which papers?",
            ["Included", "Included and maybe", "All", "Current filter"],
            horizontal=True,
        )
        if chosen == "Included":
            export = [item for item in entries if item.decision == "include"]
        elif chosen == "Included and maybe":
            export = [item for item in entries if item.decision in ("include", "maybe")]
        elif chosen == "Current filter":
            export = filtered
        else:
            export = entries
        csv_column, json_column, bib_column = st.columns(3)
        csv_column.download_button(
            "Download CSV",
            data=review_csv(export),
            file_name="literature-review.csv",
            mime="text/csv",
        )
        json_column.download_button(
            "Download JSON",
            data=review_json(export),
            file_name="literature-review.json",
            mime="application/json",
        )
        bib_column.download_button(
            "Download BibTeX",
            data=review_bibtex(export),
            file_name="references.bib",
            mime="application/x-bibtex",
        )
        for entry in filtered:
            article = entry.hit.article
            index = next(i for i, item in enumerate(entries) if item.key == entry.key)
            with st.container(border=True):
                st.subheader(article.title or "Untitled publication")
                if article.authors:
                    st.caption(", ".join(article.authors))
                st.caption(
                    f"Published: {article.publication_date or 'Unknown'}"
                    f"  |  Found in: {', '.join(entry.hit.sources)}"
                )
                link = doi_link(article.doi)
                if link is not None:
                    st.link_button("Open DOI", link)
                with st.expander("Abstract", expanded=False):
                    st.write(
                        readable_abstract(article.abstract)
                        or "No abstract was supplied by these databases."
                    )
                decision = st.selectbox(
                    "Screen this paper",
                    options=["unreviewed", "include", "maybe", "exclude"],
                    index=["unreviewed", "include", "maybe", "exclude"].index(
                        entry.decision
                    ),
                    key=f"decision_{entry.key}",
                )
                notes = st.text_area(
                    "Personal notes",
                    value=entry.notes,
                    key=f"notes_{entry.key}",
                    placeholder="Why is this paper relevant to your question?",
                )
                updated = update_entry(
                    entry, decision=cast(Decision, decision), notes=notes
                )
                if updated != entry:
                    entries[index] = updated

with faculty_tab:
    st.subheader("Teaching and research")
    st.caption(
        "Build a reusable review protocol, assignment brief and manual "
        "critical appraisal worksheet. No role-based access is implied."
    )
    with st.form("review_protocol"):
        title = st.text_input("Project or course title")
        question = st.text_area("Research question")
        population = st.text_input("Population or context")
        intervention = st.text_input("Intervention or exposure")
        comparator = st.text_input("Comparison")
        outcomes = st.text_input("Outcomes")
        inclusion = st.text_area("Inclusion criteria")
        exclusion = st.text_area("Exclusion criteria")
        databases = st.text_input("Databases")
        strategy = st.text_area("Search strategy")
        plan = st.text_area("Appraisal or teaching guidance")
        protocol_submit = st.form_submit_button("Prepare protocol")
    if protocol_submit:
        try:
            st.session_state["academic_protocol"] = ReviewProtocol(
                title=title,
                question=question,
                population=population,
                intervention=intervention,
                comparator=comparator,
                outcomes=outcomes,
                inclusion=inclusion,
                exclusion=exclusion,
                databases=databases,
                search_strategy=strategy,
                assessment_notes=plan,
            )
        except ValueError:
            st.warning("Provide both a title and a research question.")
    protocol = st.session_state.get("academic_protocol")
    if isinstance(protocol, ReviewProtocol):
        a, b = st.columns(2)
        a.download_button(
            "Download research protocol",
            protocol_markdown(protocol),
            file_name="review-protocol.md",
            mime="text/markdown",
        )
        b.download_button(
            "Download assignment brief",
            assignment_markdown(protocol),
            file_name="student-assignment.md",
            mime="text/markdown",
        )

    entries_for_appraisal: list[ReviewEntry] = st.session_state["review_entries"]
    if entries_for_appraisal:
        st.subheader("Manual critical appraisal")
        paper_labels = {
            item.key: item.hit.article.title or item.key
            for item in entries_for_appraisal
        }
        chosen_paper = st.selectbox(
            "Paper to appraise",
            options=list(paper_labels),
            format_func=lambda key: paper_labels[key],
        )
        appraisals: dict[str, AppraisalEntry] = st.session_state.setdefault(
            "appraisals", {}
        )
        selected_entry = next(
            item for item in entries_for_appraisal if item.key == chosen_paper
        )
        current_appraisal = appraisals.get(
            chosen_paper, blank_appraisal(selected_entry.hit)
        )
        with st.form("manual_appraisal"):
            design = st.text_input(
                "Study design", value=current_appraisal.design
            )
            responses = (
                "not_assessed", "yes", "partly", "no", "unclear"
            )
            answers: list[str] = []
            for field_label, previous in (
                ("Is the research question clear?", current_appraisal.question),
                ("Are the methods suitable?", current_appraisal.methods),
                ("Are sources of bias discussed?", current_appraisal.bias),
                ("Is uncertainty reported?", current_appraisal.uncertainty),
            ):
                answer = st.selectbox(
                    field_label,
                    responses,
                    index=responses.index(previous),
                )
                answers.append(answer)
            critical_notes = st.text_area(
                "Methodological observations", value=current_appraisal.notes
            )
            save_appraisal = st.form_submit_button("Save appraisal")
        if save_appraisal:
            appraisals[chosen_paper] = AppraisalEntry(
                doi=current_appraisal.doi,
                title=current_appraisal.title,
                design=design,
                question=cast(Appraisal, answers[0]),
                methods=cast(Decision, answers[1]),
                bias=cast(Decision, answers[2]),
                uncertainty=cast(Decision, answers[3]),
                notes=critical_notes,
            )
            st.success("Appraisal stored in this session.")
        if appraisals:
            values = list(appraisals.values())
            a, b = st.columns(2)
            a.download_button(
                "Export appraisals (CSV)",
                appraisal_csv(values),
                file_name="academic-appraisals.csv",
                mime="text/csv",
            )
            b.download_button(
                "Export appraisals (JSON)",
                appraisal_json(values),
                file_name="academic-appraisals.json",
                mime="application/json",
            )
    else:
        st.info("Search papers to enable per-article critical appraisal.")

with help_tab:
    st.markdown(
        """
        ### How to prepare a literature review
        1. **Write a focused research question.** Search for important concepts.
        2. **Choose databases.** Different sources cover different subjects.
        3. **Read abstracts critically.** They are not substitutes for papers.
        4. **Screen papers.** Mark Include, Maybe or Exclude, and explain why.
        5. **Export your selection.** BibTeX can be imported by citation tools.
        6. **Verify references.** Check titles, DOIs and publication dates.

        **Important:** No AI-generated abstracts or relevance judgments are used.
        This tool only processes metadata retrieved from scholarly APIs.
        Notes and selections are stored in your current browser session;
        export them before closing your session.
        """
    )
