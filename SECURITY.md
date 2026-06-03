# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.x     | Yes       |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report vulnerabilities via GitHub's private
[Security Advisories](https://github.com/marcoaureliomenezes/dadaia-workspace/security/advisories/new)
feature.

Include:
- A description of the vulnerability and its potential impact
- Steps to reproduce or proof-of-concept code
- Affected versions

You can expect an acknowledgement within 72 hours. If a fix is warranted, a patched release
will be issued and you will be credited (unless you prefer anonymity).

## Scope

This library is a local developer tool (CLI). It does not run as a server, does not handle
user authentication, and does not store credentials. Security issues of interest include:

- Arbitrary code execution via untrusted workspace configuration files
- Privilege escalation through the hook system (`sdd-spec-gate.sh`, `ctx-inject.sh`)
- Secret leakage via log files or reports written to disk
- Supply-chain issues in published PyPI artifacts

## Security Features

- All GitHub Actions use OIDC (no static cloud credentials)
- All Actions are pinned to full commit SHAs
- CI runs `gitleaks` on every push and pull request (`.github/workflows/secret-scan.yml`)
- PyPI publishing uses Trusted Publishing (no `TWINE_PASSWORD`)
