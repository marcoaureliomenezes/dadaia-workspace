---
name: security-audit-protocol
description: >
  Reference for security-reviewer agent. OWASP Top 10 mapping, dependency scan
  workflow, secret detection regex set, IaC review (Docker/GH Actions/Terraform),
  STRIDE threat-modeling template, CVSS-aware severity matrix.
applyTo: ".dadaia/reports/**"
---

# security-audit-protocol — Vulnerability + Infrastructure Audit

## OWASP Top 10 (2025) Mapping

Each item lists locally-detectable signals a security-reviewer can find without
runtime access to the target system.

| # | Category | Locally-Detectable Signals |
|---|---|---|
| A01 | Broken Access Control | Missing auth decorator/middleware on route handlers; wildcard `allowFrom: ["*"]` in config; no RBAC check before privileged operation; `dmPolicy: "open"` without ID restriction |
| A02 | Cryptographic Failures | Hardcoded secrets or tokens in source; weak hash (`md5`, `sha1`) for passwords; HTTP URLs in config where HTTPS expected; unencrypted secrets in docker-compose env |
| A03 | Injection | SQL string concatenation (`f"SELECT … {user_input}"`); `shell=True` with user input; `eval()`/`exec()` on external data; unsanitized template variables; prompt-injection: user content injected into system prompt without escaping |
| A04 | Insecure Design | Auth skipped because "internal network"; no rate limiting on auth endpoints; sensitive data returned in error responses; missing threat model for new external-facing surface |
| A05 | Security Misconfiguration | Debug mode enabled in production config; default credentials; exposed admin endpoints without auth; verbose stack traces to end-users; Docker container running as root |
| A06 | Vulnerable & Outdated Components | `pip-audit` HIGH+ findings; `npm audit` HIGH+; dependencies pinned to versions with known CVEs; no lockfile committed |
| A07 | Identification & Auth Failures | Passwords stored as plaintext or MD5; no account lockout on failed login; session tokens not invalidated on logout; `HttpOnly`/`Secure` flags absent on auth cookies |
| A08 | Software & Data Integrity Failures | CDN script tags without `integrity` hash; no signature verification for downloaded artifacts; GitHub Actions using third-party actions at mutable `@main` ref |
| A09 | Security Logging & Monitoring Failures | Auth failures not logged; logs contain passwords, tokens, or PII; no structured log for privileged operations; `print()` instead of structured logger |
| A10 | Server-Side Request Forgery (SSRF) | User-supplied URL passed directly to `requests.get()` / `fetch()`; no allowlist for outbound URL targets; metadata endpoint reachable from container |

---

## Secret Detection Regex Set

Run against the full diff or repo with `git grep -P` or `ripgrep`. A match is a
CRITICAL finding requiring immediate credential rotation.

```
# AWS Access Key
AKIA[0-9A-Z]{16}

# AWS Secret Access Key (context: key = value pattern)
(?i)(aws_secret_access_key|aws_secret)\s*[=:]\s*[A-Za-z0-9/+]{40}

# GitHub Personal Access Token (classic)
ghp_[A-Za-z0-9]{36}

# GitHub Fine-Grained Token
github_pat_[A-Za-z0-9_]{82}

# Generic Bearer / API token assignment
(?i)(api_?key|api_?token|bearer|secret_?key|access_?token)\s*[=:]\s*["']?[A-Za-z0-9\-_]{20,}["']?

# JWT (three base64url segments)
eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+

# RSA Private Key header
-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----

# Generic .env assignment of sensitive value
(?i)^(PASSWORD|PASSWD|SECRET|TOKEN|KEY)\s*=\s*.{8,}

# Slack token
xox[baprs]-[A-Za-z0-9\-]{10,}

# Stripe secret key
sk_(live|test)_[A-Za-z0-9]{24,}
```

**After any match:** rotate the credential before fixing the code. Treat the
leaked secret as fully compromised from the moment of first commit.

---

## Dependency Scan Commands

Run all three scans and include output in the report. Flag any finding rated
HIGH or CRITICAL as a FAIL.

### Python

```bash
# Install if absent
pip install pip-audit

# Scan installed environment
pip-audit --strict --output json > pip-audit-report.json

# Or scan a requirements file directly
pip-audit -r requirements.txt --output json

# With poetry
poetry export -f requirements.txt | pip-audit -r /dev/stdin
```

### Node.js / npm

```bash
# Skip dev-only deps (production audit)
npm audit --omit dev --json > npm-audit-report.json

# Or with pnpm
pnpm audit --prod --json > pnpm-audit-report.json
```

### Go

```bash
# List all modules (transitive)
go list -m all > go-modules.txt

# Use govulncheck for CVE detection
govulncheck ./...
```

Minimum action thresholds:
- CRITICAL: block merge, patch immediately.
- HIGH: patch within 48 h; document in report if deferring.
- MEDIUM: schedule within current sprint.
- LOW / INFO: log in backlog.

---

## Auth/Authz Audit Checklist

### Cookie Flags

Every auth-session cookie must carry all three flags:

| Flag | Required Value | Signal if Missing |
|---|---|---|
| `Secure` | present | Cookie transmitted over HTTP → session hijack risk |
| `HttpOnly` | present | JS-accessible session cookie → XSS escalation |
| `SameSite` | `Strict` or `Lax` | CSRF possible |

### CSRF Tokens

- POST/PUT/PATCH/DELETE endpoints that mutate state must validate a CSRF token.
- Token must be tied to the session and verified server-side.
- SameSite=Strict alone is not sufficient for all browser versions.

### Password Hashing

Accepted algorithms: `bcrypt` (work factor ≥ 12), `argon2id` (m ≥ 64 MB, t ≥ 3).
Unacceptable: `md5`, `sha1`, `sha256` (without stretching), plain text, base64.

```python
# Correct (Python)
from passlib.hash import argon2
hashed = argon2.using(time_cost=3, memory_cost=65536).hash(password)
```

---

## Injection Vectors

### SQL Injection

```python
# FAIL — string interpolation
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# PASS — parameterized
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### Command Injection

```python
# FAIL
subprocess.run(f"convert {filename} output.png", shell=True)

# PASS
subprocess.run(["convert", filename, "output.png"], shell=False)
```

### Prompt Injection

Pattern: user content included verbatim in a system prompt or instruction block.

```python
# FAIL
system_prompt = f"You are a helpful assistant. User says: {user_message}"

# PASS — user content confined to a clearly delimited role
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": user_message},  # separate role, not interpolated
]
```

Regex signal for prompt injection risk:
```
(?i)(system_?prompt|instruction)\s*[=+]\s*f["'].*\{.*\}
```

### Template Injection (Jinja2 / Mako)

```python
# FAIL — render with user input as template source
jinja2.Template(user_input).render()

# PASS — user input as variable only
jinja2.Environment(autoescape=True).from_string(template_str).render(value=user_input)
```

### ReDoS (Regex Denial-of-Service)

Patterns with nested quantifiers on overlapping groups are vulnerable:
```
(a+)+   (a|aa)+   ([a-zA-Z]+)*
```
Fix: use possessive quantifiers or rewrite to linear-time equivalent.

---

## IaC Security Review

### Dockerfile

| Check | PASS | FAIL |
|---|---|---|
| Non-root USER | `USER <name>` or `USER <uid>` declared after installs | `USER root` or no USER directive |
| No secrets in ENV/ARG at build time | Build args are non-sensitive | `ARG API_KEY` with real value in compose |
| Minimal base image | `slim`, `alpine`, distroless | `ubuntu:latest`, `debian:latest` |
| No `COPY . .` before dependency install | deps installed first for layer cache | single `COPY . .` at top |
| Port exposure matches threat model | Only necessary ports in `EXPOSE` | `EXPOSE 22` in non-SSH container |

### GitHub Actions

| Check | PASS | FAIL |
|---|---|---|
| Third-party actions pinned to SHA | `uses: actions/checkout@a81bbbf` | `uses: actions/checkout@main` |
| OIDC token scope minimal | `permissions: contents: read` | `permissions: write-all` |
| No `pull_request_target` + checkout of PR head | n/a | workflow checks out PR code in high-privilege context |
| Secrets not echoed in logs | `run: echo masked` | `run: echo ${{ secrets.TOKEN }}` |

### Terraform / IaC

| Check | PASS | FAIL |
|---|---|---|
| IAM policy actions | Explicit list | `"Action": "*"` |
| S3 bucket public access | `block_public_acls = true` | `acl = "public-read"` without intent |
| Security group ingress | Port-specific CIDR | `cidr_blocks = ["0.0.0.0/0"]` on non-80/443 ports |

---

## STRIDE Threat-Modeling Template

For each data-flow boundary in scope, assess all six categories.

```
Component: <name>
Data-flow: <source> → <destination>

| Threat | Mitigated? | Control | Residual Risk |
|---|---|---|---|
| Spoofing (identity) | yes/no | <auth mechanism> | <LOW/MED/HIGH> |
| Tampering (data integrity) | yes/no | <signing/validation> | |
| Repudiation (audit trail) | yes/no | <logging policy> | |
| Information Disclosure | yes/no | <encryption/access ctrl> | |
| Denial of Service | yes/no | <rate limiting/timeouts> | |
| Elevation of Privilege | yes/no | <authz checks> | |
```

---

## CVSS-Aware Severity Matrix

| Severity | CVSS Range | SLA | Merge Action |
|---|---|---|---|
| CRITICAL | 9.0 – 10.0 | Rotate/patch before any other work | Block merge; escalate immediately |
| HIGH | 7.0 – 8.9 | Patch within 48 h | Block merge unless mitigated with compensating control |
| MEDIUM | 4.0 – 6.9 | Patch within current sprint | WARN in report; merge allowed with documented acceptance |
| LOW | 0.1 – 3.9 | Backlog item | INFO in report; merge allowed |
| INFO | N/A (best practice) | Discretionary | Advisory only |

---

## Report Template

Emit as HTML. Section order is mandatory.

### Executive Summary

```
Overall verdict: CRITICAL / HIGH / MEDIUM / LOW / CLEAN
OWASP findings: N (C=x, H=y, M=z, L=w)
Dependency CVEs: N
Secret leaks: N
IaC issues: N
```

### Findings

Each finding:

```
ID: SEC-<n>
CWE: CWE-<id> — <name>
Severity: CRITICAL | HIGH | MEDIUM | LOW | INFO
CVSS: <score> (if applicable)
File: <path>:<line>
Description: <what is vulnerable>
Evidence: <REDACTED code snippet — never include live credentials>
Fix: <specific remediation>
```

### Dependency Audit

Paste `pip-audit` / `npm audit` / `govulncheck` JSON summary (not raw output).
Table: Package | Current Version | CVE | CVSS | Fix Version.

### Secrets Scan

List every matched pattern: file:line, regex pattern that matched, action taken
(credential rotated / false-positive noted).

### Infrastructure Review

Dockerfile, GitHub Actions, and Terraform findings with line references.

### Backlog

Medium and Low findings deferred with justification and ticket reference.
