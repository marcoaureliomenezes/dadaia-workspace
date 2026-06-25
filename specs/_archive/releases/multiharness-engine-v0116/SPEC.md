# SPEC — Release: multiharness-engine-v0116

**Status:** Aprovado
**Release ID:** multiharness-engine-v0116
**Owner:** product-engineer
**Opened:** 2026-06-24
**Branch:** `feature/v0.1.16` (stacked on `feature/v0.1.15`, operator holds merges)
**Maturity:** alpha-1

---

## 1. Problem and context

The workspace ships two non-converged SDD-driving systems: a real-but-half-wired procedural
lifecycle engine (`features/lifecycle/`, spine LIVE) and a reference-only markdown-workflow layer
(`dadaia orchestrate`, dispatchers that spawn nothing). The operator wants ONE procedural-Python
engine that drives each lifecycle phase by issuing scoped prompts to a **per-step-selectable
harness** behind `AgentRuntimePort` — SDK-first in-process, headless-fallback subprocess.

Source of truth: ADR `adr-procedural-multiharness-lifecycle-engine.md`, EPIC
`sdk-lifecycle-engine-multiharness-antislop.md` (reframed engine-led 2026-06-24), and the
investigation report
`.dadaia/reports/dadaia-workspace/software-architect/2026-06-24T004654Z-multiharness-workflow-engine-shift.html`.

**The structural gap this release closes:** `LifecycleAgentRunner` already accepts a `runtime:
AgentRuntimePort` by injection (`features/lifecycle/agent_runner.py:43`), but **nothing in
`container.py` selects or constructs an adapter by kind** — there is no factory, and
`AgentRuntimeKind` (`core/models/lifecycle.py:45`) knows only `FAKE` and `CODEX_EXEC`. Without that
seam, "selectable / mixable harness per step" is impossible. This release lands that seam.

**Grill-me:** compressed and coordinator-conducted under the operator's autonomous directive
(`/goal "pick the big change and define the release and implement it"`, 2026-06-24). The scoping
decisions a grill would surface are pre-answered as ADR-1..ADR-5 below. The mandatory interactive
grill is recorded as **compressed**; open questions are tracked in §5.

---

## 2. Objective

Land the **per-step harness-selection spine** of the multi-harness workflow engine: a
`build_agent_runtime(kind, ...) -> AgentRuntimePort` factory plus the full adapter set behind the
port, so any lifecycle step can run on a selectable, mixable harness — Codex headless today; Claude
Agent SDK and OpenCode as documented stubs behind the same port.

---

## 3. Scope (alpha-1 — IN, implemented this wave)

| Cluster | Acceptance |
|---|---|
| **W1 — Runtime kinds** | `AgentRuntimeKind` gains `CLAUDE_SDK` and `OPENCODE_RUN`; `AgentRunRequest` to_dict/from_dict round-trip every member. |
| **W2 — Runtime factory** | `build_agent_runtime(kind, *, …) -> AgentRuntimePort` in `container.py`, mirroring the `_select_dispatcher`/`PLATFORM` seam: `FAKE→FakeAgentRuntime`, `CODEX_EXEC→CodexExecAdapter`, `OPENCODE_RUN→OpenCodeAdapter`, `CLAUDE_SDK→ClaudeSdkAdapter`. Unknown kind → explicit error. The returned port's `runtime_kind()` matches the requested kind. |
| **W3 — OpenCode adapter stub** | `OpenCodeAdapter` (`infrastructure/opencode_runtime.py`) implements `AgentRuntimePort`; `runtime_kind()==OPENCODE_RUN`; `run()` raises `NotImplementedError` with a documented message (degrade-to-Ring-2 noted, API unverified). |
| **W4 — Claude SDK adapter stub** | `ClaudeSdkAdapter` (`infrastructure/claude_sdk_runtime.py`) implements `AgentRuntimePort`; `runtime_kind()==CLAUDE_SDK`; `run()` raises `NotImplementedError` (requires `claude-agent-sdk`; live integration deferred to a dep-approval release). No new dependency added. |
| **W5 — Tests** | Hermetic unit tests: enum round-trip; factory returns the right port per kind + rejects unknown; both stubs raise with the documented message; `FakeAgentRuntime` still drives `LifecycleAgentRunner` green. No real venvs, no real model calls. |

A `FakeAgentRuntime` for tests already exists in the test tree; this release does not relocate it.

---

## 4. Out of scope (DEFINED, deferred — do not let leak)

- **WS-1 — per-phase workflow orchestrators** (replace the `unavailable_workflow` stubs in
  `cli/commands/lifecycle.py`). Highest behavioral risk; ship shadow-first in a following alpha.
- **WS-3 — collapse the markdown `orchestrate` layer** (retire the 4 dispatchers, re-point the
  panel workflow tab). High blast radius; separate atomic release.
- **WS-4 live — real Claude Agent SDK integration** (`can_use_tool` Ring-1). Needs operator
  approval to add `claude-agent-sdk` (per-token API-key billing) + a tech-stack memory update in a
  DEFINITION phase. Stub only this release.
- **WS-6 anti-slop self-governance**, **WS-7 prompt prefix-cache**, **D12 surface-collapse
  execution.**
- The pre-existing `codex-config-emits-invalid-approved-commands` bug (separate LOW cleanup).

---

## 5. Dependencies, risks, open questions

- **Builds on** the v0.1.15 deterministic-lifecycle kernel (CLOSED) — its lease/run liveness,
  `gate_policy` classifier, and `AgentRuntimePort`/models are reused, not duplicated.
- **Risk (LOW):** the factory is pure construction + injection; the only runtime behavior added is
  two `NotImplementedError` stubs. Blast radius is contained to `container.py` + two new
  infrastructure files + the enum. No existing call path changes behavior (nothing wires the factory
  into a live workflow yet — that is WS-1).
- **ADR-1:** Adapter stubs ship behind the port now (EPIC: "the port is shipped; adapters are
  mechanical follow-ups"). Confirmed IN.
- **ADR-2:** No `claude-agent-sdk` dependency this release — keeps the build offline-first and avoids
  an unapproved dep. Confirmed.
- **ADR-3:** New adapters live in `infrastructure/` (the only layer allowed `subprocess`/SDK I/O);
  `core/` and `features/` stay provider-agnostic. Confirmed.
- **ADR-4:** Factory mirrors the existing `PLATFORM`/`_select_dispatcher` selection idiom rather than
  inventing a registry. Confirmed.
- **ADR-5:** Panel, Spec Context Project model, and Canonical SDD specs format remain untouched
  (this release adds construction surface only). Confirmed.
- **Open question (tracked, non-blocking):** OpenCode's pre-execution permission callback and
  `opencode run --format json` schema are unverified — resolved when WS-3/WS-5-live is built, not
  here. The stub records this.
