---
slug: release-lifecycle
title: release-lifecycle
tldr: Candidates in rc-<N>/ grow one live release; release.py writes _RELEASE.json; a candidate is a DAG of jobs ending in Reconciliation; promote archives it.
summary: The release lifecycle — one live release directory whose _RELEASE.json state document is written by release.py (new, phase, drift, memory, ship, check), candidates that each review the as-is units their demand touches, then define, implement and close a SPEC, a PLAN drawing the DAG of jobs and one job file per job in its own rc-<N>/ folder, the PLAN and job-file checks at IMPLEMENTATION, release.py check as the one readiness judge in every phase and the one judge of the SPEC's Origin line and its trace back, the memory reconciliation gate at closure, and promotion by merging the release PR release-please opens, which ship records by archiving the release folder.
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

- Exactly one release directory is live, `specs/releases/<M.m.p>/`, with open scope; it grows by candidates, each a closed-scope cycle whose `SPEC.md`, `PLAN.md` and job files `tasks/<job>.md` sit in `releases/<M.m.p>/rc-<N>/` (a closed candidate keeps its `TASKS.md` as history); the live candidate is the highest `rc-<N>/`, and no verb rewrites a closed one.
- Only `_RELEASE.json` sits at the release root: the specs canon and the pre-push gate refuse a flat trio ([[sdd-gate-v3]]), and `specs upgrade` folds one into the next `rc-<N>/` ([[specs-migration]]).
- The live candidate has two readers pinned equal by one contract test: `_release_store.live_ids` for the stdlib scripts and `core/gitflow.py`'s resolver for the package.
- `_RELEASE.json` is one mutable `release-state-v1` document `{schema, release, phase, defined, implemented, shipped, log}`; `phase` is `DEFINITION | IMPLEMENTATION | CLOSURE`, and the gate never reads it ([[sdd-gate-v3]]); `defined` and `implemented` hold the live candidate's stamps, and every `phase` also appends a `kind: milestone` entry `{candidate, milestone, sha}`, so each candidate's stamps survive in the `log`; stamps older than those entries are its `Candidate defined at …`/`Candidate implemented at …` notes.
- `log` is append-only, oldest first, entries `{ts, agent, kind, text}` with `kind` one of `note summary size drifts dispositions test-dispositions artifact-gc reviews merge memory milestone`; it is the closure narrative's only home, no `ts` precedes the one before it, and a merged job's `kind: merge` entry, written by hand with no verb, carries `job: <name>; start: <UTC>; end: <UTC>; wall: <min>; ritual_wait: <min>; dispatches: <n>; job_gate_runs: <n>`, the shape `check` validates.
- Every SPEC carries one `**Origin:**` line, the first counting: `operator-demand`, or `backlog:<ids>; bugs:<ids>; findings:<ids>`, each kind at most once, a finding id in full (`<audit-id>-F<nnn>`); `_release_schema.origin` is its one parser, which `backlog.py exit` imports, and `release.py check` its one judge ([[backlog-ledger]], [[bug-ledger]], [[audits-canon]]).
- `specs/releases/_archive/` is history, exempt from every release check by location: `_archive/<M.m.p>/` holds a shipped release's whole folder, and `releases_histo.jsonl` is the ship ledger, one `delivered` line per release, ever.
- A live `releases/<M.m.p>/RELEASE.json` without `_RELEASE.json` is the doctor's `SPEC-DOC-046` warning, renamed by `--fix` ([[workspace-doctor]]).

## The writer — `release.py`

- `python3 .agents/skills/dd-release-implementation/scripts/release.py <verb> [--specs <path>]` is the state document's one writer and validator; each write validates the new bytes before replacing the file atomically, and every refusal carries one fix line — a command with real values, or `Operator action:` naming in words what to supply, never a `<…>` placeholder; a `phase` refusal's operator action names the absolute path of the document to correct — `SPEC.md`, `PLAN.md` or a job file.
- `new <id> [--origin <origin>]` opens a candidate: a `SPEC.md` stub whose first `## ` heading is `## Bug window review`, then Problem and context, Objective, Scope, Replaces, Out of scope, Dependencies and risks, in the next `rc-<N>/` plus `_RELEASE.json` in `DEFINITION`, all or nothing, writing no `PLAN.md`; on a live release already in `CLOSURE` with the same id it stacks the next candidate once `bugs.py status --found-in` finds no bug open in the closing candidate, reopening `DEFINITION` and leaving every closed `rc-<N>/` untouched; a second live release, a non-SemVer id or a symlinked path is refused; `--origin bugs:<ids>` seeds one scope clause per bug with its repro line.
- `phase IMPLEMENTATION --sha <sha>` requires `SPEC.md` and `PLAN.md` `**Status:** Approved`, a PLAN carrying a `## DAG` section and a `### Hot files` section, and every job file well formed (below), and stamps `defined`; it needs no `TASKS.md`; `phase CLOSURE --sha <sha>` requires no open `wt/*` worktree of the repo but the one it runs in ([[worktrees]]) — the Reconciliation tree, run before any task tree is cut and before the memory pass — reads no task marker, and stamps `implemented`; each phase follows its predecessor exactly once per candidate, and each stamp appends its `milestone` entry.
- `memory --reviewed <slugs> --changed <slugs>` is a no-op when the last `kind: memory` entry already ends at `HEAD`; otherwise it derives its window from the state document — the previous `kind: memory` entry's `until`, else `defined.sha` — to `HEAD`, computes the worklist itself and appends the closure's `kind: memory` log entry carrying `since`, `until`, `reviewed` and `changed`; it refuses outside `CLOSURE`, a worklist entry named in neither list, a name outside the worklist, and a `changed` atom git reports unmoved over the window.
- `drift` prints the closure worklist over the live release's memory window (`memory.py drift`'s rules).
- `ship --sha <sha> [--pr <n>]` records the merged promote (`shipped.pr` is the PR number, or null when the host has none) and is refused while a bug found in the live candidate is `open` or `deferred` (`bugs.py status --found-in`), on any `check` error, a phase short of `CLOSURE` (fix: that phase's next verb) and a release already archived — one readiness authority; it stamps `shipped`, appends its `delivered` line (`summary` null) to the ship ledger and moves the whole release folder, `_RELEASE.json` and every `rc-<N>/`, to `_archive/<M.m.p>/`, deleting nothing.
- `check [--json]` validates every live state document, the presence of the live candidate's `SPEC.md` and `PLAN.md` in `IMPLEMENTATION` and `CLOSURE`, its job files and the PLAN's DAG in every phase, the one-live-release rule, the ship ledger and every archived state document, which must carry `shipped` `{sha, pr}`; under `DEFINITION` a closure entry (any kind but `note`, `milestone` and `merge`) logged after the candidate's birth note is a finding whose fix runs `phase IMPLEMENTATION` at the commit that last touched SPEC and PLAN; in a closed candidate's `TASKS.md`, a task whose `W:` writes `specs/memory` is a finding.
- A job file is malformed with no `## Stage` heading, a stage with no `- Contract:` line, or two tasks of one stage writing one path; a task is a bullet line or a table row, its `W:` the backticked paths up to the first `·` (or the cell under a `W:` column), a parenthesized one named, not written. The PLAN's `## DAG` table (`job | waits on | why`) holds a Job 1, at most 8 jobs with Reconciliation uncounted, and no cycle; each refusal names its fix ([[agent-orchestration]]).
- `check` reads the live SPEC's head: its first `## ` heading not `## Bug window review` is an error in `DEFINITION` and an info line after; then its Origin line: its grammar and every id's existence always; each carried id is listed with whether its owning ledger points back to the release — an entry's `delivered`/`superseded` exit, a `to-bug` exit to a standing bug or a `rejected` disposition, a bug resolved in it or rejected, a finding dispositioned to it; a missing pointer is an error only once the live candidate logged its `dispositions` entry, or at `ship`, its fix the verb that writes the pointer where one can; `--json` emits the errors only, the text view also lists the traced ids, and only an error exits 1.
- On a live release in `CLOSURE` `check` also relays `bugs.py balance --check` over `QUALITY.md`'s `## Bugs` block, a stale one a warning that blocks nothing and a ledger the verb cannot read an error; it also re-judges the latest `kind: memory` entry over its own `since`..`until` with the `memory` verb's rules and requires that no atom's sources moved after it, through that one reach decider (a non-ancestor `until` refuses); the window stays judged until HEAD, read from local git, is the branch given as `--principal` (none given, or a detached HEAD, stays judged), which closes it; the script reads no constitution, and `dadaia doctor`'s `ledgers` section runs `check` (`LEDGER-RELEASE-SCHEMA`) passing the principal `core/gitflow.py` reads ([[workspace-doctor]]).

## The candidate arc

- Definition: the picked backlog and bug set, the bug window review, the as-is review, the mandatory grill, the SPEC by `dd-product-engineer`, PLAN and job files by `dd-software-engineer`, in the candidate's `define` worktree, one definition commit on the work branch (`<work prefix><live release id>`, with no live release the first-release default of `work_branch` in `dadaia_workspace/core/gitflow.py`, never derived from a tag; the constitution's `gitflow:`) ([[agent-orchestration]]).
- The SPEC's `Replaces` names one current behaviour per DELETE or REBUILD row, or `none` with its reason; tasks realizing DELETE/REBUILD rows precede tasks realizing ADD rows, each expand–contract (add the new path, switch consumers, delete the old), each independently green.
- Implementation: a candidate is a DAG of jobs, Job 1 first; each job holds stages, a stage is a barrier over tasks of disjoint `W:` worked in parallel task worktrees, stage 1 writing every acceptance test RED as a strict xfail; a task is `running` while its worktree exists, and the job's close task writes `done` once; each job lands by `worktree.py merge` after one review, then appends its `kind: merge` entry ([[worktrees]]).
- A candidate is closed: never amended once approved, a new AC going to the next candidate; a red outside a stage's envelope appends a stage, and a stage's third red gate stops the job, logged as a `kind: note` `stop:` entry; the next candidate is drafted in a `define` worktree while one implements.
- Closure is the Reconciliation job, the last one, in its `reconcile` worktree, where `phase CLOSURE` runs first: memory reconciliation with its derived docs in the same merge, `measured_by` repairs, the candidate's measurement, the closure `log` entries, the disposition sweep (`backlog.py exit`, `audit.py disposition`/`close`, `bugs.py archive`), artifact GC; then the work -> integration PR merged green and the operator's promote-or-continue choice ([[audits-canon]]).

## The as-is review

- Definition's second step, after the pick and before the grill: `dd-software-engineer`, dispatched by the main thread, reads every As-is unit the picked set touches and its bug-ledger slice (`bugs.py status`/`stats`, `git log` on the unit), read-only, and returns the table in its handoff; the main thread carries it into the grill; it lands as PLAN §1.
- An As-is unit is a module or a law, skill or doc section with a today-behaviour — never `memory.py drift`'s code unit.
- PLAN §1 is one Markdown table `unit | today | bugs | verdict | why`, one row per touched As-is unit; the As-is verdict is `DELETE`, `REBUILD`, `UPDATE` or `KEEP`, considered in that order (DELETE vs KEEP is the deletion test), then `ADD` rows with `today` `—` only for what no existing unit can carry, `why` saying why.
- REBUILD is mandatory when the unit carries ≥ 2 bugs, the demand changes its fundamental behaviour, the change would need a flag, branch, special case or second path, or its contract contradicts the demand; the engineer and the reviewer judge these triggers — no script counts bugs or reads code.
- The `dd-release-definition` skill carries the PLAN §1 skeleton and its `### … Authorities` table; no script reads either — the reviewer and the audit judge them.
- The review's spec axis reads PLAN §1 beside SPEC and the job files: a DELETE or REBUILD unit the reviewed range leaves unchanged is a HIGH finding, a KEEP unit the range grew is a finding ([[agent-orchestration]]).
- A bug fix whose `caused_by` is not `none`, or on a unit with ≥ 2 prior fixes in its lineage window, is a rebuild of that unit, never a patch ([[bug-ledger]]).

## The memory reconciliation gate

- `python3 .agents/skills/dd-spec-navigator/scripts/memory.py drift --since <sha> [--json]` lists the atoms whose `sources` globs match a path changed over `<sha>..HEAD` and every code unit no atom covers, exiting 1 while that worklist is non-empty; `--since` is required and has no default window. Every verb's window, `release.py check`'s included, goes through the one decider, which refuses, naming `git fetch --unshallow`, a window in a shallow clone, and refuses a `since` or `until` that is not an ancestor of `HEAD` — a sha a rebase rewrote, which a clone of the branch lacks — with an `Operator action:` naming the commit HEAD reaches in its place.
- A code unit is derived from the audited repo alone: each directory directly holding a tracked file, of any language; a root-level file belongs to no unit; `specs/`, `tests/`, `test/`, `docs/` and dot-directories hold none, and a unit is covered once any atom's `sources` match a file under it.
- Each listed atom is reconciled from its sources' diff — delete, update, then add — and `memory.py catalog generate` regenerates the catalog pair ([[workspace-doctor]]).
- `release.py check` (`LEDGER-RELEASE-SCHEMA`) keeps a live release in `CLOSURE` red until a `kind: memory` entry stamped at or after `implemented.ts` carries `since`, `until`, `reviewed` and `changed`, its `since` equal to the state-derived window start.

## Which candidate held an instant

- `_release_schema.candidate_at` is the one answer: the release whose half-open span — its first `log` ts to its `shipped.ts` — holds the instant, and the `rc-<N>` whose non-Approved `SPEC.md` was added last before it in that release, else `unknown`; a shallow clone refuses, since a cut history would place an instant wrong for good; `bugs.py` stamps `found_in`, derives `resolved_release` and lists its `window` through it ([[bug-ledger]]).

## Promote

- Promote is merging the integration branch into the principal, then merging the release PR release-please opens there; that PR owns the version, the CHANGELOG section and the tag, and the publish jobs run on it ([[pypi-distribution]]); `ship` then records the merged promote PR.
- Release ids are bare SemVer; a context's live version moves only at an operator-approved deploy; a repo's own `AGENTS.md` may override the rule (`dd-gitflow-default`).

## Runtime state

`specs/releases/<M.m.p>/{_RELEASE.json,rc-<N>/{SPEC.md,PLAN.md,tasks/<job>.md}}`, a closed candidate's `rc-<N>/TASKS.md`, `specs/releases/_archive/**`.

## Dependencies

[[backlog-ledger]], [[bug-ledger]], [[audits-canon]], [[workspace-doctor]], [[pypi-distribution]], [[sdd-gate-v3]], [[agent-orchestration]], [[specs-migration]], [[worktrees]].
