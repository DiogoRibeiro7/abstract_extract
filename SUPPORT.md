# Support

## Where to ask

Use the repository's GitHub issue forms for project support:

- **Bug report** — reproducible incorrect behavior, errors, regressions, or compatibility problems.
- **Feature request** — focused proposals for new capabilities or public API changes.

Before opening an issue, check the README and documentation site for installation, configuration, API usage, and release information.

## Security issues

Do not publish credentials, tokens, private data, or exploit details in a public support request.

Follow [SECURITY.md](SECURITY.md) for vulnerability reporting.

## What to include in a bug report

A useful report should contain:

- the installed `abstract-extract` version;
- the Python version;
- the operating system when relevant;
- a minimal reproduction;
- the expected behavior;
- the observed behavior;
- the traceback or relevant logs with secrets removed.

For Scopus-related problems, never include the API key.

## Supported versions

The project supports the Python versions declared in `pyproject.toml` and tested by CI.

Bug fixes target the current development branch and future releases. Older package versions may not receive backports unless a specific maintenance release is warranted.

## External services

Some behavior depends on third-party services, particularly Scopus and Crossref.

The project can help diagnose how `abstract-extract` interacts with those services, but it cannot resolve:

- account or subscription problems;
- Scopus API-key provisioning;
- upstream API outages;
- upstream metadata errors;
- provider-specific access restrictions.

## Response expectations

This is an independently maintained open-source project. Support is provided on a best-effort basis and no response-time guarantee is implied.
