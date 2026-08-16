---
title: "Thin-wrapper projected scripts — one logic, one source"
status: candidate
opened: 2026-08-14
description: >-
  Extraction of W6, the sole surviving finding of the resilience audit (2026-07-18),
  per grill ADR #2 (2026-08-14 refinement report): W6 is dispositioned `superseded` by
  this entry; every other finding of that audit is `rejected` (the audited object was
  demolished in v0.3.0, −60k lines); the audit archives citing this entry. The still
  true concern: projected/standalone scripts re-implement package behavior and drift
  (audit evidence: bugs 10, 24, README/CLI drift). The fix W6 proposed: projected
  scripts become thin wrappers that exec the workspace venv's package code — one logic,
  one source. Evidence of today's INVERSION of that principle: the package itself
  shells out to the standalone script — features/specs/doctor_memory.py:38-40 resolves
  _LINT_SCRIPT to public/scripts/lint-memory-atoms.py and :357 runs it via
  subprocess([sys.executable, "-B", str(_LINT_SCRIPT), ...]) inside
  MemoryValidator.check_lint1_memory_atoms (LINT-1), instead of importing one shared
  implementation.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/specs/doctor_memory.py#MemoryValidator
    change: >-
      LINT-1 stops shelling out to the standalone lint-memory-atoms.py script
      (_LINT_SCRIPT at :38-40, subprocess at :357): the lint logic lives once in the
      package and is imported here; the projected script becomes a thin wrapper that
      execs the workspace venv's package entry point.
  - subject:
      kind: cli
      ref: public doctor
    change: >-
      Every projected script under public/scripts/ follows the thin-wrapper contract:
      no re-implemented package logic in the projection; the wrapper resolves the
      workspace venv and delegates. Doctor/projection tests assert the contract so
      script↔package drift (the W6 defect class) is structurally impossible.
---

# Thin-wrapper projected scripts

## Description

See frontmatter. Provenance:
`specs/audits/2026-07-18-architecture-resilience-review.md`, finding W6 ("Projected
assets duplicate package logic … *Remaining (proposed):* projected scripts become thin
wrappers that exec the workspace venv's package code — one logic, one source"),
dispositioned `superseded` by this entry in the 2026-08-14 grill (ADR #2).

The direction today is inverted twice: projections duplicate package logic, and the
package shells out to a script (`doctor_memory.py:38-40,357`) rather than owning the
logic and letting the projection delegate inward.

## Acceptance criteria

No projected script under `public/scripts/` carries package logic; each is a thin
wrapper exec'ing the venv's package code; LINT-1 runs in-process (or through the same
single implementation); a test pins the wrapper contract; suite green;
`dadaia public doctor` green.
