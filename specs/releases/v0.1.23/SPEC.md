# SPEC — Release: v0.1.23 — Multi-harness Layer-2 completion + two-layer fidelity

**Status:** Aprovado
**Release ID:** v0.1.23
**Owner:** product-engineer
**Opened:** 2026-06-25
**superseded_by:** v0.1.24

> **SUPERSEDED by v0.1.24 (2026-06-26).** After this release was defined and its
> implementer work landed (T-23-01..12 `[x]`), the operator redesigned the harness model:
> Layer-2 workers become **pi/codex only** and **OpenCode is deleted entirely**. v0.1.23's
> open human gate (T-23-13/14/15: live-validation, CLOSURE, deploy) was never confirmed and
> this release was **never deployed**. v0.1.24 branches off `feature/v0.1.23`, **keeps the
> surviving parts** (RPC-drop ADR-23-1, Codex Ring-2 git-diff parity T-23-05, the
> IMPLEMENTATION→CLOSURE + backtrack pipeline e2e T-23-02/03, the Claude SDK binding
> T-23-09..11 as Layer-1/SDK code), and **reverses the OpenCode work** (deletes the
> `OpenCodeAdapter` from T-23-06..08 and the opencode parity test T-23-04) plus removes
> `claude` from the Layer-2 `--harness` choices. Do NOT close or deploy v0.1.23
> independently — v0.1.24 is the shipping release and carries its acceptance forward.

---

## 1. Problem and context

dadaia-workspace publicly states a "4 harnesses × 2 agentic layers × N transports"
story. An evidence-based audit (verified against the source tree, not the docs) found
that story is **only partially real**. This release makes it genuinely true — every
claimed harness actually executes as a Layer-2 worker — and validates it before the
package version is bumped and deployed.

### Audited facts (the problem statement, cited from on-disk code)

**Layer 2 — workers behind `AgentRuntimePort`, dispatched by the lifecycle pipeline.**
`core/models/lifecycle.py:45` declares five `AgentRuntimeKind` values:

| Kind | Adapter | State (verified) |
|------|---------|------------------|
| `FAKE` | `infrastructure/fake_runtime.py` | Complete test double. Real. |
| `PI_HEADLESS` | `infrastructure/pi_runtime.py` | **REAL.** `pi --mode json` adapter; injectable runner, env allowlist, real git-diff Ring-2 `changed_paths` (`_with_changed_paths`, `_GitDiffPort`), redaction, defensive `message_end` parsing, fail-degraded. 17 unit tests + opt-in live contract test (`tests/integration/pi_live/`, `DADAIA_PI_LIVE=1`, not CI-gated). |
| `CODEX_EXEC` | `infrastructure/codex_runtime.py` | **REAL adapter, two gaps.** `codex exec` adapter; injectable runner, env allowlist, redaction, defensive `last-message.json` parsing. 5 unit tests (mocked). **GAP-A:** no Layer-2 *adapter* live contract test (PI has one; the existing `tests/integration/codex_live/` exercises the **Layer-1 hook** contract, not the `CODEX_EXEC` adapter → `AgentRunResult` mapping). **GAP-B:** no `_GitDiffPort` injected — Codex has NO real Ring-2 `changed_paths` seam (PI does). |
| `CLAUDE_SDK` | `infrastructure/claude_sdk_runtime.py` | **PARTIAL.** The Ring-1 `write_permission` seam (`is_in_scope` decider) and the `AgentRunResult` mapping are real and fully tested via an injectable `query_fn`. But `_default_query_fn` (line 142) is `raise NotImplementedError` — the real `claude-agent-sdk` transport binding (`query()` / `can_use_tool` → `PermissionResultDeny`) is deferred to "first networked install". **Claude cannot run as a Layer-2 worker yet.** |
| `OPENCODE_RUN` | `infrastructure/opencode_runtime.py` | **STUB.** `run()` (line 42) is `raise NotImplementedError`. No live execution. Engine enforcement for this harness degrades to Ring-2 post-flight diff only. |

**Transports.** The codebase has exactly two real Layer-2 transports: **CLI-headless**
(PI, Codex, and the planned OpenCode adapter) and **SDK** (the planned Claude adapter).
**RPC is ABSENT entirely** — zero references in the codebase — yet it is still referenced
as a *stated* transport in governance/docs.

**Layer 1 — entry harness + projection + pre-disk SDD gate.** In good shape. All four
harnesses project via `dadaia public install --target {claude,codex,opencode,pi}`, and
each has a real pre-disk gate delegating to the single Python `pre_gate`: claude
PreToolUse hook, codex PreToolUse wrapper, opencode `tool.execute.before` plugin
(`.opencode/plugins/sdd-gate.ts`, projection + `dadaia_workspace.hooks.sdd_gate`
content-tested in `test_opencode_parity_hardening.py`), pi `tool_call` post-trust
extension (`.pi/extensions/dadaia-sdd-gate.ts`, projection + deep content-invariant tested
in `test_public_assets.py::test_install_target_pi_projects_ring1_sdd_gate_extension`).
**GAP:** the OpenCode gate plugin test asserts projection + a couple of content markers,
but NOT the full content-invariant parity the PI test asserts (write→Write / edit→Edit
mapping, fail-open, venv resolution, block-envelope). Claude/codex hook projections are
only implicitly tested. PI's gate is post-trust (live efficacy not CI-verifiable).

**Default lifecycle workflows** (`cli/commands/lifecycle.py`,
`features/lifecycle/pipeline.py`): canonical 7-phase flow
`BACKLOG_DEFINITION → RELEASE_DEFINITION → IMPLEMENTATION → QA_REVIEW → SECURITY_REVIEW →
CODE_REVIEW → CLOSURE`, harness-selectable per step (`--harness`,
`--step-harness label=harness`). **GAP:** every e2e uses `--harness fake` (one pipeline
test injects a PI stream); the existing pipeline e2e (`test_lifecycle_pipeline_cli.py`)
**stops at the first BLOCKED gate** — the happy path never reaches `CLOSURE` in any e2e;
phase advancement/backtrack transitions are unit-tested only
(`test_lifecycle_models.py`).

---

## 2. Objective

Complete the two Layer-2 worker adapters that are not real (OpenCode, Claude SDK), add
the missing live/contract/e2e coverage that proves the multi-harness story, drop RPC as a
stated transport, and gate CLOSURE + deploy on hands-on operator live-validation of every
real harness.

---

## 3. Scope

Eight workstreams. Each carries verifiable acceptance criteria. WS-1..WS-6 are
implementer work; WS-7 (live-validation) and WS-8 (deploy) are operator-owned (`human`).

### WS-1 — OpenCode Layer-2 worker (`OpenCodeAdapter.run`)

Implement the real adapter against `opencode run` headless JSON/stream output, mirroring
the structure of `PiHeadlessAdapter`/`CodexExecAdapter`.

**Acceptance:**
- `OpenCodeAdapter.run` no longer raises `NotImplementedError`; on a wrong-runtime request
  it returns a `FAILED` `AgentRunResult` (mirrors PI/Codex guard) rather than raising.
- Injectable subprocess runner (`Runner` seam); env allowlist; secret redaction
  (`_SECRET_NAME_PARTS`); defensive parsing that **never crashes** — a malformed/empty
  stream degrades to a `SUCCEEDED` raw-summary or a typed `FAILED`, never an exception.
- Real Ring-2 `changed_paths` sourced from injected `git diff` (`_GitDiffPort`), never a
  model self-report — matching the PI adapter's boundary.
- The studied `opencode run` output contract (event/stream schema, JSON envelope) is
  documented in the adapter docstring and confirmed by the WS-1 live test.
- Unit tests (mocked subprocess) cover: success mapping, wrong-runtime guard, timeout,
  OSError on start, malformed-stream degrade, secret redaction, changed_paths from git.
- Opt-in live contract test under `tests/integration/opencode_live/`, gated by
  `DADAIA_OPENCODE_LIVE=1` + binary-present + auth-present (mirror `pi_live`); NOT
  CI-gated; auto-SKIPs when preconditions unmet.
- `container.build_agent_runtime(OPENCODE_RUN)` returns the working adapter with no
  call-site change.

### WS-2 — Claude SDK Layer-2 worker (`ClaudeSdkAdapter._default_query_fn`)

Complete the real `claude-agent-sdk` transport binding into the existing Ring-1 seam.

**Acceptance:**
- `_default_query_fn` wires the real SDK `query()` and routes the existing
  `write_permission` decider into the SDK `can_use_tool` callback so out-of-scope writes
  are denied pre-disk (Ring-1). It no longer raises `NotImplementedError` when the package
  is present.
- The no-import-at-module-load discipline is preserved (`claude_agent_sdk` imported lazily
  inside `_default_query_fn`); absence still raises the actionable `ImportError`
  (`_MISSING_SDK`).
- The bounded-worker contract holds: any SDK exception maps to a `FAILED`
  `AgentRunResult`, never a crash of the engine.
- Existing injectable-`query_fn` unit tests stay green; add unit tests for the
  permission→`can_use_tool` wiring using a fake SDK module/object (no network).
- Opt-in live contract test under `tests/integration/claude_live/`, gated by
  `DADAIA_CLAUDE_LIVE=1` + `claude-agent-sdk` installed + `ANTHROPIC_API_KEY`; NOT
  CI-gated; auto-SKIPs otherwise.

> Open risk (see §5): the precise installed `claude-agent-sdk` API surface
> (`query()` signature, `can_use_tool` callback shape, `PermissionResultDeny`) is
> upstream-owned and can only be fully confirmed against the installed package — WS-7
> live-validation is the confirmation point.

### WS-3 — Codex Layer-2 adapter live contract test (+ Ring-2 parity)

**Acceptance:**
- Opt-in live contract test that drives the REAL `codex exec` binary through
  `CodexExecAdapter` and asserts a typed, non-crashing `AgentRunResult` (mirrors
  `pi_live/test_pi_live_contract.py`). Gated by `DADAIA_CODEX_LIVE=1` + binary +
  `~/.codex/auth.json`; NOT CI-gated. This is the **Layer-2 adapter** seam — distinct
  from the existing `codex_live` **Layer-1 hook** tests, which stay.
- (GAP-B closure) Inject a `_GitDiffPort` into `CodexExecAdapter` so Codex carries a real
  Ring-2 `changed_paths` seam matching PI; unit test it with a fake git client. If the
  operator scopes this out, record it as a deferred backlog return — but the SPEC's
  default is to close the parity gap.

### WS-4 — RPC removal (stated-transport truth-up)

**Acceptance:**
- RPC is removed as a **supported/stated** Layer-2 transport from `constitution.md`,
  README, `specs/memory/architecture.md`, and any other doc/memory that states the
  transport set. The supported transports are stated consistently everywhere as exactly
  two: **CLI-headless** and **SDK**.
- RPC may appear only as an explicitly-labelled *possible future*, never as part of the
  current supported architecture.
- No RPC code is written. (Memory atom writes happen in the CLOSURE phase, not now —
  this WS's TASKS that touch `specs/memory/**` are CLOSURE-phase.)

### WS-5 — Workflow e2e depth (IMPLEMENTATION → CLOSURE + backtracks)

**Acceptance:**
- A full happy-path e2e on `--harness fake` that walks `IMPLEMENTATION → QA_REVIEW →
  SECURITY_REVIEW → CODE_REVIEW → CLOSURE`, proving phase advancement and that each review
  gate accepts a green handoff and advances (the first e2e to actually reach `CLOSURE`).
- E2e coverage of the backtrack transitions (`QA_REVIEW`, `SECURITY_REVIEW`, `CODE_REVIEW`
  → `IMPLEMENTATION`) end-to-end, asserting a rejected handoff routes back to
  `IMPLEMENTATION`.
- (Optional, behind the live env-gates) a per-real-harness pipeline e2e that runs one step
  on each of PI/Codex/OpenCode/Claude — auto-SKIPs in CI.

### WS-6 — OpenCode Layer-1 gate content-invariant parity test

**Acceptance:**
- Extend the OpenCode gate-plugin test (`test_opencode_parity_hardening.py` or a sibling)
  to assert the same content-invariant parity the PI extension test asserts: delegation to
  the single Python gate, the tool-name → canonical `Write`/`Edit` mapping, fail-open
  default, venv resolution without a bash dependency, and the block-envelope check.
- (Scope note) Projection of `.opencode/plugins/sdd-gate.ts` and the
  `dadaia_workspace.hooks.sdd_gate` delegation are **already** tested — this WS closes the
  remaining *content-invariant* parity gap, it does not re-add an existing test.

### WS-7 — Live-validation acceptance gate (owner: `human`)

A blocking checklist the operator personally runs before CLOSURE + deploy. **The release
does not close and is not deployed until every item is confirmed by the operator.**

**Acceptance (operator-confirmed):**
- `DADAIA_PI_LIVE=1` PI headless run produces a real typed result.
- `DADAIA_CODEX_LIVE=1` Codex `exec` adapter run produces a real typed result.
- `DADAIA_CLAUDE_LIVE=1` Claude SDK run produces a real typed result AND a deliberate
  out-of-scope write is denied by the Ring-1 `can_use_tool` wiring.
- `DADAIA_OPENCODE_LIVE=1` OpenCode run produces a real typed result.
- PI post-trust Layer-1 gate (`.pi/extensions/dadaia-sdd-gate.ts`) blocks a FROZEN write
  in a real trusted PI session.
- (Spot-check) Each Layer-1 entry gate (claude/codex/opencode) blocks a FROZEN write in a
  real session.

### WS-8 — Version bump + deploy (owner: `human`, LAST, gated by WS-7)

**Acceptance:**
- Only after WS-7 sign-off: bump `pyproject.toml` version to `0.1.23`, tag, let
  `release.yml` publish.
- This is the final task; it is operator-gated and must not run before WS-7 is fully
  confirmed.

---

## 4. Out of scope

- Writing any RPC transport code or RPC adapter (RPC is dropped, not implemented).
- Adding a fifth harness or any new `AgentRuntimeKind`.
- Changing the Layer-1 entry-gate enforcement logic in `pre_gate` (only adding tests).
- Changing the canonical 7-phase lifecycle flow or the phase-transition graph.
- Telemetry, RPC/SDK servers, or any networked daemon for harness dispatch.
- CI-gating the live contract tests (they remain strictly opt-in, credit-spending).
- Authoring memory atoms now (that is CLOSURE-phase product work, post-approval).

---

## 5. Dependencies and risks

### ADRs (operator decisions, fixed for this release)

**ADR-23-1 — Two supported Layer-2 transports; RPC dropped.**
The supported Layer-2 transport set is exactly **CLI-headless** and **SDK**. RPC is
removed as a stated/supported transport across constitution, memory, README, and
architecture docs (WS-4). RPC may be mentioned only as a possible future. No RPC code is
written. Rationale: RPC has zero implementation and zero demand; stating it as supported
is over-claiming.

**ADR-23-2 — Operator live-validation is a hard CLOSURE/deploy gate.**
This release implements everything plus CI-mocked unit tests plus opt-in live contract
tests, but it does **not** close and is **not** deployed until the operator personally runs
the real harnesses (Codex exec, Claude SDK, OpenCode, PI headless, PI post-trust gate) and
confirms each works end-to-end (WS-7). The version bump + deploy (WS-8) happen only after
that sign-off. Rationale: mocked tests cannot prove upstream-owned CLI/SDK contracts;
only a real run can.

### Risk table

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Claude SDK API surface is upstream-owned and may differ from assumptions** (`query()` signature, `can_use_tool`, `PermissionResultDeny`). | HIGH | Keep the binding isolated in `_default_query_fn`; prove via WS-7 live run; the engine depends only on the provider-agnostic Ring-1 decider + result mapping, which stay tested. |
| **OpenCode `run` headless JSON/stream contract is unverified** (current stub docstring explicitly flags the schema as unverified). | HIGH | Study the real CLI output before coding; defensive never-crash parsing; confirm via WS-7 live run; degrade to Ring-2 diff if the pre-disk callback is unavailable. |
| Live tests spend operator model credits. | MEDIUM | All live tests strictly opt-in (env-gated), auto-SKIP, never in CI. |
| Codex Ring-2 parity (GAP-B) widens scope. | LOW | If operator scopes out, record as a backlog return; default is to close it in WS-3. |
| Memory/doc truth-up (WS-4) touches `specs/memory/**` which is gate-locked outside DEFINITION/CLOSURE. | LOW | Memory atom edits are scheduled for the CLOSURE phase; non-memory docs (README, constitution) edit during implementation. |
| Operator unavailable for WS-7 stalls the release. | MEDIUM | Acceptable by design — ADR-23-2 makes this an intentional human gate; the release simply waits. |

### Sequencing dependencies

- WS-4 (RPC removal) is independent of the adapter work and can land early.
- WS-1, WS-2, WS-3 are independent of each other (different adapters/tests).
- WS-5, WS-6 depend only on existing surfaces; independent of WS-1/2/3.
- WS-7 depends on WS-1, WS-2, WS-3 (and the live tests) being complete.
- WS-8 depends strictly on WS-7 sign-off.

### Memory files affected at closure

- `specs/memory/architecture.md` — transport set (drop RPC), Layer-2 worker matrix
  (OpenCode + Claude now real).
- `specs/memory/tech-stack.md` — record the verified `opencode` / `claude-agent-sdk` /
  `codex` versions from WS-7 live runs.
- `specs/memory/product/<harness/lifecycle atom(s)>.md` — only if a feature atom states the
  harness/transport surface.
