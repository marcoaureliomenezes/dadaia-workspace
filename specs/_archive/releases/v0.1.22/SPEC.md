# SPEC: v0.1.22 — Hygiene sweep (release-tooling coherence + spec/config tidy)

**Status:** Aprovado
**Release ID:** v0.1.22
**Owner:** product-engineer
**Created:** 2026-06-25
**Branch:** `feature/v0.1.22` (off `main` @ a83589b, post-#66-merge)

## 1. Problem

Operator-requested hygiene sweep of accumulated small debt surfaced across recent
releases. None is a feature; all are coherence/tidy items with low blast radius.

## 2. Scope

- **H1 — `release new` SemVer coherence (bug `release-new-rejects-semver-but-doctor-requires-it`, MEDIUM/Open).**
  `release_new` (`features/spec_artifacts/new_artifacts.py`) validates the release id with
  `_SLUG_RE = ^[a-z][a-z0-9-]+$` (dots forbidden), while `specs doctor` SPEC-DOC-027
  REQUIRES a live release dir to match the SemVer canon `^v\d+\.\d+\.\d+$` (dots
  mandatory). No id satisfies both → every recent release used a slug workaround then got
  renamed. Fix (bug option a): `release_new` ALSO accepts the SemVer form (the doctor
  canon), so `dadaia release new v0.1.23` works. Backlog/bug slugs keep `_SLUG_RE`
  unchanged. Close the bug.
- **H2 — `.pi/settings.json` `prompts` config fidelity.** pi declares `prompts?: string[]`
  but the projected `public/pi/settings.json` sets a scalar `"prompts": "prompts"`. Change
  to the array form `["prompts"]` to match the schema (flagged in v0.1.21 dispositions).
- **H3 — Archive the abandoned `specs/releases/v0.1.12`.** It is `Status: Em revisão`,
  `Created: 2026-06-11`, 4/21 tasks done (15 `[ ]`, 2 `[-]`), and its intent ("Panel Auth
  Coherence") was **superseded** by the later panel-no-auth rework (the operator removed
  all panel auth). Per `release-governance` ("never delete; archive when closed"), move it
  to `specs/_archive/releases/v0.1.12/` with an honest CLOSURE marking it
  superseded/abandoned (undelivered tasks recorded, NOT faked `[x]`).

Out of scope (flagged to operator, NOT done here): the `dadaia-pi-workspace` context
DEAD-mark (`dadaia context dead` removes the repo from disk + pushes to its remote and has
a documented half-fail footgun — destructive/outward-facing, operator-gated); WS-PI-6,
RPC/SDK, OpenCode live worker. Stale-lease GC + merged-branch delete are operational (done
outside this release, no source change).

## 3. Acceptance criteria

1. `dadaia release new v<X.Y.Z>` succeeds (SemVer accepted); a slug id still works; an
   invalid id (e.g. with a space) still rejects. Unit-tested.
2. The bug file flips to `status: Closed` with a fix pointer.
3. `.pi/settings.json` `prompts` is an array; `dadaia public doctor` exit 0 +
   `[ok] public-privacy`.
4. `specs/releases/v0.1.12` archived under `_archive/` with a valid CLOSURE
   (Validations/Drifts/Memory-updates); `dadaia specs doctor` exit 0.
5. `dadaia ci preflight` green; review ladder (QA + code-review + security) APPROVED;
   gated push; CI green.

## 4. Non-goals

No feature, no behavior change beyond the release-id validator broadening, no dependency
change, no version bump.
