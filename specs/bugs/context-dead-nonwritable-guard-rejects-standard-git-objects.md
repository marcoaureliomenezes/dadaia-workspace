---
name: context-dead-nonwritable-guard-rejects-standard-git-objects
status: Closed
severity: MEDIUM
reported: 2026-06-12
session_id: null
surface: dadaia context dead (GitSyncError non-writable guard)
resolved: 2026-06-29
release: v0.1.38
---

> **Disposition (v0.1.14 release definition, 2026-06-12, product-engineer):**
> NOT PICKED — valid bug, stays Open. Surface is `context dead()` repo removal
> (file-permission guard), outside the v0.1.14 kernel scope
> (lease/gate/ctx-inject/hooks/venv). Candidate for a context-lifecycle fix release.

**Symptom:** `dadaia context dead <ctx>` fails with
`GitSyncError: Cannot remove 'repos/<ctx>': N non-writable file(s) found
(e.g. ['.git/objects/...']). Run: sudo chown -R $USER ...` — but the listed
files are ordinary loose git objects, which git creates mode 0444 **by design**
in every repository. Ownership is already correct (`find -not -user $USER` is
empty); the suggested `sudo chown` fix is wrong twice over (no ownership
problem exists, and chown would not change the mode).

**Repro:**
1. Any ALIVE context whose repo has at least one local commit (every commit
   writes 0444 loose objects).
2. `dadaia context dead <ctx>` → GitSyncError listing `.git/objects/*` files.
3. `chmod -R u+w repos/<ctx>/.git` → re-run → succeeds — until any new commit
   creates fresh 0444 objects, then it fails again.

**Expected:** the pre-removal writability guard must exempt `.git/objects/**`
(or treat user-owned 0444 files as removable — `rm -rf`/`shutil.rmtree` with an
onerror chmod handler is the standard pattern, same as `git` itself and
CPython's `tests.support.rmtree`). dead() should remove any repo it could have
created, without manual chmod.

**Notes:** First observed 2026-06-05 (dead() pushed then failed on the guard,
leaving a half-dead context); re-hit verbatim 2026-06-12. The guard fires
AFTER the git sync/push phase, so the failure leaves the context mid-transition.
Also observed: when `dead()` succeeds, a caller shell cwd'd inside the removed
repo gets `getcwd` errors and the CLI exits 1 *after* printing
`✓ Context ... is now DEAD` — success with nonzero exit confuses scripting.

## Root Cause

`SpecContextService.dead()` pre-scanned every file with `os.access(f, os.W_OK)` and rejected
the entire removal when any file lacked owner-write. Normal git loose objects are commonly
mode `0444`; they are removable by the owning user through directory write permission, so the
guard confused standard git storage with an actual ownership/removal problem.

## Fix

The pre-removal non-writable-file rejection was removed. `dead()` now delegates to
`shutil.rmtree(..., onexc=...)` with a chmod-and-retry handler, the standard pattern for
removing user-owned read-only files. The review gate and secret scan still run before any push
or removal.

## Validation

- `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/integration/test_dead_review_gate.py -q` -> `6 passed`
- `.dadaia/.venv/bin/python -m ruff check --no-cache repos/dadaia-workspace/dadaia_workspace/features/spec_context/service.py repos/dadaia-workspace/tests/integration/test_dead_review_gate.py` -> `All checks passed!`
- `.dadaia/.venv/bin/python -m mypy --strict repos/dadaia-workspace/dadaia_workspace/features/spec_context/service.py` -> `Success`
- Real command: `.dadaia/.venv/bin/python -m dadaia_workspace.cli.main context dead dadaia-pi-workspace --commit` -> `Context 'dadaia-pi-workspace' is now DEAD`
