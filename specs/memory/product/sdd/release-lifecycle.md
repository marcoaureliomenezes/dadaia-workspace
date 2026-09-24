---
slug: release-lifecycle
title: release-lifecycle
tldr: One live release grown by closed-scope candidates; release.py moves _RELEASE.json; closure is gated on a memory reconciliation; promote merges the release PR.
summary: The release lifecycle — one live release directory whose _RELEASE.json state document is written by release.py (new, phase, memory, check), candidates that each define, implement and close a SPEC/PLAN/TASKS trio at the release root, the memory reconciliation gate at closure, and promotion by merging the release PR release-please opens.
tags: [sdd, release, candidate, lifecycle, memory]
sources:
  - dadaia_workspace/public/skills/dd-release-implementation/**
  - dadaia_workspace/public/skills/dd-release-definition/**
  - dadaia_workspace/public/skills/dd-spec-navigator/scripts/**
  - dadaia_workspace/public/schemas/releases/**
  - dadaia_workspace/core/release_state.py
  - dadaia_workspace/features/specs/release_tree.py
  - dadaia_workspace/features/specs/doctor_release.py
---

## Release and candidate

- Exactly one release directory is live, `specs/releases/<M.m.p>/`, with open scope; it grows by candidates, each a closed-scope cycle whose `SPEC.md`, `PLAN.md` and `TASKS.md` sit flat at the release root and are replaced by the next candidate's, the closed trio staying in git.
- `_RELEASE.json` is one mutable `release-state-v1` document `{schema, release, phase, defined, implemented, shipped, log}`; `phase` is `DEFINITION | IMPLEMENTATION | CLOSURE | ARCHIVED`, and the gate never reads it ([[sdd-gate-v3]]).
- `log` is append-only, oldest first, entries `{ts, agent, kind, text}` with `kind` one of `note summary size drifts dispositions test-dispositions artifact-gc reviews merge memory`; it is the closure narrative's only home.
- Every SPEC carries `**Origin:** operator-demand | backlog:<slug>[,..] | bugs:<id>[,..]`; `SPEC-DOC-048` requires it on the live SPEC and resolves each cited slug or bug id ([[backlog-ledger]], [[bug-ledger]]).
- `specs/releases/_archive/` holds published versions below the live one and `releases_histo.jsonl`; it is read, never rewritten.

## The writer — `release.py`

- `python3 .agents/skills/dd-release-implementation/scripts/release.py <verb> [--specs <path>]` is the state document's one writer and validator; each write validates the new bytes before replacing the file atomically, and every refusal carries one `fix:` line.
- `new <id> [--origin <origin>]` mints the live release: a `SPEC.md` stub plus `_RELEASE.json` in `DEFINITION`, all or nothing; on a live release already in `CLOSURE` with the same id it stacks the next candidate, reopening `DEFINITION` and deleting the closed `PLAN.md`/`TASKS.md`; a second live release, a non-SemVer id or a symlinked path is refused; `--origin bugs:<ids>` seeds one scope clause per bug with its repro line.
- `phase IMPLEMENTATION --sha <sha>` requires all three trio files `**Status:** Approved` and stamps `defined`; `phase CLOSURE --sha <sha> [--pr <n>]` requires no `[ ]` or `[-]` task marker and stamps `implemented`, `--pr` recording the merged release PR in its note; each phase follows its predecessor exactly once, and `ARCHIVED` is written by no verb.
- `memory --reviewed <slugs> --changed <slugs>` derives its window from the state document — the previous `kind: memory` entry's `until`, else `defined.sha` — to `HEAD`, computes the worklist itself and appends the closure's `kind: memory` log entry carrying `since`, `until`, `reviewed` and `changed`; it refuses outside `CLOSURE`, a worklist entry named in neither list, a name outside the worklist, and a `changed` atom git reports unmoved over the window.
- `check [--json]` validates every state document, live and archived, and the ship ledger; on a live release in `CLOSURE` it also re-judges the latest `kind: memory` entry over its own `since`..`until` with the `memory` verb's rules and requires that no atom's sources moved after its `until`; `dadaia doctor`'s `ledgers` section runs it (`LEDGER-RELEASE-SCHEMA`) and its `specs` section runs the `RELEASE-TREE-*` rules ([[workspace-doctor]]).

## The candidate arc

- Definition: the picked backlog and bug set, the mandatory grill, the SPEC by `dd-product-engineer`, PLAN and TASKS by `dd-software-engineer`, one definition commit on `feature/<M.m.p>` ([[agent-orchestration]]).
- Implementation: one task reserved `[-]` at a time in its own commit, TDD, local CI preflight, `[x]` only after the reviewer's `APPROVED` on the same commit.
- Closure, in order: `phase CLOSURE`, memory reconciliation, closure `log` entries, disposition sweep (`backlog.py exit`, `audit.py disposition`/`close`, `bugs.py archive`), artifact GC, the `feature -> develop` PR merged green, then the operator's promote-or-continue choice ([[audits-canon]]).
- `SPEC-DOC-047` refuses a task whose write set names `specs/memory`: memory is closure procedure, never a task.

## The memory reconciliation gate

- `python3 .agents/skills/dd-spec-navigator/scripts/memory.py drift --since <sha> [--json]` lists the atoms whose `sources` globs match a path changed over `<sha>..HEAD` and every code unit no atom covers, exiting 1 while that worklist is non-empty; `--since` is required and has no default window.
- A code unit is derived from the audited repo alone: each directory directly holding a tracked code file, or a root-level code file on its own; `specs/`, `tests/`, `test/`, `docs/` and dot-directories hold none, and a unit is covered once any atom's `sources` match a file under it.
- Each listed atom is reconciled from its sources' diff — delete, update, then add — and `memory.py catalog generate` regenerates the catalog pair ([[workspace-doctor]]).
- `RELEASE-TREE-MEMORY` keeps a live release in `CLOSURE` red until a `kind: memory` entry stamped at or after `implemented.ts` carries `since`, `until`, `reviewed` and `changed`, its `since` equal to the state-derived window start.

## Promote

- Promote is merging `develop` into `main`, then merging the release PR release-please opens there; that PR owns the version, the CHANGELOG section and the tag, and the publish jobs run on it ([[pypi-distribution]]).
- Release ids are bare SemVer; a context's live version is the first release id when its repo has no tag, else the last tag plus one patch, minted at birth, and moves only at an operator-approved deploy; a repo's own `AGENTS.md` may override the rule (`dd-gitflow-default`).

## Runtime state

`specs/releases/<M.m.p>/{_RELEASE.json,SPEC.md,PLAN.md,TASKS.md}`, `specs/releases/_archive/**`.

## Dependencies

[[backlog-ledger]], [[bug-ledger]], [[audits-canon]], [[workspace-doctor]], [[pypi-distribution]], [[sdd-gate-v3]], [[agent-orchestration]].
