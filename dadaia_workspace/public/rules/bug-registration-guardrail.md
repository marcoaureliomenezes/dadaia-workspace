# bug-registration-guardrail

This rule is always active, for every Layer-1 entry harness (Claude, Codex, PI).

## Law

Any time you encounter a **bug** while operating dadaia-workspace tooling, you
MUST register it before you finish the turn by appending a `reported` event with
`dadaia bugs append` (see "How to register" below). "Operating the
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
and inside any `repos/<slug>/`: never blocked, writable by any persona / any runtime
regardless of any other session's presence. There is no excuse to defer registration.

## What NOT to register

This rule is for bugs in **dadaia-workspace itself**. Do NOT file a bug for:

- An error in your own throwaway/exploratory script (wrong import, typo, bad
  path) where the underlying tool is correct — fix your script and move on.
- A normal validation failure the tool is *designed* to emit (e.g. `specs
  doctor` correctly reporting a non-compliant tree, or the gate correctly
  blocking an unauthorized write). That is the contract working, not a bug.

When in doubt whether a failure is a product bug or your own mistake, reproduce
it against the tool directly; if the tool misbehaves, register it.

## How to register — `dadaia bugs append`

Bugs are **event-sourced JSONL** (v0.1.46), not hand-authored Markdown. Register a
bug by appending a `reported` event with the `dadaia bugs append` CLI — never by
creating a `specs/bugs/<slug>.md` file. Each event is one JSON line validated against
`bug-event-v1` and appended to `specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl`.

```bash
dadaia bugs append \
  --bug-id <short-kebab-case-slug> \
  --event reported \
  --reported-by <agent-or-runtime> \
  --title "<short human-readable title>" \
  --severity LOW|MEDIUM|HIGH|CRITICAL \
  --surface <component/command that failed> \
  --component <subsystem/module> \
  --context <active-spec-context> \
  --tag <tag> [--tag <tag> ...] \
  --symptom "what happened (the error / wrong output)" \
  --repro "the exact command / steps" \
  --expected "what the contract promises" \
  --notes "environment / logs — redacted"
```

`append` validates against the schema before writing: on any validation failure
nothing is written and the command exits non-zero with the message. The `reported`
event requires every field above (`title`, `severity`, `surface`, `component`,
`context`, `tags[]`, `symptom`, `repro`, `expected`, `notes`).

**Event lifecycle.** A `bug_id`'s stream opens with `reported` and carries at most one
**terminal** event — `{resolved, superseded, deferred, rejected}` — appended later by
the release that dispositions it (`resolved --release <id>`, `superseded
--superseded-by <slug>`, `deferred`/`rejected --reason <text>`). Do not append a
terminal event when you register; that is the disposition step, not registration.

Inspect the stream with `dadaia bugs status` (lists open bugs) and `dadaia bugs stats`
(aggregates by severity/status). Archiving a bug's legacy source is a `git mv` into
`specs/bugs/_archive/` and emits **no** JSONL event.

### Redaction (preserved requirement)

Never put operator-local absolute paths, IPs, hostnames, private repo names, or
secrets into any bug event field — especially `notes`, `repro`, and `symptom`. Redact
first (see the privacy/public-boundary rules). The store's `redact()` is a backstop,
not a licence to paste raw local data.
