---
name: specs-doctor-errors-on-frozen-nonsemver-archives
status: Closed
severity: MEDIUM
reported: 2026-07-01
resolved: 2026-07-01
surface: dadaia specs doctor (SPEC-DOC-016) + tests/e2e/test_lifecycle_engine_smoke.py
session_id: null
---

**Resolution (v0.1.45, operator-directed):** bumped `RELEASE_VINTAGE_CUTOFF` in
`dadaia_workspace/features/specs/doctor.py` from `2026-05-17` to `2026-06-04`, grandfathering
the frozen pre-June-5 `_archive` sub-patch releases (created June 2-4) that predate the
SemVer-folder mandate's rollout. The `SPEC-DOC-016` rule keeps **hard-enforcing** for every
release created after the cutoff (v0.1.44 onward), so future non-SemVer folder names still
break CI. `specs doctor` on the repo returns 0 errors again and
`test_temp_workspace_lifecycle_engine_smoke` passes. The `test_semver_folder_name_non_semver_new_release_warns`
fixture Created date was moved to `2026-06-10` so it stays post-cutoff and continues to
assert enforcement. No FROZEN archive was renamed (immutable history preserved).

---

**Symptom:** `dadaia specs doctor --specs-dir <repo>/specs` reports **8 SPEC-DOC-016
ERRORS** (exit 1) on FROZEN `specs/_archive/releases/` folders whose historical names are
not 3-part SemVer: `v0.1.4.1`, `v0.1.4.2`, `v0.1.4.3`, `v0.1.4.3-report-retention`,
`v0.1.4.4`, `v0.1.4.5`, `v0.1.4.6`, `ctx-inject-v2-drift-fix-v1` (created 2026-06-02..04).
The e2e smoke test `test_temp_workspace_lifecycle_engine_smoke` asserts the repo's
`specs doctor` exit code is 0 and therefore **fails deterministically**.

**Repro:**
```
dadaia specs doctor --specs-dir repos/dadaia-workspace/specs   # -> 8 error(s), exit 1
python -m pytest tests/e2e/test_lifecycle_engine_smoke.py::test_temp_workspace_lifecycle_engine_smoke
```

**Pre-existing / not a regression:** the failure is byte-identical on `origin/main`
(v0.1.44 shipped), on `7264f6c4`, and on `feature/v0.1.45` — the test file, `_archive`
folders, and doctor code are unchanged across them. v0.1.44 and v0.1.43 both shipped with
this condition and their PR CI was GREEN, so the blocking CI pytest scope does not include
this e2e test (or skips it in the CI environment). The pre-push `dadaia ci preflight` also
passed for both releases with the same condition.

**Two coupled issues:**
1. **Doctor inconsistency.** Some legacy non-SemVer `_archive` names are grandfathered as
   SPEC-DOC-027 WARNINGS (e.g. `multiharness-engine-v0116`, `pi-fourth-harness-v1`), while
   the `v0.1.4.x` / `ctx-inject-*` names are hard SPEC-DOC-016 ERRORS. FROZEN archives are
   historical and should be treated consistently — either all grandfathered to WARNING, or
   a one-time rename decision.
2. **CI-invisible red test.** `test_temp_workspace_lifecycle_engine_smoke` fails on `main`
   yet CI stays green — a real coverage gap: a deterministically-failing e2e test is not
   gating merges.

**Expected:** either (a) SPEC-DOC-016 grandfathers pre-existing FROZEN `_archive` names
(as SPEC-DOC-027 already does for some), so `specs doctor` on the repo is 0-errors; or
(b) a governance decision to rename the 8 frozen archive folders to canonical SemVer, with
the smoke test then green; and the CI pytest scope is reconciled so this test's status is
truthful in CI.

**Notes:** out of scope for the v0.1.45 panel release — filed as pre-existing debt. No
operator-local paths/secrets. Needs an archive-naming-remediation release (touches FROZEN
`_archive`, so a deliberate governance decision, not a mechanical fix).
