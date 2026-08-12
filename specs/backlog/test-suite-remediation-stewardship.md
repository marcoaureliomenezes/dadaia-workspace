---
title: "Test-suite remediation — apply the stewardship doctrine to dadaia-workspace's own tests"
status: candidate
opened: 2026-08-12
description: >-
  Companion to test-stewardship-standardization: once the doctrine/skill/enforcement
  ship, run the first full curation of this repo's own suite against it. The 2026-08-12
  scans mapped the work: tautology/change-detector cleanup in the named worst offenders,
  ~6 tombstone deletions, LARGE ownership declarations, quarantine adoption, orphan
  tooling disposition, wall-clock/durations wiring, artifact residue sweep. All
  curation lands as qa-engineer verdicts executed by software-engineer (steward is
  verdict-only), with the S-15 demotion map recorded at closure.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/public_assets.py#FileSystemPublicAssetManager
    change: >-
      Rework the tautological/implementation-coupled test families that orbit this
      surface: tests/unit/infrastructure/test_public_assets_doctor.py (byte-matching
      ~10 private methods -> assert observable doctor outcomes), test_public_assets_hooks.py
      (generator-constant hand-copies -> externally-held contract frozensets, per the
      existing test_claude_scaffold_is_loadable.py pattern; embedded old-wiring
      tombstone asserts removed), test_public_doctor_parity.py (self-consistency loop
      -> behavioral assertions).
  - subject:
      kind: doc
      ref: quality-assurance.md#Purpose
    change: >-
      Suite-wide curation pass: delete the ~6 tombstone tests (no-auth memorial,
      removed-view/param asserts) with S-16 evidence in the commit; fix f(x)==f(x)
      contracts (test_model_mapping.py, test_pricing.py cross-table) by pinning
      externally-held expectations; declare owners for all 26 LARGE files; carry every
      env-gate skip with a plan ref or delete; wire-or-delete
      tests/scripts/check_skill_orphans.py; kill the journey spec's permanent local
      skip; dedupe the panel readiness helpers; sweep artifact residue (dead gitignore
      line, local tmpdir GC).
---

# Test-suite remediation — first curation under the new doctrine

## Description

Executes the findings of the 2026-08-12 scans (dossier:
`.dadaia/tmp/software-engineer/20260812/stewardship-research-dossier.md`) against the
shipped stewardship doctrine. Blocked until test-stewardship-standardization delivers.

## Acceptance criteria

Every scan finding dispositioned (fixed / kept-with-justification recorded); curation
commits carry verdict evidence; suite green with the new tier timeouts; demotion map in
the closing CLOSURE; LARGE ownership 100%.
