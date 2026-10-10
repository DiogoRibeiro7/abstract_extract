# Article Finder: search papers without code

Article Finder is a browser interface for students and researchers who do not
want to use Python. It uses the same typed `search_articles()` service as
the Python package.

## A full student research workflow

The Article Finder browser application now has four areas:

- **Discover papers:** search selected databases and apply local filters for
  words, source, publication year and abstract availability. Sort results or
  view them in batches of ten. Filtering is applied to the retrieved first page,
  not to the full database.
- **My reading list:** save papers, take notes, mark them as To read, Reading,
  Reviewed or Excluded, and download an annotated reading matrix.
- **Compare papers:** examine up to three saved records side by side using
  their available bibliographic metadata, abstracts and your notes.
- **Research guide:** follow a critical-reading and source-verification checklist.

### Save work between sessions

Reading lists and notes stay in the current browser session. Select **Save
project (JSON)** before closing the browser and use **Import saved reading list**
next time. The project format includes no API keys. The app does not maintain a
student database or user accounts.

### Export formats

You can export search results as CSV, annotated notes as CSV, saved projects as
JSON, and provisional references as BibTeX. BibTeX uses generic `@misc` records
when venue and publication-type metadata are absent. Verify the source records
before citing: the app does not fabricate journals, volumes, issues or pages.

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
