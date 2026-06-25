# SPEC: Release — pi-fourth-harness-v1

> **Status:** Aprovado
> **Release ID:** pi-fourth-harness-v1
> **Owner:** product-engineer
> **Phase:** SPEC → PLAN → TASKS → IMPLEMENTATION
> **Scope:** EPIC `pi-agent-fourth-harness` workstreams **WS-PI-1 + WS-PI-2** only
> **Binding ADR:** `specs/backlog/adr-pi-headless-vs-rpc.md`

## Objective

Make PI (`@earendil-works/pi-coding-agent`) a **live, fully-supported fourth harness**,
peer to Claude Code, Codex, and OpenCode, selectable per lifecycle step via `--harness pi`
and `--step-harness x=pi`. This release delivers the highest-confidence core of the EPIC:

- a real `AgentRuntimeKind.PI_HEADLESS` member;
- a second-layer `PiHeadlessAdapter` (subprocess `pi --mode json`) behind the existing
  `AgentRuntimePort`, structurally mirroring `CodexExecAdapter`;
- a typed `AgentRunResult` extracted from PI's line-delimited JSON event stream;
- a **real Ring-2 write boundary** for PI: `changed_paths` derived from `git diff`
  (NOT model self-report), so the engine's post-flight out-of-scope block actually fires.

The result: PI becomes a one-shot-per-step bounded worker with a deterministic typed
result and a trustworthy write boundary, **fully testable offline with faked runners**,
changing **zero** engine-spine files.

## Context — the two-layer architecture

Per the binding ADR and release `multiharness-engine-v0116`, the engine is harness-agnostic
by construction:

- **First agentic layer (thin coordinator):** the operator enters a harness at the
  terminal; the harness calls the `dadaia` CLI. (PI's first-layer `.pi/` projection is
  WS-PI-3 — OUT OF SCOPE here.)
- **Second agentic layer (procedural Python engine):** `dadaia lifecycle` verbs run Python
  workflows that drive bounded agent workers behind `AgentRuntimePort`, selectable per step.

Adding a harness is a clean **adapter addition**. The engine spine
(`core/scope_match.py`, `features/lifecycle/agent_runner.py`, `phase_workflow.py`,
`pipeline.py`) needs **zero** changes. The four touch points are: the enum
(`core/models/lifecycle.py:45-49`), the factory (`container.py:303-340`), the CLI harness
map (`cli/commands/lifecycle.py:27-32`), and one new adapter
(`infrastructure/pi_runtime.py`).

## Product deltas

1. **Harness selection.** `--harness pi` and `--step-harness <step>=pi` resolve and run
   across every `dadaia lifecycle` verb, with no change to `phase_workflow.py` or
   `pipeline.py`. The operator can compose, e.g. `claude implements / pi reviews`, per step.
2. **Typed PI result.** PI worker runs produce a typed `AgentRunResult` (summary,
   `artifact_refs`, `structured_output`) parsed from the `pi --mode json` event stream.
3. **PI write boundary.** PI worker writes are constrained by the engine's Ring-2 post-flight
   block: an out-of-scope `changed_paths` (computed from `git diff`) blocks the transition,
   exactly as for Codex/OpenCode.

## Architecture deltas

- **NEW** `infrastructure/pi_runtime.py` — `PiHeadlessAdapter` + frozen `PiHeadlessConfig`,
  mirroring `CodexExecAdapter` (`codex_runtime.py:49-216`). Lives in the **infrastructure**
  layer; imports no PI client at module load (subprocess only — offline-first preserved,
  mirroring the optional/lazy posture of `claude-agent-sdk`).
- **`container.build_agent_runtime`** gains a `PI_HEADLESS` branch (lazy-import the adapter,
  mirror the `CODEX_EXEC` branch at `container.py:325-331`). The factory stays **total** over
  the enum — the `ValueError` path is intact.
- **Layering invariant unchanged.** `features/` must not import `infrastructure/` directly
  (DI via the port); `infrastructure/` depends only on `core/`. `core/scope_match.py` is
  untouched — the Ring-2 classifier is reused, not re-implemented. The 6 import-linter
  contracts in `setup.cfg` must stay 6 kept / 0 broken.
- **Git-diff helper.** The adapter computes `changed_paths` via a `git diff --name-only`
  against a pre-run baseline. The OS-call boundary stays in **infrastructure** — implemented
  through the existing `GitSubprocessClient` (`infrastructure/git_subprocess.py`), extended
  with a name-only diff helper (the client currently has no diff method).

## Tech-stack deltas

- New **operator-environment runtime dependency for live execution only:** Node + the `pi`
  binary (`@earendil-works/pi-coding-agent`) + `ANTHROPIC_API_KEY`. This is NOT a Python
  package dependency and NOT a build/test dependency — the adapter is a subprocess and the
  unit suite is fully faked. The verified `pi` version is pinned/recorded in
  `specs/memory/tech-stack.md` at CLOSURE, after live verification.

## Security / operations deltas

- **Secret redaction.** `PiHeadlessConfig.env_allowlist` must include `ANTHROPIC_API_KEY`
  (PI auth) and the adapter's `_redact` helper must redact it from all output (reuse the
  existing `*_KEY`/`*_TOKEN`/`*_SECRET` redaction pattern from `codex_runtime.py:208-215`).
- **Write boundary.** PI ships on the same posture as Codex/OpenCode: **Ring-2 post-flight +
  git chokepoints** (pre-commit lease gate, pre-push security-verdict gate). PI has no
  CLI-level pre-disk (Ring-1) gate in this release — that is WS-PI-4, explicitly deferred.
  The non-negotiable here is that `changed_paths` comes from `git diff`, NOT a model claim,
  so Ring-2 has a real signal. Without it, PI would ship with no write boundary — unacceptable.

## Memory files affected at closure

- `specs/memory/tech-stack.md` — record PI (`pi --mode json` subprocess harness), the live
  runtime requirement (Node + `pi` binary + `ANTHROPIC_API_KEY`), and the **verified `pi`
  version pin**.
- `specs/memory/architecture.md` — add `PI_HEADLESS` to the `AgentRuntimeKind` /
  `build_agent_runtime` adapter list and note the four-harness adapter set.
- `specs/memory/product/<harness-or-lifecycle-feature-slug>.md` — update the harness-selection
  feature atom to list PI as the fourth selectable harness (exact slug confirmed at CLOSURE).

## Acceptance criteria

- **AC1 — Enum.** `AgentRuntimeKind.PI_HEADLESS = "pi_headless"` exists;
  `AgentRunRequest.to_dict/from_dict` round-trips it (already via `AgentRuntimeKind(str(...))`,
  no model change). Covered in `tests/unit/core/test_agent_runtime_kind.py`.
- **AC2 — Adapter run/mapping.** `PiHeadlessAdapter.runtime_kind()` returns `PI_HEADLESS`;
  `run()` validates `request.runtime is PI_HEADLESS` (mismatch → FAILED), builds
  `pi --mode json --tools <csv> -p -` (prompt on stdin), runs via an injected
  `subprocess.run`-style runner, and maps the JSONL stream to a typed `AgentRunResult`.
  Timeout → FAILED; OSError → FAILED; secrets (incl. `ANTHROPIC_API_KEY`) redacted.
- **AC3 — Factory.** `build_agent_runtime(AgentRuntimeKind.PI_HEADLESS)` returns a
  `PiHeadlessAdapter`; the factory stays total (unknown kind still raises `ValueError`).
  Covered in `tests/unit/test_build_agent_runtime.py`.
- **AC4 — CLI.** `_HARNESS_KINDS` includes `"pi": AgentRuntimeKind.PI_HEADLESS`;
  `--harness pi` and `--step-harness x=pi` resolve across all verbs with no change to
  `phase_workflow.py` / `pipeline.py`.
- **AC5 — Result extraction (WS-PI-2).** `_result_from_output` parses stdout as JSONL, takes
  the **last** `{"type":"message_end","message":{...}}` event, extracts assistant text from
  `message.content` (handling BOTH string and content-block shapes defensively). No/unparseable
  `message_end` → **degraded fallback** treats raw stdout as the summary (SUCCEEDED, never
  crashes). A fenced JSON block matching `request.expected_schema` populates `structured_output`
  (the append-system-prompt sentinel is the in-band channel for review verdicts ONLY, not the
  primary transport). `verdict` / `commit_sha` / `summary` / `artifact_refs` map to the fields
  the runner reads (`agent_runner.py:127-160`).
- **AC6 — Real Ring-2 boundary (WS-PI-2 root-cause).** Before `run()` spawns `pi`, the adapter
  snapshots a git baseline in `cwd`; after, it computes `git diff --name-only` and writes the
  comma-separated list into `result.structured_output["changed_paths"]` (the field
  `agent_runner.py:126-130` splits on `,`). An end-to-end faked-runner test through
  `LifecycleAgentRunner` proves an out-of-scope `changed_paths` triggers the Ring-2 block
  (`agent_runner.py:114-123`). The path list comes from git diff, never from a model claim.
- **AC7 — Gate green.** `dadaia ci preflight` (ruff format/check, mypy --strict, pytest) is
  green, AND `lint-imports` reports 6 kept / 0 broken (run manually — preflight does NOT run
  lint-imports).
- **AC8 — Live seam.** A `tests/integration/pi_live/` opt-in (`DADAIA_PI_LIVE=1`, skipped by
  default, mirroring `tests/integration/codex_live/`) exists and is documented as the
  live-`pi`-binary verification seam. It is NOT CI-gated.

## Out of scope (deferred — DO NOT implement in this release)

- **WS-PI-3** — first-layer `.pi/` projection target (`public/pi/`, `dadaia public install
  --target pi`, doctor PI drift checks). Deferred.
- **WS-PI-4** — Ring-1 `.pi/extensions/dadaia-sdd-gate.ts` pre-disk `tool_call` gate. Deferred
  (High risk; loads only post-trust; Ring-2 + chokepoints are the backstop).
- **WS-PI-5** — absorb/retire `dadaia-pi-workspace`. Deferred (curation; may run alongside).
- **WS-PI-6** — telemetry adapter + academy doc. Deferred/optional (anti-slop: only if a real
  local PI session source exists).
- **`pi --mode rpc`** transport and the **TypeScript SDK** in-process path — rejected for the
  primary path per ADR Decision 1 (speculative generality / Python↔Node bridge). Not adopted.
- Any change to `phase_workflow.py`, `pipeline.py`, `core/scope_match.py`, or any engine-spine
  file. Strictly a clean adapter addition.

## Decision reference — headless vs RPC

Transport is fixed by ADR `adr-pi-headless-vs-rpc` **Decision 1**: adopt `pi --mode json`
headless subprocess (deterministic typed event stream, the direct analog of Codex
`--output-last-message`). `pi -p` free-text + sentinel parser is rejected as fragile slop and
survives only as a degraded fallback; `--mode rpc` and the TS SDK are deferred. Write-boundary
is fixed by **Decision 2**: Ring-2 now, Ring-1 (WS-PI-4) later, with `changed_paths` sourced
from `git diff`, not model self-report.

## Dependencies and risks

- **Dependency:** release `multiharness-engine-v0116` (the two-layer engine + port + factory +
  per-step `--harness`) is LIVE on disk. Confirmed by inspection of the four touch-point files.
- **Risk (the single unverified seam):** the live `pi --mode json` event schema — specifically
  the `AgentMessage.content` shape (string vs content-block array) — is **upstream-owned** and
  must be **live-verified on first networked install** with `ANTHROPIC_API_KEY` + Node `pi`
  present (`tests/integration/pi_live/`). This is the ONE unverified binding in the release.
  ALL engine integration + mapping logic is real and faked-tested offline. Mitigation: key only
  on the documented `type` discriminator and `message`/`content` fields, handle both content
  shapes defensively, and keep the degraded fallback so a schema drift downgrades to a summary
  rather than a crash. Pin/record the verified `pi` version in tech-stack memory at CLOSURE.
- **Risk (low):** the new git-diff helper on `GitSubprocessClient` is the only net-new git
  surface; it is faked in unit tests and exercised live only via the opt-in seam.
