---
slug: release-lifecycle
title: release-lifecycle
tldr: Candidates, each in its own rc-<N>/, grow one live release; release.py writes _RELEASE.json; memory gates closure; promote merges a PR and archives it.
summary: The release lifecycle — one live release directory whose _RELEASE.json state document is written by release.py (new, phase, drift, memory, ship, check), candidates that each review the as-is units their demand touches, then define, implement and close a SPEC/PLAN/TASKS trio in its own rc-<N>/ folder, the structural PLAN checks (As-is review, Authorities, Parallel schedule) at IMPLEMENTATION, the memory reconciliation gate at closure, and promotion by merging the release PR release-please opens, which ship records by archiving the release folder.
tags: [sdd, release, candidate, lifecycle, memory, as-is-review]
sources:
  - dadaia_workspace/public/skills/dd-release-implementation/**
  - dadaia_workspace/public/skills/dd-release-definition/**
  - dadaia_workspace/public/skills/dd-spec-navigator/scripts/**
  - dadaia_workspace/public/schemas/releases/**
  - dadaia_workspace/core/release_state.py
  - dadaia_workspace/features/specs/doctor_release.py
---

## Release and candidate

- Exactly one release directory is live, `specs/releases/<M.m.p>/`, with open scope; it grows by candidates, each a closed-scope cycle whose `SPEC.md`, `PLAN.md` and `TASKS.md` sit in `releases/<M.m.p>/rc-<N>/`; the live candidate is the highest `rc-<N>/`, and no verb rewrites a closed one.
- Only `_RELEASE.json` sits at the release root: the specs canon and the pre-push gate refuse a flat trio ([[sdd-gate-v3]]), and `specs upgrade` folds one into the next `rc-<N>/` ([[specs-migration]]).
- The live candidate has two readers pinned equal by one contract test: `_release_store.live_ids` for the stdlib scripts and `core/gitflow.py`'s resolver for the package.
- `_RELEASE.json` is one mutable `release-state-v1` document `{schema, release, phase, defined, implemented, shipped, log}`; `phase` is `DEFINITION | IMPLEMENTATION | CLOSURE`, and the gate never reads it ([[sdd-gate-v3]]); `defined` and `implemented` hold the live candidate's stamps, each candidate's `phase` restamping them, so an earlier candidate's stamps survive only in its `log` notes.
- `log` is append-only, oldest first, entries `{ts, agent, kind, text}` with `kind` one of `note summary size drifts dispositions test-dispositions artifact-gc reviews merge memory`; it is the closure narrative's only home.
- Every SPEC carries `**Origin:** operator-demand | backlog:<slug>[,..] | bugs:<id>[,..]`; `SPEC-DOC-048` requires it on the live SPEC and resolves each cited slug or bug id ([[backlog-ledger]], [[bug-ledger]]).
- `specs/releases/_archive/` is history, exempt from every release check by location: `_archive/<M.m.p>/` holds a shipped release's whole folder, and `releases_histo.jsonl` is the ship ledger, one `delivered` line per release, ever.
- A live `releases/<M.m.p>/RELEASE.json` without `_RELEASE.json` is the doctor's `SPEC-DOC-046` warning, renamed by `--fix` ([[workspace-doctor]]).

## The writer — `release.py`

- `python3 .agents/skills/dd-release-implementation/scripts/release.py <verb> [--specs <path>]` is the state document's one writer and validator; each write validates the new bytes before replacing the file atomically, and every refusal carries one `fix:` line; a `phase` fix line names an absolute path derived from the script's own location — the trio document, `TASKS.md` or the installed `dd-release-definition/SKILL.md` — never a cwd-relative path or a shell command.
- `new <id> [--origin <origin>]` opens a candidate: a `SPEC.md` stub (Problem and context, Objective, Scope, Replaces, Out of scope, Dependencies and risks) in the next `rc-<N>/` plus `_RELEASE.json` in `DEFINITION`, all or nothing, writing no `PLAN.md`; on a live release already in `CLOSURE` with the same id it stacks the next candidate, reopening `DEFINITION` and leaving every closed `rc-<N>/` untouched; a second live release, a non-SemVer id or a symlinked path is refused; `--origin bugs:<ids>` seeds one scope clause per bug with its repro line.
- `phase IMPLEMENTATION --sha <sha>` requires all three trio files `**Status:** Approved`, then the PLAN structure (below), and stamps `defined`; `phase CLOSURE --sha <sha>` requires no `[ ]` or `[-]` task marker and no open `wt/*` worktree of the repo but the one it runs in ([[worktrees]]), and stamps `implemented`; each phase follows its predecessor exactly once per candidate.
- `memory --reviewed <slugs> --changed <slugs>` derives its window from the state document — the previous `kind: memory` entry's `until`, else `defined.sha` — to `HEAD`, computes the worklist itself and appends the closure's `kind: memory` log entry carrying `since`, `until`, `reviewed` and `changed`; it refuses outside `CLOSURE`, a worklist entry named in neither list, a name outside the worklist, and a `changed` atom git reports unmoved over the window.
- `ship --sha <sha> --pr <n>` records the merged promote PR: only a `CLOSURE` release ships, and one already archived is refused; it stamps `shipped`, appends its `delivered` line to the ship ledger and moves the whole release folder, `_RELEASE.json` and every `rc-<N>/`, to `_archive/<M.m.p>/`, deleting nothing.
- `check [--json]` validates every live state document, the live candidate's trio and PLAN structure in `IMPLEMENTATION` and `CLOSURE`, the one-live-release rule and the ship ledger; on a live release in `CLOSURE` it also re-judges the latest `kind: memory` entry over its own `since`..`until` with the `memory` verb's rules and requires that no atom's sources moved after its `until`; `dadaia doctor`'s `ledgers` section runs it (`LEDGER-RELEASE-SCHEMA`) ([[workspace-doctor]]).

## The candidate arc

- Definition: the picked backlog and bug set, the as-is review, the mandatory grill, the SPEC by `dd-product-engineer`, PLAN and TASKS by `dd-software-engineer`, one definition commit on the work branch (`<work prefix><live release id>`, with no live release the first-release default of `work_branch` in `dadaia_workspace/core/gitflow.py`, never derived from a tag; the constitution's `gitflow:`) ([[agent-orchestration]]).
- The SPEC's `Replaces` names one current behaviour per DELETE or REBUILD row, or `none` with its reason; tasks realizing DELETE/REBUILD rows precede tasks realizing ADD rows, each expand–contract (add the new path, switch consumers, delete the old), each independently green.
- Implementation: each task in its own `impl` worktree, reserved `[-]` in its own commit, TDD, local CI preflight, landed by `worktree.py merge` after the reviewer's `APPROVED` on the rebased commit; tasks share a Parallel-schedule step only when their `W:` sets are disjoint ([[worktrees]]).
- Closure runs in the candidate's `release` worktree, in order: `phase CLOSURE`, memory reconciliation, closure `log` entries, disposition sweep (`backlog.py exit`, `audit.py disposition`/`close`, `bugs.py archive`), artifact GC, the work -> integration PR merged green, then the operator's promote-or-continue choice ([[audits-canon]]).
- `SPEC-DOC-047` refuses a task whose write set names `specs/memory`: memory is closure procedure, never a task.

## The as-is review

- Definition's second step, after the pick and before the grill: `dd-software-engineer`, dispatched by the main thread, reads every As-is unit the picked set touches and its bug-ledger slice (`bugs.py status`/`stats`, `git log` on the unit), read-only, and returns the table in its handoff; the main thread carries it into the grill; it lands as PLAN §1.
- An As-is unit is a module or a law, skill or doc section with a today-behaviour — never `memory.py drift`'s code unit.
- PLAN §1 is one Markdown table `unit | today | bugs | verdict | why`, one row per touched As-is unit; the As-is verdict is `DELETE`, `REBUILD`, `UPDATE` or `KEEP`, considered in that order (DELETE vs KEEP is the deletion test), then `ADD` rows with `today` `—` only for what no existing unit can carry, `why` saying why.
- REBUILD is mandatory when the unit carries ≥ 2 bugs, the demand changes its fundamental behaviour, the change would need a flag, branch, special case or second path, or its contract contradicts the demand; the engineer and the reviewer judge these triggers — no script counts bugs or reads code.
- The `dd-release-definition` skill carries the PLAN §1 skeleton; a contract test extracts it from the skill text and proves it passes the check, so the teaching and the gate cannot drift.
- The check `phase IMPLEMENTATION` runs is structure only: the first level-2 heading whose text contains `as-is review` or `as is review` (case-insensitive); within its section, the table starts at the first line whose cells equal the five columns, the next line is the separator, data rows run until the first line without a pipe; cells split on unescaped pipes, outer pipes optional, trimmed of whitespace, `` ` `` and `*`; at least one data row; every As-is verdict one of the five, case-insensitive; an all-ADD table and empty `bugs`/`why` cells pass.
- A missing heading and a missing or malformed table refuse with distinct messages; a verdict outside the vocabulary names its row's unit and verdict; `_RELEASE.json` stays byte-identical; the check never reads SPEC `Replaces`, TASKS order or code.
- The same judge requires a `### … Authorities` table (`question | authority | consults | deleted`) under §1, each question with one non-empty authority, and a `## … Parallel schedule` table (`step | tasks open together | width | how`) stating a `Critical path`: each width counts its task ids, and two unfinished tasks in one step never share a `W:` path outside `TASKS.md`, the `*.jsonl` ledgers and each path the section declares `derived`.
- The review's spec axis reads PLAN §1 beside SPEC and TASKS: a DELETE or REBUILD unit the reviewed range leaves unchanged is a HIGH finding, a KEEP unit the range grew is a finding ([[agent-orchestration]]).
- A bug fix on a unit with ≥ 2 prior fixes in its lineage window is a rebuild of that unit, never a third patch ([[bug-ledger]]).

## The memory reconciliation gate

- `python3 .agents/skills/dd-spec-navigator/scripts/memory.py drift --since <sha> [--json]` lists the atoms whose `sources` globs match a path changed over `<sha>..HEAD` and every code unit no atom covers, exiting 1 while that worklist is non-empty; `--since` is required and has no default window.
- A code unit is derived from the audited repo alone: each directory directly holding a tracked code file, or a root-level code file on its own; `specs/`, `tests/`, `test/`, `docs/` and dot-directories hold none, and a unit is covered once any atom's `sources` match a file under it.
- Each listed atom is reconciled from its sources' diff — delete, update, then add — and `memory.py catalog generate` regenerates the catalog pair ([[workspace-doctor]]).
- `release.py check` (`LEDGER-RELEASE-SCHEMA`) keeps a live release in `CLOSURE` red until a `kind: memory` entry stamped at or after `implemented.ts` carries `since`, `until`, `reviewed` and `changed`, its `since` equal to the state-derived window start.

## Promote

- Promote is merging the integration branch into the principal, then merging the release PR release-please opens there; that PR owns the version, the CHANGELOG section and the tag, and the publish jobs run on it ([[pypi-distribution]]); `ship` then records the merged promote PR.
- Release ids are bare SemVer; a context's live version moves only at an operator-approved deploy; a repo's own `AGENTS.md` may override the rule (`dd-gitflow-default`).

## Runtime state

`specs/releases/<M.m.p>/{_RELEASE.json,rc-<N>/{SPEC.md,PLAN.md,TASKS.md}}`, `specs/releases/_archive/**`.

## Dependencies

[[backlog-ledger]], [[bug-ledger]], [[audits-canon]], [[workspace-doctor]], [[pypi-distribution]], [[sdd-gate-v3]], [[agent-orchestration]], [[specs-migration]], [[worktrees]].
