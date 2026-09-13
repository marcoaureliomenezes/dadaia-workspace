---
name: dd-workspace-doctor
description: >
  Run the one compliance scan and reaper — sections workspace (zones, root and
  harness-dir slop, TTL-expired entries, states canon), specs (canon tree, releases,
  fixed law) and ledgers (every committed governance record). Use when the operator
  mentions "doctor", "drift", "slop", "compliance", or "fix workspace".
---

# dd-workspace-doctor — The One Scan

## 1. When

- The operator mentions "doctor", "drift", "slop", "compliance", "fix workspace", or `/dd-workspace-doctor`.
- Instance state, the `specs/` canon tree and every committed governance record (`DADAIA.md` §8.5).
- Spec-vs-code drift belongs to `project-auditor`; lib-vs-projection drift to `dadaia public doctor`.
- `specs doctor` and `backlog doctor` no longer exist and are not aliased — this is the one verb.

## 2. Vocabulary — use these terms exactly

- **Section**: one of `workspace`, `specs`, `ledgers` — each scores its own line, in that order.
- **Zone** (workspace section): one top-level `.dadaia/` directory; the registry is `core/workspace_layout.DADAIA_ZONES`, rendered into `.dadaia/AGENTS.md`.
- **Finding verdict**: `canon | operator | slop | expired | missing`; `canon` + `operator` are canonical.
- **Finding line**: `<CODE> <verdict> <message>`; codes are `WS-<zone>-<verdict>` (`<zone>` = `root`, a harness dir, `dadaia`, or a zone name without its leading dot), `SPEC-DOC-*`, `TREE-*`, `RELEASE-TREE-*`, `BL-SCHEMA|CONFLICT|STALE`, `LEDGER-<NAME>-SCHEMA`.
- **Score lines**: `compliance(<section>): N/M <unit> canonical (P%)` per section, then `compliance(total)` last.
- Avoid: `ROOT-n`, "quarantine", "gc", "cleanup", "specs doctor", "backlog doctor" — retired names, no longer verbs.

## 3. Steps

1. Dry run from the workspace root: `dadaia doctor --context <ctx>` (`--json` for the machine mirror; `--specs-dir`/`--public-dir` to aim it). Done when every finding line and all four score lines are read; exit 1 means an error-class finding exists.
2. Classify each finding: `expired` = TTL by mtime; `slop` = outside the projection manifest, the zone registry and `.dadaia/states/instance_exceptions.txt`; `missing` = a states-canon file absent.
2a. A `LEDGER-*-SCHEMA` finding means a committed record of `decisions.jsonl`, `BACKLOG.json`, `BUGS.jsonl`, `FINDINGS.jsonl`, a `_RELEASE.json` or a `_histo.jsonl` violates its schema — repair the record, never the schema.
3. Reap expired entries: `dadaia doctor --fix --expired-only` — what SessionStart already runs. Done when a rerun shows zero `*-expired` lines.
4. Slop: name each `WS-*-slop` line to the operator with its cause (stray root entry, unknown zone, harness-dir file outside the manifest). Only an explicit operator `dadaia doctor --fix` deletes it; never delete by hand.
5. An operator-owned entry that must stay: add one glob per line to `.dadaia/states/instance_exceptions.txt` (`#` comments), then rerun. Done when the entry reads `operator`.
6. `missing` or projection drift: `dadaia public stage && dadaia public install --target all && dadaia public doctor`; `--fix` recreates a missing `harness_profile.json`. Never hand-edit a projection.
7. Report the `compliance(total)` line verbatim; 100% is the bar for a candidate's artifact GC (`dd-release-implementation`, `RC-FLOW.md` step 8).

## 4. What `--fix` touches

- Deletes: every `expired` entry, and with a plain `--fix` every `slop` entry — nothing the dry run did not list.
- Repairs in the `specs` section: the fixed law sections (FIXED-1/2), a losslessly-refreshable law projection (TREE-5), a missing `_archive/` (SPEC-DOC-034), a stale verdict (SPEC-DOC-044), a legacy `RELEASE.json` name (SPEC-DOC-046), a stray root entry (TREE-8).
- Never touches: `canon` and `operator` entries, `.venv/`, `references/`, `sessions/` (own reaper), anything outside the workspace.

## 5. Done when

- `compliance(total)` reads 100%, or every remaining finding is named to the operator with its cause.
- No lib-originated file and no runtime JSON was hand-edited to fake a fix.

## 6. References

- `DADAIA.md` §5.1 (root, exceptions), §8.1 (reprojection), §8.5 (the scan).
- `.dadaia/AGENTS.md` — the rendered zone table; `.dadaia/states/AGENTS.md` — the states canon.
- `dadaia doctor --help` wins over any flag remembered here.
