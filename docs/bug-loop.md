# The bug loop

Register → RED → fix → resolve. A confirmed bug in code the work branch holds uses a hotfix lane;
after CLOSURE a block-list bug in code only the `wt-rc` holds is fixed on that `wt-rc`;
other bugs enter the approved release scope through its ordinary job structure.

## 1. Register — ask first

A bug is a merged change that reproducibly breaks a documented contract; a failure inside
an unmerged worktree is rework. Registration starts with a proposal naming the violated
contract, one reproducing command already run, why the failure is not agent error and its
severity. `append` runs only after the operator confirms.

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append \
  --bug-id doctor-exits-zero-with-errors --reported-by dd-sw-engineer-sr \
  --title "doctor exits 0 while reporting error findings" \
  --severity HIGH --component "cli/commands/doctor.py#run" \
  --context demo --symptom "…" --repro "…" --expected "…" --correlates none
```

The ledger holds one record per bug, keyed by id. `append` prints each earlier bug whose
id-line fix commit touched a path the `component` names, with the REBUILD due on that
path when a child bug (its `caused_by` names an earlier fix of the path) landed after the path's last REBUILD, opens the record, refuses a duplicate id or a `component` naming no tracked path, and
requires `--correlates` as ledger or archive ids (repeated or comma-separated), or `none`;
`update --set correlates=<a>,<b>` records a correlate found later. `component` is precise free text; its tracked paths
are the bug's files. Every supplied value passes the same privacy check used by the push gate.

Not a bug: an agent mistake, wrong usage, an environment limit, designed validation, law
ambiguity or a missing feature.

## 2. Lineage, then RED

Read the ledger slice `dd-bug-resolution/LINEAGE.md` names for the bug's fix files or
component. Inspect each prior fix, the commit whose `fix(bugs): <id>` or
`refactor(bugs): <id>` line names its bug (the recorded `fix_sha` is only a hint), and blame the production
lines the new fix replaces. End with `caused_by: <bug-id> | <task-id> | none`; use `none`
only when blame offers no candidate.

A REBUILD is due as `bugs.py append` prints it; it keeps the regression tests. Then add the lowest-level case that fails for the real cause before production code
moves. Existing assertions remain contract evidence.

## 3. Fix at the owning seam

Replace the faulty path and let the RED case turn GREEN. Prefer deletion and locality over
a wrapper around the old behavior. The fix commit's id line is its cite; the rule is `specs/bugs/AGENTS.md`'s, and `resolve` derives `fix_sha` and `fix_files` from it; its production numstat is the source for any later diff-direction analysis.

## 4. Resolve with persisted facts

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <bug-id> \
  --cause "…" --caused-by none --solution "…"
```

- `resolve` requires `cause`, `caused_by` and `solution`, derives `fix_sha`, then stamps
  `status: resolved` and `closed_at`.
- `caused_by` names a live or archived bug, a known release task, or `none`; `check`
  refuses a dangling link or loop.
- `supersede --by` and `reject --reason` are the other terminal transitions.
- `update <id> --set field=value` uses the schema's mutability classes and cannot replace
  transition-owned state.
- Every write validates the candidate bytes before atomic replacement, so refusal leaves
  both ledger files unchanged.

`bugs.py archive <ids…>` moves exactly the named terminal records into
`specs/bugs/_archive/bugs_histo.jsonl`. The archive retains historical record shapes as
readable history; new writes use the lean schema.
