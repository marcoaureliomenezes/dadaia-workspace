---
title: init-ignores-workspace-flag
severity: Medium
opened: 2026-06-07
session_id: null
status: Closed
shipped_in: 0.1.5
resolved_in: already-fixed (verified 2026-06-09)
---

**Resolution (verified 2026-06-09):** current `workspace_resolver.py:resolve_workspace_root_for_init(explicit=...)` returns `cwd.resolve()` immediately when `--workspace` is given; `init.py` passes `explicit=workspace is not None`. The reported upward-walk no longer occurs. Closed.


# Bug: init-ignores-workspace-flag

# Description

`dadaia init --workspace <dir>` does not reliably target `<dir>`. When the
current working directory is already inside an existing workspace, the resolver
walks **up** to the nearest ancestor containing
`.dadaia/states/spec_contexts.json` and operates on **that** workspace instead of
the supplied `<dir>`. The `--workspace` flag is effectively a no-op in that case,
silently writing into the ancestor workspace.

## Steps to reproduce

1. `cd` into a path inside an existing workspace (e.g. `<ws>/.dadaia/tmp/...`).
2. `dadaia init --workspace /tmp/freshws`.
3. **Expected:** `/tmp/freshws` is initialized.
   **Actual:** files are written into the ancestor workspace `<ws>/.dadaia/...`;
   `/tmp/freshws` is untouched. (Reproduced live 2026-06-07: init wrote
   `.dadaia/scripts/*` into the live workspace, not the target.)

## Location

- `dadaia_workspace/core/workspace_resolver.py:~57,100` —
  `resolve_workspace_root_for_init` forwards `--workspace` as the `cwd` to
  `resolve_workspace_root`, which still walks upward to the sentinel ancestor
  rather than treating the explicit path as authoritative.

## Impact

Footgun: an explicit `--workspace` target is silently ignored; init can mutate
an unintended workspace. No data corruption observed (projections are
idempotent) but the behavior is surprising and unsafe.

## Fix direction

When `--workspace` is explicitly provided, treat it as authoritative: initialize
exactly that directory (create the sentinel there) instead of walking up to an
ancestor workspace.
