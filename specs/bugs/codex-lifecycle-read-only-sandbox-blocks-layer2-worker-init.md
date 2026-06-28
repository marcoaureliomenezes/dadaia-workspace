---
name: codex-lifecycle-read-only-sandbox-blocks-layer2-worker-init
status: Closed
severity: HIGH
reported: 2026-06-27
surface: lifecycle Codex Layer-2 runtime adapter / backlog-definition workflow
session_id: sess_2687aa9b
---

**Symptom:** A live Codex Layer-2 workflow attempt reached the real
`backlog_definition.intake_grill` step, but Codex failed before producing a worker result.

Observed command:

```bash
.dadaia/.venv/bin/dadaia lifecycle backlog define \
  --context dadaia-workspace \
  --release-id v0.1.33 \
  --run-id codex-v0133-backlog-define-smoke \
  --harness codex \
  --model gpt-5.5:high \
  --json
```

Observed workflow result:

```json
{
  "status": "BLOCKED",
  "blocked": {
    "blocked_at_step": "intake_grill",
    "reason": "WARNING: proceeding, even though we could not create PATH aliases: Read-only file system (os error 30)\nError: failed to initialize in-process app-server client: Read-only file system (os error 30)"
  },
  "steps": [
    {"label": "intake_grill", "runtime": "codex_exec", "accepted": false}
  ]
}
```

**Root cause:** `CodexExecConfig.sandbox` defaulted to `read-only`. The lifecycle container
uses that default when building the Codex Layer-2 adapter, so `codex exec` starts with a
read-only sandbox even for workflow steps that must write scoped artifacts. The installed
Codex CLI also initializes local client/PATH-alias state before answering; with a
read-only sandbox it fails before the Python workflow gate can inspect a worker result.

**Expected:** Codex Layer-2 workflow runs should start with a sandbox that permits the
scoped artifact writes the workflow asks for. The SDD gate/git chokepoints and
workflow-scoped `allowed_paths` remain responsible for bounding writes; the Codex process
must not be unable to initialize before those gates are reached.

**Impact:** Codex cannot practically be used as a Layer-2 dadaia-workflow worker through
the default container path. Operators see a workflow `BLOCKED` result at the first model
step even though the worker never had a chance to comply.

**Acceptance:** Change the Codex lifecycle adapter default sandbox to `workspace-write`;
add a regression test proving a container-built Codex adapter uses `--sandbox
workspace-write`; rerun a live Codex-backed workflow smoke and confirm it gets past Codex
initialization.

## Resolution

Fixed in `v0.1.35`.

`CodexExecConfig.sandbox` now defaults to `workspace-write`, and
`CodexExecAdapter._command()` passes that sandbox value to `codex exec`. This lets the
Layer-2 worker initialize and write scoped workflow artifacts before Python gates inspect
the result.

Evidence:

- `dadaia_workspace/infrastructure/codex_runtime.py#CodexExecConfig`
- `dadaia_workspace/infrastructure/codex_runtime.py#CodexExecAdapter._command`
- `specs/releases/v0.1.35/alpha-1/TASKS.md` T-35-04 Codex smoke:
  `v0135-codex-scope-smoke` completed `release_scope` on `codex_exec`.
