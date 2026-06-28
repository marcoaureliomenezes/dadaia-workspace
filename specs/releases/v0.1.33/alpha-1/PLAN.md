# PLAN: v0.1.33 alpha-1 - codex dadaia-workflows enablement

**Status:** Aprovado
**Release ID:** v0.1.33
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-27

---

## Approach

Implement this as three small fixes with regression coverage before broad validation.

## Implementation Plan

### 1. Codex exec argv compatibility

Update `dadaia_workspace/infrastructure/codex_runtime.py` so the adapter no longer emits
the stale `--ask-for-approval` flag. Preserve:

- `codex exec`
- `--ignore-user-config`
- `--sandbox <mode>`
- `--cd <cwd>`
- `--skip-git-repo-check`
- `--output-last-message <path>`
- `-m <model>`
- `-c model_reasoning_effort="<effort>"`
- stdin prompt marker `-`

Provide a workspace-local runtime environment for live Codex workers:

- `HOME=.dadaia/tmp/codex-runtime/home`
- `CODEX_HOME=.dadaia/tmp/codex-runtime/codex-home`
- `XDG_{CONFIG,CACHE,DATA}_HOME=.dadaia/tmp/codex-runtime/xdg/...`
- copy only available `auth.json` / `config.toml` into the isolated `CODEX_HOME`

Update unit tests in `tests/unit/infrastructure/test_codex_exec_runtime.py` so the old
flag is forbidden, not expected, and the isolated runtime home + git-repo-check bypass are
test-pinned.

### 2. Structured-data workflow gate

Extend `AgentRunnerInput` / `LifecycleAgentRunner` semantics to support create steps that
produce structured data rather than file artifacts. The safe rule:

- review step: requires `verdict: APPROVED`;
- artifact create step: requires non-empty `artifact_refs`;
- structured-data create step: may pass with empty `artifact_refs` if
  `structured_output` is non-empty and the workflow step declares structured output;
- no-op create step: still blocks.

Thread that declaration only where needed for `backlog_definition.intake_grill`; avoid
making all create steps permissive.

### 3. Codex context injection transcript bound

Keep the once-per-session sentinel behavior. Change the Codex-visible bootstrap payload so
it is bounded:

- repeat prompt with same `session_id` emits nothing;
- first bound-context payload emits context identity + short memory self-pull pointer;
- no full ranked catalog JSON in the visible additionalContext payload.

Prefer changes in `hooks/ctx_inject.py` and projected runtime config tests; do not add
Codex-only drift by hand-editing `.codex/`.

### 4. E2E and regression tests

Add or update tests at these layers:

- unit: Codex argv builder;
- unit: lifecycle gate structured-data vs artifact/no-op;
- integration: `backlog_definition` workflow structured intake path;
- integration/CLI: `dadaia lifecycle backlog define --harness codex --model
  gpt-5.5:high` resolves the real workflow path, Codex runtime kind, and discrete model
  while replacing only the live runtime process with an in-process fake;
- live smoke: operator-triggered `dadaia lifecycle backlog define --harness codex --model
  gpt-5.5:high` completes with Codex as the model worker when network access is allowed;
- e2e/features: Codex ctx-inject bounded first payload and silent repeat.

### 5. Validation

Run targeted pytest with cache disabled:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  tests/unit/infrastructure/test_codex_exec_runtime.py \
  tests/unit/features/lifecycle/test_agent_runner_review_only_gate.py \
  tests/integration/test_cli_backlog_define.py \
  tests/integration/test_backlog_definition_workflow.py \
  tests/e2e/features/test_ctx_inject_bind_boundary.py
```

Then run:

```bash
.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs
.dadaia/.venv/bin/dadaia backlog doctor --specs-dir repos/dadaia-workspace/specs
```

Live workflow smoke:

```bash
.dadaia/.venv/bin/dadaia lifecycle backlog define \
  --context dadaia-workspace \
  --release-id v0.1.33 \
  --run-id codex-v0133-backlog-define-smoke-5 \
  --harness codex \
  --model gpt-5.5:high \
  --json
```

## Lifecycle-Asymmetry Coverage

- Delete/orphan: no new persistent entity is introduced; run-store artifacts already have
  existing retention/handoff coverage.
- Dirty input: malformed/no-op worker output remains blocked by gate tests.
- Missing dependency: missing Codex binary remains an existing adapter `OSError` failure
  path; not changed in this alpha.
