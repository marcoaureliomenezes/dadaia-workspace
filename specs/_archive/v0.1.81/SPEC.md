# SPEC — Release v0.1.81 — Deprecation strips & doctor cleanup

**Status:** Aprovado
**Source:** backlog `20260710-deprecation-strips-and-doctor-cleanup` (P3, renumbered
from the plan's v0.1.80 slot).
**Date-gate waiver:** the entry's ship-on/after-2026-08-01 constraint (one consumer
re-projection window for the `tier:` fallback strip) was **explicitly waived by the
operator on 2026-07-11** ("waive the window and ship v0.1.81 now"). Consequence
accepted: a consumer workspace that has not re-projected since v0.1.64 and still
carries stale `tier:` agent frontmatter will see the standard unknown-field drop
warning and the dispatch band default to 3 (with its missing-band warning) until it
runs `dadaia public install` — degraded-with-warnings, never a crash.

## FRs

- **FR1 — Strip the v0.1.64 `tier:` tolerate window.** In
  `features/agents/reader.py`: remove the silent legacy fallback read
  (`band_raw = raw.get("tier")`, line ~173); drop `tier` from `_ALLOWED_FIELDS` (an
  unknown `tier:` then gets the standard unknown-field drop warning; band defaults to
  3 with the missing-band warning); delete the module-level alias
  `MissingTierError = MissingDispatchBandError` (line ~109) and its
  `features/agents/__init__.py` re-export (+ `__all__` entries in both). Flip the
  AC-6 fallback test from proving silent tolerance to proving the legacy key is
  unknown. UNTOUCHED: the `dispatch_band`-preferred path, the contract test's pinned
  model/effort map, and the registry `Tier` (model-cost axis — unrelated, keeps its
  name).
- **FR2 — Specs-doctor WARNING invariant for partial archived release dirs.** In
  `features/specs/doctor_release.py#ReleaseValidator`: a
  `specs/_archive/releases/<id>/` directory containing NONE of
  SPEC.md/PLAN.md/TASKS.md/CLOSURE.md is residue masquerading as an archived release
  (the v0.1.41 precedent). The check honors the SPEC-DOC-027 legacy-name allowlist,
  tolerates segmented layouts (`<id>/<segment>/` — a dir whose SUBDIRS carry the
  artifacts is fine), suggests relocation to `specs/_archive/wip-abandoned/<id>/`
  with a README breadcrumb, and stays WARNING severity so historical trees never
  hard-fail doctor.

## Acceptance

- Legacy `tier:` frontmatter → unknown-field warning + band 3 default (test-pinned);
  no `MissingTierError` importable; grep zero `raw.get("tier")` in production.
- The invariant fires on a v0.1.41-class fixture (artifact-empty dir), does NOT fire
  on allowlisted legacy names, segmented layouts, or complete archives; WARNING only.
- This workspace's own `specs/` tree stays doctor-clean (0 errors) after the new
  invariant lands — if it flags real residue here, relocate it per the suggestion in
  the same release.
- Full suite green; mypy --strict; ruff; doctors; per-sha security APPROVE.
