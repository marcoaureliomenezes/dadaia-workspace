---
name: retention-sweep-test-uses-windows-unsupported-utime-followsymlinks
status: Closed
severity: LOW
reported: 2026-06-25
surface: tests/unit/features/lifecycle/test_retention_sweep.py (D5 retention sweep)
session_id: null
---

**Symptom:** The 3-OS CI matrix went red on Windows only. `test_symlink_escaping_dadaia_is_refused`
raised `NotImplementedError: utime: follow_symlinks unavailable on this platform` at
`tests/unit/features/lifecycle/test_retention_sweep.py:208`. Linux local + Linux CI passed, masking it
until push. (`Unit fast (Windows/macOS)` and `Contract coverage (Windows/macOS)` jobs, run 28146264479.)

**Repro:** Run the retention-sweep unit tests on `windows-latest`:
`pytest tests/unit/features/lifecycle/test_retention_sweep.py::test_symlink_escaping_dadaia_is_refused`.
CPython on Windows does not support `os.utime(path, ..., follow_symlinks=False)`.

**Expected:** The workspace test suite is cross-platform (Linux/macOS/Windows, established v0.1.8). A
new test introduced by D5 (T-016-15) must not call a POSIX-only `os` API.

**Root cause / fix:** The test aged the symlink itself with `os.utime(link, follow_symlinks=False)` to
push it past TTL. That aging is unnecessary: `RetentionSweep._collect_unit` collects a symlink as a
candidate **unconditionally** (a symlink is a leaf for the deleter and skips the `newest >= cutoff` TTL
check), so it always reaches the ESCAPE guard regardless of mtime. Removed the
`os.utime(link, ..., follow_symlinks=False)` line; the assertion (escape refused, outside tree
survives) is unchanged and now portable. Fixed in the multiharness-engine-v0116 closure.

**Notes:** Cross-platform-portability lesson re-confirmed: Linux-only local runs do not prove the
Windows leg of the 3-OS matrix; POSIX-only `os` flags (`follow_symlinks=` on `utime`) are the recurring
trap. No production code changed — test-only.
