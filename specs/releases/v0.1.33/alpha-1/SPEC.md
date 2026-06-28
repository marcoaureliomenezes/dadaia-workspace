# SPEC: v0.1.33 alpha-1 - codex dadaia-workflows enablement

**Status:** Aprovado
**Release ID:** v0.1.33
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-27

---

## Objective

Make `dadaia lifecycle` workflows usable from Codex as a Layer-2 worker harness, and
prove the workflow path with E2E tests that cover the actual failure modes found during
operator use.

This alpha is intentionally focused on workflow enablement, not the whole open Codex bug
backlog.

## Picked Bugs

- `lifecycle-codex-exec-ask-for-approval-invalid` — Codex-harnessed workflows call
  `codex exec` with a stale `--ask-for-approval` flag rejected by Codex CLI 0.142.3.
- `backlog-definition-pi-intake-grill-artifact-evidence-gate` — the
  `backlog_definition.intake_grill` structured-data step is blocked by the generic
  artifact evidence gate even though it produces `backlog-demand-v1`, not a file.
- `codex-bind-context-injection-visible-transcript-noise` — bind/session context
  injection floods Codex transcript-visible context with dispatcher preflight and ranked
  catalog JSON.
- `codex-lifecycle-read-only-sandbox-blocks-layer2-worker-init` — live Codex workflow
  workers cannot initialize when the adapter gives Codex a read-only/non-writable runtime
  home.
- `codex-lifecycle-workspace-root-requires-skip-git-repo-check` — live Codex workflow
  workers refuse the dadaia workspace root because it is intentionally not a Git repo.

## Scope

### FR-1 — Codex exec command compatibility

`CodexExecAdapter` must build a `codex exec` command accepted by the installed Codex CLI
generation documented in the bug (`codex-cli 0.142.3`): no stale `--ask-for-approval`
flag. Approval/sandbox posture must remain explicit and test-pinned through supported
configuration flags or config overrides.

The lifecycle adapter must also provide a writable isolated `HOME`/`CODEX_HOME` under
workspace `.dadaia/tmp/` and pass `--skip-git-repo-check`, because dadaia workflows run
from the workspace root while writing workspace-scoped artifacts.

### FR-2 — Structured workflow steps without artifact refs

The lifecycle gate must distinguish artifact-producing create steps from structured-data
producer steps. A structured-data workflow step such as `backlog_definition.intake_grill`
may advance when the worker emits a schema-valid result with the expected structured
payload, even if it does not write an artifact path.

No-op workers must still block. Review steps must still require `verdict: APPROVED`.

### FR-3 — Codex context injection is transcript-bounded

The Codex hook output used for bind/session context injection must not flood the
operator-visible transcript with the full memory catalog. The first visible payload after a
bind may identify the loaded context and point to self-pull memory, but it must not include
the ranked catalog JSON or the full dispatcher preflight.

Repeat prompts in the same Codex session must remain silent.

### FR-4 — Workflow E2E coverage

Add E2E/integration coverage that proves:

- Codex workflow command construction matches the supported CLI surface.
- The real `dadaia lifecycle backlog define --harness codex --model ...` CLI path
  resolves a Codex Layer-2 runtime and discrete model without requiring a live Codex
  process in CI.
- A live, operator-triggered `dadaia lifecycle backlog define --harness codex --model
  gpt-5.5:high` smoke can run Codex as the Layer-2 worker through the workflow path when
  network access is allowed.
- A `backlog_definition` workflow can advance through a structured-data intake step
  without artifact refs while still blocking no-op output.
- Codex context injection is bounded on first bind/session payload and silent on repeats.

## Non-Goals

- Running paid live Codex/PI workers in default CI. Live worker probes remain opt-in.
- Fixing every open Codex projection, panel, or subagent bug.
- Changing the `dadaia lifecycle` public command vocabulary beyond what is required to
  unblock Codex workflow execution.

## Acceptance Criteria

1. `CodexExecAdapter` unit tests prove the generated argv contains no
   `--ask-for-approval` flag and still carries sandbox/model/reasoning/cwd/output controls.
2. A lifecycle gate test proves a structured-data create step can pass without
   `artifact_refs` only when an expected structured payload is present.
3. A regression test proves a no-op create step still blocks.
4. An integration/E2E test drives `dadaia lifecycle backlog define --harness fake` through
   the real workflow path using the same gate semantics required by Codex/PI workers.
5. A CLI integration test drives `dadaia lifecycle backlog define --harness codex
   --model gpt-5.5:high` through the real command/workflow path with a hermetic fake
   runtime factory, proving Codex runtime/model selection without spawning the live Codex
   binary.
6. A live Codex workflow smoke reaches `status: OK`, with `intake_grill` and
   `backlog_author` both executed as `codex_exec`.
7. A Codex hook test proves first visible injection is bounded and repeat injection for the
   same `session_id` emits nothing.
8. `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` reports 0 errors.
9. Targeted pytest for lifecycle runner, Codex runtime, backlog workflow, CLI workflow
   selection, and ctx-inject
   passes with repo caches disabled.
