# CODEX_RUNTIME_DECISION: v0.1.15

**Status:** Aprovado
**Release ID:** v0.1.15
**Decision:** use `CodexExecAdapter` as the default Codex runtime adapter.

## Decision

v0.1.15 implements Codex integration through the installed `codex exec` CLI,
behind `AgentRuntimePort`. It does not add a Codex SDK or package dependency.

Lifecycle authority stays in Python:

- Python builds bounded `AgentRunRequest` payloads.
- `CodexExecAdapter` only runs the worker prompt and returns `AgentRunResult`.
- `LifecycleAgentRunner` validates structured verdict, artifact evidence, and
  write-scope paths before the lifecycle state machine can advance.
- Agent prose alone never passes a gate.

## Exec Surface

The adapter invokes:

```text
codex exec
  --ignore-user-config
  --sandbox <explicit sandbox>
  --ask-for-approval <explicit policy>
  --cd <explicit cwd>
  --output-last-message <temp file>
  -m <explicit model>
  -c model_reasoning_effort="<explicit effort>"
  -
```

The prompt is passed on stdin as structured JSON. The last assistant message is
read from `--output-last-message`; when it is JSON, the adapter maps `summary`,
`artifact_refs`, and `structured_output` into `AgentRunResult`.

## Controls

- **cwd:** explicit `CodexExecConfig.cwd`; no implicit project-local discovery.
- **env:** explicit allowlist only. The adapter never passes `os.environ` as a
  whole.
- **credentials:** secret-looking environment values are redacted from errors.
- **project-local config:** `--ignore-user-config` prevents profile/config
  layering into the worker invocation. Auth remains a user-controlled Codex CLI
  concern outside lifecycle state.
- **model/profile:** model and reasoning effort come from explicit adapter config
  or registry-derived Codex tier views. Unknown project-local profiles are not
  read.
- **sandbox:** defaults to `read-only`. Widening sandbox or approval behavior
  requires explicit `CodexExecConfig` input and is visible to callers.
- **live execution:** opt-in only. CI uses fake runner tests.

## Rejected

- **Codex SDK adapter now:** rejected for v0.1.15 because no package/version was
  picked, approved, or scoped. A future SDK adapter must be a separate release
  item with dependency, auth, telemetry, and support criteria.
- **Agent-owned lifecycle transitions:** rejected. It repeats the nondeterminism
  this release is designed to remove.
- **Whole-environment pass-through:** rejected because it risks leaking
  credentials and operator-local state into run records, logs, reports, and
  spawned processes.
