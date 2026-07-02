---
name: context-dead-nonwritable-guard-rejects-standard-git-objects
status: Open
severity: MEDIUM
reported: 2026-06-12
session_id: null
surface: dadaia context dead (GitSyncError non-writable guard)
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
