# PLAN — Release: multiharness-engine-v0116

**Status:** Aprovado
**Release ID:** multiharness-engine-v0116
**Owner:** product-engineer
**Created:** 2026-06-24

---

## Architecture

The seam is the **port + factory** pattern already used for OS adapters (`PLATFORM` →
`build_process_ancestry`, `_select_lock_adapter`) and for the legacy reference dispatchers
(`_select_dispatcher`). We extend it to runtime adapters:

```
core/models/lifecycle.py        AgentRuntimeKind += CLAUDE_SDK, OPENCODE_RUN   [provider-agnostic]
core/protocols/agent_runtime.py AgentRuntimePort (unchanged — already LIVE)
infrastructure/
  codex_runtime.py              CodexExecAdapter (unchanged — first adapter)
  opencode_runtime.py   (NEW)   OpenCodeAdapter  — stub, runtime_kind=OPENCODE_RUN
  claude_sdk_runtime.py (NEW)   ClaudeSdkAdapter — stub, runtime_kind=CLAUDE_SDK
container.py                    build_agent_runtime(kind, *, …) -> AgentRuntimePort  (NEW)
```

**Layering law honored:** adapters that do subprocess/SDK I/O live only in `infrastructure/`;
`core/` and `features/` never import them. `container.py` is the only place that maps a
`AgentRuntimeKind` to a concrete adapter — exactly as it maps `PLATFORM` to OS adapters and runtime
strings to dispatchers today.

**Why stubs, not full adapters:** the EPIC's design is "ship the port; adapters are mechanical
follow-ups behind it." Codex is already a real adapter. Claude SDK needs an unapproved dependency
(deferred). OpenCode's permission/stream API is unverified (deferred). Both ship as documented
`NotImplementedError` stubs so the factory is complete and total over the enum, and a later release
swaps a stub body for a real implementation with zero call-site change.

## Test strategy

- **Unit (`tests/unit/`)** — enum round-trip; factory→port mapping per kind; unknown-kind error;
  stub `run()` raises `NotImplementedError` with the documented substring; `runtime_kind()` identity.
- **Reuse** the existing `FakeAgentRuntime` pattern (`tests/unit/features/lifecycle/`) to prove
  `LifecycleAgentRunner(runtime=build_agent_runtime(FAKE, …))` still transitions green.
- **Hermetic:** no real venv (autouse `_no_real_venv_in_tests`), no subprocess, no model calls,
  `_repo_root_write_guard` clean.
- **Gates locally runnable:** `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`.

## Sequencing

Hard spine: T-016-00 (release start) → W1 (enum) → W2 (factory) depends on W3+W4 (adapters exist) →
W5 (tests) → review gate → CLOSURE. W3 and W4 are disjoint (two new files) and parallelizable; W2
imports both. One `[-]` per owner at a time unless write sets are disjoint as declared.

## Risk register

| Risk | Sev | Mitigation |
|---|---|---|
| Enum addition breaks an exhaustive match elsewhere | LOW | grep for `AgentRuntimeKind.` matches; mypy `--strict` catches non-exhaustive handling |
| Factory becomes a dumping ground | LOW | keep it a pure dispatch fn mirroring `_select_dispatcher`; no business logic |
| Stub mistaken for working adapter | LOW | `NotImplementedError` message names the deferred workstream + dep |
| Scope creep into WS-1/WS-3 | MED | TASKS marks them OUT; this release adds construction surface only |
