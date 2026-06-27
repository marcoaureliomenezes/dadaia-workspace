# PLAN: v0.1.22 — Hygiene sweep

**Status:** Aprovado
**Release ID:** v0.1.22

## Approach

Branch `feature/v0.1.22` off `main`. One small commit set, then the gate ladder, gated
push, PR, CI green. All three items are low-risk coherence fixes.

1. **DEFINITION** — SPEC/PLAN/TASKS.
2. **IMPLEMENTATION** —
   - H1: add a release-id validator that accepts SemVer `^v\d+\.\d+\.\d+$` OR the legacy
     slug, used only by `release_new` (backlog/bug keep `_SLUG_RE`); update help/docstring;
     add unit tests (SemVer accepted, slug accepted, invalid rejected); flip the bug to
     `Closed`.
   - H2: `public/pi/settings.json` `prompts` → `["prompts"]`; `public stage && install
     --target pi && doctor`.
   - H3: write `specs/releases/v0.1.12/CLOSURE.md` (honest superseded/abandoned record with
     the required sections), then `git mv` the dir into `_archive/releases/`.
3. **CLOSURE** — CLOSURE.md, archive v0.1.22, gate ladder, gated push, PR, CI watched green.

## Notes / risk

- H3 does NOT fake `[x]` — the undelivered tasks are recorded as superseded in the CLOSURE.
- The `release_id` validator change is additive (broadens acceptance); existing slug
  releases and the doctor canon stay intact. A test pins all three branches.
- No version bump → `release.yml` stays self-skipped (no deploy), consistent with the
  operator's standing constraint.

## Verification

`dadaia release new` SemVer test · bug `Closed` · `public doctor` `[ok] public-privacy` ·
`specs doctor` 0 · `ci preflight` green · security APPROVE keyed to pushed tip · CI green.
