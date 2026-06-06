# TASKS: v0.1.5 rc-2 — propagation-pair + semaphore-liveness + panel-verify

**Status:** Aprovado
**Release ID:** v0.1.5
**Segment:** rc-2
**Owner:** product-engineer
**Created:** 2026-06-06

Markers: `[ ]` OPEN · `[-]` IN PROGRESS · `[x]` DONE.
At most one `[-]` active per owner at a time (unless disjoint write sets are declared below).
Execution order: G2 → G3 → G1 → SHIP.

---

## Group G2 — Propagation pair

### T-PROP-01 — install hash-compare overwrite

- **Status:** [-]
- **Owner:** software-engineer-python
- **Write set:** `dadaia_workspace/features/public_assets/public_assets.py`, `tests/unit/features/public_assets/test_install_hash_compare.py`
- **Preconditions:** none (independent of other G2 tasks at implementation level)
- **Done criterion:**
  1. `dadaia public install --target all` overwrites a projected file when `sha256(staged) != sha256(projected)`.
  2. `dadaia public install --target all` is a no-op when `sha256(staged) == sha256(projected)`.
  3. `dadaia public install --force --target all` clobbers regardless of hash match (existing semantics preserved).
  4. Three new unit tests pass: `test_update_propagates_without_force`, `test_noop_when_hashes_match`, `test_force_still_clobbers_locally_modified`.
- **Parallelism:** disjoint write set from T-PROP-02 (same source file but different functions/lines; see note below) — prefer sequential commits to avoid conflicts on `public_assets.py`.
- **Commit convention:** `fix(public-assets): install overwrites on hash mismatch (T-PROP-01)`

### T-PROP-02 — doctor staging-vs-projected check

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Preconditions:** T-PROP-01 committed (staging SHA logic must be stable before doctor reads it)
- **Write set:** `dadaia_workspace/features/public_assets/public_assets.py` (doctor delegate), `tests/unit/features/public_assets/test_doctor_projected_drift.py`
- **Done criterion:**
  1. `dadaia public doctor` exits non-zero and emits `[drift] <path>` for every staged asset whose SHA256 differs from the projected file.
  2. `dadaia public doctor` exits 0 and emits `[ok]` for every asset on a clean workspace.
  3. Three new unit tests pass: `test_clean_tree_exits_0`, `test_projected_drift_exits_nonzero`, `test_staged_but_not_installed_exits_nonzero`.
- **Commit convention:** `fix(public-assets): doctor adds staging↔projected drift check (T-PROP-02)`

### T-PROP-03 — update dadaia-workspace-dev-guardrail rule

- **Status:** [ ]
- **Owner:** ai-engineer
- **Preconditions:** T-PROP-01 and T-PROP-02 committed (rule must describe the fixed behavior accurately)
- **Write set:** `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md`; bug frontmatter: `specs/bugs/install-skips-existing-files.md`, `specs/bugs/doctor-blind-to-projected-drift.md`
- **Done criterion:**
  1. "Correct edit workflow" in the guardrail rule describes plain `install` as the propagation step (no `--force` needed for updates).
  2. `dadaia-workspace-dev-guardrail.md` accurately describes the `[drift]` / `[ok]` doctor signals including the new staging↔projected check.
  3. Both bug files have `resolved_in: v0.1.5/rc-2` added to frontmatter.
  4. `dadaia public stage && dadaia public install --force --target all && dadaia public doctor` exits 0.
- **Commit convention:** `docs(rules): update dev-guardrail for fixed install+doctor behavior (T-PROP-03)`

---

## Group G3 — Semaphore liveness

### T-SEMA-01 — _is_stale liveness check + acquire reclaim

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Preconditions:** none (independent of G2)
- **Write set:** `dadaia_workspace/features/spec_context/semaphore.py`, `tests/unit/features/spec_context/test_semaphore_liveness.py`
- **Done criterion:**
  1. `_is_stale` returns `True` when the owner's PID is not alive (checked via `os.kill(pid, 0)`).
  2. `_is_stale` returns `True` when the owner's session file does not exist.
  3. `_is_stale` still returns `True` on TTL expiry (existing behavior preserved).
  4. `_is_stale` returns `False` for a live holder with a recent heartbeat.
  5. `acquire_context_semaphore` silently reclaims a stale-by-liveness semaphore (log audit entry, then acquire).
  6. Four unit tests pass: `test_dead_pid_reclaims_immediately`, `test_missing_session_reclaims_immediately`, `test_live_holder_still_blocks`, `test_ttl_still_reclaims_after_expiry`.
- **Commit convention:** `fix(semaphore): liveness reclaim on dead PID / missing session (T-SEMA-01)`

### T-SEMA-02 — doctor SEM-1 invariant + --fix

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Preconditions:** T-SEMA-01 committed (doctor reuses the liveness logic from semaphore.py)
- **Write set:** `dadaia_workspace/features/spec_context/doctor.py`, `tests/unit/features/spec_context/test_doctor_semaphore_invariant.py`
- **Done criterion:**
  1. `dadaia doctor` (or `dadaia specs doctor`) detects an orphaned `ctx_locks/*.semaphore.json` (context not in alive spec_contexts.json) and emits `[orphan-semaphore] <path>`.
  2. `dadaia doctor` detects a stale-by-liveness semaphore and emits `[stale-semaphore] <path>`.
  3. `dadaia doctor --fix` deletes flagged semaphores and appends an entry to `.dadaia/states/audit/semaphore-reclaims.jsonl`.
  4. Four unit tests pass: `test_clean_state_no_warning`, `test_orphan_semaphore_flagged`, `test_stale_semaphore_flagged`, `test_fix_reclaims_and_logs`.
  5. Bug `specs/bugs/semaphore-no-liveness-reclaim.md` has `resolved_in: v0.1.5/rc-2` added to frontmatter.
- **Commit convention:** `fix(doctor): SEM-1 semaphore invariant + --fix reclaim (T-SEMA-02)`

---

## Group G1 — Panel reports verify + invariant

### T-PANEL-01 — qa verify of commit 028ffd5

- **Status:** [ ]
- **Owner:** qa-engineer
- **Preconditions:** G2 and G3 committed (verify against stable branch state)
- **Write set:** `specs/backlog/candidates.md` (add `resolved_in` annotation to BUG-PANEL-REPORTS-01 if verified); `.dadaia/handoff/dadaia-workspace/<UTC>-qa-engineer-panel-reports-verify.handoff.json`
- **Done criterion:**
  1. All four symptom paths (RC#1-4) and the 224→2 regression are reproduced and confirmed fixed against current `feature/0.1.5`.
  2. If all fixed: emit handoff with `verdict: APPROVED`; annotate `BUG-PANEL-REPORTS-01` entry in candidates.md with `resolved_in: v0.1.5/rc-2`.
  3. If any residual gap: emit handoff with `verdict: REJECTED` and list specific gaps; T-PANEL-02 owner addresses gaps before T-PANEL-01 re-runs.
- **Commit convention:** `test(panel): qa verify BUG-PANEL-REPORTS-01 resolved (T-PANEL-01)` (only if bug confirmed fixed)

### T-PANEL-02 — dadaia reports doctor RPT-1 invariant + optional dedup polish

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Preconditions:** T-PANEL-01 completed (scope depends on qa verdict: full scope if gap found, invariant-only if no gap)
- **Write set:** `dadaia_workspace/features/specs/doctor.py` or new `dadaia_workspace/features/panel/reports_doctor.py`; `tests/unit/features/panel/test_reports_doctor_invariant.py`; (optionally) `dadaia_workspace/features/panel/views/api.py` if T-PANEL-01 finds a gap
- **Done criterion:**
  1. RPT-1 invariant detects any `.handoff.json` whose `artifact.path` points at a non-HTML file or a missing file, and emits `[dangling-artifact-path] <sidecar> → <artifact.path>`.
  2. A sidecar-less HTML report does NOT trigger RPT-1 (sidecar-less reports are valid).
  3. Three unit tests pass: `test_invariant_clean_passes`, `test_dangling_artifact_path_flagged`, `test_missing_html_sidecar_not_flagged`.
  4. If T-PANEL-01 reported a residual de-dup gap: the gap is closed in `api.py` and qa-engineer re-verifies.
- **Commit convention:** `fix(reports-doctor): RPT-1 invariant for dangling artifact.path (T-PANEL-02)`

---

## SHIP gate

### T-SHIP-01 — Pre-ship CI gate

- **Status:** [ ]
- **Owner:** software-engineer-python (or devops-engineer)
- **Preconditions:** all G1/G2/G3 tasks `[x]`
- **Write set:** none (validation only; update TASKS.md marker)
- **Done criterion:**
  1. `ruff format --check dadaia_workspace/` exits 0.
  2. `ruff check dadaia_workspace/` exits 0.
  3. `mypy --strict dadaia_workspace` exits 0 with zero errors.
  4. `pytest -p no:cacheprovider` passes all tests.
  5. Evidence (stdout snippet or commit SHA) captured in handoff or commit message.
- **Commit convention:** `chore(ci): rc-2 pre-ship CI gate green (T-SHIP-01)`

### T-SHIP-02 — QA review

- **Status:** [ ]
- **Owner:** qa-engineer
- **Preconditions:** T-SHIP-01 `[x]`
- **Write set:** `.dadaia/handoff/dadaia-workspace/<UTC>-qa-engineer-rc-2-review.handoff.json`
- **Done criterion:** handoff emitted with `verdict: APPROVED`. REJECTED blocks the gate.
- **Commit convention:** n/a (handoff file only)

### T-SHIP-03 — Code review

- **Status:** [ ]
- **Owner:** code-reviewer
- **Preconditions:** T-SHIP-01 `[x]`
- **Write set:** `.dadaia/handoff/dadaia-workspace/<UTC>-code-reviewer-rc-2-review.handoff.json`
- **Done criterion:** handoff emitted with `verdict: APPROVED`. REJECTED blocks the gate.
- **Commit convention:** n/a (handoff file only)

### T-SHIP-04 — Security review

- **Status:** [ ]
- **Owner:** security-reviewer
- **Preconditions:** T-SHIP-01 `[x]`
- **Write set:** `.dadaia/handoff/dadaia-workspace/<UTC>-security-reviewer-rc-2-review.handoff.json`
- **Done criterion:** handoff emitted with `verdict: APPROVED`. REJECTED blocks the gate.
- **Commit convention:** n/a (handoff file only)

### T-SHIP-05 — CLOSURE

- **Status:** [ ]
- **Owner:** product-engineer
- **Preconditions:** T-SHIP-02, T-SHIP-03, T-SHIP-04 all `[x]` with `verdict: APPROVED`
- **Write set:** `specs/releases/v0.1.5/rc-2/CLOSURE.md`; memory atoms in `specs/memory/` (CLOSURE phase only); `specs/releases/ACTIVE.md`
- **Done criterion:**
  1. `specs/releases/v0.1.5/rc-2/CLOSURE.md` written with summary, tasks, validations, drifts, memory updates, backlog returns, archive decision.
  2. Affected memory atoms updated.
  3. `ACTIVE.md` updated (phase → ARCHIVED or release → next).
  4. Deploy remains operator-gated — NO push/PR/merge/tag performed by this task.
- **Commit convention:** `docs(closure): v0.1.5/rc-2 CLOSURE (T-SHIP-05)`

---

## Disjoint write set declaration

The following tasks may run in parallel within their group if the operator chooses, because their write sets are disjoint:

- T-PROP-01 and T-SEMA-01 — different modules (`public_assets.py` vs `semaphore.py`).
- T-SHIP-02, T-SHIP-03, T-SHIP-04 — different handoff files; no source code changes.

T-PROP-02 must follow T-PROP-01 (same source file, sequential commits required).
T-PROP-03 must follow T-PROP-01 + T-PROP-02 (describes fixed behavior).
T-SEMA-02 must follow T-SEMA-01 (reuses liveness logic).
T-PANEL-02 must follow T-PANEL-01 (scope determined by qa verdict).
