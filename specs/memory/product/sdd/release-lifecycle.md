---
slug: release-lifecycle
title: release-lifecycle
tldr: One live release grows through closed-scope candidates; _RELEASE.json holds current phase, milestones and a lean append-only narrative.
summary: Candidate birth, approval, task and job structure, phase transitions, authoritative memory drift, closure records, open-bug ship authorization and archival.
tags: [release, candidate, sdd, state, closure]
sources:
  - dadaia_workspace/public/skills/dd-release-definition/**
  - dadaia_workspace/public/skills/dd-release-implementation/**
  - dadaia_workspace/features/specs/doctor_release.py
---

## State and candidate shape

- Exactly one bare-SemVer release directory is live. `_RELEASE.json` contains `phase`, `defined`, `implemented`, `shipped` and an append-only `log`.
- New log entries use only `note`, `milestone`, `summary` and closure-only `memory`; historical kinds remain readable.
- One reader serves the live release to `phase`, `drift`, `memory`, `ship` and `check`'s tree rules: it refuses a state that breaks the release schema (a log entry that is not an object, lacks `ts` or names a candidate not shaped `rc-<N>`) with `check`'s first finding and its fix line, so no reader meets a refused shape.
- Each candidate lives in `rc-<N>/` with approved `SPEC.md`, `PLAN.md` and one `tasks/job<n>.md` per job. The highest candidate is live.
- PLAN carries the as-is review, job DAG, waves and complete write sets. Each job file carries lean task rows with task id, `who` (`sr`, `jr`, `pe` or `cr`, the dispatched persona, [[agent-orchestration]]), AC and exact write set; no stage grammar and no done marker exist. A task whose write set names `specs/memory` is an error until the candidate reaches CLOSURE, where its rows are history; memory is reconciled in the `wt-rc`'s last commits.

## Lifecycle

- `release.py new` creates a release or stacks the next candidate and writes the definition stub atomically. One rule names the next candidate, shared by `new`, the closure fence and the upgrade fold: the last `milestone` entry's candidate plus one, else the highest `rc-<N>` folder plus one, so a drafted `rc-<N>/SPEC.md` with no milestone is adopted, never skipped.
- `release.py origin <spec>` prints the ids a SPEC's first `**Origin:**` line carries, one `<kind> <id>` per line; the backlog exit reads a pick through it.
- `phase IMPLEMENTATION` requires approved SPEC and PLAN plus structurally valid PLAN and job files, then stamps the defined milestone; `check` and `phase` judge the PLAN DAG and the job files through one decider, so a DAG `check` admits is one `phase` admits.
- Each behavior begins with a RED-test task and continues in a fresh source-only implementation task. A candidate is defined, implemented and closed on its `wt-rc` tree: each job merges into it after its one independent review and tracked repository verification, and the `wt-rc` merges into the work branch through the same gate plus the ledger checks; a push reruns none of them ([[worktrees]]).
- `phase CLOSURE` refuses while the worktree owner lists any row of the repo (a tree, an orphan `wt/*` branch, a paused, foreign or stray row, old grammar included) except a `wt-rc` and the tree it runs from (the one holding the specs it was given); that refusal prints the owner row's `exit`, else its `fix`, and authors no line of its own. A specs tree in no git checkout is one refusal with the `Agent action:` to close from a repo's checkout. A spawn of the owner that cannot start is a refusal with the owner's `list` fix. Otherwise it stamps the implemented milestone.
- The reconcile is the closure's whole scope: after `phase CLOSURE` a confirmed bug in code the work branch holds still takes the version's hotfix lane and reaches the `wt-rc` by `worktree sync`; in code only the `wt-rc` holds, only a block-list bug lands, as commits on the `wt-rc` itself; any other work is a job of the next candidate, born at once ([[bug-ledger]]). Its order is the `measured_by` repairs, the independent measurement, the disposition sweep and artifact GC, then the memory pass last.
- In closure, `release.py drift` reads the memory entries newest first: the newest `until` HEAD reaches opens the window, else the defined sha HEAD reaches, else the root commit, so a rebase of the closure tree only widens the window; its worklist comes from the kernel's one drift decider, the same one `memory.py drift` runs. The product pass reads every matched source diff, reconciles atoms and derived documents, generates the catalog, and records one `memory` entry per pass at a new HEAD; the latest one's `until` governs.
- The closure summary is the last `summary` entry at or after the defined timestamp: one line that `release.py check` fullmatches against `delivered: …; carried: …; backlog exits: …`, each field non-empty, `none` standing for an empty one; it is the only home of the candidate's independent measurement and goal readouts (a closed SPEC and PLAN are never edited). The main thread's closure report to the operator, never the summary, carries the readout table `verdict.py stats <M.m.p>-rc<N>` prints (local metrics 1, 2, 4, 6, 7 and 9, each with its target; metrics 1 and 9 count the bugs closed from the previous candidate's CLOSURE to this one's, metric 4 reads the first first-parent integration merge holding the closure sha, else `n/a`, and an unknown or malformed candidate reads `n/a` throughout; stats refuses any tree `release.py check` refuses, so in CLOSURE the readout runs after the memory pass is recorded) and the batch of operator-reserved acts and bug proposals ([[agent-comms]], [[agent-orchestration]]). Ledgers and git retain their own detailed evidence; closure does not reconstruct it into extra log kinds.

## Checks and shipping

- `release.py check` is the release-state validator. It checks tree shape, the PLAN DAG against the job files and the presence of a closure memory entry after the implemented timestamp; in DEFINITION it refuses a closure entry logged after the candidate's birth note. Each id of the live SPEC's Origin line is one row: a traced id, or an untraced one before the candidate logs its closure summary (or ships), is an info row; an untraced id after it is an error carrying the owning script's verb that writes its exit, else an `Agent action:`; an unknown id carries the `Agent action:` to name a live id or rule it out of the Origin line. The live SPEC's first `## ` heading must be the bug-window review: in DEFINITION that is an error with the `Agent action:` to open it, past DEFINITION an info row. An info row carries no fix. It prints each other finding with its `fix:` line, and a release file that is not UTF-8 is one finding carrying the `Agent action:` to re-encode the failing line as UTF-8 in place, every other line kept.
- The memory writer requires every authoritative worklist slug in exactly one of `--reviewed` or `--changed`, rejects names outside the worklist, and records the derived `since` and `until`.
- Ship requires CLOSURE and a clean release check. Every open bug needs one `--allow-open <id>`, a verbatim operator-authorization note and the id in the carried field of the live candidate's closure summary — the last `summary` entry since its definition, read by one reader that `check` shares; otherwise ship refuses.
- Ship records the merged principal sha and optional PR, appends the delivered history record and moves the full release directory to the archive.
- At promote the main thread asks one question, promote or continue, and for promote the next release id or none. After the promote PR merges, the old work tip is tagged `archive/<work><old>` and the work branch is renamed to the next id (`git branch -m <work><old> <work><id>`, and `git push -u origin <work><id> :<work><old>` when it has a remote), never cut anew or deleted, so every commit on it, the ship record included, reaches integration with the next work PR; the ship is recorded from a backlog lane on that branch ([[worktrees]]).

## Dependencies

[[worktrees]], [[bug-ledger]], [[backlog-ledger]], [[audits-canon]], [[workspace-doctor]], [[agent-orchestration]], [[agent-comms]].
