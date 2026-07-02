---
name: release-new-rejects-semver-but-doctor-requires-it
status: Closed
severity: MEDIUM
reported: 2026-06-25
surface: dadaia release new (release-id validator) vs dadaia specs doctor (SPEC-DOC-027 naming canon)
session_id: null
---

**Resolution (v0.1.22, fix option a):** `release_new`
(`features/spec_artifacts/new_artifacts.py`) now validates the release id via
`_is_valid_release_id` = SemVer canon `^v\d+\.\d+\.\d+$` (mirrors
`scaffolder._RELEASE_SEMVER_RE` / SPEC-DOC-027) **OR** the legacy slug `^[a-z][a-z0-9-]+$`.
`dadaia release new v0.1.23` now succeeds; the doctor canon and backlog/bug slug validators
are unchanged. The CLI help + docstring updated; unit tests pin SemVer-accepted /
slug-accepted / dotted-non-SemVer-rejected (e.g. `0.1.23`, `v0.1`, `v0.1.2.3` still reject).
The naming contract is now coherent: SemVer `vX.Y.Z` is both creatable and doctor-canonical.

**Symptom:** Two tooling rules give contradictory naming constraints for a release directory:
- `dadaia release new <id>` rejects any id containing a dot — the id validator is
  `^[a-z][a-z0-9-]+$` (no dots), so `v0.1.16` is refused at creation time.
- `dadaia specs doctor` SPEC-DOC-027 (`features/specs/doctor.py:1177`) REQUIRES a release
  dir to match `^v<MAJOR>.<MINOR>.<PATCH>$` (dots mandatory) and emits an **ERROR** for a
  non-conforming dir that is **live in `specs/releases/`** with a SPEC `Created:` date on/after
  `RELEASE_SEMVER_CUTOFF` (2026-06-01).

There is no name that satisfies both: SemVer is blocked at creation, descriptive slugs are
flagged by the doctor. This forced a slug workaround for every recent release
(`multiharness-engine-v0116`, `pi-fourth-harness-v1`, `pi-operational-two-layer-v1`).

**Repro:**
1. `dadaia release new v0.1.18 …` → rejected (dot in id).
2. Create the release as a slug instead (e.g. `pi-operational-two-layer-v1`), SPEC `Created:`
   ≥ 2026-06-01, leave it live in `specs/releases/`.
3. `dadaia specs doctor --specs-dir specs` → `[ERR] SPEC-DOC-027: Release dir … does not
   follow the naming canon ^v<MAJOR>.<MINOR>.<PATCH>$ — rename it`.

**Expected:** One coherent naming contract. Either (a) `release new` accepts the SemVer
`v<MAJOR>.<MINOR>.<PATCH>` form the doctor canon mandates, or (b) the doctor canon recognises
the documented descriptive-slug convention the CLI actually produces (e.g. an allowlisted
`<slug>-vN` pattern for live dirs, not only the `_archive` legacy allowlist).

**Notes / impact (not blocking this release):**
- The error is NOT CI-gated (no `specs doctor` job in CI) and downgrades to a WARNING once the
  release dir is archived (`is_live=False`), so every session release dodged it by being
  doctored only post-archive. The live-phase ERROR is therefore transient but real.
- Accumulating effect: archived slug dirs that are not on the `_archive` legacy allowlist
  (`RELEASE_NAMING_LEGACY_ALLOWLIST`) remain permanent SPEC-DOC-027 **WARNINGs** — slow drift
  the operator should resolve with a naming-policy decision (rename history, extend the
  allowlist convention, or fix `release new` to mint SemVer).
- Root-cause fix belongs in a release-tooling release, not in `pi-operational-two-layer-v1`
  (scope = make PI operational). Filed here for the operator/project-manager to schedule.
