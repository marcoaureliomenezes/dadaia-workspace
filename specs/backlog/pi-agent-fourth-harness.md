---
name: pi-agent-fourth-harness
status: delivered
type: epic
reported: 2026-06-25
owner: project-manager
relates_to: adr-pi-headless-vs-rpc, sdk-lifecycle-engine-multiharness-antislop, adr-procedural-multiharness-lifecycle-engine
surface: core/models/lifecycle, infrastructure/pi_runtime, container, cli/commands/lifecycle, public/pi, features/telemetry
intents:
  - subject: { kind: catalog, ref: "context-management" }
    change: "WS-PI-5 (residual, operator-gated): DEAD-mark the standalone dadaia-pi-workspace context with a deprecation pointer to this epic (clean tree first); never delete the repo"
---

# EPIC — PI as the Fourth Fully-Supported Harness

**Owner:** project-manager (curates) → product-engineer (release definition after a MANDATORY grill).
**Status:** DELIVERED-IN-PART — core PI fourth-harness shipped v0.1.18–v0.1.21 (merged to
main: `PiHeadlessAdapter`, `AgentRuntimeKind.PI_HEADLESS`, container/CLI wiring, `.pi/`
Ring-1 extension), and **WS-PI-6 (PI telemetry adapter + reader + academy module) shipped in
v0.1.30** (`features/telemetry/reader/pi.py` + `PiRuntimeAdapter` + `ADAPTER_REGISTRY["pi"]` +
panel A12 wiring — see `specs/_archive/releases/v0.1.30/CLOSURE.md`).
**Final disposition:** CONSUMED — v0.1.38. The last residual, **WS-PI-5**, is complete:
`dadaia-pi-workspace` now carries a deprecation pointer on its remote `main` branch and the
workspace context is DEAD. The local checkout was removed by `dadaia context dead`; the remote
repo and history were not deleted.
**ADR:** `specs/backlog/adr-pi-headless-vs-rpc.md` (transport, ring-boundary, and fold-in decisions).
**Design report:** `.dadaia/reports/dadaia-workspace/software-architect/2026-06-25T-pi-fourth-harness-design.md`
**Builds on:** `multiharness-engine-v0116` (the two-layer engine: `AgentRuntimePort`,
`build_agent_runtime`, `LifecyclePhaseWorkflow`/`LifecyclePipeline`, per-step `--harness`).

---

## Thesis

PI (`@earendil-works/pi-coding-agent`) becomes the **fourth `AgentRuntimeKind`**, peer to
Claude Code, Codex, and OpenCode. The engine is harness-agnostic by construction, so PI is
a **clean adapter addition**: the engine spine (`core/scope_match.py`,
`features/lifecycle/agent_runner.py`, `phase_workflow.py`, `pipeline.py`) needs **ZERO**
changes. PI ships in two layers exactly like the others: a second-layer **adapter** behind
the port (workers), and a first-layer **`.pi/` projection** (the operator "enters pi" with
dadaia context/rules).

**Key correction (see ADR Decision 1):** PI is **not** a free-text-only harness. It ships
`pi --mode json` — a deterministic line-delimited JSON event stream with `message_end`
events carrying a typed `AgentMessage`. The transport is therefore the direct analog of
Codex `--output-last-message`, not a fragile free-text parser. The brief's
sentinel-JSON-via-append-system-prompt approach is demoted to a degraded fallback only.

## Ordered, independently-shippable workstreams

Each workstream is a standalone release slice with its own SPEC/PLAN/TASKS. Order reflects
dependency and confidence (highest-confidence core first).

---

### WS-PI-1 — Second-layer `PiHeadlessAdapter` (the core)

**Goal.** Add PI as a live `AgentRuntimeKind` so `--harness pi` / `--step-harness x=pi`
work across every `dadaia lifecycle` verb automatically.

**Touch points (file:line).**
1. `core/models/lifecycle.py:45-49` — add `PI_HEADLESS = "pi_headless"` to
   `AgentRuntimeKind`. No change needed to `AgentRunRequest.to_dict/from_dict`
   (lines 264-299) or `AgentRunResult` (302-331) — they round-trip `runtime` via
   `AgentRuntimeKind(str(...))`, so the new member is covered automatically. Verify the
   round-trip in `tests/unit/core/test_agent_runtime_kind.py`.
2. `infrastructure/pi_runtime.py` (NEW) — `PiHeadlessAdapter` + frozen `PiHeadlessConfig`,
   **mirroring `CodexExecAdapter` (`codex_runtime.py:49-216`)**:
   - `PiHeadlessConfig(cwd, pi_bin="pi", model=None, timeout_seconds=900,
     env_allowlist=(...), tools=("read","write","edit","bash"))`. Env allowlist must
     include `ANTHROPIC_API_KEY` (PI auth) **and** redact it from output (the
     `_redact` helper already covers `*_KEY`).
   - `runtime_kind()` returns `AgentRuntimeKind.PI_HEADLESS`.
   - `run()` validates `request.runtime is AgentRuntimeKind.PI_HEADLESS` (mirror
     `codex_runtime.py:72-77`), builds the command
     `pi --mode json --tools <csv> -p -` (prompt on stdin, mirror `_prompt`
     at `codex_runtime.py:154-169`), runs via `subprocess.run` with the same
     timeout/OSError handling (`codex_runtime.py:82-104`), and maps the result.
   - Imports **no PI client at module load** — subprocess only (offline-first preserved,
     mirroring the optional/lazy posture of `claude-agent-sdk`).
3. `container.py:303-340` — add a `PI_HEADLESS` branch to `build_agent_runtime`,
   lazy-importing `PiHeadlessAdapter` (mirror the `CODEX_EXEC` branch at 325-331). Keep the
   factory total over the enum.
4. `cli/commands/lifecycle.py:27-32` — add `"pi": AgentRuntimeKind.PI_HEADLESS` to
   `_HARNESS_KINDS`. `_resolve_harness` (371-376) then resolves `--harness pi` and
   `--step-harness x=pi` for free across all verbs.

**Acceptance.**
- `pytest tests/unit/core/test_agent_runtime_kind.py` covers the new enum member round-trip.
- New `tests/unit/infrastructure/test_pi_runtime.py` (mirror `test_codex_runtime.py`): an
  injected fake `Runner` returns a canned JSONL stream; assert `AgentRunResult` mapping,
  runtime-kind mismatch → FAILED, timeout → FAILED, OSError → FAILED, secret redaction.
- `tests/unit/test_build_agent_runtime.py` covers the new factory branch (returns a
  `PiHeadlessAdapter`; factory stays total).
- `--harness pi` and `--step-harness x=pi` resolve without touching `phase_workflow.py` /
  `pipeline.py`.

**Risk.** Low. The adapter is structurally identical to `CodexExecAdapter`. The only
net-new logic is JSONL parsing, isolated in WS-PI-2 (WS-PI-1 may ship with a minimal
"last `message_end` → summary" parser and WS-PI-2 hardens it).

**Deferred/uncertain seams.** Live `pi` binary behavior is operator-environment-dependent
(Node + `ANTHROPIC_API_KEY`); the unit suite is fully faked — a `tests/integration/pi_live/`
opt-in (`DADAIA_PI_LIVE=1`) is the live-verification seam, mirroring
`tests/integration/codex_live/`. Do not gate CI on a live `pi`.

---

### WS-PI-2 — Result-extraction contract (typed `AgentRunResult` from the JSON stream + real `changed_paths`)

**Goal.** Turn the `pi --mode json` JSONL stream into a typed `AgentRunResult`, and give
Ring-2 a **trustworthy** `changed_paths` signal.

**Touch points (file:line).**
1. `infrastructure/pi_runtime.py` (extends WS-PI-1) — `_result_from_output(stdout, proc)`:
   - Parse stdout as JSONL; take the **last** `{"type":"message_end","message":{...}}`
     event; extract the assistant message text from `message.content`. This is the analog
     of `codex_runtime.py:171-206` reading `--output-last-message`.
   - **Degraded fallback** (mirror `codex_runtime.py:182-186`): if no `message_end` is
     found or a line is unparseable, treat raw stdout as the summary (SUCCEEDED) rather than
     failing — robustness over strictness, exactly as Codex does.
   - Map review-style structured fields (`verdict`, `commit_sha`, `summary`,
     `artifact_refs`) the runner already reads (`agent_runner.py:127-160`). When the final
     assistant message carries a fenced JSON block matching the requested
     `request.expected_schema`, parse it into `structured_output`; otherwise leave
     `structured_output` minimal. The **append-system-prompt sentinel** survives ONLY here,
     as the in-band channel for review verdicts, NOT as the primary transport.
2. `infrastructure/pi_runtime.py` — **`changed_paths` via git diff (NOT model self-report).**
   Before `run()` spawns `pi`, snapshot `git rev-parse HEAD` (or stash-free
   `git status --porcelain` baseline) in `cwd`; after, compute
   `git diff --name-only` of the worker's changes and write the comma-separated list into
   `result.structured_output["changed_paths"]` — the exact field `agent_runner.py:126-130`
   splits on `,`. Use the existing `GitSubprocessClient` (`infrastructure/`) rather than raw
   subprocess, keeping the OS-call boundary in infrastructure.

**Acceptance.**
- Unit tests assert: last-`message_end` extraction; multi-`message_end` (last wins);
  unparseable line → degraded summary, not crash; fenced-JSON verdict block → populated
  `structured_output`; `changed_paths` reflects a faked git-diff (not a model claim).
- An end-to-end faked-runner test through `LifecycleAgentRunner` shows an out-of-scope
  `changed_paths` triggers the Ring-2 block (`agent_runner.py:114-123`), proving PI has a
  real write-boundary.

**Risk.** Medium. The `--mode json` event schema is upstream-owned. Mitigation: pin/record
the verified `pi` version in `tech-stack.md`, key only on the documented `type` discriminator
and `message`/`content` fields, and keep the degraded fallback so a schema drift downgrades
to a summary rather than a crash.

**Deferred/uncertain seams.** The exact `AgentMessage.content` shape (string vs content
blocks) must be live-verified against the pinned `pi` build before the parser is finalized
(`tests/integration/pi_live/`). Until then the parser handles both shapes defensively.

---

### WS-PI-3 — First-layer `.pi/` projection target ("enter pi" with dadaia context)

**Goal.** The operator can launch `pi` in the workspace and get dadaia context/rules, the
same way `claude`/`codex`/`opencode` are projected.

**Touch points (file:line — design-level; exact lines set at SPEC time).**
1. `dadaia_workspace/public/pi/` (NEW source tree) — canonical PI first-layer assets:
   `AGENTS.md` (or PI's `SYSTEM.md`), `.pi/settings.json`, `.pi/skills/**`,
   `.pi/prompts/**`, `.pi/extensions/**` (WS-PI-4 lands the gate extension here). Salvage the
   surface map from `dadaia-pi-workspace`'s `pi-native-agent-surface.md`.
2. `dadaia public install` — add a `pi` target alongside `claude`/`codex`/`opencode` (the
   install/stage/doctor chain in `public-asset-distribution`). `--target pi` projects
   `public/pi/` into `.pi/`; `--target all` includes it. Frontmatter-strip / format-adapt as
   the other targets do.
3. `dadaia public doctor` — add PI projection drift checks (source↔staging↔projected),
   mirroring the per-target doctor checks. Register PI assets in
   `.dadaia/agentic/manifest.json` so they are lib-originated (never hand-edited).

**Acceptance.**
- `dadaia public install --target pi` produces a `.pi/` tree; `--target all` includes it;
  `dadaia public doctor` exits 0 with a `[ok]` PI line; re-running install is idempotent.
- The projected `.pi/` carries dadaia's context-injection + SDD discipline instructions
  (sourced from `public/`, not duplicated).
- No private paths/names leak into `public/pi/` (privacy gate stays green).

**Risk.** Medium. PI's trust model means `.pi/**` is **executable TypeScript run as the
user with no sandbox** — a real security boundary. The projected assets must be minimal and
auditable; document the trust boundary explicitly (salvage `dadaia-pi-workspace`
constitution §11). This WS ships projection only; the executable gate extension is WS-PI-4.

**Deferred/uncertain seams.** Whether PI reads `AGENTS.md` natively or needs `SYSTEM.md`
(and whether a `CLAUDE.md`-style bridge is required) must be live-verified against the pinned
`pi` build before finalizing the projection shape.

---

### WS-PI-4 — Ring-1 `.pi/extensions/dadaia-sdd-gate.ts` (pre-disk tool_call gate) — DEFERRED

**Goal.** Give PI a pre-disk write boundary equivalent to Claude SDK's `write_permission`,
via a `.pi/` TypeScript extension intercepting `tool_call` for write-like tools post-trust.

**Touch points (design-level).**
1. `public/pi/.pi/extensions/dadaia-sdd-gate.ts` (NEW) — a `tool_call` interceptor that, for
   write/edit/bash tools, classifies the target path against the active context's
   allowed/forbidden scope and the SDD path-class taxonomy, denying out-of-scope writes
   before disk. Mirrors the **classifier** Claude SDK reuses (`core/scope_match.is_in_scope`)
   and the SDD path-class logic — the extension must call a thin, stable contract (e.g. read
   the lease/scope state files), not re-implement the gate.
2. Salvage `dadaia-pi-workspace` constitution §7 (Pi enforcement model) as the design spec.

**Acceptance.**
- Post-trust, an out-of-scope write attempt inside `pi` is denied pre-disk with an
  actionable message; an in-scope write proceeds.
- The extension degrades safely (fails toward Ring-2 + chokepoints) when context state is
  indeterminate — never a silent allow of a clearly out-of-scope MUTATING write, never a
  false block of ADDITIVE work.

**Risk.** High and explicitly deferred. (a) The extension loads only **after operator
trust** — it is not a sandbox; (b) it is TS in a Python-owned engine, a cross-language
contract; (c) Ring-2 + git chokepoints already provide the deterministic backstop. Ship only
after WS-PI-1/2 are live and the `tool_call` extension API is live-verified.

**Deferred/uncertain seams.** PI's `tool_call` interception API surface and how an extension
reads workspace state must be live-verified; until then PI's enforcement posture is
Ring-2-only (identical to Codex/OpenCode), which is acceptable.

---

### WS-PI-5 — Absorb and retire `dadaia-pi-workspace`

**Goal.** Honor the operator directive ("no 2 projects") by folding PI into dadaia-workspace
and retiring the standalone PoC, salvaging its specs as input.

**Touch points.**
1. Salvage into this EPIC's downstream SPECs: `dadaia-pi-workspace`
   `specs/constitution.md` §11 (security law) → WS-PI-3/4 security docs;
   `pi-native-agent-surface.md` → WS-PI-3 projection; constitution §7 (enforcement) →
   WS-PI-4.
2. Add a deprecation `README.md` to `repos/dadaia-pi-workspace/` pointing at this EPIC;
   `dadaia context` DEAD-mark the `dadaia-pi-workspace` context (clean tree first, per the
   `dead()` discipline). **Never delete** the repo (history/evidence).

**Acceptance.**
- The pi-workspace context is DEAD with a deprecation pointer; no orphaned ALIVE context
  with open work remains; the salvaged facts are cited (not duplicated) in PI SPECs.

**Risk.** Low. Pure curation/deprecation; no production code. Sequence after WS-PI-1 so the
fold-in target actually exists.

---

### WS-PI-6 (optional) — Telemetry adapter + academy doc

**Goal.** Surface PI sessions in the panel and document PI in the academy.

**Touch points (file:line).**
1. `features/telemetry/aggregator/runtimes.py:354-358` — add a PI entry to
   `ADAPTER_REGISTRY` (today claude, codex only) **iff** PI emits a consumable local
   session artifact (jsonl/sqlite). If PI has no local session store, this WS is a no-op and
   should be dropped rather than faked.
2. Academy module documenting PI as the fourth harness (enter-pi flow, trust boundary,
   per-step `--harness pi`).

**Acceptance.** PI sessions appear in the panel Agents/Sessions tab **only if** a real local
session source exists; otherwise the WS is explicitly closed as not-applicable (no
placeholder telemetry).

**Risk.** Low. Optional; gated on a real telemetry source. **Anti-slop guard:** do NOT
invent a telemetry adapter with no source — that is monitoring theater.

---

## Recommended first release slice

**WS-PI-1 + WS-PI-2 together** as the first release (`pi-fourth-harness-v1` or similar). They
deliver the highest-confidence, highest-value core: PI is a live, per-step-selectable harness
with a deterministic typed result and a **real Ring-2 write-boundary** (git-diff
`changed_paths`). This is fully testable offline with faked runners and changes **zero**
engine-spine files. WS-PI-3 (projection) follows; WS-PI-4 (Ring-1) and WS-PI-6 (telemetry)
are deferred/optional; WS-PI-5 (retire pi-workspace) is curation that can run alongside.

## Anti-slop / root-cause guards (architect gates)

- **Speculative generality (REJECTED in primary path):** `--mode rpc` and the TS SDK are
  NOT adopted now — the engine is one-shot-per-step; a long-lived RPC session or a
  Python↔Node SDK bridge is unneeded surface. Deferred behind a concrete future need.
- **Fragile parser (REJECTED):** the free-text→sentinel-JSON parser is demoted to a degraded
  fallback; `--mode json` is the deterministic primary transport.
- **Monitoring theater (GUARDED):** WS-PI-6 telemetry ships only with a real local session
  source; otherwise it is closed, not faked.
- **Write-boundary integrity (ROOT-CAUSE):** `changed_paths` MUST come from `git diff`, not
  model self-report — a worker cannot be trusted to declare what it wrote. Without this,
  Ring-2 has no real signal and PI ships unenforced.
- **No duplicated stack (ROOT-CAUSE):** folding PI in (not a parallel pi-workspace) prevents
  the two-non-converged-systems defect the multiharness ADR exists to kill.

## What this EPIC does NOT authorize

No production edits. Implementation requires the operator to pick this EPIC into a release, a
mandatory `dadaia-grill-me` session, and product-engineer-authored SPEC/PLAN/TASKS under an
approved SDD gate.

## Consumed Evidence

- Release: `specs/releases/v0.1.38/alpha-1/`
- Standalone repo deprecation commit: `dadaia-pi-workspace` `main` at
  `4ffc2376666ba324a1ebf8c6bc8b387048e43719`
- Context state: `dadaia context show dadaia-pi-workspace --json` reports `"state": "dead"`.
- Local checkout: `repos/dadaia-pi-workspace/` absent after `dadaia context dead`.
