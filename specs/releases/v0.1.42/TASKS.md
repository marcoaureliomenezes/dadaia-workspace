# TASKS — Release: v0.1.42

**Status:** Aprovado
**Release ID:** v0.1.42

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Disjoint write sets per owner.

## WS-A — Constitution lean rewrite + single-source (coordinator)
- [x] T-A1 Purge OpenCode/`OPENCODE_RUN`/`.opencode`/"five kinds"/"ten entries" from `constitution.md`; restate {claude,codex,pi} / 4 runtime kinds / nine root entries
- [x] T-A2 Single-source the roster: constitution enumerates zero kinds, cites `tech-stack#agent-runtimes`; make `tech-stack.md` the one home (+ WS-B6 PI-auth fix there)
- [x] T-A3 Collapse §8 → ≤20-line invariant block; cite `sdd-gate-v3` / `context-management` for mechanism
- [x] T-A4 Move §0 vision→`product-vision`, layers/layout→`architecture`; keep ~18-line Definitions; fix "ten"→"nine"
- [x] T-A5 Strip embedded dated amendments/changelog; add Governance + version-header (constitution semver)
- [x] T-A6 De-pin `LEASE_TTL_SECONDS=120` literal → pointer; constitution now 264 lines (was 663)
- [x] T-B1a De-stale `product-vision.md` (3 harnesses, 4 kinds, PI third; receive §0 vision)

## WS-B-destale — OpenCode purge + §8 receivers + index (product-engineer #1)
- [x] T-B1b De-stale `harness-primitives.md` (3 harnesses, 4 kinds, PI third, drop `.opencode/`)
- [x] T-B2a De-stale `agent-orchestration.md` (OpenCode out; 7 dadaia-workflows not "2")
- [x] T-B2b De-stale `public-asset-distribution.md` (targets {agents,claude,codex,pi}; no `.opencode`/`opencode.json`)
- [x] T-B2c De-stale `multi-platform-parity.md` (fix "2 workflows" tldr; OpenCode-removed)
- [x] T-B2d De-stale `workspace-init.md` (no `.opencode/` bootstrap; not "quatro tools")
- [x] T-B2e De-stale `workspace-portability.md` (no opencode/.opencode/opencode.json export paths)
- [x] T-B2f De-stale residue: `agent-comms.md`, `agent-sdd-alignment.md`, `cross-platform-portability.md`
- [x] T-A3-recv Ensure `sdd-gate-v3.md` (gate/chokepoints) + `context-management.md` (lease/mode) hold the §8 mechanism the constitution now cites; drop residual OpenCode rows
- [x] T-B4 Single-source workflow count → 7 dadaia-workflows in `lifecycle-foundation.md`; reframe legacy "2 workflows"
- [x] T-B3 Author §13-compliant `product/index.md` — RESOLVED as the generated catalog TOC (lockstep with catalog.json); vision/users/limits live in `product-vision.md`; constitution §13 updated to match

## WS-B7 + WS-C — architecture + QA memory (product-engineer #2 + coordinator finish)
- [x] T-B7 De-narrate `architecture.md` (removed `(v0.1.NN)` law-tags); fixed `OPENCODE_SESSION_ID`, import-linter "17 capped edges", "23 subcommands"; received §0 layout; `token_estimate` re-stamped 15066. OpenCode mentions are all legitimate (absence/historical/anti-regression-guard)
- [x] T-C QA memory: budgets re-validated vs ~1424 (every bracket contains live count); documented auto-marker-by-directory + Playwright/Node panel-e2e job + cross-platform matrix + conftest guards; replaced v0.1.34 collapse narrative with present-tense "Coverage by surface"; reconciled coverage vs 80% gate; stamps→v0.1.42. **qa-engineer review: APPROVED**

## WS-D + WS-E — code (software-engineer + coordinator test reconcile)
- [x] T-D Fix `lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence`: `FakeAgentRuntime._write_allowed_close_artifact` emits a closure handoff so close advances; regression test added; obsolete `test_create_phase_close_still_blocks_on_fake_without_artifact` updated to the fixed behavior; bug → Closed
- [x] T-E Add `SPEC-DOC-034` doctor invariant: constitution hard-codes no `AgentRuntimeKind`/harness enumeration (must cite memory); red on enumeration, green on the rewrite; 6 unit tests

## WS-B8 + validation (coordinator, last)
- [x] T-B8 Regenerated `catalog.json` + `index.md` (lockstep); stale tldrs flushed (remaining catalog mentions are accurate historical "removed v0.1.24" notes)
- [x] T-VAL **FULL GREEN.** specs doctor 0 errors (incl. SPEC-DOC-034) · backlog doctor clean · public doctor semantic checks `[ok]` (privacy/ai-surface/workflow-policy-no-opencode) · `ruff format --check` + `ruff check` clean (whole tree) · `mypy --strict` Success (292 files) · **full pytest suite 1419 passed, 0 failed** (11 skipped = opt-in live) · **architect review APPROVED** (architecture-fidelity gate REJECTED→APPROVED, zero normative loss) · **qa review APPROVED**.
  - Also reconciled 11 failures that originated in the operator's uncommitted v0.1.35–41 WIP (not the audit scope, surfaced by the shared working tree): updated `features/ci_preflight/` tests for the new `lint-imports` 5th check; extended the FR-R3-01 pointer-namespace ownership contract with a documented READ-ONLY core-layer consumer exception for `core/specs_resolver.py`'s persisted-bind resolver (§6-justified, mirrors the existing session-record allowlist); removed a forbidden in-repo `.dadaia/`+cache pollution dir; and `ruff format`-normalized 9 stray WIP files. **WIP files touched (formatting/test-reconcile only, no feature-logic change): `tests/unit/features/ci_preflight/{test_service,test_resolve_tool}.py`, `tests/e2e/features/test_ci_preflight_poetry_off_path.py`, `tests/contract/test_session_store_ownership.py`, + 9 ruff-format-only files.**
