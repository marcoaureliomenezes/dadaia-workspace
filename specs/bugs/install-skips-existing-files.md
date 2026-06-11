---
title: install-skips-existing-files
severity: High
opened: 2026-06-05
session_id: null
status: Closed
resolved_in: v0.1.5/rc-2
resolution_note: resolved by v0.1.5/rc-2 T-PROP-01 (install hash-compare overwrite) + T-PROP-02 (doctor staging↔projected check) + T-PROP-03 (guardrail rule alignment)
---

# Bug: install-skips-existing-files

## Description

`dadaia public install --target all` silently **skips any projected file that
already exists**. When a lib-originated source asset under `dadaia_workspace/public/`
is *modified* (not newly added), the documented edit workflow does **not**
propagate the change to the instance — the stale projection stays in place and
the new content never reaches `.dadaia/scripts/`, `.claude/`, `.codex/`,
`.opencode/`, etc.

This makes the canonical "Correct edit workflow" in the
`dadaia-workspace-dev-guardrail` rule incorrect for the common case of editing an
existing asset (step 3 `install --target all` is a no-op for existing files).
Only `install --force --target all` overwrites, but the guardrail reserves
`--force` for operator/devops drift repair — leaving ordinary edit-then-propagate
with no working authorized path.

## Steps to reproduce

1. Edit an existing lib-originated file, e.g.
   `dadaia_workspace/public/scripts/sdd-spec-gate.sh`.
2. `dadaia public stage && dadaia public install --target all`.
3. Install prints `[skip] .../.dadaia/scripts/sdd-spec-gate.sh`.
4. `diff dadaia_workspace/public/scripts/sdd-spec-gate.sh .dadaia/scripts/sdd-spec-gate.sh`
   → DIFFERS. Expected: projection updated to match source.

Reproduced live 2026-06-05 while propagating v0.1.5/rc-1 T-R1-04 gate fixes.

## Environment

- dadaia version: v0.1.4 (pyproject); working tree on `feature/0.1.5`
- OS: Linux
- Python: 3.12

## Root cause hypothesis

`install` treats an existing destination as "already installed" and skips it
instead of comparing content hashes (staging SHA256 vs projected) and overwriting
on mismatch. Proposed fix: overwrite when staged hash differs from projected hash
(idempotent; no `--force` for legitimate updates); reserve `--force` only for
clobbering locally-divergent projections. Pairs with
[[doctor-blind-to-projected-drift]].
