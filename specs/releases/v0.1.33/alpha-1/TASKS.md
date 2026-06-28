# TASKS: v0.1.33 alpha-1 - codex dadaia-workflows enablement

**Status:** Aprovado
**Release ID:** v0.1.33
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-27

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T-33-01 — Fix Codex exec workflow command

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/infrastructure/codex_runtime.py`
  - `tests/unit/infrastructure/test_codex_exec_runtime.py`
- **Acceptance:** Codex runtime tests prove the adapter no longer emits
  `--ask-for-approval`, while preserving supported sandbox/model/reasoning/cwd/output
  controls.

### T-33-02 — Fix structured-data workflow gate

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/core/models/lifecycle.py`
  - `dadaia_workspace/features/lifecycle/agent_runner.py`
  - `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`
  - `tests/unit/features/lifecycle/test_agent_runner_review_only_gate.py`
  - `tests/integration/test_backlog_definition_workflow.py`
- **Acceptance:** `backlog_definition.intake_grill` can pass as a structured-data
  producer without artifact refs; no-op create output and review verdict failures still
  block.

### T-33-03 — Bound Codex context-injection transcript output

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/hooks/ctx_inject.py`
  - `tests/e2e/features/test_ctx_inject_bind_boundary.py`
  - `tests/unit/features/lifecycle/test_ctx_inject_dehydration.py`
- **Acceptance:** First Codex-visible bound-context injection is bounded and contains no
  ranked catalog JSON; repeat prompt with the same session id emits nothing.

### T-33-04 — Validate release gates

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `specs/releases/v0.1.33/alpha-1/TASKS.md`
- **Acceptance:** Targeted pytest passes with cache disabled; `specs doctor` has 0 errors;
  `backlog doctor` is clean.

### T-33-05 — Prove Codex workflow CLI selection

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `tests/integration/test_cli_backlog_define.py`
  - `specs/releases/v0.1.33/alpha-1/SPEC.md`
  - `specs/releases/v0.1.33/alpha-1/PLAN.md`
  - `specs/releases/v0.1.33/alpha-1/TASKS.md`
- **Acceptance:** `dadaia lifecycle backlog define --harness codex --model
  gpt-5.5:high` is covered by a hermetic CLI integration test that runs the real
  command/workflow path, proves `codex_exec` step selection, and proves the concrete
  Codex model is threaded into the runtime factory without spawning the live Codex binary.

### T-33-06 — Prove live Codex Layer-2 workflow startup

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/infrastructure/codex_runtime.py`
  - `tests/unit/infrastructure/test_codex_exec_runtime.py`
  - `specs/bugs/codex-lifecycle-read-only-sandbox-blocks-layer2-worker-init.md`
  - `specs/bugs/codex-lifecycle-workspace-root-requires-skip-git-repo-check.md`
  - `specs/releases/v0.1.33/alpha-1/SPEC.md`
  - `specs/releases/v0.1.33/alpha-1/PLAN.md`
  - `specs/releases/v0.1.33/alpha-1/TASKS.md`
- **Acceptance:** Live escalated smoke
  `dadaia lifecycle backlog define --context dadaia-workspace --release-id v0.1.33
  --run-id codex-v0133-backlog-define-smoke-5 --harness codex --model gpt-5.5:high
  --json` returns `status: OK`, with `intake_grill` and `backlog_author` executed as
  `codex_exec`.
