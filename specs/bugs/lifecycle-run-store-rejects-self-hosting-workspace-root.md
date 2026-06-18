---
status: open
severity: high
created_at: 2026-06-18
reported_by: codex
release: v0.1.15
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
LifecycleRunStoreError: refusing to create lifecycle state inside a repository tree: /home/marco/workspace/dadaia
```

The workspace root `/home/marco/workspace/dadaia` is the initialized
self-hosting workspace and contains `.dadaia/`, `repos/`, and `.git/`. The guard
must reject Spec Context Project repo trees such as `repos/dadaia-workspace/**`,
but must not reject the initialized workspace root itself.

## Expected

`JsonLifecycleRunStore(/home/marco/workspace/dadaia)` should write under the
workspace runtime state:

```text
.dadaia/states/lifecycle/
```

`JsonLifecycleRunStore(/home/marco/workspace/dadaia/repos/dadaia-workspace)` and
subdirectories under that repo must still be rejected.
