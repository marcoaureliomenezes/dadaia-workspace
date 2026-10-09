# The bug loop

Register → RED → fix → resolve. A confirmed block-list bug uses a hotfix job; other bugs
enter the approved release scope through its ordinary job structure.

## 1. Register — ask first

A bug is a merged change that reproducibly breaks a documented contract; a failure inside
an unmerged worktree is rework. Registration starts with a proposal naming the violated
contract, one reproducing command already run, why the failure is not agent error and its
severity. `append` runs only after the operator confirms.

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append \
  --bug-id doctor-exits-zero-with-errors --reported-by dd-software-engineer \
  --title "doctor exits 0 while reporting error findings" \
  --severity HIGH --surface cli --component "cli/commands/doctor.py#run" \
  --context demo --symptom "…" --repro "…" --expected "…" --correlates none
```

The ledger holds one record per bug, keyed by id. `append` prints correlation candidates,
opens the record, refuses a duplicate id or unknown tracked-directory `surface`, and
requires `--correlates <ids>|none`. `component` remains precise free text. Every supplied
value passes the same privacy check used by the push gate.

Not a bug: an agent mistake, wrong usage, an environment limit, designed validation, law
ambiguity or a missing feature.

## 2. Lineage, then RED

Read at most the 20 most recent records sharing the bug's surface or component since the
newest archived audit. Inspect the persisted `fix_sha` commits and blame the production
lines the new fix replaces. End with `caused_by: <bug-id> | <task-id> | none`; use `none`
only when blame offers no candidate.

Two or more prior fixes on the touched module require a REBUILD that keeps the regression
tests. Then add the lowest-level case that fails for the real cause before production code
moves. Existing assertions remain contract evidence.

## 3. Fix at the owning seam

Replace the faulty path and let the RED case turn GREEN. Prefer deletion and locality over
a wrapper around the old behavior. The implementation commit's sha becomes the persisted
`fix_sha`; its production numstat is the source for any later diff-direction analysis.

## 4. Resolve with persisted facts

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <bug-id> \
  --cause "…" --caused-by none --solution "…" --fix-sha <40-hex-sha>
```

- `resolve` requires `cause`, `caused_by`, `solution` and `fix_sha`, then stamps
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
