---
slug: release-lifecycle
title: release-lifecycle
tldr: One live release grows through closed-scope candidates; _RELEASE.json holds current phase, milestones and a lean append-only narrative.
summary: Candidate birth, approval, task and job structure, phase transitions, authoritative memory drift, closure records, open-bug ship authorization and archival.
tags: [release, candidate, sdd, state, closure]
sources:
  - dadaia_workspace/public/schemas/releases/release-state-v1.schema.json
  - dadaia_workspace/public/skills/dd-release-definition/**
  - dadaia_workspace/public/skills/dd-release-implementation/**
  - dadaia_workspace/features/specs/doctor_release.py
---

## State and candidate shape

- Exactly one bare-SemVer release directory is live. `_RELEASE.json` contains `phase`, `defined`, `implemented`, `shipped` and an append-only `log`.
- New log entries use only `note`, `milestone`, `summary` and closure-only `memory`; historical kinds remain readable.
- Each candidate lives in `rc-<N>/` with approved `SPEC.md`, `PLAN.md` and one `tasks/<job>.md` per job. The highest candidate is live.
- PLAN carries the as-is review, job DAG, waves and complete write sets. Each job file carries lean task rows with task id, AC and exact write set; no stage grammar exists.

## Lifecycle

- `release.py new` creates a release or stacks the next candidate and writes the definition stub atomically.
- `phase IMPLEMENTATION` requires approved SPEC and PLAN plus structurally valid PLAN and job files, then stamps the defined milestone.
- Each behavior begins with a RED-test task and continues in a fresh source-only implementation task. Jobs merge after their one independent review and tracked repository verification ([[worktrees]]).
- `phase CLOSURE` refuses while another canonical worktree is open and stamps the implemented milestone.
- In closure, `release.py drift` derives the memory window from the latest memory entry's `until`, otherwise the defined sha. The product pass reads every matched source diff, reconciles atoms and derived documents, generates the catalog, and records exactly one `memory` entry.
- The closure summary carries delivered, carried and backlog-exit scope. Ledgers and git retain their own detailed evidence; closure does not reconstruct it into extra log kinds.

## Checks and shipping

- `release.py check` is the release-state validator. It checks tree shape, origins and the presence of a closure memory entry after the implemented timestamp.
- The memory writer requires every authoritative worklist slug in exactly one of `--reviewed` or `--changed`, rejects names outside the worklist, and records the derived `since` and `until`.
- Ship requires CLOSURE and a clean release check. Every open bug needs one `--allow-open <id>`, a verbatim operator-authorization note and the id in the closure summary's carried field; otherwise ship refuses.
- Ship records the merged principal sha and optional PR, appends the delivered history record and moves the full release directory to the archive.

## Dependencies

[[worktrees]], [[bug-ledger]], [[backlog-ledger]], [[audits-canon]], [[workspace-doctor]], [[agent-orchestration]].
