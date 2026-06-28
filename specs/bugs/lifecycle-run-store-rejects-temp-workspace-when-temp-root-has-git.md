---
name: lifecycle-run-store-rejects-temp-workspace-when-temp-root-has-git
status: Open
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
