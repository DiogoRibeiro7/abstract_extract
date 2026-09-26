# Getting started

## Requirements

- Python 3.12
- Poetry
- a Scopus API key for Scopus requests

Crossref lookups do not require a Scopus key.

## Install from source

```bash
git clone https://github.com/DiogoRibeiro7/abstract_extract.git
cd abstract_extract
poetry install
```

Enter the Poetry environment or prefix commands with `poetry run`.

## Configure Scopus credentials

Copy the example environment file:

```bash
cp .env.example .env
```

Set the credential locally:

```text
SCOPUS_API_KEY=your-scopus-api-key
```

The package itself accepts the API key explicitly. Loading environment variables is left to the calling application.

!!! warning "Do not commit credentials"
    API keys, tokens, and local environment files must not be committed. If a credential is exposed, rotate it at the provider even after removing it from the current source tree.

## Verify the installation

```python
from abstract_extract import Article

article = Article(
    title="Example",
    abstract=None,
    publication_date="2026-01-01",
    authors=("A. Author",),
    doi="10.1000/example",
)

print(article.title)
```
