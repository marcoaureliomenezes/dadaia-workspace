---
name: dd-workspace-doctor
description: >
  Run the one compliance scan and reaper — sections workspace (zones, root and
  harness-dir slop, every ALIVE repo's top, held reaped entries, installed git-hook
  drift), specs (canon tree, releases, fixed law) and ledgers (every committed
  governance record). Use when the operator mentions "doctor", "drift", "slop",
  "compliance", "reaped", or "fix workspace".
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
- **Finding verdict**: `canon | operator | reaped | slop | expired | missing`; `canon`, `operator` and `reaped` are canonical.
- **Reaped**: an entry the reaper MOVED to `.dadaia/reaped/<YYYYMMDD>/<workspace-relative-path>`, held 7 days from the move, one hold per origin per day.
- **Sweep**: the one traversal primitive behind every walk, move and remove — a symlink is never followed, a vanished entry is absent, an OSError is one `skipped` action.
- **Finding line**: `<CODE> <verdict> <message>`; codes are `WS-<zone>-<verdict>` (`<zone>` = `root`, a harness dir, `dadaia`, or a zone name without its leading dot), `SPEC-DOC-*`, `TREE-*`, `RELEASE-TREE-*`, `BL-SCHEMA|CONFLICT|STALE`, `LEDGER-<NAME>-SCHEMA`.
- **Score lines**: `compliance(<section>): N/M <unit> canonical (P%)` per section, then `compliance(total)` last.
- Avoid: `ROOT-n`, `REPO-DADAIA-1`, "quarantine", "gc", "cleanup", "specs doctor", "backlog doctor", "doctor deletes slop" — retired names and a retired behavior.

## 3. Steps

1. Dry run from the workspace root: `dadaia doctor --context <ctx>` (`--json` for the machine mirror; `--specs-dir`/`--public-dir` to aim it). Done when every finding line and all four score lines are read; exit 1 means an error-class finding exists.
2. Classify each finding: `expired` = TTL by mtime; `slop` = outside the projection manifest, the zone registry and `.dadaia/states/instance_exceptions.txt`; `missing` = a states-canon file absent; `reaped` = already held, nothing to do.
2b. `HOOKS-DRIFT-1` = an ALIVE repo's installed `.git/hooks/{pre-commit,pre-push}` byte-differs from the shipped script; its fix line is `.dadaia/.venv/bin/dadaia ci install-hook --force`, run in that repo. The doctor never rewrites a chokepoint itself.
2a. A `LEDGER-*-SCHEMA` finding means a committed record of `decisions.jsonl`, `BACKLOG.json`, `BUGS.jsonl`, `FINDINGS.jsonl`, a `_RELEASE.json` or a `_histo.jsonl` violates its schema — repair the record, never the schema.
3. `dadaia doctor --fix --expired-only` scopes the REPORT to the TTL lane — what SessionStart runs; the reaper itself is the same in both lanes. Done when a rerun shows zero `*-expired` lines.
4. Slop: name each `WS-*-slop` line to the operator with its cause (stray root entry, unknown zone, harness-dir file outside the manifest, an excluded artifact or nested `.dadaia/` inside a repo). `--fix` MOVES it to `reaped/`; it is recoverable for 7 days. Never delete by hand.
5. An operator-owned entry that must stay: add one glob per line to `.dadaia/states/instance_exceptions.txt` (`#` comments), then rerun. Done when the entry reads `operator`.
6. `missing` or projection drift: `dadaia public stage && dadaia public install --target all && dadaia public doctor`; `--fix` recreates a missing `harness_profile.json`. Never hand-edit a projection.
7. Report the `compliance(total)` line verbatim; 100% is the bar for a candidate's artifact GC (`dd-release-implementation`, `RC-FLOW.md` step 8).

## 4. What `--fix` touches

- Moves: every `slop` entry and every DEAD-context repo leftover into `reaped/` — nothing the dry run did not list.
- Deletes: only what a TTL zone expired, `reaped/` included. Nothing else is ever deleted directly.
- Repairs in the `specs` section: the fixed law sections (FIXED-1/2), a losslessly-refreshable law projection (TREE-5), a missing `_archive/` (SPEC-DOC-034), a stale verdict (SPEC-DOC-044), a legacy `RELEASE.json` name (SPEC-DOC-046), a stray root entry (TREE-8).
- Never touches: `canon`, `operator` and `reaped` entries, a registered repo's source, `.venv/`, `references/`, `sessions/` and presence (own reapers), a zone's `AGENTS.md`, anything outside the workspace.
- The same reaper runs unattended at SessionStart and on the PostToolUse throttle; `--fix` adds the specs repairs on top.

## 5. Done when

- `compliance(total)` reads 100%, or every remaining finding is named to the operator with its cause.
- No lib-originated file and no runtime JSON was hand-edited to fake a fix.

## 6. References

- `DADAIA.md` §5.1 (root, exceptions), §8.1 (reprojection), §8.5 (the scan).
- `.dadaia/AGENTS.md` — the rendered zone table; `.dadaia/states/AGENTS.md` — the states canon.
- `dadaia doctor --help` wins over any flag remembered here.
