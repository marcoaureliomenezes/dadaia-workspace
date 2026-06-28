---
name: prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound
status: Closed
severity: MEDIUM
reported: 2026-06-26
resolved_in: v0.1.34
surface: dadaia ci preflight (pre-push gate) / tests/performance/test_lifecycle_hygiene_scan.py
session_id: null
---

**Resolution (v0.1.34):** Marked the synthetic hygiene scan as `pytest.mark.performance`
and added the `performance` marker to `pyproject.toml`. The ci-preflight pytest check now
runs with `-m "not performance"` in both full and quick profiles, so the wall-clock-bound
synthetic performance test remains explicitly runnable but no longer blocks ordinary
pre-push/default validation under host load.

**Symptom:** The pre-push CI gate (`dadaia ci preflight`, run by the git pre-push hook)
runs the full pytest suite, which includes
`tests/performance/test_lifecycle_hygiene_scan.py::test_hygiene_status_scans_synthetic_baseline_tree_with_bounded_content_reads`.
That test scans **437,724 synthetic files** and asserts the scan completes within a
**90.0s wall-clock bound** (`MAX_SCAN_SECONDS`). On a developer machine under concurrent
CPU load (observed: a competing Playwright/browser suite + multiple agent sessions,
load average swinging 2 → 10), the scan takes **280–290s**, the assert fails, and the
pre-push gate **blocks every push** — regardless of what the push actually changes.

```
>       assert elapsed < MAX_SCAN_SECONDS
E       assert 282.9791796661448 < 90.0
tests/performance/test_lifecycle_hygiene_scan.py:175: AssertionError
1 failed, 3845 passed, 14 skipped in 1023.44s
```

**Repro:**
1. Start a CPU-heavy workload alongside the workspace (e.g. a Playwright suite).
2. `git push` any branch in a Spec Context repo → the pre-push hook runs `dadaia ci
   preflight` → the perf test exceeds 90s → push blocked.
3. The same suite is **green on GitHub Actions runners** (every prior release shipped
   with all CI jobs green) and green locally when the machine is idle — so it is a
   wall-clock/contention sensitivity, not a logic failure.

**Expected:** The local pre-push gate must not be a coin-flip against machine load. A
wall-clock-bound performance assertion either (a) should not gate the pre-push hook
(performance tests belong in a dedicated, possibly-non-blocking CI job, e.g. mark
`@pytest.mark.performance` and have `ci preflight` deselect them or run them advisorily),
or (b) must be measured in a contention-robust way (CPU-time / operation-count budget
rather than wall-clock, or a generous multiplier), so a correct change is never blocked
by an unrelated concurrent workload.

**Notes:** Surfaced shipping v0.1.28 + v0.1.29 (both functionally green: 3845 passed,
ruff/mypy clean). Neither release touches the hygiene service
(`features/lifecycle/hygiene.py`) — `git diff` confirms. The block is purely the perf
test's wall-clock bound under host contention. Workaround used to ship: push during an
idle window where the scan completes under 90s. Redacted of operator-local paths.
