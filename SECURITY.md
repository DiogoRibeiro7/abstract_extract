# Security Policy

## Supported versions

Security fixes are applied to the latest code on the `main` branch.

The project is currently pre-1.0, so older revisions and unreleased development snapshots are not maintained as separate supported lines.

## Reporting a vulnerability

Please do not open a public GitHub issue containing exploit details, credentials, private data, or instructions that would make a vulnerability easier to abuse.

If GitHub displays a **Report a vulnerability** option for this repository, use that private reporting channel.

If no private reporting option is available, open a minimal public issue that states only that you need to report a security vulnerability. Do not include technical exploit details in that issue. A private channel can then be established before sensitive information is shared.

A useful private report should include:

- the affected component or function;
- the impact you believe the issue could have;
- the conditions required to reproduce it;
- a minimal reproduction where safe;
- affected versions or commit SHAs, if known;
- any suggested mitigation or fix.

## Credentials

Scopus credentials and other secrets must never be committed to the repository.

If a credential is exposed:

1. revoke or rotate it at the provider;
2. remove it from the current source tree;
3. inspect Git history and published artifacts for additional exposure;
4. review logs and external systems that may have copied the secret.

Removing a secret from the latest commit does not invalidate copies already present in Git history.

## Dependency vulnerabilities

Dependency updates that address known security issues should remain focused and should preserve the existing test, type-checking, and linting gates.

Do not weaken CI checks solely to make a security-related dependency update pass. Fix the incompatibility or document the constraint explicitly.

## Scope

Relevant security issues include, but are not limited to:

- credential disclosure;
- unsafe handling of authentication data;
- dependency vulnerabilities that affect the package;
- malicious or unsafe processing of external API responses;
- vulnerabilities introduced by package installation or build configuration;
- CI or release workflow weaknesses that could allow unauthorized code or artifacts.

Ordinary bugs, feature requests, and documentation problems should use the standard issue templates instead.
