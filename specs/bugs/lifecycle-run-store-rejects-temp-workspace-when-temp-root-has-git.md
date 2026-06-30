---
name: lifecycle-run-store-rejects-temp-workspace-when-temp-root-has-git
status: Closed
severity: MEDIUM
reported: 2026-06-27
surface: lifecycle run store / CI preflight pytest temp workspaces
session_id: null
---

**Symptom:** `JsonLifecycleRunStore` rejects otherwise valid temporary workspace roots
when the system temporary directory itself contains a `.git/` directory.

**Root cause:** `JsonLifecycleRunStore._reject_repo_tree_root()` walks every parent of
the requested workspace root and rejects on the first `.git/` it sees. In this
environment `/tmp/.git` exists, so pytest workspaces under `/tmp/pytest-*` are
incorrectly classified as inside a repository tree even when the requested root is a
standalone `.dadaia` workspace fixture.

The guard was intended to prevent creating repo-local `.dadaia` lifecycle state inside a source repository, but it treated the system temp root as an authoritative repository ancestor.

**Evidence:**

- `git push` pre-push pytest failed in `tests/unit/features/lifecycle/test_run_store.py`.
- Focused failure raised `LifecycleRunStoreError: refusing to create lifecycle state
  inside a repository tree` for a pytest `tmp_path`.
- `find /tmp / -maxdepth 1 -name .git -type d` returned `/tmp/.git`.

**Expected:** Temporary workspace roots under the system temp directory should not be
rejected solely because the temp root contains an ambient `.git/`.

**Actual:** Lifecycle run-store initialization failed before tests could persist any run
state.

**Acceptance:** Stop the repository-ancestor scan at the resolved system temp root. Keep
rejecting `.git/` directories below that boundary so repo-local `.dadaia` state remains
blocked.

## Resolution

Closed in v0.1.40 alpha-1 T7.

Root cause review: `JsonLifecycleRunStore._reject_repo_tree_root()` in the current tree
already stops the ancestor scan at `Path(tempfile.gettempdir()).resolve()` before testing
that temp root for `.git`. The root cause had therefore been fixed in implementation but
the bug record remained open and unpinned by a focused regression.

Fix/evidence:

- Added `tests/unit/features/lifecycle/test_json_lifecycle_run_store.py`.
- `test_run_store_allows_temp_workspace_under_ambient_temp_git` proves an ambient
  temp-root `.git` no longer rejects a standalone temp workspace.
- `test_run_store_still_rejects_repo_local_dadaia_below_temp_root` proves the guard still
  rejects a real repository ancestor below the temp boundary.
- Focused 66-test validation run passed.
