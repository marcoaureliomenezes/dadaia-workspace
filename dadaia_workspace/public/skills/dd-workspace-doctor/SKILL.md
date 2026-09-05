---
name: dd-workspace-doctor
description: >
  Run the one workspace compliance scan and reaper: `.dadaia/` zones, root and
  harness-dir slop, TTL-expired entries, states canon, projection drift. Use when
  the operator mentions "doctor", "drift", "slop", "compliance", or "fix workspace".
---

# dd-workspace-doctor — The One Scan

## 1. When

- The operator mentions "doctor", "drift", "slop", "compliance", "fix workspace", or `/dd-workspace-doctor`.
- Instance state only: what `.dadaia/`, the root and the harness dirs contain (`DADAIA.md` §8.5).
- Spec-vs-code drift belongs to `project-auditor`; lib-vs-projection drift to `dadaia public doctor`.

## 2. Vocabulary — use these terms exactly

- **Zone**: one top-level `.dadaia/` directory; the registry is `core/workspace_layout.DADAIA_ZONES`, rendered into `.dadaia/AGENTS.md`.
- **Finding verdict**: `canon | operator | slop | expired | missing`; `canon` + `operator` are canonical.
- **Finding code**: `WS-<zone>-<verdict>`; `<zone>` = `root`, a harness dir (`claude codex kimi-code agents`), `dadaia`, or a zone name without its leading dot.
- **Score line**, last line of every run: `compliance: N/M entries canonical (P%)`.
- Avoid: `ROOT-n`, "quarantine", "gc", "cleanup" — retired names, no longer verbs.

## 3. Steps

1. Dry run from the workspace root: `dadaia doctor` (`--json` for the machine mirror). Done when every finding line and the score line are read; exit 1 means slop or expired entries exist.
2. Classify each finding: `expired` = TTL by mtime; `slop` = outside the projection manifest, the zone registry and `.dadaia/states/instance_exceptions.txt`; `missing` = a states-canon file absent.
3. Reap expired entries: `dadaia doctor --fix --expired-only` — what SessionStart already runs. Done when a rerun shows zero `*-expired` lines.
4. Slop: name each `WS-*-slop` line to the operator with its cause (stray root entry, unknown zone, harness-dir file outside the manifest). Only an explicit operator `dadaia doctor --fix` deletes it; never delete by hand.
5. An operator-owned entry that must stay: add one glob per line to `.dadaia/states/instance_exceptions.txt` (`#` comments), then rerun. Done when the entry reads `operator`.
6. `missing` or projection drift: `dadaia public stage && dadaia public install --target all && dadaia public doctor`; `--fix` recreates a missing `harness_profile.json`. Never hand-edit a projection.
7. Report the final score line verbatim; 100% is the bar for a candidate's artifact GC (`dd-release-implementation`, `RC-FLOW.md` step 8).

## 4. What `--fix` touches

- Deletes: every `expired` entry, and with a plain `--fix` every `slop` entry — nothing the dry run did not list.
- Never touches: `canon` and `operator` entries, `.venv/`, `references/`, `sessions/` (own reaper), anything outside the workspace.

## 5. Done when

- The score line reads 100%, or every remaining finding is named to the operator with its cause.
- No lib-originated file and no runtime JSON was hand-edited to fake a fix.

## 6. References

- `DADAIA.md` §5.1 (root, exceptions), §8.1 (reprojection), §8.5 (the scan).
- `.dadaia/AGENTS.md` — the rendered zone table; `.dadaia/states/AGENTS.md` — the states canon.
- `dadaia doctor --help` wins over any flag remembered here.
