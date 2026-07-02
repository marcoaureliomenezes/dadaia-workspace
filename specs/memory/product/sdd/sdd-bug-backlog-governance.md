---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: Event-sourced JSONL bug store + backlog-consistency engine + bug/backlog → release governance (grill, disposition, audit-disposition law, security-gated push).
summary: >-
  Owns the bug + backlog governance mechanism: the event-sourced JSONL bug store
  (bug-event-v1; dadaia bugs append|status|stats; reported + one terminal event),
  the backlog-consistency engine (subject registry, fail-closed classifier,
  backlog doctor BL-*, consumed_backlog ledger + removal-on-release), the
  bug/backlog → release protocol (PM-dispatched pick, sanitize, mandatory grill,
  bug-always-solved/supersession), the audit-disposition law, the alpha-N/rc-N
  maturation model, and the mechanically gated push boundary.
tags:
  - sdd
  - governance
  - release-lifecycle
  - backlog
  - bugs
  - alpha-rc-model
  - backlog-ownership
agent_tier: self-pull
token_estimate: 1575
last_updated: '2026-07-02'
release_origin: v0.1.48
---

Skill: `dadaia-release-definition` · Rules: `release-governance.md`, `backlog-ownership.md`, `bug-registration-guardrail.md` (always-on)

## Purpose

Defines how **bugs are registered and dispositioned**, how the **backlog stays a
consistent SET**, and how **bugs + backlog become releases** that mature and are
reviewed. Three pillars: the bug event store, the backlog-consistency engine, and the
bug/backlog → release protocol with its gates.

## What it is

### Bug event store (JSONL, event-sourced)

Bugs are **JSONL events**, never Markdown files with status frontmatter. The store
lives in `specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl` — append-only files per hour window,
with a row-count rotation ceiling — and is **git-tracked** (the source repo's
`.gitignore` re-includes `specs/bugs/*.jsonl`). Each line is a JSON validated against
**`bug-event-v1`** before the append: on validation failure nothing is written and the
command exits non-zero.

- **Registration:** `dadaia bugs append --bug-id <slug> --event reported --title …
  --severity … --surface … --component … --context … --tag … --symptom … --repro …
  --expected … --notes …` — the `reported` event requires all these fields.
- **Disposition (terminal):** a `bug_id` carries **at most ONE terminal event** from
  `{resolved, superseded, deferred, rejected}` (`resolved --release <id>`;
  `superseded --superseded-by <slug>`; `deferred`/`rejected --reason <text>`),
  appended by the release that dispositions it — never at registration. A later
  `reported` **reopens** the `bug_id` (clears the previous terminal; a legitimate
  reopen is not a double-terminal).
- **`archived` is a NON-terminal annotation:** archiving a bug's legacy source is a
  `git mv` into `specs/bugs/_archive/` and **emits no event**.
- **Inspection:** `dadaia bugs status` (open bugs) and `dadaia bugs stats` (aggregates
  by severity/status). `features/bugs/service.py` folds the stream into current state
  per `bug_id`.
- **Redaction:** no field carries operator-local absolute paths, IPs, hostnames, or
  secrets; the store's `redact()` is a backstop, not a licence.
- **Mechanical invariant:** SPEC-DOC-033 ([[specs-doctor]]) validates per-line schema,
  the rotation ceiling, and event coherence (terminal without a prior `reported` ⇒
  ERROR; double terminal ⇒ ERROR).
- **Coexistence:** `dadaia bug new` (the legacy Markdown scaffolder) still exists in
  the CLI, but the canonical registration path is `dadaia bugs append` — no new
  workflow writes a bug as `.md`.

### Backlog-consistency engine (`features/backlog/`)

The backlog is a deduplicated, conflict-free, non-stale SET, mechanically enforced:

- **Item schema:** frontmatter `intents[]`, each intent `Subject{kind, ref} →
  change`; `kind ∈ {code, api, cli, panel, doc, invariant, catalog}`; typed refs,
  never free text (`code` refs are module-relative `path#symbol`; operator-local /
  private-repo paths rejected).
- **Canonical subject registry** (`subject_registry.py`): auto-derived from the live
  tree on every run (never a stored file) — kinds `code`/`cli`/`catalog`/`doc`/
  `invariant`; `panel`/`api` bind only through the operator's alias map
  (`.dadaia/states/backlog_subject_aliases.txt`). The model proposes a subject; Python
  binds it to an anchor and **HALTs** on unresolved/ambiguous (never silent NEW).
- **Fail-closed classifier** (`classifier.py`): empty anchor intersection ⇒
  `UNRELATED` (no model); same anchors + same change ⇒ `DUPLICATE`; shared anchor +
  divergent change ⇒ **`DIVERGENT_CONFLICT`** by default — the model may only
  downgrade with an explicit proven-compatible merge.
- **`dadaia backlog doctor`** (the real enforcement — backlog is gitignored +
  ADDITIVE, so the file-write gate does not classify it): BL-SCHEMA / BL-DUP /
  BL-CONFLICT / BL-STALE, non-zero exit on violation. Runs in CI (job
  `backlog-doctor`) and in the **scoped** pre-commit chokepoint: BL-* blocks only
  commits whose staged paths intersect `specs/backlog/**` — pre-existing debt does not
  block an unrelated commit; the full sweep stays in CI.
- **Removal-on-release (closed loop):** the SPEC's `**Consumes:** <slugs>` line →
  the post-step of `dadaia lifecycle release define` writes the ledger
  `specs/_archive/<release>/consumed_backlog.json` (fail-loud `ConsumesBindError` on
  an unresolvable slug/anchor; full-slug granularity) → `dadaia lifecycle close` runs
  the residual-aware removal (rewrite-down-to-residual default; full removal only at
  zero residual, with a durable copy in `_archive/<release>/consumed-backlog/<slug>.md`
  BEFORE the unlink). BL-STALE matches by exact slug membership against the ledger.

### Ownership

`project-manager` **curates** `specs/backlog/**`; `product-engineer` **reads** the
PM-curated backlog to author SPEC/PLAN/TASKS and never curates. There is no ownership
gate — `specs/backlog/**` is ADDITIVE and always flows; the product's only
deterministic lock is the single-session lease per Spec Context. Consistency
enforcement is the doctor above.

## Usage flow

### Bug/Backlog → Release (skill `dadaia-release-definition`)

1. **Dispatch.** PM dispatches PE to define a release from the open bugs
   (`dadaia bugs status`) + backlog. PE never self-initiates.
2. **Sanitization.** Stale/invalid items receive an explicit disposition (backlog:
   terminal status + archive move; bugs: a `deferred`/`rejected` event with a reason).
   Never delete — archive.
3. **Pick.** Open bugs and undispositioned audits **outrank** plain backlog. Every
   picked bug is solved in the release (**bug-always-solved**), unless a picked
   backlog item supersedes it — then a `superseded --superseded-by <slug>` event + the
   item's TASKS cover the bug's acceptance. Never silently dropped.
4. **Audit-disposition law:** every audit generates exactly ONE remediation release
   that gives EACH finding an explicit disposition (fixed / superseded /
   deferred-with-reason / rejected-with-reason); the audit archives to
   `specs/audits/_archive/` only when fully dispositioned AND the release approved
   (SPEC-DOC-036/038 are the backstop).
5. **Mandatory grill** (`dadaia-grill-me`) on the picked set BEFORE the SPEC.
6. **SPEC** as Draft → `Aprovado`. At the end of the release, PE appends the terminal
   events of the dispositioned bugs.

### Maturation and push boundary

- A release is `v<M>.<m>.<p>` on a single `feature/{version}` branch, maturing through
  `alpha-N → rc-N` segments (each segment with SPEC/PLAN/TASKS/CLOSURE when used;
  `ACTIVE.md` carries an optional `segment:`). A hotfix is a normal release that ships
  from `alpha-1` (PATCH ≥ 1). Coexistence: `dadaia specs hotfix open` exists as the
  scaffolding verb — the scaffolder enforces PATCH ≥ 1, and `hotfix/v*` branches
  trigger CI.
- **Commits** are never review-blocked (only the pre-commit lease gate + the scoped
  backlog-doctor). **Push** is mechanically gated: the pre-push hook runs `dadaia ci
  preflight` (ruff format/check, mypy --strict, pytest — excluding
  `tests/performance`) AND the security-verdict check — a `security-reviewer` APPROVED
  handoff whose `metrics.commit_sha` equals each pushed sha ([[sdd-gate-v3]]).
- **Semantic gates** (`features/lifecycle/gates.py`) validate QA/security/code-review
  handoffs by agent, context, release, verdict, hash, sha, age, and severity — the
  gates the dadaia-workflows consume ([[lifecycle-foundation]]).
- **Blocked/resume:** when an external action cannot execute, `dadaia lifecycle
  preflight` returns a typed BLOCKED with the exact command + resume token.

## Typical trigger

Bug registration in any session (ADDITIVE, no lease, no bind); start of a release
cycle (PM dispatches PE); disposition of bugs/audits at the end of a release; a commit
touching `specs/backlog/**`.

## Differentiator

Every release decision has an explicit owner; every bug has a declared destiny in an
auditable, schema-validated stream; the backlog accumulates neither duplicates nor
silent conflicts; audits never become read-and-forget; and the push boundary is a
mechanical gate, not a convention.

## Runtime state touched

- `specs/bugs/*.jsonl` (git-tracked; append via `dadaia bugs append`) +
  `specs/bugs/_archive/` (legacy sources moved by `git mv`).
- `specs/backlog/**` (gitignored in the source repo; ADDITIVE) +
  `.dadaia/states/backlog_subject_aliases.txt`.
- `specs/_archive/<release>/consumed_backlog.json` + `consumed-backlog/<slug>.md`.
- `specs/releases/ACTIVE.md`, `specs/releases/<ver>/**`.
- Git hooks: `pre-commit-lease-gate.sh` (+ scoped backlog-doctor),
  `pre-push-ci-gate.sh` (preflight + verdict).

## Dependencies

- [[sdd-gate-v3]] — the path classes (bugs/backlog/audits ADDITIVE; `_archive` FROZEN
  before ADDITIVE) and the git chokepoints.
- [[specs-doctor]] — SPEC-DOC-033 (event-store invariant), 031/035 (backlog
  disposition), 036/038 (audit disposition/archiving).
- [[lifecycle-foundation]] / [[dadaia-workflows]] — the workflow bodies
  (release_definition, backlog_definition, bug_report) that orient this flow.
- [[public-asset-distribution]] — propagates skill + rules + git-hook scripts.
