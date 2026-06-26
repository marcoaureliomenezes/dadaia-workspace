# PLAN — Release: v0.1.23 — Multi-harness Layer-2 completion + two-layer fidelity

**Status:** Aprovado
**Release ID:** v0.1.23
**Owner:** product-engineer

---

## 1. Strategy

Make the stated multi-harness story true and proven before deploy. The work splits into
three concerns:

1. **Complete the two unreal Layer-2 adapters** (OpenCode stub, Claude SDK NotImplemented)
   so every `AgentRuntimeKind` actually executes — using the proven `PiHeadlessAdapter`
   structure as the template (injectable runner, env allowlist, redaction, defensive
   never-crash parsing, real git-diff Ring-2 boundary).
2. **Close the coverage gaps** that let the over-claim persist: a Codex Layer-2 adapter
   live test, a full happy-path + backtrack workflow e2e that actually reaches `CLOSURE`,
   and OpenCode Layer-1 gate content-invariant parity.
3. **Truth-up the architecture story** by dropping RPC as a stated transport.

Then a hard human gate (WS-7) validates every real harness against its real upstream CLI/
SDK before the version bump + deploy (WS-8). Mocked tests prove the engine-side logic;
only live runs prove the upstream-owned contracts.

## 2. Layers affected

| Layer | Files (representative) |
|-------|------------------------|
| Infrastructure adapters | `infrastructure/opencode_runtime.py`, `infrastructure/claude_sdk_runtime.py`, `infrastructure/codex_runtime.py` |
| Container wiring | `container.py` (`build_agent_runtime` — should need no signature change) |
| Unit tests | `tests/unit/infrastructure/test_opencode_runtime.py`, `test_claude_sdk_runtime.py`, `test_codex_runtime.py` |
| Live contract tests | `tests/integration/opencode_live/`, `tests/integration/claude_live/`, `tests/integration/codex_live/` (adapter-level addition) |
| Workflow e2e | `tests/integration/cli/test_lifecycle_pipeline_cli.py` (or a new e2e module) |
| Layer-1 gate parity test | `tests/e2e/features/test_opencode_parity_hardening.py` (or sibling) |
| Docs/governance (non-memory) | `specs/constitution.md`, `README.md` |
| Memory (CLOSURE phase only) | `specs/memory/architecture.md`, `specs/memory/tech-stack.md`, affected product atom(s) |
| Packaging (WS-8, human) | `pyproject.toml` |

The engine spine (`core/models/lifecycle.py`, `features/lifecycle/**`) is **not** modified
— this release adds adapters/tests and removes a stated transport from docs. No new
`AgentRuntimeKind`.

## 3. Execution order and maturity (alpha-N segments)

Per the `release-governance` rule, this release matures on a single `feature/v0.1.23`
branch through `alpha-N` segments (qa-only review at each alpha boundary; full trio +
CLOSURE at the shipping `rc-N`). Proposed segmentation:

### alpha-1 — Truth-up + coverage (no upstream-contract risk)
- **WS-4** RPC removal from constitution/README (memory atom part deferred to CLOSURE).
- **WS-5** workflow happy-path-to-CLOSURE + backtrack e2e on FAKE.
- **WS-6** OpenCode Layer-1 gate content-invariant parity test.
- **WS-3 (unit half)** Codex `_GitDiffPort` Ring-2 parity + its unit test.
- Boundary: qa-engineer review → commit on `feature/v0.1.23`. No push, no closure.

### alpha-2 — Real adapters (upstream-contract risk, mocked-tested)
- **WS-1** `OpenCodeAdapter.run` implementation + unit tests + opt-in live test scaffold.
- **WS-2** `ClaudeSdkAdapter._default_query_fn` binding + unit tests + opt-in live test
  scaffold.
- **WS-3 (live half)** Codex Layer-2 adapter live contract test.
- Boundary: qa-engineer review → commit. The live tests are written but stay opt-in/SKIP
  in CI.

### rc-1 — Validation + ship
- **WS-7** operator live-validation (hard gate; owner `human`). The trio (qa + security +
  code) review the full release here; security APPROVE is the mechanical push gate.
- On operator ship decision: push `feature/v0.1.23` (security verdict per push-cycle), PR
  → merge.
- **CLOSURE** (product-engineer): write CLOSURE.md, update memory atoms (architecture +
  tech-stack with WS-7-verified versions), disposition sweep, archive.
- **WS-8** version bump + deploy (owner `human`), only after WS-7 sign-off.

> If WS-1/WS-2 live validation surfaces an upstream-contract surprise, open `rc-2` rather
> than forcing the ship — the human gate is allowed to iterate.

## 4. Technical risks (implementation-level)

- **Claude SDK binding (WS-2):** the real `claude-agent-sdk` `query()`/`can_use_tool`/
  `PermissionResultDeny` API is upstream-owned. Mitigation: isolate in `_default_query_fn`;
  unit-test the permission wiring against a fake SDK object; defer final confirmation to
  WS-7. Keep lazy import so the offline build/lockfile is untouched.
- **OpenCode `run` schema (WS-1):** the headless JSON/stream envelope and the pre-execution
  permission callback are flagged unverified in the current stub. Mitigation: study the
  real CLI first; write defensive parsing that degrades (never crashes); confirm via WS-7;
  if no pre-disk permission callback exists, the harness's enforcement degrades to Ring-2
  diff (documented, acceptable).
- **e2e reaching CLOSURE (WS-5):** the existing pipeline e2e stops at the first BLOCKED
  gate. Reaching CLOSURE requires feeding each review step a green handoff. Mitigation:
  construct the e2e with green handoff fixtures per gate; assert the run advances to
  `CLOSURE` (proving the transition graph end-to-end), not just that no error is raised.
- **No engine-spine change:** keep `build_agent_runtime` total over `AgentRuntimeKind`
  with no call-site change — swap stub/NotImplemented bodies only.

## 5. Validation plan

| What | How | Gate |
|------|-----|------|
| Adapter logic (mocked) | `pytest tests/unit/infrastructure/` | green, CI |
| Workflow transitions e2e | `pytest tests/integration/cli/test_lifecycle_pipeline_cli.py` (+ new) | green, CI; reaches CLOSURE |
| OpenCode Layer-1 gate parity | `pytest tests/e2e/features/test_opencode_parity_hardening.py` | green, CI |
| Full suite | `ruff format --check && ruff check && mypy --strict && pytest` (pre-push CI gate) | green before any push |
| Projection consistency | `dadaia public stage && install --target all && doctor` (devops) | `[ok] public-privacy`, exit 0 |
| SDD structure | `dadaia specs doctor` | green |
| **Live: PI** | `DADAIA_PI_LIVE=1 pytest tests/integration/pi_live/` (operator) | WS-7 |
| **Live: Codex** | `DADAIA_CODEX_LIVE=1 pytest tests/integration/codex_live/` (operator) | WS-7 |
| **Live: Claude** | `DADAIA_CLAUDE_LIVE=1 pytest tests/integration/claude_live/` (operator) | WS-7 |
| **Live: OpenCode** | `DADAIA_OPENCODE_LIVE=1 pytest tests/integration/opencode_live/` (operator) | WS-7 |
| **Live: PI post-trust gate** | real PI trusted session blocks a FROZEN write (operator) | WS-7 |
| Deploy | `pyproject` bump → tag → `release.yml` (operator) | WS-8, post-WS-7 |

## 6. Drift policy

Any divergence from this plan during implementation (e.g. the OpenCode CLI lacks a JSON
mode, or the Claude SDK callback shape differs) is recorded in CLOSURE.md `## Drifts` with
description, resolution, and memory-update impact. If a drift invalidates an acceptance
criterion, it returns to the operator before `[x]`.
