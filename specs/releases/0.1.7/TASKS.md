# Tasks: Release 0.1.7 — Implementation Rot Remediation

**Status:** Aprovado
**Release ID:** 0.1.7
**Owner:** product-engineer

Parallelism note: T-017-01 through T-017-05 and T-017-14 have disjoint write sets
and may run in parallel (Wave 1). All other waves are sequential per PLAN.md.

---

## Wave 1 — Trivial / Safe (parallel-safe; disjoint write sets)

### [x] T-017-01
**Finding:** D-01 / AR-05
**Title:** Fix stale `CANONICAL_AGENTS` in `reports_next/service.py`
**Owner:** software-engineer
**Write set:** `dadaia_workspace/features/reports_next/service.py`, `tests/unit/features/reports_next/`
**Precondition:** none
**Work:** Replace the `CANONICAL_AGENTS` frozenset at lines 23-41 with the 12-name
public set (9 core + 3 plugins): `ai-engineer`, `code-reviewer`, `design-specialist`,
`devops-engineer`, `frontend-engineer`, `product-engineer`, `project-auditor`,
`project-manager`, `qa-engineer`, `security-reviewer`, `software-architect`,
`software-engineer`. Update any unit tests that assert on the old 15-name set.
**Done criterion:** `grep -A30 'CANONICAL_AGENTS' dadaia_workspace/features/reports_next/service.py`
shows exactly 12 names. `pytest tests/unit/features/reports_next/` exits 0.

---

### [x] T-017-02
**Finding:** D-02 / AR-06
**Title:** Replace `_WORKSPACE_ROOT` static derivation with `resolve_workspace_root()`
**Owner:** software-engineer
**Write set:** `dadaia_workspace/cli/main.py`, `repos/.dadaia/` (delete)
**Precondition:** none
**Work:** Delete `_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent`
(line 68). Inside `_safe_app()`, replace its usage with a call to
`resolve_workspace_root()` wrapped in `try/except WorkspaceNotInitializedError`
(fall back to a path under `/tmp` on error). Delete the stray `repos/.dadaia/` directory
and its contents. Add a one-line comment explaining the fix.
**Done criterion:** `grep '_WORKSPACE_ROOT' dadaia_workspace/cli/main.py` returns empty.
`[ ! -d repos/.dadaia ]` exits 0. `pytest tests/unit/cli/` exits 0 (if tests exist).

---

### [x] T-017-03
**Finding:** D-04 / AR-07
**Title:** Delete dead HTML-era classes in `specs/doctor.py`
**Owner:** software-engineer
**Write set:** `dadaia_workspace/features/specs/doctor.py`
**Precondition:** none
**Work:** Delete `_MemoryHtmlSummary`, `_MemoryParser`, and `_parse_memory_html` at
lines 266-350. Replace the "retained for any callers" comment with
"HTML-era parser deleted in v0.1.7 post-memory-markdown-source-v1 cleanup."
**Done criterion:** `grep -r '_MemoryHtmlSummary\|_MemoryParser\|_parse_memory_html' dadaia_workspace/`
returns empty. `pytest tests/unit/features/specs/` exits 0.

---

### [x] T-017-04
**Finding:** D-10
**Title:** Remove 4 hidden deprecated `context` stubs
**Owner:** software-engineer
**Write set:** `dadaia_workspace/cli/commands/context.py`, `tests/` (any tests covering these stubs)
**Precondition:** none
**Work:** Delete the four `@app.command(hidden=True)` functions `activate`, `deactivate`,
`promote`, `use` at lines 428-469. Add a one-line comment at the top of the removed section:
"# v2 removals: activate/deactivate/promote/use removed in v0.1.7". Delete any test that
exclusively tests these stub commands.
**Done criterion:** `grep -n 'def activate\|def deactivate\|def promote\|def use'
dadaia_workspace/cli/commands/context.py` returns empty. `pytest` exits 0.

---

### [x] T-017-05
**Finding:** D-08 / D-09
**Title:** Test slop cleanup — duplicate contrast tests, dead dashboard test, misplaced test
**Owner:** software-engineer
**Write set:** `tests/unit/features/panel/`, `tests/unit/test_dashboard.py`, `tests/test_orchestration_registry.py`, `tests/unit/features/specs/`
**Precondition:** none
**Work:**
1. Compare `tests/unit/features/panel/test_contrast.py` and `test_panel_css_contrast.py`.
   Keep the more complete file, delete the other. Update any imports.
2. Delete `tests/unit/test_dashboard.py` (tests dead `dashboard.render_html()`).
3. Move `tests/test_orchestration_registry.py` to
   `tests/unit/features/specs/test_orchestration_registry.py`. Do not change test content.
**Done criterion:** Only one contrast test file exists in `tests/unit/features/panel/`.
`[ ! -f tests/unit/test_dashboard.py ]` exits 0.
`[ ! -f tests/test_orchestration_registry.py ]` exits 0.
`[ -f tests/unit/features/specs/test_orchestration_registry.py ]` exits 0.
`pytest` exits 0.

---

### [x] T-017-14
**Finding:** W-5
**Title:** Bump `pyproject.toml` version 0.1.5 → 0.1.7
**Owner:** software-engineer
**Write set:** `pyproject.toml`
**Precondition:** none
**Work:** Change `version = "0.1.5"` to `version = "0.1.7"`. No other changes.
**Done criterion:** `grep 'version = ' pyproject.toml` shows `"0.1.7"`.

---

## Wave 2 — DI / Structural (sequential; architect-designed)

Read `repos/dadaia-workspace/specs/audits/20260608T035551Z-da1a1b2c/architect-review.md`
AR-01..AR-03 before starting any task in this wave.

### [-] T-017-10
**Finding:** AR-08
**Title:** Extract session-staleness predicate to `core/lock_liveness.py`
**Owner:** software-engineer
**Write set:** `dadaia_workspace/core/lock_liveness.py`, `dadaia_workspace/features/panel/views/kanban.py`, `dadaia_workspace/features/spec_context/locking.py`
**Precondition:** Wave 1 green (`pytest` exit 0)
**Work:** Add `is_stale_session(last_seen_at: str, ttl_seconds: int) -> bool` to
`core/lock_liveness.py`. Remove the inline `_is_stale` function from `kanban.py` (lines 69-81)
and replace all call sites with the imported `is_stale_session`. Remove the duplicated
predicate from `locking.py` and replace with the same import.
**Done criterion:** `grep 'def _is_stale' dadaia_workspace/features/panel/views/kanban.py`
returns empty. `grep 'is_stale_session' dadaia_workspace/features/panel/views/kanban.py`
shows import. `pytest` exits 0.

---

### [ ] T-017-06
**Finding:** AR-02
**Title:** Panel DI — inject `WorkflowsService`; fix `container.py` private-attr read
**Owner:** software-engineer
**Write set:** `dadaia_workspace/features/panel/service.py`, `dadaia_workspace/container.py`
**Precondition:** T-017-10 done
**Work:** Remove `self._workflows_service = WorkflowsService(workspace_root)` from
`PanelService.__init__` (line 157). Add `workflows_service` as a constructor parameter
(type annotation: `WorkflowsService` or the `IWorkflowSummaryProvider` protocol if T-017-07
is being done concurrently; if sequential, use concrete type now and update type annotation
in T-017-07). Update `container.py:289` to inject `WorkflowsService` directly into
`build_panel_service()` and `build_panel_views()` instead of accessing
`service._workflows_service`.
**Done criterion:** `grep 'WorkflowsService(workspace_root)' dadaia_workspace/features/panel/service.py`
returns empty. `grep '_workflows_service' dadaia_workspace/container.py` returns empty.
`pytest` exits 0.

---

### [ ] T-017-07
**Finding:** D-03 / AR-01
**Title:** Panel protocols — declare 3 `core/protocols/` interfaces; update `panel/service.py` imports
**Owner:** software-engineer
**Write set:** `dadaia_workspace/core/protocols/` (new files), `dadaia_workspace/features/panel/service.py`, `dadaia_workspace/container.py`
**Precondition:** T-017-06 done
**Work:**
1. Create `dadaia_workspace/core/protocols/context_project_provider.py` with
   `ContextProjectProvider` Protocol.
2. Create `dadaia_workspace/core/protocols/server_registry_provider.py` with
   `ServerRegistryProvider` Protocol.
3. Create `dadaia_workspace/core/protocols/workflow_provider.py` with
   `WorkflowProvider` Protocol.
4. Update `panel/service.py:45-48` to import from `core/protocols/` not from sibling features.
5. Update `container.py` to wire concrete implementations against the protocols.
Derive the protocol surface from the methods actually called by `PanelService` on each
dependency (minimum surface principle).
**Done criterion:**
`grep -E 'from dadaia_workspace.features.(server_registry|spec_context|workflows)'
dadaia_workspace/features/panel/service.py` returns empty.
`ls dadaia_workspace/core/protocols/*.py` shows at least the 3 new files.
`mypy --strict dadaia_workspace` exits 0. `pytest` exits 0.

---

### [ ] T-017-08
**Finding:** AR-03
**Title:** Panel views — move `ReportRetentionService` into `PanelService`; inject `ADAPTER_REGISTRY`
**Owner:** software-engineer
**Write set:** `dadaia_workspace/features/panel/views/api.py`, `dadaia_workspace/features/panel/service.py`, `dadaia_workspace/container.py`
**Precondition:** T-017-07 done
**Work:**
1. Move `ReportRetentionService` concern into `PanelService` (the service already has
   `workspace_root`). Remove the per-request `retention = ReportRetentionService(service._workspace_root)` inside `render_api_reports` closure.
2. Remove `ADAPTER_REGISTRY` direct import from `panel/views/api.py`. Pass it as an
   injected mapping through `PanelService` or the container.
3. View functions should receive only `PanelService` and DTOs (no concrete feature imports).
**Done criterion:** `grep 'ReportRetentionService(' dadaia_workspace/features/panel/views/api.py`
returns empty. `grep 'ADAPTER_REGISTRY' dadaia_workspace/features/panel/views/api.py`
returns empty (import removed). `pytest` exits 0; panel integration tests pass.

---

## Wave 3 — Refactors (public_assets.py)

### [ ] T-017-09
**Finding:** D-06 / AR-04
**Title:** Collapse triplicated guardrail-pair install functions + merge duplicate consumer-repo discovery
**Owner:** software-engineer
**Write set:** `dadaia_workspace/infrastructure/public_assets.py`
**Precondition:** Wave 2 green
**Work:**
1. Collapse `_install_workspace_guardrail_pair`, `_install_workspace_root_guardrail_pair`,
   and `_install_consumer_repos_guardrail_pair` into a single function with a
   `targets: set[Literal["workspace", "repos"]]` parameter. Approximately 330 → 60 lines.
2. Merge `_consumer_repos_for_root` (free function) and
   `FileSystemPublicAssetManager._consumer_repos` (instance method) into a single
   module-level function.
**Done criterion:** `grep 'def _install_workspace_guardrail_pair\|def _install_workspace_root_guardrail_pair\|def _install_consumer_repos_guardrail_pair'
dadaia_workspace/infrastructure/public_assets.py` returns ≤1 result.
`dadaia public doctor` exits 0. `pytest` exits 0.

---

### [ ] T-017-11
**Finding:** D-06 (W-8b)
**Title:** `public_assets.py` module split (staged; finish or explicit rc-gate defer decision)
**Owner:** software-engineer
**Write set:** `dadaia_workspace/infrastructure/public_assets.py`, `dadaia_workspace/infrastructure/` (new sub-modules)
**Precondition:** T-017-09 done
**Work:** Attempt the module split as proposed in W-8:
- Extract Codex rendering to `infrastructure/runtime_transforms/codex_assets.py`
- Extract guardrail-pair logic to `infrastructure/workspace_guardrail.py`
- Extract privacy scanning to `infrastructure/privacy_check.py`
- Keep staging/install/doctor as residual in `public_assets.py` (<600 lines)
Each extraction: maintain re-exports at `infrastructure/__init__.py`, run `mypy --strict`,
run `pytest`, run `dadaia public doctor`.
**If the split cannot safely complete in this release:** record an explicit defer decision
in this task's done note before marking `[x]`: "Deferred to 0.1.8: [reason]."
**Done criterion (either):**
- Split complete: `wc -l dadaia_workspace/infrastructure/public_assets.py` shows <600 lines.
  `dadaia public doctor` exits 0. `pytest` exits 0.
- Explicit defer: Task marked `[x]` with note "Deferred to 0.1.8: [reason]" added here.
  No partial changes committed.

---

## Wave 4 — Gate Fix

### [ ] T-017-15
**Finding:** NEW (gate bug — blocked PM backlog writes this session)
**Title:** Fix backlog-ownership gate persona session-pointer fallback in `sdd-spec-gate.sh`
**Owner:** software-engineer
**Write set:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
**Precondition:** Wave 3 green (or concurrent with Wave 2/3 if isolated)
**Work:** In the backlog branch of the gate (RULE A2), add a persona session-pointer
fallback so that `project-manager` is resolvable even when the context variable is
resolved via `.ptr` file (the same fallback that exists in the context-resolution branch).
The current gate blocks legitimate PM backlog writes when persona resolution fails to
match `project-manager`. After the fix, run `dadaia public stage && dadaia public install --target all`.
**Done criterion:** `dadaia public doctor` exits 0 after re-projection. Manual smoke test:
PM agent write to `specs/backlog/` does not trigger gate error. `pytest` exits 0.

---

## Wave 5 — Memory (product-engineer; DEFINITION phase — applied now)

### [x] T-017-12
**Finding:** D-05
**Title:** Correct `specs/memory/architecture.md:268` session-file claim
**Owner:** product-engineer
**Write set:** `specs/memory/architecture.md`
**Precondition:** DEFINITION phase active (now)
**Work:** Applied in DEFINITION phase. The claim "Removido em v0.1.6: os stores
`.dadaia/sessions/<sess_*>.json`" is inaccurate. Session files are retained for the
Kanban view and session display. The locking mechanism (Lock-3) was removed, but the
session files themselves were not. Correction applied inline.
**Done criterion:** `grep 'sess_\*' specs/memory/architecture.md` shows retention
claim, not removal claim. `dadaia specs doctor` exits 0.

---

### [x] T-017-13
**Finding:** D-07
**Title:** Fix `specs/memory/quality-assurance.md` broken test path reference
**Owner:** product-engineer
**Write set:** `specs/memory/quality-assurance.md`
**Precondition:** DEFINITION phase active (now)
**Work:** Applied in DEFINITION phase. The Dependências section references
`tests/integration/test_gate_session_locks.py` which does not exist. The real
gate tests live at `tests/unit/gate/` and `tests/integration/gate/`. Reference corrected.
**Done criterion:** `grep 'test_gate_session_locks' specs/memory/quality-assurance.md`
shows corrected paths. `dadaia specs doctor` exits 0.
