---
title: install-does-not-prune-orphan-projections
severity: High
opened: 2026-06-06
session_id: null
status: Closed
target: v0.2.0/integration
resolved_in: 0.1.7 (rc-4, T-017-32)
---

**Resolution (0.1.7 rc-4, T-017-32):** added the reverse orphan-prune sweep to `copy_agents_for_opencode` (it previously only wrote forward) and ungated the stale-`.toml` prune in `install_codex_agents` (was `if force:` only). All copy strategies now prune orphans on plain `install`, matching `copy_tree`. Tests `test_copy_agents_for_opencode_prunes_orphan` + existing prune suite. The library-side dangling skill-refs + a `stage`-time ref-integrity gate are tracked under `agent-skill-surface-slop` (T-017-36).


# Bug: `dadaia public install` does not prune orphan projections; doctor is blind to them

## Description

When a persona or skill is deleted from `dadaia_workspace/public/` and re-staged,
`dadaia public install --force --target all` projects the *current* staged files but
does **not remove** previously-projected files whose source no longer exists. The
orphans remain live in `.claude/agents/`, `.opencode/agents/`, `.claude/skills/`,
`.opencode/skills/`, etc. `dadaia public doctor` exits 0 despite these orphans —
it validates source↔staging↔projected for files that *exist in staging*, but has no
check for projected files that are **absent from staging** (orphan detection).

Surfaced during v0.1.8 (roster 15→9): after deleting 4 personas + 5 skills and
running `install --force --target all`, `.claude/agents/` and `.opencode/agents/`
still listed 16 files (12 expected) and the 5 deleted skills remained. The live
Claude Code runtime would still load the deleted personas — a correctness drift,
not cosmetic.

## Reproduction

1. Delete a file under `dadaia_workspace/public/agents/` (e.g. `researcher.md`).
2. `dadaia public stage && dadaia public install --force --target all`.
3. `ls .claude/agents/` still contains `researcher.md` (orphan).
4. `dadaia public doctor` → exit 0 (blind to the orphan).

## Workaround applied (v0.1.8)

Manually `rm` the known orphan agent `.md`/`.toml` files and skill dirs from
`.claude/`, `.opencode/`, `.codex/`. This is legitimate drift reconciliation
(removing files with no source), but is not a durable fix.

## Proposed fix (owned by v0.2.0 integration — drift-elimination, T-020)

1. `dadaia public install` (or a `--prune` flag, on by default for `--force`)
   removes managed projected files (agents/skills/workflows/rules) that are absent
   from the current staging set, while never touching operator-added files
   (use the manifest to distinguish lib-managed from operator files).
2. `dadaia public doctor` gains an orphan-projection check: any projected
   agent/skill/workflow/rule absent from staging → `[orphan]` non-zero exit.
3. Add a regression test: stage with file A, install, delete A from source, stage,
   install, assert A is absent from every runtime projection and doctor flags it
   before the prune.

## Related

- Memory `public-asset-distribution` (install/doctor semantics).
- v0.1.8 T-018-07 (propagation) had to manually prune to reach 12-per-runtime.
