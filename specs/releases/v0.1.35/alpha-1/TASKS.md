# TASKS: v0.1.35 alpha-1 - dadaia-workflows operational hardening

**Status:** Aprovado
**Release ID:** v0.1.35
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T-35-01 — Add explicit release-definition scope inputs

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/cli/commands/lifecycle.py`
  - `dadaia_workspace/features/lifecycle/workflows/release_definition.py`
  - `tests/integration/cli/test_release_definition_workflow.py`
  - `specs/bugs/release-definition-lacks-operator-intent-channel-and-infers-scope-from-run-id.md`
- **Acceptance:** CLI accepts explicit intent/backlog/bug/audit inputs, injects them
  into `release_scope`, and tests prove a misleading `run_id` no longer becomes scope.

### T-35-02 — Gate create steps on canonical artifacts

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/features/lifecycle/workflows/release_definition.py`
  - `tests/integration/cli/test_release_definition_workflow.py`
  - `specs/bugs/release-definition-spec-create-accepts-handoff-only-without-spec-file.md`
- **Acceptance:** `spec_create`, `plan_create`, and `tasks_create` block unless the
  expected canonical artifact exists with path/hash evidence; handoff-only SPEC output
  blocks at `spec_create`.

### T-35-03 — Dogfood bug-report workflow and inspect transcript noise

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/**`
  - `tests/**`
  - `specs/bugs/agents-bypass-bug-report-workflow-and-handwrite-bug-files.md`
  - `specs/bugs/codex-bind-context-injection-visible-transcript-noise.md`
- **Acceptance:** workflow-owned bug reporting has a clear executable path or a fixed
  blocker; transcript-noise bug has root cause and either a fix or a precise residual
  follow-up.

### T-35-04 — Verify and push

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `specs/releases/v0.1.35/alpha-1/TASKS.md`
- **Acceptance:** focused tests and specs doctor pass; Codex workflow smoke is attempted
  with explicit v0.1.35 scope; branch is committed and pushed.
- **Evidence:** Focused workflow suite: `10 passed`. Codex smoke:
  `v0135-codex-scope-smoke` completed with `release_scope` on `codex_exec` and
  downstream fake steps, final phase `implementation`.
