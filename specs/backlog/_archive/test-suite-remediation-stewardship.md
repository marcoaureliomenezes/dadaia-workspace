---
title: "Test-suite remediation — apply the stewardship doctrine to dadaia-workspace's own tests"
status: candidate
opened: 2026-08-12
description: >-
  Rewritten 2026-08-14 by project-manager per grill ADR #6: the previous text carried a
  stale baseline ("26 LARGE files") and referenced a dossier that no longer exists
  (.dadaia/tmp is ephemeral — verified gone at HEAD). Live baseline, re-measured at
  HEAD on 2026-08-14 (commands in the body): 55 e2e-tier pytest tests collected under
  tests/e2e/** across 17 files, plus 41 Playwright cases in 11 browser specs
  (tests/e2e/panel/*.spec.ts) — broad LARGE census 96 total, against the declared
  LARGE cap of 30 (specs/memory/quality-assurance.md:145-146, WARN while above);
  333 pytest test files repo-wide. The work: the first full curation of this repo's
  own suite under the shipped stewardship doctrine — LARGE census down to (or
  justified against) the cap, ownership declarations, tombstone/tautology cleanup,
  quarantine adoption, orphan tooling disposition. All curation lands as qa-engineer
  verdicts executed by software-engineer (steward is verdict-only), with the demotion
  map recorded at closure. EXCLUDED from the current release round (grill ADR #6);
  strong candidate for its own follow-up release.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/public_assets.py#FileSystemPublicAssetManager
    change: >-
      Rework the tautological/implementation-coupled test families that orbit this
      surface — re-verified present at HEAD 2026-08-14:
      tests/unit/infrastructure/test_public_assets_doctor.py (byte-matching private
      methods -> assert observable doctor outcomes) and test_public_assets_hooks.py
      (generator-constant hand-copies -> externally-held contract frozensets, per the
      existing test_claude_scaffold_is_loadable.py pattern). NOTE: the previously
      named test_public_doctor_parity.py no longer exists — that finding is void; the
      pick-time scan re-derives the offender list instead of trusting this one.
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#Test Health
    change: >-
      Suite-wide curation pass against the live 2026-08-14 baseline: bring the LARGE
      census (96 broad / 55 e2e-tier pytest vs cap 30) down via the demotion protocol
      or justify the excess explicitly; declare owners for every LARGE test; fix
      f(x)==f(x) self-consistency contracts (re-located at HEAD:
      tests/unit/infrastructure/runtime_transforms/test_model_mapping.py,
      tests/unit/features/telemetry/test_pricing.py) by pinning externally-held
      expectations; wire-or-delete tests/scripts/check_skill_orphans.py (still
      unwired at HEAD); carry every env-gate skip with a plan ref or delete it;
      sweep artifact residue. Every deletion/demotion is a qa-engineer verdict with
      evidence, executed by software-engineer.
---

# Test-suite remediation — first curation under the stewardship doctrine

## Description

Companion to the delivered `test-stewardship-standardization` (v0.7.0): run the first
full curation of this repo's own suite against the shipped doctrine.

## Live baseline (measured at HEAD, 2026-08-14 — supersedes all earlier scans)

| Measure | Value | Command |
|---|---|---|
| e2e-tier pytest tests | **55** collected | `pytest tests/e2e --collect-only -q` → "55 tests collected" |
| e2e pytest files | 17 | `find tests/e2e -name "*.py"` |
| Browser (Playwright) cases | **41** in 11 specs | `grep -c "test(" tests/e2e/panel/*.spec.ts` |
| Broad LARGE census | **96** (55 + 41) | sum above |
| Pytest test files repo-wide | 333 | `find tests -name "test_*.py"` |
| Declared LARGE cap | **30** (WARN while above) | `specs/memory/quality-assurance.md:145-146` |

Divergence noted: QA memory (`quality-assurance.md:60-64`) states the broad census as
"~84" — the 2026-08-14 measurement gives 96. The memory correction belongs to
`product-engineer` at the remediation release's CLOSURE, not to this entry.

The 2026-08-12 dossier
(`.dadaia/tmp/software-engineer/20260812/stewardship-research-dossier.md`) no longer
exists and is no longer evidence. Findings carried forward only where re-verified at
HEAD (see intents); everything else is re-derived by a fresh scan at pick time.

## Acceptance criteria

Every scan finding dispositioned (fixed / kept-with-justification recorded); curation
commits carry qa-engineer verdict evidence; LARGE ownership 100%; LARGE census at or
justified against the cap of 30; suite green with the tier timeouts; demotion map in
the closing CLOSURE; QA memory census corrected at CLOSURE.
