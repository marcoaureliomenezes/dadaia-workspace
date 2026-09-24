---
slug: audits-canon
title: audits-canon
tldr: Audits are committed three-pillar reviews over a sha window, their findings moved by audit.py; decisions are decisions.jsonl records the operator accepts.
summary: The two governance records that police canonical truth — an audit folder (AUDIT.md plus FINDINGS.jsonl) whose findings move by audit.py disposition and which audit.py close archives, and the decision ledger specs/ADRs/decisions.jsonl whose accepted records admit every canonical memory statement.
tags: [sdd, audits, findings, adrs, decisions, governance]
sources:
  - dadaia_workspace/public/skills/dd-audit-project/**
  - dadaia_workspace/public/schemas/audits/**
  - dadaia_workspace/public/schemas/ADRs/**
  - dadaia_workspace/features/specs/doctor_closure_audit.py
  - dadaia_workspace/features/specs/doctor_adr.py
---

## The audit

- The audit is the only full-tree inspection lane; every other quality boundary is diff-scoped. `dd-code-reviewer` runs it under the audit lens, suggested every five releases, never mandatory ([[agent-orchestration]]).
- An audit is a committed folder `specs/audits/<YYYYMMDD>-<slug>/` holding `AUDIT.md` (scope, the window `[from-sha, HEAD]`, method per pillar, the eight forensic metrics, summary) and `FINDINGS.jsonl`; `specs/audits/**` is ADDITIVE, writable bound or not ([[sdd-gate-v3]]).
- The window opens at the newest record in `specs/audits/_archive/audits_histo.jsonl`, or covers the whole history when that file is empty; an audit is never a release milestone.
- A context whose `audits_histo.jsonl` holds no record gets the first pass (`dd-audit-project` §3): its worklist is `memory.py drift --since <the repo's first commit>`, every uncovered code unit; `dd-product-engineer` fills `ARCHITECTURE.md`, `QUALITY.md` and the product atoms from the code and from `specs-bkp/` when present; done = the worklist covered and `memory.py check` exit 0, then the `audits_histo.jsonl` record opens the next window. It is the last onboarding level ([[workspace-init]]).
- All three pillars run together, and fewer than three is not an audit: bug history over every record in the window, stamping `audited` through `bugs.py update --set` ([[bug-ledger]]); spec compliance through `dadaia doctor` plus commit shapes and milestone completeness ([[workspace-doctor]]); memory drift, running every principle's `Measured by:` check and flagging HIGH a canonical memory hunk with no accepted decision in the same commit.
- `finding-record-v1` keeps `id`, `pillar` (`bugs | specs | memory`), `severity`, `refs`, `claim` and `evidence` immutable and `disposition`, `release`, `reason` mutable; `disposition` is `open` or one of `resolved superseded deferred rejected`; `evidence` is a reproducible command plus a redacted one-line result.

## The writer — `audit.py`

- `python3 .agents/skills/dd-audit-project/scripts/audit.py <verb> [--specs <path>]` is the findings ledger's one writer and validator; `<audit>` is confined to `specs/audits/`, and every refusal carries one `fix:` line.
- `disposition <audit> <finding-id> --disposition resolved|superseded|deferred|rejected [--release <id>] [--reason <text>]` rewrites one finding's governance triple in place, every other field unchanged; `resolved`/`superseded` need `--release`, `deferred`/`rejected` need `--reason`; an unknown finding is refused naming the known ids.
- `close <audit> --sha <window-end>` refuses an audit with no findings, with any undispositioned finding (naming it), or whose findings name more than one release; otherwise it appends one `histo-record-v1` to `audits_histo.jsonl` — `disposition: resolved`, the one remediation release, the per-pillar counts as `summary`, `entry = {sha, pillars, dispositions}` — and deletes the folder, the histo append last.
- `check [--json]` validates every live `FINDINGS.jsonl` and `audits_histo.jsonl`; `dadaia doctor`'s `ledgers` section runs it (`LEDGER-FINDINGS-SCHEMA`), and `SPEC-DOC-036` (an open finding in an archived audit) and `SPEC-DOC-038` (a live audit whose findings are all terminal) police both directions ([[workspace-doctor]]).
- One audit generates exactly one remediation release, which dispositions every finding at its closure sweep before the audit closes ([[release-lifecycle]]).

## Decisions

- `specs/ADRs/decisions.jsonl` (`decision-record-v1`) is the decision ledger: one line per decision, fields `id ts title status context decision consequences measured_by supersedes amends`, `status` one of `proposed accepted rejected superseded`; it has no writer script — agents append with file tools.
- Any agent appends a `proposed` record; only the operator flips it to `accepted`, and an `accepted` record names a `measured_by` the schema can resolve — a `pytest` or `lint-imports` invocation or a doctor code (`SPEC-DOC-nnn`, `WS-*`, `BL-*`, `RELEASE-TREE-*`, `LEDGER-*`).
- A canonical memory statement in `ARCHITECTURE.md` or `QUALITY.md` changes only in the commit carrying its accepted decision; a reversal is a new record naming the old one in `supersedes` or `amends`, the superseded line staying in place.
- `dadaia doctor` runs `LEDGER-ADR-SCHEMA` over every committed line and `ADR-SUPERSEDED-CITATION` over memory atoms, skills, data and scaffold that cite a superseded decision ([[workspace-doctor]]).

## Runtime state

`specs/audits/<dir>/{AUDIT.md,FINDINGS.jsonl}`, `specs/audits/_archive/audits_histo.jsonl`, `specs/ADRs/decisions.jsonl`.

## Dependencies

[[bug-ledger]], [[release-lifecycle]], [[workspace-doctor]], [[sdd-gate-v3]], [[agent-orchestration]].
