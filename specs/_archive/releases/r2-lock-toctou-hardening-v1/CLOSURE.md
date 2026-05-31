# Closure: Release — r2-lock-toctou-hardening-v1

> **Status:** Aprovado
> **Release ID:** r2-lock-toctou-hardening-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-31

## Summary

This patch release closes three pre-existing defects in the R2 locking layer
(`spec-context-session-locks-v1`) that were surfaced by the barrier-based race tests written
during R3 (`panel-kanban-v1`). All three defects live inside two source files and share a
common theme: the Impl-XOR-Review invariant could be broken or produce wrong exceptions under
concurrent load.

**Defect 1** (STALE-blocks-review): `check_impl_xor_review` now treats `STALE` the same as
`HELD` in the REVIEW branch, blocking review until the stale implementation lock is explicitly
reclaimed or released. A STALE lock indicates a session that likely died mid-work; allowing
review to proceed over a half-done implementation would violate the Impl-XOR-Review invariant.

**Defect 2** (TOCTOU atomicity): `context.py bind()` now wraps both the XOR check and the
subsequent create/write call inside a single `workspace_lock()` critical section — for the
IMPLEMENTATION path (non-force) and for the REVIEW path alike. The race window between
`check_impl_xor_review` and the actual lock acquisition/session write is closed.

**Defect 3** (shared `.tmp` collision): `create_impl_lock`, `reclaim_impl_lock`, and
`renew_heartbeat` each use a per-call `uuid4()`-based tmp filename instead of the shared
`lock_path.with_suffix(".tmp")`. Concurrent losers now raise `LockHeldError` deterministically
rather than a confusing `FileNotFoundError` from `os.replace`.

The three K-QA-RACE acceptance tests (AC-3.5, AC-3.7, AC-3.8) that previously documented
the buggy behaviour were rewritten to assert the hardened semantics. The full test suite
passed at 2458 tests (0 failed, 88.80% coverage), all race tests pass across multiple random
seeds, and no `time.sleep` remains in the race-test file. QA declared the gate APPROVED.

No session-file schema version was bumped, no public API changed, and no PyPI publish was
triggered — this is a pure patch-level hardening in an unreleased library.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-1 | Fix `locking.py` (STALE policy + per-call UUID tmp × 3) and `context.py bind()` (atomic TOCTOU wrapper for impl + review paths) | `d8a414b` |
| T-2 | Rewrite AC-3.5 / AC-3.7 / AC-3.8 in `test_kanban_lock_conflict.py` to assert hardened behaviour (barrier-based, no `time.sleep`) | `d8a414b` |
| T-3 | Full-suite + gates validation: ruff, mypy --strict, pytest 2458/0/88.80%, grep no-sleep gate, QA handoff `verdict: APPROVED` | `0edaa4d` |

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| ruff lint clean | `poetry run ruff check dadaia_workspace/ tests/` | Exit 0; 0 errors |
| mypy --strict clean (161 files) | `poetry run mypy --strict dadaia_workspace/` | Exit 0; 0 errors; 161 files checked |
| Full pytest suite green | `poetry run pytest -p randomly tests/` | 2458 passed, 0 failed, 1 skipped, 1 xpassed; 88.80% coverage (≥80 gate) |
| AC-3.5 pass — STALE blocks review | `pytest test_impl_stale_blocks_review_until_reclaim` | Passes across 5 random seeds |
| AC-3.7 pass — XOR race exactly one winner | `pytest test_r_impl_xor_review_only_one_binds` | Passes across 5 random seeds |
| AC-3.8 pass — two-impl race loser raises LockHeldError | `pytest test_r_two_impl_sessions_race` | Passes across 5 random seeds; `FileNotFoundError` never raised |
| AC-3.1 / 3.2 / 3.3 / 3.4 / 3.6 no regression | `pytest tests/unit/features/spec_context/test_kanban_lock_conflict.py` | All 5 unchanged tests still pass |
| No time.sleep in race tests | `grep -r 'time\.sleep' tests/unit/features/spec_context/test_kanban_lock_conflict.py` | No output (clean) |
| specs doctor exit 0 | `dadaia specs doctor` | Exit 0; benign STRUCT-4 YAML-absent WARN only (expected) |
| public doctor exit 0 | `dadaia public doctor` | Exit 0 |
| QA handoff APPROVED | `dadaia reports validate .dadaia/reports/dadaia-workspace/qa-engineer/2026-05-31T172000Z-r2-lock-toctou-hardening-v1-qa.handoff.json` | `verdict: APPROVED`; `dadaia reports validate` exit 0 |

---

## Drifts

### t3-marker-self-committed-by-qa-agent

**Description:** The T-3 task marker flip (`[ ]` → `[x]` in TASKS.md) was self-committed by
the `qa-engineer` agent (commit `0edaa4d`, TASKS.md only). Under the standard protocol,
marker flips for the final task are orchestrator-owned. The qa-engineer committed the marker
as part of its QA gate workflow.

**Resolution:** Benign. The commit content is exactly what it should be — only the TASKS.md
marker changed, no source or test files were touched in that commit. The TASKS.md state is
correct and consistent with all three tasks `[x]`. No re-do required.

**Memory updates:** None — this was a process deviation, not a product behaviour change.

### patch-no-version-bump

**Description:** This is a patch-level fix to an unreleased library. The SPEC explicitly
stated no `pyproject.toml` version bump, no new session-file schema version, and no PyPI
publish. The `required-reviewer` branch-protection gate needed for PyPI publishing is deferred
to the `go-open-source` capstone release when the repository goes public.

**Resolution:** No action needed. The patch is complete and correct; the PyPI publish path is
gated separately.

**Memory updates:** None — no version or API surface changed.

---

## Memory updates

- `specs/memory/product/context-management.html` — updated the Impl-XOR-Review subsection
  (within `<section id="purpose">`) to document: (1) STALE impl locks now block review bind
  until explicit reclaim or release (treated same as HELD); (2) `bind()` check-then-act is
  atomic under the workspace fcntl lock for both IMPLEMENTATION (non-force) and REVIEW paths.
  Meta line updated to `r2-lock-toctou-hardening-v1`. No changelog section added.
- `specs/memory/architecture.html` — no change; no architectural layer, module, or dependency
  contract changed.
- `specs/memory/tech-stack.html` — no change; no new PyPI dependencies.
- `specs/memory/product/index.html` — no change; no new feature added or removed from
  catalog.

---

## Backlog returns

None. All three defects were fixed in scope. No new candidates or ideas emerged.

---

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/r2-lock-toctou-hardening-v1/` via `git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.
