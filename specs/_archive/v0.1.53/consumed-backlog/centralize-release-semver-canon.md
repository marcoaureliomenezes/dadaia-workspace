---
title: Centralize the release SemVer canon into one shared constant
status: idea
opened: 2026-06-25
surface: features/specs/scaffolder.py, features/specs/doctor.py, features/spec_artifacts/new_artifacts.py
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/specs/scaffolder.py#_RELEASE_SEMVER_RE" }
    change: "remove the literal SemVer regex copy; import the shared canon from core/specs_version.py"
  - subject: { kind: code, ref: "dadaia_workspace/features/specs/doctor.py#RELEASE_SEMVER_RE" }
    change: "remove the SPEC-DOC-027 literal copy; import the shared canon from core/specs_version.py"
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_artifacts/new_artifacts.py#_RELEASE_SEMVER_RE" }
    change: "remove the v0.1.22 literal copy; import the shared canon from core/specs_version.py"
---

## Problem

The release SemVer regex `^v\d+\.\d+\.\d+$` is now duplicated as an independent
literal in **three** feature modules:

- `dadaia_workspace/features/specs/scaffolder.py:18` (`_RELEASE_SEMVER_RE`)
- `dadaia_workspace/features/specs/doctor.py:130` (`RELEASE_SEMVER_RE`, SPEC-DOC-027 canon)
- `dadaia_workspace/features/spec_artifacts/new_artifacts.py:28` (`_RELEASE_SEMVER_RE`, added v0.1.22 / H1)

plus a prose copy in the `product-engineer` persona.

v0.1.22 closed the bug `release-new-rejects-semver-but-doctor-requires-it` by making
`release_new` agree with the doctor canon — but it did so by **copy-pasting a third
literal**, not by sharing one. The original bug *was* two naming rules drifting apart;
the current fix makes them agree **today** with no shared constant and no test asserting
the three agree. SPEC-DOC-027 is not CI-gated, so if the canon ever evolves a missed edit
silently re-opens the exact contradiction v0.1.22 closed. This is latent drift, flagged
**MEDIUM** by the software-architect review of v0.1.22 (and LOW DRY by code-review).

## Proposed direction

Lift `RELEASE_SEMVER_RE` + an `is_release_semver(id: str) -> bool` helper into the
existing `dadaia_workspace/core/specs_version.py` (already the canonical specs-versioning
constants module, and the only layer-clean cross-feature home — `new_artifacts` lives in a
different feature package from `doctor`/`scaffolder`). Have all three modules import it.
Add a test asserting a single source of truth (e.g. all three call sites resolve to the
same compiled pattern). Update the persona prose to reference the canon, not restate it.

## Acceptance (draft)

- One shared `RELEASE_SEMVER_RE` / `is_release_semver()` in `core/specs_version.py`.
- `scaffolder`, `doctor`, and `new_artifacts` import it; zero remaining literal copies of
  `^v\d+\.\d+\.\d+$` in feature modules.
- A test that fails if a second copy of the pattern is reintroduced (or that all call
  sites agree).

## Provenance

Surfaced by the v0.1.22 review ladder (software-architect MEDIUM, code-review LOW DRY,
qa LOW). Deliberately deferred out of v0.1.22 scope (a minimal hygiene sweep) per all three
reviewers. PM to curate priority.
