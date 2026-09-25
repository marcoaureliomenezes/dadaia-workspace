---
slug: bug-ledger
title: bug-ledger
tldr: One bug record per line in BUGS.jsonl, registered after operator confirmation, closed only by a transition carrying evidence; bugs.py writes it.
summary: The bug ledger — specs/bugs/BUGS.jsonl, one record per bug keyed by id, with no git-derived cache; the stdlib script bugs.py is its one writer and validator, and the ask-first registration plus the seven-phase resolution method run over it.
tags: [sdd, bugs, ledger, governance]
sources:
  - dadaia_workspace/public/skills/dd-bug-resolution/**
  - dadaia_workspace/public/skills/dd-bug-registration/**
  - dadaia_workspace/public/schemas/bugs/**
  - dadaia_workspace/core/models/bugs.py
  - dadaia_workspace/features/specs/doctor_governance.py
---

## The record

- `specs/bugs/BUGS.jsonl` holds one record per bug, appended once and keyed by `id`; git history is that line's change log, and the record carries no git-derived fact.
- `bug-record-v1` sorts every field into immutable core (`id ts reported_by title severity surface component context symptom repro expected`), mutable governance (`status cause caused_by resolved_release audited closed_at`) and write-once (`solution evidence_loop evidence_seam evidence_diff diff_direction superseded_by`); an unknown key is a finding.
- `status` is `open | resolved | superseded | deferred | rejected`; `closed_at` is non-null exactly when `status` is terminal and never earlier than `ts`.
- `surface` is the six non-feature layers (`cli core hooks infrastructure public-assets tests`) plus the feature packages on disk; `unknown` stays valid only on records already carrying it; `component` is free-text `path#symbol`.
- Every written field except `id`, `ts` and `reported_by` is redacted on write: control characters stripped, home-directory user names and IPv4 addresses masked.

## The writer — `bugs.py`

- `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py <verb> [--specs <path>]` is the ledger's one writer and one validator; every write builds the new ledger bytes, runs `check` over them, and only then replaces the file atomically, so a refused write leaves the file byte-identical.
- A write that finds the file changed under it re-reads and re-applies once; a second concurrent change refuses with `re-run this command`, so two fixers resolve by whichever lands first.
- Verbs: `append`, `status` (open only, `--all` for every record), `stats`, `update`, `resolve`, `supersede`, `defer`, `reject`, `archive`, `check`; every refusal prints one `fix:` line.
- `append` opens a record at `status: open`, refusing a duplicate id (a reopen is a new record) and `--surface unknown`.
- `update <id> --set field=value` writes a governance field; it refuses `status` and `closed_at` (owned by the transitions), `caused_by` (owned by `resolve`), a change to an immutable core field and a differing second write to a write-once field.
- A terminal status is reached only through its transition, each refusing an incomplete call with every missing field named: `resolve` needs `--cause --caused-by --resolved-release --solution --evidence-loop --evidence-seam --evidence-diff`, derives `diff_direction` from `--evidence-diff`'s `net-negative|net-positive|net-neutral:` prefix and accepts `--caused-by` only as a ledger id or `none`; `supersede` needs `--by`; `defer` and `reject` need `--reason`.
- `archive` moves records whose `closed_at` is older than 90 days (`--threshold-days`) into `specs/bugs/_archive/bugs_histo.jsonl`; a filing date never makes a record archivable.
- `dadaia doctor`'s `ledgers` section runs `bugs.py check` (`LEDGER-BUGS-SCHEMA`), and `SPEC-DOC-041` warns on a terminal record closed longer ago than the archive threshold ([[workspace-doctor]]).

## Registration and resolution

- A bug is a tool breaking a contract it documents; an agent's own mistake, wrong usage, an environment limit, a designed validation, a law ambiguity or a missing feature is not one.
- Registration is ask-first: the agent proposes the violated contract line, one reproducing command already run, why it is not agent error and a severity (CRITICAL a stall or data loss; HIGH a contract broken on the default path; MEDIUM off the default path or with a workaround; LOW message or cosmetic), and `append` runs only after the operator confirms; with no operator present the proposal leaves as one handoff finding whose `message` starts `bug-proposal:` ([[agent-comms]]).
- A confirmed bug is fixed on the live feature branch in any phase, with no SPEC, PLAN or TASKS: register, lineage, RED test, root-cause fix, GREEN, `resolve` with evidence, one commit holding code, test and the ledger line.
- Resolution follows seven ordered phases — lineage, red loop, minimise, hypothesise, instrument, seam test, cleanup and resolve; lineage reads at most the 20 most recent records sharing the bug's `surface` or `component` in the window since the newest archived audit and ends in `caused_by: <id> | none` plus a rebuild decision.
- ≥ 2 prior fixes on the unit the bug lands in, within that window, make the fix a REBUILD of that unit, never a third patch: the fix commit body echoes `rebuild: <unit> — prior fixes <id>, <id>` (or `rebuild: none`) beside `caused_by:`, `evidence:` and `prior diffs read:`, and a rebuild's `--solution` opens with `REBUILD <unit>:`; `bugs.py` counts nothing and carries no field for it ([[release-lifecycle]]).
- A fix whose diff grows the touched feature is routed to the architecture lens before it lands ([[agent-orchestration]]).

## Runtime state

`specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl`.

## Dependencies

[[workspace-doctor]], [[agent-comms]], [[agent-orchestration]], [[audits-canon]], [[release-lifecycle]].
