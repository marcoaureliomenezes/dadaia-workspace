# TASKS: v0.1.22 — Hygiene sweep

**Status:** Aprovado
**Release ID:** v0.1.22

## DEFINITION
- [x] T-22-01 — Author SPEC/PLAN/TASKS (Status: Aprovado).

## IMPLEMENTATION
- [x] T-22-02 — H1: `release_new` accepts SemVer (`^v\d+\.\d+\.\d+$`) OR slug; update help/docstring; unit tests (SemVer/slug/invalid); flip bug `release-new-rejects-semver-but-doctor-requires-it` → Closed.
- [x] T-22-03 — H2: `public/pi/settings.json` `prompts` → `["prompts"]`; stage + install --target pi + doctor.
- [x] T-22-04 — H3: archive `specs/releases/v0.1.12` (honest superseded CLOSURE + `git mv` to `_archive`).

## CLOSURE
- [x] T-22-05 — preflight green + review ladder (QA + code-review + security) APPROVED.
- [x] T-22-06 — CLOSURE.md + archive v0.1.22 + gated push + PR + CI watched green.
