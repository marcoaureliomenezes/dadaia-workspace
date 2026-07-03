---
status: Closed
severity: high
created_at: 2026-06-18
reported_by: codex
session_id: null
release: v0.1.15
resolved_by: v0.1.15
---

# lifecycle run store rejects self-hosting workspace root

## Summary

`JsonLifecycleRunStore` rejects the actual self-hosting workspace root when the
workspace root has both `.git/` and `.dadaia/`. This breaks `dadaia lifecycle
resume` and any container path that builds the lifecycle run store in this
workspace.

## Evidence

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m dadaia_workspace lifecycle resume missing
```

Observed:

```text
LifecycleRunStoreError: refusing to create lifecycle state inside a repository tree: /home/[REDACTED]/workspace/dadaia
```

The workspace root `/home/[REDACTED]/workspace/dadaia` is the initialized
self-hosting workspace and contains `.dadaia/`, `repos/`, and `.git/`. The guard
must reject Spec Context Project repo trees such as `repos/dadaia-workspace/**`,
but must not reject the initialized workspace root itself.

## Expected

`JsonLifecycleRunStore(/home/[REDACTED]/workspace/dadaia)` should write under the
workspace runtime state:

```text
.dadaia/states/lifecycle/
```

`JsonLifecycleRunStore(/home/[REDACTED]/workspace/dadaia/repos/dadaia-workspace)` and
subdirectories under that repo must still be rejected.

## Resolution

Fixed in v0.1.15 by allowing the initialized self-hosting workspace root while
continuing to reject repo-tree stores. Regression evidence: commit `9682c88`
and `tests/unit/features/lifecycle/test_run_store.py::test_allows_self_hosting_workspace_root_with_git_and_dadaia`.
