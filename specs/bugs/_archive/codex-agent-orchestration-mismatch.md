---
title: codex-agent-orchestration-mismatch
severity: Critical
opened: 2026-06-04
session_id: sess_6bf8281d
status: Closed
closed: 2026-06-04
closed_by_release: v0.1.4.2
---

# Bug: codex-agent-orchestration-mismatch

## Description

The workspace claims Codex agent orchestration support, but the implemented
Codex dispatcher does not spawn Codex subagents. It writes invocation files and
returns `AWAITING_GATE`. Operators therefore expect visible Codex agent fan-out,
while the CLI behaves as a manual handoff queue.

This creates a serious runtime parity gap:

- Codex personas say project-manager dispatches agents via an Agent tool or
  deferred `tool_search` multi-agent tool.
- `CodexAgentDispatcher.capabilities()` advertises `supports_parallel=True`.
- The implementation is sequential and file-based, with no call into Codex
  subagent execution.
- The operator sees no spawned agents unless the Codex conversation itself is
  explicitly instructed to use subagents.

## Steps to reproduce

1. Inspect `dadaia_workspace/infrastructure/codex_agent_dispatcher.py`.
2. Observe `dispatch()` writes `invocation_path` and returns
   `StageStatus.AWAITING_GATE`.
3. Observe `dispatch_parallel()` returns `tuple(self.dispatch(inv) for inv in
   invocations)`, so it is sequential.
4. Inspect projected agent wording:
   `rg -n "Agent tool|tool_search|supports_parallel|CodexAgentDispatcher" dadaia_workspace/public/agents dadaia_workspace/infrastructure specs/memory`
5. Expected: either Codex orchestration actually spawns subagents through the
   Codex runtime, or all docs/personas/capabilities clearly say Codex CLI
   orchestration is manual/reference-only.
6. Actual: docs and capabilities imply real dispatch/parallelism while code
   only writes handoff files.

## Environment

- dadaia version: `0.1.4` from `pyproject.toml`
- active release: `v0.1.4.1` / `IMPLEMENTATION`
- runtime: Codex
- OS: Ubuntu Linux 24.04 family, kernel `6.17.0-29-generic`
- Python: `3.12.3`

## Root cause hypothesis

The Codex renderer was adapted from Claude-style agent orchestration, but the
available Codex subagent capability lives in the host conversation tool surface,
not in a stable Python API that the `dadaia` CLI can call from a subprocess.
The product encoded optimistic wording and `supports_parallel=True` before a
real bridge existed.

## Acceptance criteria for fix

- Decide and implement one honest mode:
  - real Codex subagent spawning through a supported integration point, or
  - manual/reference-only Codex orchestration with truthful capabilities.
- If manual/reference-only is chosen, set Codex dispatcher parallel capability
  to false or a distinct partial-parity capability, and update generated
  invocation text accordingly.
- Remove stale `Agent tool` overclaims from Codex-facing project-manager and
  orchestration docs.
- Add regression tests proving Codex orchestration output matches the chosen
  behavior.

## Resolution

Resolved by archived release `specs/_archive/releases/v0.1.4.2/`.

Evidence is recorded in `specs/_archive/releases/v0.1.4.2/CLOSURE.md`:

- `T-BUG-04` made `CodexAgentDispatcher` capabilities truthful.
- `T-BUG-05` aligned Codex-facing orchestration wording.
- `T-BUG-06` added regression coverage for Codex reference-only behavior.
- `T-BUG-10` propagated generated assets and verified public doctor output.

The chosen product mode is manual/reference-only Codex orchestration. Public
doctor records Codex workflows as `[reference-only]`, and tests cover dispatcher
capabilities plus Codex-facing wording.
