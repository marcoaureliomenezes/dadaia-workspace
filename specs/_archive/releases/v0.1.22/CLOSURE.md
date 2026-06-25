# Closure: Release — v0.1.22

> **Status:** Aprovado
> **Release ID:** v0.1.22
> **Owner:** product-engineer
> **Closed:** 2026-06-25

## Summary

v0.1.22 is a **hygiene sweep** — three small, independent coherence/drift fixes, no new
feature surface, no dependency change, no version bump intent beyond this release dir.

- **H1 — SemVer release ids are creatable.** `dadaia release new` rejected any id with a
  dot (validator `^[a-z][a-z0-9-]+$`), while `dadaia specs doctor` SPEC-DOC-027 *requires*
  a live release dir to be SemVer `^v\d+\.\d+\.\d+$`. No name satisfied both, forcing a
  slug workaround on every recent release. `release_new`
  (`features/spec_artifacts/new_artifacts.py`) now validates via `_is_valid_release_id` =
  SemVer canon **OR** legacy slug; the CLI help + docstring were updated and unit tests pin
  the broadening precisely (accepts `v0.1.23` and `my-feature-v1`; rejects `0.1.23`,
  `v0.1`, `v0.1.2.3`, `v1.2.x`). `backlog_new`/`bug_new` keep the strict slug. Closes bug
  `release-new-rejects-semver-but-doctor-requires-it` via its own Expected option (a): align
  the creator to the doctor canon, leaving the canon untouched.
- **H2 — pi settings `prompts` is an array.** `public/pi/settings.json` carried a bare
  string `"prompts": "prompts"`; PI's settings schema wants `prompts?: string[]`. Changed to
  `["prompts"]` and re-projected. This closes a deferred item explicitly recorded in the
  v0.1.21 CLOSURE.
- **H3 — v0.1.12 archived honestly.** `specs/releases/v0.1.12` was an abandoned/superseded
  release left live (its panel-auth-v2 work was superseded by the later panel-no-auth
  rework). It was `git mv`'d to `specs/_archive/releases/v0.1.12/` with an honest SUPERSEDED
  CLOSURE.md (undelivered tasks NOT back-filled to `[x]`).

## Tasks completed

| Task ID | Description | Commit |
|---------|-------------|--------|
| T-22-01 | Author SPEC/PLAN/TASKS (Status: Aprovado) | `<impl>` |
| T-22-02 | H1: `release_new` SemVer-or-slug + CLI help/docstring + unit tests; close bug | `1900c9b` |
| T-22-03 | H2: `public/pi/settings.json` `prompts` → `["prompts"]`; stage + install + doctor | `1900c9b` |
| T-22-04 | H3: archive `specs/releases/v0.1.12` (honest superseded CLOSURE + `git mv`) | `1900c9b` |
| T-22-05 | preflight green + review ladder (QA + code-review + architect + security) APPROVED | `<closure>` |
| T-22-06 | CLOSURE + archive v0.1.22 + gated push + PR + CI watched green | `<closure>` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Format + lint + strict-type + full tests | `dadaia ci preflight` | 4/4 PASS (ruff format/check; mypy --strict; pytest) |
| H1 contract pinned | `pytest tests/unit/features/spec_artifacts/test_new_artifacts.py` | 25 passed; SemVer accepted, slug accepted, dotted-non-SemVer rejected; `backlog_new`/`bug_new` slug-only unregressed |
| H1 canon coherence | code read | `new_artifacts._RELEASE_SEMVER_RE` byte-identical to `doctor.RELEASE_SEMVER_RE` (SPEC-DOC-027) and `scaffolder._RELEASE_SEMVER_RE` |
| H2 projection + privacy | `dadaia public doctor` | exit 0; `[ok] pi:settings.json`; `[ok] public-privacy` |
| SDD structural health | `dadaia specs doctor` | exit 0 (no new SPEC-DOC-027 warning from archived v0.1.12; H1 makes the canon both creatable and doctor-canonical) |
| QA gate | qa-engineer APPROVE | tests non-slop, no regression, H2/H3 verified; handoff on disk |
| Code review | code-reviewer APPROVE | 6-axis clean; one LOW DRY (3-copy regex) → backlog; handoff on disk |
| Architecture / anti-slop | software-architect APPROVE | root-cause + fidelity gates PASS; one MEDIUM (centralize canon) → backlog; handoff on disk |
| Security verdict (push gate) | security-reviewer APPROVE | keyed to the closing tip sha; validator broadening is input-only, no new surface |
| GitHub Actions CI | CI for the closing tip | watched to green |

## Drifts

### release-new-rejects-semver-but-doctor-requires-it (closed)

The creator/validator (`new_artifacts.release_new`) and the structural canon
(`doctor` SPEC-DOC-027) gave contradictory naming constraints. H1 aligns the creator to the
canon — the only direction that strengthens rather than weakens the contract. The bug file
is flipped Open→Closed with a resolution pointer. No defect left live.

### Latent residual (deferred, not introduced-as-new)

H1 closes the contradiction by adding a **third** independent copy of `^v\d+\.\d+\.\d+$`
(`doctor.py`, `scaffolder.py`, now `new_artifacts.py`) rather than one shared constant; the
scaffolder↔doctor duplication is pre-existing. SPEC-DOC-027 is not CI-gated, so a future
canon edit that misses a copy could silently re-open the contradiction. Flagged MEDIUM by
the architect and filed as backlog `centralize-release-semver-canon` (hoist the canon +
`is_release_semver()` into `core/specs_version.py`, all three modules import it, add a
single-source-of-truth test). Deliberately out of v0.1.22 scope per all three reviewers.

## Memory updates

None. v0.1.22 changes no product behavior, persona, lifecycle, or gate policy that a memory
atom asserts — it is a creator-validator coherence fix, a pi-config array fix, and a
release-archival. No atom created, updated, or deleted. (The H2 deferred item recorded in
the v0.1.21 CLOSURE is now resolved; that is captured here, not in an atom.)

## Notes

No change to the Python gate policy, the lease model, the harnesses, runtime behavior, or
any dependency. The follow-up `centralize-release-semver-canon` is the durable closure of
the H1 drift class and is PM-curated backlog, not part of this release.
