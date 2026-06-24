# TASKS — Release: multiharness-engine-v0116

**Status:** Aprovado
**Release ID:** multiharness-engine-v0116
**Owner:** product-engineer
**Created:** 2026-06-24

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
TDD-first: each task lands its failing test before the fix. Maximum one `[-]` per owner unless tasks
have disjoint write sets as declared. Hard spine: T-016-00 → 01 → {02,03} → 04 → 05 → 06 → 07.

---

## Pre-work

### [x] T-016-00 — Release start: ACTIVE.md → multiharness-engine-v0116 IMPLEMENTATION
- **Owner:** product-engineer
- **Write set:** `specs/releases/ACTIVE.md`
- **Acceptance:** `ACTIVE.md` reads `release: multiharness-engine-v0116` / `phase: IMPLEMENTATION`
  with SPEC/PLAN/TASKS `**Status:** Aprovado`.
- **Parallelism:** first, before all waves.

---

## W1 — Runtime kinds

### [x] T-016-01 — Add CLAUDE_SDK + OPENCODE_RUN to AgentRuntimeKind
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/models/lifecycle.py`, `tests/unit/core/test_agent_runtime_kind.py`
- **Acceptance:** enum has FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN; `AgentRunRequest` to_dict /
  from_dict round-trips all four; test asserts `AgentRuntimeKind(v.value) == v` for every member.

---

## W3 — OpenCode adapter stub (disjoint from W4)

### [x] T-016-02 — OpenCodeAdapter stub behind the port
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/opencode_runtime.py`,
  `tests/unit/infrastructure/test_opencode_runtime.py`
- **Acceptance:** implements `AgentRuntimePort` (`@runtime_checkable` passes);
  `runtime_kind() == OPENCODE_RUN`; `run(request)` raises `NotImplementedError` whose message names
  the deferred workstream and the unverified `opencode run` API. Test asserts isinstance-of-port and
  the raise + message substring.

---

## W4 — Claude SDK adapter stub (disjoint from W3)

### [x] T-016-03 — ClaudeSdkAdapter stub behind the port
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/claude_sdk_runtime.py`,
  `tests/unit/infrastructure/test_claude_sdk_runtime.py`
- **Acceptance:** implements `AgentRuntimePort`; `runtime_kind() == CLAUDE_SDK`; `run(request)`
  raises `NotImplementedError` whose message names `claude-agent-sdk` + the deferred live
  integration. No import of `claude_agent_sdk` / `anthropic` at module load. Test asserts the raise +
  no-import.

---

## W2 — Runtime factory (depends on W1, W3, W4)

### [x] T-016-04 — build_agent_runtime factory in container.py
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/container.py`,
  `tests/unit/test_build_agent_runtime.py`
- **Acceptance:** `build_agent_runtime(kind, *, cwd=None) -> AgentRuntimePort` returns
  `FakeAgentRuntime` for FAKE, `CodexExecAdapter` for CODEX_EXEC, `OpenCodeAdapter` for OPENCODE_RUN,
  `ClaudeSdkAdapter` for CLAUDE_SDK; the returned port's `runtime_kind()` equals the requested kind
  (FAKE may map to a fake whose kind is FAKE); unknown / unhandled kind raises a clear `ValueError`.
  Test parametrizes all four kinds + the error path.

---

## W5 — Integration proof

### [x] T-016-05 — Factory-built FAKE runtime drives LifecycleAgentRunner green
- **Owner:** software-engineer
- **Write set:** `tests/unit/features/lifecycle/test_runner_with_factory_runtime.py`
- **Acceptance:** `LifecycleAgentRunner(runtime=build_agent_runtime(FAKE, …))` produces an accepted
  `TransitionDecision` for a well-formed request — proving the factory output satisfies the runner's
  injection contract end-to-end.

---

## Verification + closure

### [x] T-016-06 — Full local gate green
- **Owner:** software-engineer / qa-engineer
- **Acceptance:** `ruff format --check`, `ruff check`, `mypy --strict`, `pytest` all green;
  `_repo_root_write_guard` clean; no new venvs. QA review handoff recorded.

### [ ] T-016-07 — CLOSURE (deferred to rc / operator ship decision)
- **Owner:** product-engineer
- **Write set:** `specs/releases/multiharness-engine-v0116/CLOSURE.md`, `specs/memory/**`,
  `specs/releases/ACTIVE.md`
- **Acceptance:** CLOSURE.md with evidence triples; memory atoms updated (DEFINITION/CLOSURE phase
  only); release archived. **Held** until the operator chooses to ship alpha-1 or iterate to alpha-2
  (WS-1 per-phase workflows).

---

## W6 — Alpha-2: first real engine-driven verb (WS-1 slice)

### [x] T-016-08 — LifecyclePhaseWorkflow + wire review verbs to the engine
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/phase_workflow.py`,
  `dadaia_workspace/container.py` (`build_lifecycle_phase_workflow`),
  `dadaia_workspace/cli/commands/lifecycle.py` (`review qa|security|code`),
  `tests/unit/features/lifecycle/test_phase_workflow.py`,
  `tests/integration/test_lifecycle_review_cli.py`,
  `tests/integration/cli/test_lifecycle_command_skeletons.py` (drop the 3 review skeletons).
- **Acceptance:** `LifecyclePhaseWorkflow.run(...)` threads scoped prompt → factory-selected
  `AgentRuntimePort` → `LifecycleAgentRunner` gate → legal transition → persisted `LifecycleRun`.
  `dadaia lifecycle review {qa,security,code} --harness fake|codex|claude|opencode --release-id <id>`
  runs the engine (no longer `unavailable_workflow`): FAKE worker (no APPROVED verdict) BLOCKS with
  the real gate reason and persists the run; an injected APPROVED result advances the phase. Gate
  green (ruff/mypy --strict/pytest 3325). **NOTE:** `decision.accepted` is True even for a legal
  transition INTO BLOCKED — pass/fail is `run.blocked is None`.
- **Done:** alpha-2; QA review gate recorded.

---

## W7 — Alpha-3: every single-step lifecycle verb runs the engine

### [x] T-016-09 — Wire backlog/release/implement/close to the engine; retire the stub layer
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py` (generalize `_run_review` →
  `_run_phase_step`; wire `backlog define`, `release define`, `implement`, `close`),
  `dadaia_workspace/features/lifecycle/service.py` (remove dead `unavailable_workflow`),
  `tests/integration/cli/test_lifecycle_command_skeletons.py` (assert all 7 verbs drive the engine),
  remove redundant `tests/integration/test_lifecycle_review_cli.py`.
- **Acceptance:** all seven single-step verbs (`backlog define`, `release define`, `implement`,
  `review {qa,security,code}`, `close`) run `LifecyclePhaseWorkflow` on a `--harness`-selectable
  runtime over a legal transition; the `unavailable_workflow` service method + CLI helper are deleted
  (no dead stub layer). Integration test proves every verb blocks on the real gate with FAKE.
  Gate green (ruff/mypy --strict/pytest 3322). QA review gate recorded.
- **Done:** alpha-3.
- **Known simplification (tracked):** the runner applies a uniform APPROVED-verdict gate to every
  step, so non-review phases (implement/define) also require the worker to emit an APPROVED handoff.
  Phase-specific gating (e.g. implement needs evidence, not self-approval) is a follow-up runner
  refinement, not this release.

---

## Deferred waves (DEFINED, not yet — see SPEC §4)

- **WS-1 multi-step** — true multi-step phase workflows (e.g. implement → per-task-group qa gate in
  one run) beyond the single-step verbs landed in T-016-08/09; shadow-first.
- **WS-3** markdown `orchestrate` collapse — separate atomic release.
- **WS-4 live** Claude Agent SDK integration — operator dep-approval release.
- **WS-6** anti-slop self-governance, **WS-7** prompt prefix-cache, **D12** surface-collapse.
