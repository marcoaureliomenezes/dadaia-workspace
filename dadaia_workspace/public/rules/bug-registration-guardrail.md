# bug-registration-guardrail

This rule is always active, for every Layer-1 entry harness (Claude, Codex, OpenCode, PI).

## Law

Any time you encounter a **bug** while operating dadaia-workspace tooling, you
MUST register it as a bug file before you finish the turn. "Operating the
tooling" includes: projection (`dadaia public stage/install/doctor`), `specs
doctor`/`specs upgrade`, scaffolding/onboarding, hooks, the SDD gate, locks &
leases, context bind/alive/dead, the panel, reports/handoffs, the `dadaia` CLI,
and any production behavior of the library or its generated instance.

A "bug" is any reproducible failure, crash, wrong result, broken invariant,
silent no-op where action was expected, or projection/doctor drift — i.e. the
tool did not behave as its contract promises. (See `source-vs-instance`: a
failed workspace operation is a **product bug of the library**, never a local
quirk.)

## Where bugs go

- **Self-hosting workspace** (the `dadaia-workspace` source repo is present under
  `repos/dadaia-workspace/`): register the bug in
  `repos/dadaia-workspace/specs/bugs/`.
- **Consumer workspace** (no source repo checked out): register the bug in the
  active spec-context's `specs/bugs/`, and report it upstream to the
  dadaia-workspace project.

Bug files are **ADDITIVE** — the SDD gate's path classifier is context-relative
(v0.1.10), so `specs/bugs/` resolves to the ADDITIVE class both at the workspace root
and inside any `repos/<slug>/`: never blocked, never lease-gated, writable by any
persona / any runtime. There is no excuse to defer registration.

## What NOT to register

This rule is for bugs in **dadaia-workspace itself**. Do NOT file a bug for:

- An error in your own throwaway/exploratory script (wrong import, typo, bad
  path) where the underlying tool is correct — fix your script and move on.
- A normal validation failure the tool is *designed* to emit (e.g. `specs
  doctor` correctly reporting a non-compliant tree, or the gate correctly
  blocking an unauthorized write). That is the contract working, not a bug.

When in doubt whether a failure is a product bug or your own mistake, reproduce
it against the tool directly; if the tool misbehaves, register it.

## Minimum bug record

A bug file is Markdown with frontmatter and at least:

```markdown
---
name: <short-kebab-case-slug>
status: Open
severity: LOW | MEDIUM | HIGH | CRITICAL
reported: <YYYY-MM-DD>
surface: <component/command that failed>
session_id: null
---

**Symptom:** what happened (the error, the wrong output).
**Repro:** the exact command / steps.
**Expected:** what the contract promises.
**Notes:** environment, logs (redacted of any operator-local path/secret).
```

Never put operator-local absolute paths, IPs, hostnames, private repo names, or
secrets in a committed bug file — redact first (see the privacy/public-boundary
rules).
