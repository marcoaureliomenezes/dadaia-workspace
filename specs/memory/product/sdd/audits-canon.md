---
slug: audits-canon
title: audits-canon
tldr: Audits are committed three-pillar reviews over a sha window, findings moved by audit.py; decisions.jsonl records only the operator accepts, with his ruling.
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
- An audit is a committed folder `specs/audits/<YYYYMMDD>-<slug>/` holding `AUDIT.md` (scope, the window `[from-sha, HEAD]`, method per pillar, the eight forensic metrics, summary) and `FINDINGS.jsonl`; a bound session writes `specs/audits/**` directly in the repo checkout, the one repo path no worktree carries ([[sdd-gate-v3]]).
- The window opens at the newest record in `specs/audits/_archive/audits_histo.jsonl`, or covers the whole history when that file is empty; an audit is never a release milestone.
- A context whose memory holds no real content — `ARCHITECTURE.md` or `QUALITY.md`, fixed sections stripped, still equal to a shipped scaffold digest (every historical scaffold's digest is kept in `shipped-hashes.json`), or no product atom in the catalog — gets the first pass (`dd-audit-project`'s first-pass section, applying while doctor's next step is `first-pass`), the `ONBOARDING` agent step whose fix line names that section's absolute path and the pending items ([[workspace-init]]): its worklist is `memory.py drift --since <the repo's first commit>`, every uncovered code unit; `dd-product-engineer` fills `ARCHITECTURE.md`, `QUALITY.md` and the product atoms from the code and from `specs-bkp/` when present; done = the worklist covered and `dadaia doctor --context <ctx>` exit 0 (`LINT-1` validates the atoms, `LEDGER-MEMORY-SCHEMA` runs `memory.py check` over the generated pair). The first pass opens no audit window; the next onboarding step is `publish` (`context baseline`).
- All three pillars run together, and fewer than three is not an audit: bug history over every record in the window, stamping `audited` through `bugs.py update --set` ([[bug-ledger]]); spec compliance through `dadaia doctor` plus commit shapes, milestone completeness and the job-file rules no script reads — disjoint envelopes between jobs with no DAG edge, a born task citing its AC, a cancelled task keeping its reason, hot files in at most one `W:` per stage (a generated one in none), each AC naming its test level, no edit after approval ([[workspace-doctor]], [[release-lifecycle]]); memory drift, running every principle's `Measured by:` check and flagging HIGH a canonical memory hunk with no accepted decision in the same commit.
- `finding-record-v1` keeps `id`, `pillar` (`bugs | specs | memory`), `severity`, `refs`, `claim` and `evidence` immutable and `disposition`, `release`, `reason` mutable; `disposition` is `open` or one of `resolved superseded deferred rejected`; `evidence` is a reproducible command plus a redacted one-line result.

## The writer — `audit.py`

- `python3 .agents/skills/dd-audit-project/scripts/audit.py <verb> [--specs <path>]` is the findings ledger's one writer and validator; `<audit>` is confined to a live folder directly under `specs/audits/`, never `_archive/`, and every refusal carries one `fix:` line.
- `disposition <audit> <finding-id> --disposition resolved|superseded|deferred|rejected [--release <id>] [--reason <text>]` rewrites one finding's governance triple in place, every other field unchanged; `resolved`/`superseded` need `--release`, `deferred`/`rejected` need `--reason`; an unknown finding is refused naming the known ids, an unknown audit naming the live ones.
- `close <audit> --sha <window-end>` requires `--sha`; it refuses an audit with any undispositioned finding (naming it), or whose findings name more than one release (the fix re-dispositioning a finding naming another release to the first); otherwise, a zero-finding audit included, it appends one `histo-record-v1` to `audits_histo.jsonl` — `disposition: resolved` with the one remediation release, else `deferred` when a finding is deferred, else `rejected`, its `reason` naming the counts, the per-pillar counts as `summary`, `entry = {sha, pillars, dispositions}` — and deletes the folder, the histo append last.
- An archived audit record missing its sha is recovered with `git log -S <audit-id> -- specs/audits` (`dd-bug-resolution`'s `LINEAGE.md`).
- `check [--json]` validates every live `FINDINGS.jsonl` and `audits_histo.jsonl`, one finding per invalid line: a `FINDINGS.jsonl` line is an `Operator action:` to rewrite it as one `finding-record-v1` record, an archive line one to discard or revert the change and redo it through `audit.py close`; `dadaia doctor`'s `ledgers` section runs it (`LEDGER-FINDINGS-SCHEMA`) ([[workspace-doctor]]).
- One audit generates at most one remediation release (none for a zero-finding audit), which dispositions every finding at its closure sweep before the audit closes; a candidate SPEC carries a finding on its Origin line by its full id (`<audit-id>-F<nnn>`), and `release.py check` traces it to its disposition ([[release-lifecycle]]).

## Decisions

- `specs/ADRs/decisions.jsonl` (`decision-record-v1`) is the decision ledger: one line per decision, fields `id ts title status context decision consequences measured_by supersedes amends ruling`, `status` one of `proposed accepted rejected superseded`; it has no writer script — agents append with file tools inside a worktree ([[worktrees]]): a proposal `docs(adr): propose <slug>` or an in-place repair of a dead `measured_by` `chore(adrs): repair …` in a `backlog/<slug>` or `define` tree, an acceptance `docs(adr): accept <slug>` in a `define` or `reconcile` tree with its canonical-memory hunk.
- Any agent appends a `proposed` record; only the operator accepts one, and no role agent writes `accepted` or `ruling` (the personas and the root map point to `specs/ADRs/AGENTS.md`).
- An `accepted` record carries a non-empty `measured_by`, free text naming the check, and `ruling: {date, words}` — the operator's verbatim words or his recorded grill answer id; words reading as delegated or "in session" are refused.
- A record that is not `rejected` and supersedes or amends an accepted one must itself carry a ruling, `accepted` or since `superseded`.
- A canonical memory statement in `ARCHITECTURE.md` or `QUALITY.md` changes only in the commit carrying its accepted decision, except a correction of a non-principle section (Tech Stack, Structure, Gates, the fixed blocks) that only states what the code already is, whose commit names its code evidence instead; a reversal is a new record naming the old one in `supersedes` or `amends`, the superseded line staying in place.
- `dadaia doctor` runs `LEDGER-ADR-SCHEMA` over every committed line, read through the ledger scripts' one JSONL reader and schema engine — the schema with its `ruling` rule, the ruled-lineage rule and the `0001..N` numbering, each finding's fix an `Operator action:` to discard or revert the change that wrote the line — and `ADR-SUPERSEDED-CITATION` over memory atoms, skills, data and scaffold that cite a superseded decision ([[workspace-doctor]]).

## Runtime state

`specs/audits/<dir>/{AUDIT.md,FINDINGS.jsonl}`, `specs/audits/_archive/audits_histo.jsonl`, `specs/ADRs/decisions.jsonl`.

## Dependencies

[[bug-ledger]], [[release-lifecycle]], [[workspace-doctor]], [[sdd-gate-v3]], [[agent-orchestration]], [[worktrees]].
