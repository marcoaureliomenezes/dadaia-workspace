---
name: security-audit-protocol
description: >
  Reference for security-reviewer agent. OWASP Top 10 mapping, dependency scan
  workflow, secret detection regex set, IaC review (Docker/GH Actions/Terraform),
  STRIDE threat-modeling template, CVSS-aware severity matrix.
applyTo: ".dadaia/reports/**"
---

# security-audit-protocol — Vulnerability + Infrastructure Audit

## TODO

Full content lands in AGT-24 (P3). This stub is sufficient for P2 agent frontmatter
references to resolve.

Outline:
- OWASP Top 10 (2025) mapping with locally-detectable signals.
- Secret detection regex set (AWS, GH, JWT, RSA, generic .env leaks).
- Auth/authz pattern audit (cookie flags, CSRF tokens, password hashing).
- Injection vectors (SQL, command, prompt, template, regex DoS).
- Dependency CVE scan commands (pip-audit, npm audit, go list -m all).
- IaC review (Dockerfile USER root, exposed ports, Terraform IAM `*`).
- STRIDE threat-modeling template.
- CVSS-aware severity rubric (critical / high / medium / low).
- Output template: Executive Summary, Findings (CWE + file:line + evidence
  REDACTED + fix), Dependency audit, Secrets scan, Infrastructure, Backlog.
