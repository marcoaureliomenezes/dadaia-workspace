---
audit_id: 20260608T134914Z-ve4r8ifs
auditor: project-auditor
type: verification-re-audit
context: dadaia-workspace
produced_at: 2026-06-08T13:49:14Z
scope: verification of release 0.1.7 — all original findings D-01..D-10, AR-01..AR-08
prior_audit: specs/audits/20260608T035551Z-da1a1b2c/index.md
branch: feature/0.1.7
base_sha: 535b5db
head_sha: 70cb271
---

# dadaia-workspace — Release 0.1.7 Verification Re-Audit

**Produced:** 2026-06-08T13:49:14Z
**Auditor:** project-auditor (independent, read-only)
**Type:** Verification re-audit — no fixes, no spec edits
**Branch:** `feature/0.1.7` (commits `535b5db..70cb271`)
**Mandate:** Independently verify every finding from `20260608T035551Z-da1a1b2c` is
genuinely resolved (root-cause, not symptom-silenced), and confirm no new drift, slop,
dead code, or regressions were introduced.

---

## Executive Summary

**PASS.** Release 0.1.7 resolves 14 of 15 actionable original findings plus the SEC-01
gate security fix. The one deferred item (T-017-11: `public_assets.py` module split) is
explicitly documented in TASKS.md and leaves the tree in a fully consistent state. One
residual LOW-severity item (two cross-feature imports in `panel/views/api.py` and
`panel/service.py` from `agents.reader` and `telemetry.models`) was outside the
explicit scope of the three targeted done criteria and is recorded as carry-over for
0.1.8 rather than a blocker. The CI gate is green: 2366 passed / 2 skipped / 1 xpass,
`mypy --strict` 0 issues, `ruff check` all checks passed, `dadaia public doctor` all
`[ok]` including `[ok] public-privacy`.

**Updated overall score: 9.0 / 10** (up from 7.0).

---

## Verification Scorecard

| Finding | Task | Status | Evidence |
|---------|------|--------|----------|
| D-01/AR-05 CANONICAL_AGENTS | T-017-01 | RESOLVED | `CANONICAL_AGENTS` = 12-name frozenset; `test_canonical_agents_exact_set` asserts it |
| D-02/AR-06 `_WORKSPACE_ROOT` | T-017-02 | RESOLVED | `grep '_WORKSPACE_ROOT' cli/main.py` → empty; `resolve_workspace_root()` used at line 83; `[ ! -d repos/.dadaia ]` → true |
| D-04/AR-07 dead HTML classes | T-017-03 | RESOLVED | `grep -r '_MemoryHtmlSummary\|_MemoryParser\|_parse_memory_html' dadaia_workspace/` → empty |
| D-10 deprecated context stubs | T-017-04 | RESOLVED | `grep 'def activate\|def deactivate\|def promote\|def use' context.py` → empty |
| D-08 duplicate contrast test | T-017-05 | RESOLVED | only `test_panel_css_contrast.py` remains; `test_contrast.py` deleted |
| D-09 dead dashboard test | T-017-05 | RESOLVED | `[ ! -f tests/unit/test_dashboard.py ]` → true |
| D-08 misplaced orchestration test | T-017-05 | RESOLVED | deleted from `tests/` root; relocated to `tests/unit/features/specs/test_orchestration_registry.py` |
| D-03/AR-01 panel cross-feature imports | T-017-07 | RESOLVED | `grep -E 'from dadaia_workspace.features.(server_registry|spec_context|workflows)' panel/service.py` → empty; 3 new `core/protocols/*.py` files present |
| AR-02 `WorkflowsService` self-construct + container private-attr read | T-017-06 | RESOLVED | `grep 'WorkflowsService(workspace_root)' panel/service.py` → empty; `grep '_workflows_service' container.py` → empty |
| AR-03 panel views per-request service + `ADAPTER_REGISTRY` global | T-017-08 | RESOLVED (PRIMARY) / PARTIAL (SECONDARY) | `ReportRetentionService(` and `ADAPTER_REGISTRY` both absent from `panel/views/api.py`; two residual imports remain (see NEW-01 below) |
| D-06/AR-04 triplicated guardrail-pair + duplicate discovery | T-017-09 | RESOLVED | 3 old `def` bodies → 1 `_install_guardrail_pair` + 3 `functools.partial` aliases; `_consumer_repos` instance method delegates to `_consumer_repos_for_root`; no duplicate bodies |
| AR-08 duplicated staleness predicate | T-017-10 | RESOLVED | `is_stale_session` in `core/lock_liveness.py:98`; `kanban.py` imports it at line 41; `def _is_stale` gone from `kanban.py` and `locking.py` |
| D-05 `architecture.md` session-file claim | T-017-12 | RESOLVED | `architecture.md:270` now reads "**Retido em v0.1.6:** `.dadaia/sessions/<sess_*>.json`…" confirming retention |
| D-07 `quality-assurance.md` broken test ref | T-017-13 | RESOLVED | `grep 'test_gate_session_locks' quality-assurance.md` → empty; references now point to real `tests/unit/gate/` and `tests/integration/gate/` paths |
| W-5 `pyproject.toml` version | T-017-14 | RESOLVED | `version = "0.1.7"` |
| T-017-15 / SEC-01 backlog-gate persona fallback + sessions PROTECTED | T-017-15 | RESOLVED | `.dadaia/sessions/**` → CLASS=PROTECTED in gate (line 114); persona session-pointer fallback at lines 134-157; `tests/integration/gate/test_protected_sessions.py` exercises both |
| T-017-11 `public_assets.py` module split | T-017-11 | DOCUMENTED DEFER | TASKS.md documents explicit defer with rationale; no partial changes committed; tree consistent; `wc -l public_assets.py` = 2350 lines |

**Summary: 14 RESOLVED + 1 DOCUMENTED DEFER + 1 PARTIAL (AR-03 secondary scope)**

---

## Compliance Scorecard

| Dimension | Score (1–10) | Drift items | Notes |
|-----------|-------------|-------------|-------|
| Architecture | 9 | 1 (residual) | All three panel DI violations fixed; protocols in `core/protocols/`; `WorkflowsService` injection clean; one residual `agents.reader` cross-feature import in `panel/service.py` (NEW-01, LOW) |
| Product | 9 | 0 | CANONICAL_AGENTS correct; memory atoms D-05/D-07 corrected |
| Tech Stack | 10 | 0 | `pyproject.toml` version = "0.1.7"; no new deps |
| Security | 10 | 0 | `repos/.dadaia/` boundary violation fixed; sessions PROTECTED; no secrets found |
| Tests | 9 | 0 | 2366 passed; duplicate contrast/dashboard/misplaced tests removed; new DI tests + gate tests added |
| Agent-surface | 10 | 0 | CANONICAL_AGENTS = 12-name set with asserting test |
| **Overall** | **9.0** | **1 residual** | Up from 7.0; deferred T-017-11 is planned, not missing |

Score semantics: 10 = zero drift; 7–9 = minor drift, no blockers; 4–6 = moderate drift, some blockers; 1–3 = critical, immediate action.

---

## Evidence for Each Finding

### D-01 / AR-05 — CANONICAL_AGENTS (RESOLVED)

Evidence:
- `dadaia_workspace/features/reports_next/service.py:23-36` — `CANONICAL_AGENTS` is a 12-name frozenset containing exactly the 9-core + 3-plugin names.
- `tests/unit/features/reports_next/test_service.py:163-185` — `test_canonical_agents_count` asserts `len == 12`; `test_canonical_agents_exact_set` asserts exact equality with expected frozenset.
- Root cause addressed: frozen constant replaced with the current canonical set. Registry-derived strategy documented in spec as medium-term follow-up.

### D-02 / AR-06 — `_WORKSPACE_ROOT` (RESOLVED)

Evidence:
- `dadaia_workspace/cli/main.py` — `grep '_WORKSPACE_ROOT'` returns empty (constant deleted).
- `dadaia_workspace/cli/main.py:34,83` — `resolve_workspace_root()` imported and called inside `_safe_app()` with `WorkspaceNotInitializedError` catch.
- `repos/.dadaia/` does not exist on disk (`[ ! -d repos/.dadaia ]` exits 0).
- Root cause addressed: static path walk removed; dynamic resolution used.

### D-04 / AR-07 — dead HTML classes (RESOLVED)

Evidence:
- `grep -r '_MemoryHtmlSummary\|_MemoryParser\|_parse_memory_html' dadaia_workspace/` → empty.
- `dadaia_workspace/features/specs/doctor.py` no longer contains these symbols.
- Root cause addressed: dead code deleted (not commented-out).

### D-10 — deprecated context stubs (RESOLVED)

Evidence:
- `grep -n 'def activate\|def deactivate\|def promote\|def use' dadaia_workspace/cli/commands/context.py` → empty.
- Root cause addressed: the four hidden stubs were deleted.

### D-08 / D-09 — test slop (RESOLVED)

Evidence:
- `tests/unit/features/panel/test_contrast.py` no longer exists; `test_panel_css_contrast.py` retained.
- `tests/unit/test_dashboard.py` no longer exists.
- `tests/test_orchestration_registry.py` no longer exists at root; `tests/unit/features/specs/test_orchestration_registry.py` exists.
- All 2366 tests pass.

### D-03 / AR-01 — panel cross-feature imports (RESOLVED)

Evidence:
- `grep -E 'from dadaia_workspace.features.(server_registry|spec_context|workflows)' dadaia_workspace/features/panel/service.py` → empty.
- `dadaia_workspace/core/protocols/context_project_provider.py:8`, `server_registry_provider.py:8`, `workflow_provider.py:8` — three Protocol classes defined.
- `panel/service.py:45-48` — imports now from `core/protocols/`.
- Root cause addressed: concrete sibling-feature imports replaced with protocol interfaces.

### AR-02 — `WorkflowsService` self-construct + container private-attr read (RESOLVED)

Evidence:
- `grep 'WorkflowsService(workspace_root)' dadaia_workspace/features/panel/service.py` → empty.
- `grep '_workflows_service' dadaia_workspace/container.py` → empty.
- `tests/unit/features/panel/test_service_di_workflows.py:70-79` — test asserts `WorkflowsService(workspace_root)` absent from `PanelService.__init__` source.
- Root cause addressed: `WorkflowsService` now injected through constructor; container wires it directly.

### AR-03 — panel views per-request service + `ADAPTER_REGISTRY` (PRIMARY RESOLVED / SECONDARY PARTIAL)

Primary scope (explicitly in done criterion):
- `grep 'ReportRetentionService(' dadaia_workspace/features/panel/views/api.py` → empty. `ReportRetentionService` is now injected into `PanelService` (`service.py:307-319`).
- `grep 'ADAPTER_REGISTRY' dadaia_workspace/features/panel/views/api.py` → empty. Adapter registry passed via `PanelService`.
- Root cause for the two critical antipatterns (per-request instantiation + global mutable state) addressed.

Residual (outside explicit done criterion — see NEW-01):
- `panel/views/api.py:93-96` still imports `AgentNotFoundError`, `InvalidAgentIdError`, `get_prompt` from `dadaia_workspace.features.agents.reader`.
- `panel/views/api.py:99` still imports `AgentSummary` from `dadaia_workspace.features.telemetry.aggregator.models`.
- These were listed in AR-03's findings but were not covered by the task's done criterion. Both are lower-severity than the two fixed antipatterns: `AgentSummary` is a frozen dataclass (pure DTO, no I/O), and `get_prompt` is a read-only utility. Neither creates the per-request instantiation or global-mutable-state problems the task targeted.

### D-06 / AR-04 — triplicated guardrail-pair + duplicate consumer-repo discovery (RESOLVED)

Evidence:
- `grep 'def _install_workspace_guardrail_pair\|def _install_workspace_root_guardrail_pair\|def _install_consumer_repos_guardrail_pair' public_assets.py` → empty (no `def` bodies).
- `public_assets.py:807-819` — three `functools.partial` aliases retained for backward-compat; all delegate to single `_install_guardrail_pair` (line 719) with `targets` parameter.
- `public_assets.py:2005-2011` — `_consumer_repos` instance method is now a 1-line delegate to `_consumer_repos_for_root`; no duplicate logic.
- `dadaia public doctor` exits 0 — install/doctor pipeline unaffected.
- Root cause addressed: duplicate bodies collapsed; 3 old names retained as thin partial bindings (behavior-preserving dedup, not residual duplication).

### AR-08 — duplicated staleness predicate (RESOLVED)

Evidence:
- `dadaia_workspace/core/lock_liveness.py:26,98` — `is_stale_session` exported.
- `dadaia_workspace/features/panel/views/kanban.py:23,41` — imports `is_stale_session` from `core.lock_liveness`; `def _is_stale` is absent.
- `grep 'def _is_stale' dadaia_workspace/features/spec_context/locking.py` → empty.
- Root cause addressed: single source of truth in `core/lock_liveness.py`.

### D-05 — `architecture.md` session-file claim (RESOLVED)

Evidence:
- `specs/memory/architecture.md:270` — "**Retido em v0.1.6:** `.dadaia/sessions/<sess_*>.json` — session binding files gravados por `cli/commands/context.py:bind`… Estes arquivos não são o mecanismo de locking (Lock-3 foi removido)…"
- The old claim "Removido em v0.1.6" is replaced with the accurate "Retido em v0.1.6" retention statement.

### D-07 — `quality-assurance.md` broken test path (RESOLVED)

Evidence:
- `grep 'test_gate_session_locks' specs/memory/quality-assurance.md` → empty.
- `specs/memory/quality-assurance.md` Dependências section now references `tests/unit/gate/` and `tests/integration/gate/` (real paths).

### W-5 — `pyproject.toml` version (RESOLVED)

Evidence: `grep 'version = ' pyproject.toml` → `version = "0.1.7"`.

### T-017-15 / SEC-01 — gate persona fallback + sessions PROTECTED (RESOLVED)

Evidence:
- `dadaia_workspace/public/scripts/sdd-spec-gate.sh:114` — `*/.dadaia/sessions/*) CLASS=PROTECTED ;;`
- `sdd-spec-gate.sh:121-122` — PROTECTED path immediately blocks with CWE-284 message.
- `sdd-spec-gate.sh:134-157` — persona session-pointer fallback in backlog branch; fail-closed (blocks if persona unresolvable).
- `tests/integration/gate/test_protected_sessions.py` — automated tests cover PROTECTED classifier and persona fallback.
- `dadaia public doctor` exits 0 — re-projection confirmed.

### T-017-11 — `public_assets.py` module split (DOCUMENTED DEFER)

Evidence:
- `specs/releases/0.1.7/TASKS.md:210-248` — task marked `[x]` with explicit defer decision, rationale, and carry-over plan for 0.1.8.
- `wc -l dadaia_workspace/infrastructure/public_assets.py` → 2350 lines (post-T-017-09 reduction; T-017-11 adds no partial changes).
- No new files in `dadaia_workspace/infrastructure/` that represent a half-split (no `privacy_check.py`, no `workspace_guardrail.py`).
- Tree is consistent: `public_assets.py` in post-T-017-09 state; split deferred per explicit rc-gate decision.
- This is a **documented defer, not a silent drop**.

---

## New Issues Found in This Release

### NEW-01 — Residual cross-feature imports in `panel/views/api.py` (LOW)

**Severity:** LOW
**Dimension:** Architecture
**File:** `dadaia_workspace/features/panel/views/api.py:93-96,99`

`api.py` still imports `AgentNotFoundError`, `InvalidAgentIdError`, `get_prompt` from `dadaia_workspace.features.agents.reader` and `AgentSummary` from `dadaia_workspace.features.telemetry.aggregator.models`. These were listed in the original AR-03 finding. The task done criterion (T-017-08) only required the two highest-severity antipatterns to be fixed (`ReportRetentionService` per-request instantiation and `ADAPTER_REGISTRY` global state), which are both gone. The residual imports are lower severity:

- `AgentSummary` is a frozen dataclass (pure DTO, no I/O, no service behavior).
- `get_prompt` from `agents.reader` is a filesystem-read utility function.

Neither reproduces the per-request-service or global-mutable-state antipatterns. However, they still represent cross-feature concrete imports in the view layer.

**Recommended action (0.1.8):** `software-engineer` should move `get_prompt` access into `PanelService` (it already holds `workspace_root`) and expose an `AgentPromptResult` DTO. `AgentSummary` should either be moved to `core/models/` or exposed via `PanelService.list_agents_with_telemetry()` returning `core`-typed DTOs.

### NEW-02 — `panel/service.py` still imports from `agents.reader` (LOW)

**Severity:** LOW
**Dimension:** Architecture
**File:** `dadaia_workspace/features/panel/service.py:49`

`panel/service.py` imports `AgentDTO, read_canonical_agents` from `dadaia_workspace.features.agents.reader`. This was not targeted by any of the three original findings (D-03/AR-01 only targeted `server_registry`, `spec_context`, `workflows` imports). This is a carry-over boundary concern consistent with NEW-01.

**Recommended action (0.1.8):** When NEW-01 is addressed, evaluate whether `read_canonical_agents` should be exposed via an `AgentsProvider` protocol in `core/protocols/`.

### NEW-03 — `architecture.md` not yet updated for `is_stale_session` export (INFO)

**Severity:** INFO
**Dimension:** Memory
**File:** `specs/memory/architecture.md`

The SPEC.md states `architecture.md` should be updated with the `lock_liveness` module entry at CLOSURE (not in DEFINITION phase). This update is not yet present — it is intentionally deferred to the CLOSURE phase per the release plan. Not a defect; recorded for completeness.

---

## CI Gate Results

| Check | Command | Result |
|-------|---------|--------|
| pytest | `pytest -p no:cacheprovider -q` | 2366 passed, 2 skipped, 1 xpassed |
| mypy | `mypy --strict dadaia_workspace` | Success: no issues found in 183 source files |
| ruff | `ruff check .` | All checks passed! |
| public doctor | `dadaia public doctor` | All `[ok]`, including `[ok] public-privacy` |

---

## T-017-11 Deferred — Assessment

The defer is **legitimate and well-documented**:
1. The correctness harm (triplicated bodies + duplicate discovery) was **fully eliminated** in T-017-09.
2. What remains is a pure SRP/organizational refactor (splitting into sub-modules).
3. The TASKS.md documents the reason: HIGH blast radius, 2+ releases per architect classification, no correctness gain from executing before the review/ship gate.
4. No partial changes were committed — the tree is in a clean, consistent post-T-017-09 state.
5. The 0.1.8 carry-over plan is written in TASKS.md with concrete extraction order.

**Verdict on T-017-11: acceptable defer; not a blocker; not a silent drop.**

---

## Updated Score vs Original

| Dimension | Original Score | 0.1.7 Score | Change |
|-----------|---------------|-------------|--------|
| Architecture | 7 | 9 | +2 (panel DI fixed; 1 residual LOW) |
| Product | 7 | 9 | +2 (CANONICAL_AGENTS + memory corrections) |
| Tech Stack | 8 | 10 | +2 (version correct) |
| Security | 8 | 10 | +2 (boundary violation fixed; PROTECTED sessions) |
| Tests | 6 | 9 | +3 (slop removed; new DI + gate tests) |
| Agent-surface | 8 | 10 | +2 (CANONICAL_AGENTS with test) |
| **Overall** | **7.0** | **9.0** | **+2.0** |

Weighting (drift-detection skill formula): Architecture 0.20 × 9 + Product 0.25 × 9 + Tech-Stack 0.15 × 10 + Security 0.20 × 10 + Tests 0.15 × 9 + Agent-surface 0.05 × 10 = 1.8 + 2.25 + 1.5 + 2.0 + 1.35 + 0.5 = 9.4; floor = min(9) → cap at floor+2 = 11, so final = min(9.4, 11) = **9.0** (no cap triggered).

---

## Recommended Actions for 0.1.8

Ordered by severity:

1. **LOW — NEW-01/NEW-02 (Architecture):** `software-engineer` + `software-architect` should complete the AR-03 secondary scope: move `get_prompt` logic into `PanelService`; convert `AgentSummary` usage to a `core`-typed DTO; introduce `AgentsProvider` protocol if warranted.

2. **INFO — T-017-11 (Architecture):** `software-engineer` should execute the `public_assets.py` module split as planned in TASKS.md T-017-11 carry-over: `privacy_check.py` → `runtime_transforms/codex_assets.py` → `workspace_guardrail.py`, one commit each with full CI green after each.

3. **INFO — NEW-03 (Memory):** `product-engineer` should update `architecture.md` at CLOSURE to record `is_stale_session` in the `lock_liveness` module entry.

---

## Verdict

**PASS.** The audit's 15 actionable points were addressed:
- 14 RESOLVED with root-cause fixes (not symptom-silencing)
- 1 DOCUMENTED DEFER (T-017-11) — explicit, rationale recorded, tree consistent
- 1 PARTIAL (AR-03 secondary scope) — the two critical antipatterns fixed; 2 residual LOW imports carried to 0.1.8 as NEW-01/NEW-02
- No UNRESOLVED original findings
- No new CRITICAL or HIGH issues introduced
- CI gate: 2366 passed, mypy clean, ruff clean, public doctor all `[ok]`
