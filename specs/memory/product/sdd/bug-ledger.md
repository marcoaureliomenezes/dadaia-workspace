---
slug: bug-ledger
title: bug-ledger
tldr: BUGS.jsonl stores one lean current record per confirmed defect; its writer persists registration, resolution and fix-file facts while git owns derived history.
summary: The bug record grammar, confirmation and privacy boundary, terminal transitions, persisted fix lineage and fix files, the earlier-bug and REBUILD-due readout, archival and candidate integration.
tags: [bugs, ledger, lineage, resolution]
sources:
  - dadaia_workspace/public/scaffold/bugs/AGENTS.md
  - dadaia_workspace/public/skills/dd-bug-resolution/**
---

## Record

- `specs/bugs/BUGS.jsonl` holds one `bug-record-v1` object per id. Registration facts are immutable; `solution`, `fix_files` and `superseded_by` are write-once; `surface` is an optional legacy property that only records filed before fix files were recorded carry; `status`, `closed_at`, `cause`, `caused_by` and `fix_sha` are governance fields; unknown fields are rejected.
- Status is `open | resolved | superseded | rejected`. Terminal records carry `closed_at`; a reopen is a new id.
- A resolved record persists `cause`, `solution`, `caused_by`, the 40-hex `fix_sha` and `fix_files`, the paths that commit touched, read once at resolve when HEAD reaches it. Git supplies the diff, numstat and subsequent history.
- A rebase rewrites the commit `fix_sha` names, so `update --set fix_sha=<sha>` repoints it. `check` refuses each live record whose `fix_sha` no repo reaches from its HEAD — the main repo first, then every other git checkout in the `repos/` directory beside it, with no registry read — its fix an `Agent action:` to find the fix commit in git log and run that `update`; only when a miss exists and one of those repos is a shallow clone are the misses one finding, with that repo's `git fetch --unshallow` as its fix.
- `caused_by` names a live or archived bug, a known task id or `none`; a task id is known when a job file or a closed release's `TASKS.md` carries it, in the current grammar or as the head of a historical task line (`T-<n>-<n>`, lettered `J<X>.S<n>.T<n>`); validation rejects dangling links and cycles.

## Writer and transitions

- `bugs.py` is the one writer and validator. Reads are `status`, `stats` (counts per field, then one `rebuild-due:<path>` line, with its ids, for each path the `fix_files` of two or more live or archived records name) and `check` (`check` prints each finding with its `fix:` line on the next line, and a ledger that is not UTF-8 is one finding carrying the `Agent action:` to re-encode the failing line as UTF-8 in place, every other line kept); writes are `append`, governance `update`, `resolve`, `supersede`, `reject` and `archive`.
- Registration follows an operator-confirmed proposal naming the violated contract and reproduction. `append` takes no surface: it refuses duplicate ids and a `--component` text that names no tracked path (read through the kernel git runner), prints each earlier live or archived bug whose `fix_files` lie under a path the component names and, for such a path, the REBUILD due (`REBUILD due: <ordinal> bug on <path>`, the ordinal one past the earlier count), refuses `--correlates` ids that neither the ledger nor the archive holds, and subjects every supplied value to the publication privacy matcher.
- `resolve` requires cause, lineage, solution and fix sha, and records the fix's files. `supersede` names the replacement; `reject` records the reason. The schema's mutability classes prevent generic update from changing transition-owned state.
- `archive` moves named terminal records into the bug history. Open records cannot be archived.
- Every candidate ledger is validated before atomic replacement, so a refusal leaves both live and archived bytes unchanged.
- Every timestamp comes from the one clock; no verb takes a timestamp argument.
- `dd-bug-resolution/scripts` also holds the kernel the other skill scripts and the package load for every shared fact: the refusal with its one printer and the one `fix:` spelling and parser, `act(kind, text)`, the one producer of the `Agent action:` and `Operator action:` labels, the git runner with its scrubbed environment (repo-selecting `GIT_*` removed, bytecode writing off, so no child it starts writes `__pycache__`, and `DADAIA_WT=1` marking a sanctioned run), the JSONL reader, the atomic writer, the context-name grammar, the one live-release decider, the closure worklist decider, the frontmatter parser, the clock, the one OS boundary `_platform.py` that decides every host fact ([[cross-platform-portability]]), the workspace-root walk, the one spawn of the workspace CLI (a missing or unstartable CLI is a refusal carrying the `uvx dadaia-workspace init` fix) and the privacy matcher with its baseline ([[public-asset-distribution]]).

## Resolution discipline

- Read matching records and their named fixes before changing code. At most the twenty most recent fix-file/component matches and their fix commits belong to one fix investigation.
- Bugs sharing a cause are fixed together. Two failed fix attempts on one bug hand it to a fresh session with a written diagnosis.
- Establish the lowest-level RED behavior first, then fix the owning seam. The fix hardens the contract test in that contract's one home: it tightens an assert or adds the missing partition, never loosens or removes one, and the reviewer confirms the hardened test goes red with the fix reverted; then persist the implementation sha.
- Two prior fixes on the touched module, or a `caused_by` other than `none`, require a REBUILD that keeps regression coverage.
- Block-list bugs use hotfix lanes; after a candidate enters CLOSURE only a block-list bug lands in it, and any other bug, REBUILD or demand is a job of the next candidate. Other confirmed bugs become explicit candidate scope; ship may carry an open id only through the exact operator authorization enforced by [[release-lifecycle]].
- The next candidate's bug-window review owns KEEP or REBUILD maturity. No runtime balance, source-quality reconstruction or cached candidate placement lives in the ledger.

## Dependencies

[[release-lifecycle]], [[worktrees]], [[audits-canon]], [[sdd-gate-v3]], [[QUALITY]], [[cross-platform-portability]].
