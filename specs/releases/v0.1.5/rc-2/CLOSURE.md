# Closure: Release — v0.1.5 / rc-2

> **Status:** Aprovado
> **Release ID:** v0.1.5
> **Segment:** rc-2
> **Owner:** product-engineer
> **Closed:** 2026-06-06

## Summary

rc-2 closes three bugs observed during rc-1 implementation and verifies a panel fix that
shipped between segments, extending v0.1.5 on the same `feature/0.1.5` branch. A single
v0.1.5 tag (when eventually deployed) will cover rc-1 + rc-2; rc-1 is superseded by rc-2
for CLOSURE purposes.

**G2 — Propagation pair (HIGH):** `dadaia public install` now performs a content-hash
comparison before skipping an existing projected file. When the staged SHA256 differs from
the projected file's SHA256, the file is overwritten without requiring `--force`. `dadaia
public doctor` gained a third comparison pass that detects staging-vs-projected drift and
emits `[drift]` with a non-zero exit code for any mismatch. The `dadaia-workspace-dev-guardrail`
rule was updated to reflect the corrected workflow — plain `install` now propagates updates;
`--force` is reserved for locally-divergent projection repair. Both G2 bugs
(`install-skips-existing-files`, `doctor-blind-to-projected-drift`) are formally closed.

**G3 — Semaphore liveness reclaim (MEDIUM):** `semaphore.py:_is_stale` now checks PID
liveness (`os.kill(pid, 0)`) and session-file existence in addition to TTL expiry.
`acquire_context_semaphore` silently reclaims a stale-by-liveness semaphore (log audit
entry, then acquire) so a new bind behind a dead holder succeeds immediately without waiting
the full 300 s TTL. `dadaia doctor` gained a new invariant family `SEM-1` that scans
`ctx_locks/*.semaphore.json` for orphan and stale semaphores and emits `[orphan-semaphore]`
/ `[stale-semaphore]` diagnostics; `dadaia doctor --fix` reclaims flagged semaphores and
appends audit entries to `.dadaia/states/audit/semaphore-reclaims.jsonl`. Bug
`semaphore-no-liveness-reclaim` is formally closed.

**G1 — Panel reports verify + invariant (HIGH):** `qa-engineer` confirmed that commit
`028ffd5` resolves all four original symptom paths (RC#1-4) and the 224-to-2 regression in
the Reports panel tab. `dadaia reports doctor` (via `features/panel/reports_doctor.py`)
gained the `RPT-1` invariant that flags any `.handoff.json` whose `artifact.path` points at
a non-HTML file or a missing file as `[dangling-artifact-path]`. `BUG-PANEL-REPORTS-01` is
closed. No de-dup gap was found, so T-PANEL-02 scope was limited to the RPT-1 invariant.

The full CI suite ran clean: **2290 tests passed**, ruff format+check and mypy --strict all
exit 0. The review trio (qa-engineer, code-reviewer, security-reviewer) returned unanimous
APPROVED for the commit range `3deed20..a978d1d`. CWE-22 remediation confirmed at both
path-construction sites in `semaphore.py` (commit `2a6a766`).

**DEPLOYMENT EXPLICITLY HELD BY OPERATOR.** No push, no PR, no merge, no `git tag`, no
PyPI publish, no live-instance propagation has been performed. rc-1 is also superseded into
this single pending v0.1.5 publish. All rc-2 commits live locally on `feature/0.1.5`. The
operator will initiate deployment as a deliberate act when ready.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-PROP-01 | install hash-compare overwrite — no `--force` needed for content-driven update | `feature/0.1.5` (range `3deed20..a978d1d`) |
| T-PROP-02 | doctor staging↔projected check — non-zero exit on drift, `[drift]` signal | `feature/0.1.5` |
| T-PROP-03 | update `dadaia-workspace-dev-guardrail` rule + bug frontmatter resolved | `feature/0.1.5` |
| T-SEMA-01 | `_is_stale` PID liveness + session-file check; `acquire_context_semaphore` reclaim | `2a6a766` (CWE-22 fix committed here) |
| T-SEMA-02 | doctor `SEM-1` invariant + `--fix` reclaim with audit log | `feature/0.1.5` |
| T-PANEL-01 | qa-engineer verification of commit `028ffd5` — all RC#1-4 fixed, bug closed | `52493c8` (test commit evidence) |
| T-PANEL-02 | `RPT-1` invariant (`reports_doctor.py`) + 3 unit tests | `feature/0.1.5` |
| T-SHIP-01 | Pre-ship CI gate green: ruff + mypy --strict + pytest 2290 passed | `a978d1d` (final reviewed commit) |
| T-SHIP-02 | QA review — qa-engineer APPROVED | `.dadaia/handoff/dadaia-workspace/2026-06-06T025133Z-qa-engineer-rc2.handoff.json` |
| T-SHIP-03 | Code review — code-reviewer APPROVED | `.dadaia/handoff/dadaia-workspace/2026-06-06T030313Z-code-reviewer-rc2.handoff.json` |
| T-SHIP-04 | Security review — security-reviewer APPROVED | `.dadaia/handoff/dadaia-workspace/2026-06-06T030500Z-security-reviewer-rc2.handoff.json` |

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| ruff format check passes | `ruff format --check dadaia_workspace/` | Exit 0 — qa-engineer handoff `2026-06-06T025133Z-qa-engineer-rc2.handoff.json` (`tests_passed: 2290`) |
| ruff lint passes | `ruff check dadaia_workspace/` | Exit 0 — same handoff |
| mypy strict passes | `mypy --strict dadaia_workspace` | Zero errors — same handoff |
| pytest full suite | `pytest -p no:cacheprovider` | 2290 passed, 2 skipped — qa-engineer handoff metrics |
| install overwrites on hash mismatch (no `--force`) | `dadaia public install --target all` after source edit | T-PROP-01 acceptance: `test_update_propagates_without_force`, `test_noop_when_hashes_match`, `test_force_still_clobbers_locally_modified` green |
| doctor exits non-zero on staging↔projected drift | `dadaia public doctor` with stale projection | T-PROP-02 acceptance: `test_projected_drift_exits_nonzero`, `test_staged_but_not_installed_exits_nonzero` green |
| semaphore reclaims dead-PID holder immediately | `dadaia context bind` behind dead holder | T-SEMA-01 acceptance: `test_dead_pid_reclaims_immediately`, `test_missing_session_reclaims_immediately` green |
| doctor SEM-1 detects orphan/stale semaphore; `--fix` reclaims | `dadaia doctor` with stale semaphore | T-SEMA-02 acceptance: `test_orphan_semaphore_flagged`, `test_stale_semaphore_flagged`, `test_fix_reclaims_and_logs` green |
| RPT-1 flags dangling artifact.path | `dadaia reports doctor` (or `dadaia specs doctor`) | T-PANEL-02 acceptance: `test_dangling_artifact_path_flagged` green |
| Panel RC#1-4 and 224-to-2 regression confirmed fixed | manual + code-inspection | commit `52493c8` + qa-engineer handoff `2026-06-06T025133Z-qa-engineer-rc2.handoff.json` verdict: APPROVED |
| CWE-22 remediation at semaphore path-construction sites | code inspection of `semaphore.py` | `security-reviewer` handoff `2026-06-06T030500Z-security-reviewer-rc2.handoff.json` — commit `2a6a766` |
| qa-engineer verdict | handoff JSON | `verdict: APPROVED` — `.dadaia/handoff/dadaia-workspace/2026-06-06T025133Z-qa-engineer-rc2.handoff.json` |
| code-reviewer verdict | handoff JSON | `verdict: APPROVED` — `.dadaia/handoff/dadaia-workspace/2026-06-06T030313Z-code-reviewer-rc2.handoff.json` |
| security-reviewer verdict | handoff JSON | `verdict: APPROVED` — `.dadaia/handoff/dadaia-workspace/2026-06-06T030500Z-security-reviewer-rc2.handoff.json` |

---

## Review trio verdicts (rc-2)

**qa-engineer** — `2026-06-06T025133Z-qa-engineer-rc2.handoff.json`
- `verdict: APPROVED`
- 2290 tests passed, 2 skipped; 45 rc-2-specific tests verified; 3 work-streams; 7 tasks; 0 blocking gaps.
- Notable findings: T-PANEL-01 standalone handoff not emitted (prior session stalled) — subsumed by this ship-gate review. XPASS on `test_pid_zero_documented_as_xfail` (non-regression, correctly xfail-marked).

**code-reviewer** — `2026-06-06T030313Z-code-reviewer-rc2.handoff.json`
- `verdict: APPROVED`
- 18 files changed, 2348 lines added, 83 removed, 16 commits reviewed. Zero CRITICAL or HIGH findings.
- 1 MEDIUM (advisory only: path-traversal guard ordering in `ReportsDoctor` — `resolve()+relative_to()` containment is authoritative and sound).
- 3 LOW (code-quality: `_stub_sha` recomputed in inner closure; staleness reason duplicated in `acquire`; `_src_sha` comment inaccurate). Non-blocking.

**security-reviewer** — `2026-06-06T030500Z-security-reviewer-rc2.handoff.json`
- `verdict: APPROVED`
- Zero CRITICAL, HIGH, or MEDIUM findings. Zero secrets detected. Zero CVE deltas.
- CWE-22 remediation confirmed at both path-construction sites in `semaphore.py` commit `2a6a766`.
- 1 LOW (pre-existing, predates rc-2): unsanitized `session_id` in `doctor.py` LOCK-orphan path check at lines 622 and 831 — same threat model as the now-remediated semaphore site; requires local write access to `.dadaia/ctx_locks/`. Suggested for v0.1.6 hardening.

---

## Bugs resolved

| Bug slug | Severity | Resolved by | Tasks |
|----------|----------|-------------|-------|
| `install-skips-existing-files` | HIGH | v0.1.5/rc-2 | T-PROP-01, T-PROP-02, T-PROP-03 |
| `doctor-blind-to-projected-drift` | HIGH | v0.1.5/rc-2 | T-PROP-01, T-PROP-02, T-PROP-03 |
| `semaphore-no-liveness-reclaim` | MEDIUM | v0.1.5/rc-2 | T-SEMA-01, T-SEMA-02 |

`BUG-PANEL-REPORTS-01` (tracked in `specs/backlog/candidates.md`) was additionally confirmed
closed: commit `028ffd5` resolved all four original RC symptom paths.

---

## Residual advisories (non-blocking)

The following items were raised by the review trio and are recorded here for traceability.
None block the rc-2 ship gate.

- **MEDIUM (code-reviewer):** Path-traversal guard ordering in `ReportsDoctor._check_rpt1_path` — parts-based `'..'` pre-check is defence-in-depth; `resolve()+relative_to()` is the authoritative gate. Advisory: simplify by removing the pre-check. Not blocking.
- **LOW (code-reviewer):** `_write_pair` inner closure recomputes `_stub_sha` on every iteration; peer functions hoist it. Hoist to match pattern. Not blocking.
- **LOW (code-reviewer):** Staleness reason rebuilt independently in `acquire_context_semaphore` after `_is_stale()` call — duplicated logic. Consider returning a named reason from `_is_stale`. Not blocking.
- **LOW (code-reviewer):** `_src_sha` variable comment inaccurate. Not blocking.
- **LOW (security-reviewer):** Pre-existing unsanitized `session_id` in `doctor.py` LOCK-orphan path (lines 622 and 831) — suggested for v0.1.6 hardening batch.

---

## Drifts

### panel-reports-tab-pre-existing

**Description:** `BUG-PANEL-REPORTS-01` (224-to-2 regression + RC#1-4 on Reports tab) was
filed during rc-1 implementation after commit `028ffd5` had already addressed it on
`feature/0.1.5`. The fix pre-dated the formal bug and was never formally verified until
rc-2 T-PANEL-01.

**Resolution:** qa-engineer verified all four RC paths and the regression against current
`feature/0.1.5`. Code inspection confirmed api.py:910-944 addresses all paths. Bug closed.
RPT-1 invariant added as a structural guard to prevent recurrence.

**Memory updates:** `specs/memory/product/panel.md` — Reports tab `source` semantics
updated to reflect that reports are indexed by both `*.html` direct rglob and `.handoff.json`
sidecars (HTML-first); `RPT-1` invariant added to specs-doctor dependency note.

### t-panel-01-handoff-not-emitted

**Description:** The qa-engineer session that executed T-PANEL-01 stalled before emitting
its standalone handoff. No `T-PANEL-01` handoff.json exists in `.dadaia/handoff/dadaia-workspace/`.

**Resolution:** The verification evidence is documented in commit `52493c8`
(`test(panel): qa verify BUG-PANEL-REPORTS-01 resolved (T-PANEL-01)`). The T-SHIP-02
ship-gate review (qa-engineer handoff `2026-06-06T025133Z`) formally subsumes the
T-PANEL-01 verification with unambiguous evidence. No blocking gap.

**Memory updates:** None — process drift only; no product state change.

---

## Memory updates

- `specs/memory/product/public-asset-distribution.md` — updated `Diferencial` and
  `Dependências` sections to reflect that `dadaia public install` now performs hash-compare
  overwrite (no `--force` for legitimate updates) and `dadaia public doctor` now detects
  staging-vs-projected drift with `[drift]` signal and non-zero exit. `last_updated`
  bumped to `2026-06-06`; `release_origin` updated to `v0.1.5`.
- `specs/memory/product/context-management.md` — Lock 4 (per-context semaphore) table row
  updated: limitation note `semaphore-no-liveness-reclaim` removed (bug is closed); row now
  describes PID-liveness + session-file check as active reclaim paths alongside TTL. Doctor
  invariants paragraph updated to include SEM-1 (`[orphan-semaphore]`, `[stale-semaphore]`,
  `dadaia doctor --fix` for semaphore surface). `last_updated` bumped to `2026-06-06`.
- `specs/memory/product/workspace-doctor.md` — added `SEM-1` invariant family to the
  invariants table (orphan semaphore flagged, stale-by-liveness semaphore flagged, `--fix`
  reclaims and logs to `semaphore-reclaims.jsonl`). `last_updated` bumped to `2026-06-06`.
- `specs/memory/product/panel.md` — Reports tab entry updated: Reports are indexed HTML-first
  (direct rglob `*.html` + sidecar enrichment from `.dadaia/handoff/` and `.dadaia/reports/`);
  sidecar-less reports are now visible. `RPT-1` invariant reference added to the
  `specs-doctor` dependency note. `last_updated` bumped to `2026-06-06`.
- `specs/memory/architecture.md` — no change required: G2/G3/G1 changes are within existing
  layers (infrastructure/public_assets, features/spec_context, features/panel); no new layer
  or module introduced.
- `specs/memory/tech-stack.md` — no change: no new dependencies added in rc-2.
- `specs/memory/product/index.md` — catalog order and entries unchanged: no new production
  feature added or removed in rc-2.

---

## Backlog returns

The security-reviewer identified a pre-existing low-severity issue that security recommends
addressing in the next release:

- `specs/backlog/candidates.md` ← `doctor-session-id-path-sanitization`: unsanitized
  `session_id` in `doctor.py` LOCK-orphan path check at lines 622 and 831 (pre-existing,
  predates rc-2). Apply `_safe_session_filename()` (or equivalent allowlist filter) to
  session_id reads. Suggested severity LOW; recommended for v0.1.6 batch.

**Note:** The D5 backlog-ownership gate blocks non-project-manager writes to
`specs/backlog/**`. The above backlog entry is recorded here in CLOSURE.md for the
product-engineer handoff to project-manager. PM is responsible for authoring the formal
backlog candidate entry in `specs/backlog/candidates.md`.

---

## Archive decision

**MOVE** — segment directory `specs/releases/v0.1.5/rc-2/` to be moved to
`specs/_archive/releases/v0.1.5/rc-2/` via `git mv`. The flat release directory
`specs/releases/v0.1.5/` (including rc-1 and rc-2 subdirectories) will move to
`specs/_archive/releases/v0.1.5/` once the operator triggers deployment.

Archive is deferred along with deployment. ACTIVE.md will be updated to `release: none`
(or the next active release) when the operator authorizes archiving.

Command (to be run by devops-engineer or operator when ready):
```
git mv specs/releases/v0.1.5 specs/_archive/releases/v0.1.5
```
