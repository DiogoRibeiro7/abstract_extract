# Article Finder: search papers without code

Article Finder is a browser interface for students and researchers who do not
want to use Python. It uses the same typed `search_articles()` service as
the Python package.

## What students can do

1. Open the app link provided by an instructor.
2. Enter a topic (for example, *sleep monitoring and machine learning*).
3. Select **Search articles**.
4. Read article titles, authors, years and available abstracts, and follow
   DOI links to publishers or other DOI destinations.
5. Select **Download results (CSV)** to save a spreadsheet of the results.

**Search options** offers additional providers, an upper limit for results
per provider, and optional Crossref abstract enrichment. OpenAlex is selected
by default. **Scopus** is shown only when an instructor or administrator has
configured its API key on the server.

Searches use a first page of at most **25 results per database**. They may
show duplicates without DOIs because title-based merging could confuse
different works. Missing abstracts are indicated, never generated.

## Local setup (instructors and developers)

This project uses Python 3.12-3.14 and Poetry. From the repository root:

```bash
poetry install --with ui
poetry run streamlit run webapp/app.py
```

Streamlit prints the local browser URL. The package's normal installation
does **not** include Streamlit; this keeps its runtime dependencies small.

For quality checks:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src webapp
poetry run pytest
```

## Hosting for a class

The repository contains `webapp/app.py` and `webapp/requirements.txt`,
which can be used to deploy a browser app on Streamlit Community Cloud:

1. Merge the UI PR to `main`.
2. In Streamlit Community Cloud, select this GitHub repository and choose
   `main` with entrypoint `webapp/app.py`.
3. Select Python 3.12 and enter any API credentials using the platform's
   **Secrets** settings, not in files committed to GitHub.
4. Share the deployed URL with the class.

The requirements file located beside the entrypoint installs this repository
and Streamlit. Deploying and managing the hosting account is a separate
administrator action; committing the code alone does not create a live app.

For larger classes, plan for quotas and rate limiting from upstream academic
APIs. If the class requires restricted access or stronger privacy controls,
use school-managed hosting rather than relying on a public link.

## Server-side API credentials (optional)

The UI reads these **environment variables on the server**. Streamlit Cloud
supports root-level secrets that are made available as environment variables.

| Variable | Purpose |
| --- | --- |
| `OPENALEX_API_KEY` | OpenAlex authenticated usage budget |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar quota and access |
| `NCBI_API_KEY` | PubMed E-utilities quota and access |
| `NCBI_EMAIL` | NCBI contact email |
| `SCOPUS_API_KEY` | Required to offer Scopus in the UI |

Users do not enter API keys. Do not commit real keys, add them to screenshots,
or show them in query strings or UI error messages. Avoid external API calls
containing sensitive student information.

OpenAlex supports casual keyless queries with restricted budgets. Semantic
Scholar and PubMed may also permit keyless access under provider limits.
The app displays partial-search warnings when one or more sources fail.
These warnings identify the source but do not expose tokens or internal URLs.

## Export and limitations

CSV export includes title, authors, publication date, DOI, abstract,
discovery sources and abstract provenance. Fields starting with spreadsheet
formula characters are prefixed with an apostrophe to reduce spreadsheet
formula-injection risks. JATS/XML abstract markup is converted to readable
text for display and export.

This app deliberately does not offer user accounts, automatic literature
reviews, AI-generated abstracts, full-text downloads, or scholarly claim
verification. Searches are not cached across students, and stored results
are limited to each browser session.

See the [provider guide](providers.md) for detailed search semantics and
the project's issue tracker for pagination, bulk export and rate limits.

## Literature screening workspace

After searching, open **My reading list**. Students can filter by keyword,
publication year, screening decision, and abstract availability. Each paper
has an abstract, DOI link, relevance decision (*Include*, *Maybe*, *Exclude*),
and free-text notes.

The dashboard displays the number of retrieved papers, included papers,
uncertain papers, and reviewed papers.

Export either the included papers, included and maybe papers, all results,
or the currently filtered set. Available formats:

- **CSV:** metadata, abstract, screening decision, and notes.
- **JSON:** a structured and versioned record of findings and notes.
- **BibTeX:** citations to import into a reference manager or LaTeX.

Only the current browser session stores this reading list. Export your work
before closing the session. The application does not currently synchronize
across devices or offer student accounts.

No relevance decisions are made by AI. A literature review still requires
reading the primary publications and verifying each citation.
