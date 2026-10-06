---
slug: bug-ledger
title: bug-ledger
tldr: One bug record per line in BUGS.jsonl, registered after operator confirmation, closed only by a transition carrying its red loop; bugs.py writes it.
summary: The bug ledger — specs/bugs/BUGS.jsonl, one record per bug keyed by id, storing no git-derived fact (bugs.py fix and window derive them on read); the stdlib script bugs.py is its one writer and validator, and the ask-first registration plus the seven-phase resolution method run over it.
tags: [sdd, bugs, ledger, governance]
sources:
  - dadaia_workspace/public/skills/dd-bug-resolution/**
  - dadaia_workspace/public/skills/dd-bug-registration/**
  - dadaia_workspace/public/schemas/bugs/**
  - dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_check.py
---

## The record

- `specs/bugs/BUGS.jsonl` holds one record per bug, appended once and keyed by `id`; git history is that line's change log, and the record stores no git-derived fact — `bugs.py fix` and `window` derive the fix commits and `introduced_in` on read.
- `bug-record-v1` sorts every field into immutable core (`id ts reported_by title severity surface component context symptom repro expected`), mutable governance (`status cause caused_by resolved_release audited closed_at`) and write-once (`correlates found_in introduced_in solution evidence_loop lineage_reason evidence_seam evidence_diff superseded_by`); `evidence_seam` and `evidence_diff` are optional; an unknown key is a finding.
- `found_in` is `{release, rc}`, the candidate holding the registration instant, stamped by `append`; `introduced_in` has the same shape, stored only where no culprit commit derives it; `rc` is `rc-<N>` or `unknown`.
- `status` is `open | resolved | superseded | deferred | rejected`; `closed_at` is non-null exactly when `status` is terminal and never earlier than `ts`.
- `surface` is the name of one directory tracked in the context's repo, at any depth, a dot-directory such as `.github` included — the set of tracked directory names is the one decider; records already carrying free text or `unknown` stay valid as written; `component` is free-text `path#symbol`.
- `correlates` lists the ledger ids the bug was judged to correlate with at registration, empty for none.
- Every written field except `id`, `ts` and `reported_by` is redacted on write: control characters stripped, home-directory user names and IPv4 addresses masked; a write whose new records carry a match the push refuses — the denylist of the workspace holding the specs tree, whatever the cwd, plus the structural baseline — refuses, while a match the ledger's published text (its first publication boundary) already carries passes, the push's own question; a failed git read amnesties nothing ([[sdd-gate-v3]]).

## The writer — `bugs.py`

- `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py <verb> [--specs <path>]` is the ledger's one writer and one validator; every write builds the new ledger bytes, runs `check` over them, and only then replaces the file atomically, so a refused write leaves the file byte-identical.
- A write that finds the file changed under it re-reads and re-applies once; a second concurrent change refuses with `Operator action: re-run the same command, unchanged`, so two fixers resolve by whichever lands first.
- Verbs: `append`, `status` (open only, `--all` for every record), `stats` (counts by status, severity and `direction:` — derived from each fix commit's numstat), `update`, `resolve`, `supersede`, `defer`, `reject`, `archive`, `check`, `fix`, `window`; every refusal prints one fix line, a command with real values or an `Operator action:` naming what to supply.
- `append` first prints the correlation candidates — the open records on the same surface and those resolved there in the last 30 days — then opens a record at `status: open` carrying `found_in`, refusing a duplicate id (a reopen is a new record), a surface that is no tracked directory name (naming close matches), and a missing or unknown `--correlates <ids>|none`.
- `update <id> --set field=value` writes a governance field, `caused_by` included (its repair), or a write-once one (an object field as JSON); it refuses `status` and `closed_at` (owned by the transitions), `resolved_release` (owned by `resolve`), `superseded_by` (owned by `supersede`), a change to an immutable core field and a differing second write to a write-once field.
- A terminal status is reached only through its transition, each refusing an incomplete call with every missing field named: `resolve` needs `--cause --caused-by --solution --evidence-loop` and derives `resolved_release`, the release whose span holds the resolve instant (`unknown` outside every span); it prints the blame candidates — the bugs whose fix and the tasks whose `<type>(<task-id>)` commit wrote a line the staged diff removes — and refuses a `--caused-by` outside them, or `none` while any exist, unless `--lineage-reason` says why (stored); `supersede` needs `--by`; `defer` and `reject` need `--reason`.
- `archive --adr <id> <ids…>` moves exactly the named terminal records into `specs/bugs/_archive/bugs_histo.jsonl`, each stamped `archived_by: <id>`; a record leaves the ledger only by an accepted ADR, and a non-accepted ADR or an open record is refused; no record ever leaves by age.
- `caused_by: X` means the fix of X wrote the lines this fix corrects; X names a live or archived record, a task id a closed candidate's `TASKS.md` (`T-…`) or a job file `tasks/<job>.md` (`J<n>.S<m>.T<k>`, `JR.…`) under `specs/releases/` carries, `_archive/` included, or `none`, and never forms a loop: every write and `check` refuse otherwise, `check` re-judging the whole ledger, since a merge can join two valid writes into a cycle.
- `fix [<ids>]` prints each resolved record's fix commits (a shape-3 `fix(bugs):`/`refactor(bugs):` commit, or the task shas a shape-4 `chore(bugs): resolve` names), their numstat and the direction on production paths, or `unlinked`; a fix a later `Revert "<its subject>"` undid is not listed, a redo after the revert is, and a commit named by both its full and its short sha is listed once; the record stores none of it.
- `window` lists every live and archived record found in or born in the live or the last shipped release, `introduced_in` read from `caused_by`'s culprit commit first, and the `release` `unknown` ones apart.
- `check` emits one finding per invalid line with its fix: a governance verb with real values where one clears it (`update <id> --set caused_by=none` for a dangling cause), else an `Operator action:` naming the file, the line and the law — discard the uncommitted change or revert the commit that introduced it, then redo it through `bugs.py`.
- `check` also holds every archived v1 record to an `archived_by` naming an accepted ADR; pre-v6 `event` lines in the archive are history and pass unchanged.
- `dadaia doctor`'s `ledgers` section runs `bugs.py check` (`LEDGER-BUGS-SCHEMA`) ([[workspace-doctor]]).

## Registration and resolution

- A bug is a merged change that reproducibly breaks a documented contract; a failure inside an unmerged worktree is rework, and an agent's own mistake, wrong usage, an environment limit, a designed validation, a law ambiguity or a missing feature is not one.
- Registration is ask-first: the agent proposes the violated contract line, one reproducing command already run, why it is not agent error and a severity (CRITICAL a stall or data loss; HIGH a contract broken on the default path; MEDIUM off the default path or with a workaround; LOW message or cosmetic), and `append` runs only after the operator confirms; with no operator present the proposal leaves as one handoff finding whose `message` starts `bug-proposal:` ([[agent-comms]]).
- Registration lands in a job or `backlog/<slug>` worktree, so a backlog entry's `to-bug` exit shares one with it ([[backlog-ledger]]).
- The block list is closed: the work branch's CI red, a Stall, the running task unable to deliver its AC, a security finding or an open dependency-vulnerability alert, data loss or corruption. A block-list bug is a hotfix — registered with `caused_by`, its own job outside the candidate's DAG, the job gate and one review, landing before any other job merge, its fix body naming `block: <item>` ([[worktrees]]).
- No candidate closes with an open bug: every other bug is registered, `found_in` its candidate, and fixed by the candidate's bug batch — one job outside the DAG, after its last job merges and before the Reconciliation job, grouped by cause, a fix-induced one as a REBUILD; a bug found in the Reconciliation job is fixed inside it; the next candidate's `## Bug window review` judges those fixes and its Job 1 executes the verdicts ([[release-lifecycle]]).
- A fix is a RED new case (a fix never rewrites an old assert), root-cause fix, GREEN, `resolve` with its red loop, one commit holding code, test and the ledger line, its red loop quoted in the body.
- Resolution follows seven ordered phases — lineage, red loop, minimise, hypothesise, instrument, seam test, cleanup and resolve; lineage reads at most the 20 most recent records sharing the bug's `surface` or `component` in the window since the newest archived audit and ends in `caused_by: <id> | none` plus a rebuild decision.
- ≥ 2 prior fixes on the unit the bug lands in, within that window, make the fix a REBUILD of that unit, never a third patch: the fix commit body echoes `rebuild: <unit> — prior fixes <id>, <id>` (or `rebuild: none`) beside `caused_by:`, `evidence:` and `prior diffs read:`, and a rebuild's `--solution` opens with `REBUILD <unit>:`; `bugs.py` counts nothing and carries no field for it ([[release-lifecycle]]).
- A fix whose diff grows the touched feature is routed to the architecture lens before it lands ([[agent-orchestration]]).

## Runtime state

`specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl`.

## Dependencies

[[workspace-doctor]], [[agent-comms]], [[agent-orchestration]], [[audits-canon]], [[release-lifecycle]], [[worktrees]], [[backlog-ledger]], [[sdd-gate-v3]].
