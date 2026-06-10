---
title: doctor-blind-to-projected-drift
severity: High
opened: 2026-06-05
session_id: null
status: resolved
resolved_in: v0.1.5/rc-2
resolution_note: resolved by v0.1.5/rc-2 T-PROP-01 (install hash-compare overwrite) + T-PROP-02 (doctor staging↔projected check) + T-PROP-03 (guardrail rule alignment)
---

# Bug: doctor-blind-to-projected-drift

## Description

`dadaia public doctor` only validates **source-vs-staging** (it prints
`[ok] stage:scripts/<file>` etc.) and never checks **staging-vs-projected** — the
actual installed files under `.dadaia/scripts/`, `.claude/`, `.codex/`,
`.opencode/`. Consequently, when a projection is stale (e.g. because
`install` skipped an existing file — see [[install-skips-existing-files]]),
doctor still reports `[ok]` for every asset and **exits 0**, giving a false
all-clear while the running instance (hooks, gate, personas) is out of date.

This directly defeats the source-vs-instance contract: doctor is the tool agents
rely on to confirm "the instance reflects the library", but it cannot detect the
most common drift.

## Steps to reproduce

1. Modify a lib-originated file and `dadaia public stage` (so source==staging).
2. Do NOT force-install (leave the projection stale).
3. `dadaia public doctor` → reports `[ok] stage:scripts/sdd-spec-gate.sh`,
   exit code 0.
4. `diff dadaia_workspace/public/scripts/sdd-spec-gate.sh .dadaia/scripts/sdd-spec-gate.sh`
   → DIFFERS. Doctor reported no drift; expected a `[drift]`/non-zero signal.

Reproduced live 2026-06-05 during v0.1.5/rc-1 R1 propagation.

## Environment

- dadaia version: v0.1.4 (pyproject); working tree on `feature/0.1.5`
- OS: Linux
- Python: 3.12

## Root cause hypothesis

Doctor's checks compare source against the staging manifest only. It needs a
third comparison: staging SHA256 vs the projected file's actual content hash for
every target runtime, emitting `[drift]` (and a non-zero exit) on mismatch.
Pairs with [[install-skips-existing-files]] (the install no-op that creates the
drift doctor cannot see).
