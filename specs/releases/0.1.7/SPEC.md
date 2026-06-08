# Release 0.1.7 — Implementation Rot Remediation

**Status:** Aprovado
**Release ID:** 0.1.7
**Owner:** product-engineer
**Branch:** feature/0.1.7
**Opened:** 2026-06-08

---

## Objective

Eliminate the implementation rot identified by the deep audit (`20260608T035551Z-da1a1b2c`)
and the subsequent architect review. The audit scored the library at 7.0/10 overall and the
architecture at 6.5/10. This release restores the library to full conformance with the
declared three-ring architecture, removes dead/stale code, corrects two memory atom
inaccuracies, fixes one gate bug, and bumps the package version to match the shipped 0.1.6.

No new user-visible features. Every change is behavior-preserving unless the existing
behavior was a bug (e.g. `_WORKSPACE_ROOT` writing to `repos/.dadaia/`).

---

## Canonical Evidence

All findings in this release trace to one of two evidence sources:

- `repos/dadaia-workspace/specs/audits/20260608T035551Z-da1a1b2c/index.md`
  — scorecard 7.0/10, findings D-01..D-10.
- `repos/dadaia-workspace/specs/audits/20260608T035551Z-da1a1b2c/architect-review.md`
  — architecture review 6.5/10; findings AR-01..AR-08.

---

## Pillars this Release Restores

1. **Strong layers / boundary enforcement** — panel DI violations fixed (AR-01, AR-02, AR-03)
2. **Single source of truth / no duplication** — CANONICAL_AGENTS derived/updated (D-01/AR-05);
   guardrail-pair collapse (AR-04b); staleness predicate extracted (AR-08)
3. **Block-by-block encapsulation** — no service constructed inside another service (AR-02/AR-03)
4. **No dead/stale code** — HTML-era classes deleted (D-04/AR-07); deprecated CLI stubs removed (D-10)
5. **Human-friendly + UML-derivable** — panel module maps cleanly to UML after DI fix
6. **Simplicity first** — guardrail-pair triplication collapsed; god-module partial decomposition

---

## Product Deltas

This release makes zero changes to externally visible behavior. All changes are internal:
one bug fix (workspace root derivation), one correctness fix (CANONICAL_AGENTS), one gate fix
(backlog-ownership persona resolution), and six structural refactors/cleanups. The only
visible change to operators is that `dadaia reports next` will correctly parse PLAN.md files
authored after the 15→9 agent consolidation.

---

## Architecture Deltas

| Component | Before | After |
|-----------|--------|-------|
| `panel/service.py` imports | 3 concrete sibling-feature class imports | 3 protocol interfaces from `core/protocols/` |
| `PanelService.__init__` | instantiates `WorkflowsService` internally | receives `WorkflowsService` via DI injection |
| `container.py:289` | accesses `service._workflows_service` private attr | injects `WorkflowsService` directly |
| `panel/views/api.py` | imports concrete types + constructs `ReportRetentionService` per-request | receives only `PanelService` + DTOs; `ReportRetentionService` moved into `PanelService` |
| `core/protocols/` | no panel protocols | adds `ContextProjectProvider`, `ServerRegistryProvider`, `WorkflowProvider` |
| `core/lock_liveness.py` | staleness predicate only for leases | adds `is_stale_session()` exported for panel kanban |
| `public_assets.py` | 3 triplicated guardrail-pair install functions (~330 lines) | 1 function with `targets` param (~60 lines) |
| `public_assets.py` | 2 duplicate consumer-repo discovery functions | 1 module-level function |

---

## Tech-Stack Deltas

None. No new dependencies introduced. `pyproject.toml` version field is bumped from `0.1.5`
to `0.1.7` (skipping the unpublished 0.1.6 intermediate).

---

## Security / Operations Deltas

**Bug fixed (D-02/AR-06):** `cli/main.py`'s `_WORKSPACE_ROOT` static derivation wrote exception
reports to `repos/.dadaia/bugs/reported.json` (a boundary violation: `.dadaia/` must not exist
inside any repo). After this release, `_safe_app()` calls `resolve_workspace_root()` and
catches `WorkspaceNotInitializedError` gracefully. No secret leak was present; the fix removes
the boundary violation and ensures `dadaia doctor` can find exception reports.

---

## Scope of the 15 Tasks

| Task | Finding | Short title |
|------|---------|-------------|
| T-017-01 | D-01/AR-05 | Fix stale `CANONICAL_AGENTS` (12-name public set) |
| T-017-02 | D-02/AR-06 | Replace `_WORKSPACE_ROOT` with `resolve_workspace_root()` + clean residue |
| T-017-03 | D-04/AR-07 | Delete dead HTML-era classes in `specs/doctor.py:266-350` |
| T-017-04 | D-10 | Remove 4 hidden deprecated `context` stubs + tests |
| T-017-05 | D-08/D-09 | Test slop: merge duplicate contrast tests, delete dead dashboard test, relocate misplaced test |
| T-017-06 | AR-02 | Panel DI: remove `WorkflowsService` self-construct, inject it; fix `container.py:289` |
| T-017-07 | D-03/AR-01 | Panel protocols: declare 3 `core/protocols/` interfaces; annotate `panel/service.py` |
| T-017-08 | AR-03 | Panel views: move `ReportRetentionService` into `PanelService`; inject `ADAPTER_REGISTRY` |
| T-017-09 | D-06/AR-04 | Collapse triplicated guardrail-pair + duplicate consumer-repo discovery |
| T-017-10 | AR-08 | Extract session-staleness predicate to `core/lock_liveness.py` |
| T-017-11 | D-06 (W-8b) | `public_assets.py` module split (staged; finish or explicit rc-gate defer) |
| T-017-12 | D-05 | Correct `architecture.md:268` session-file claim |
| T-017-13 | D-07 | Fix `quality-assurance.md` broken test path reference |
| T-017-14 | W-5 | Bump `pyproject.toml` 0.1.5 → 0.1.7 |
| T-017-15 | NEW (gate bug) | Fix backlog-ownership gate persona session-pointer fallback |

---

## Memory Files Affected at Closure

- `specs/memory/architecture.md` — correct session-file retention claim (T-017-12; applied in
  DEFINITION phase per §13) + update lock_liveness module entry at CLOSURE
- `specs/memory/quality-assurance.md` — fix broken `test_gate_session_locks.py` path reference
  (T-017-13; applied in DEFINITION phase per §13)

---

## Acceptance Criteria

Each criterion is independently verifiable:

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-01 | `CANONICAL_AGENTS` in `reports_next/service.py` equals the 12-name set (9 core + 3 plugins) | `grep -A30 'CANONICAL_AGENTS' dadaia_workspace/features/reports_next/service.py` |
| AC-02 | `_WORKSPACE_ROOT` constant deleted from `cli/main.py` | `grep '_WORKSPACE_ROOT' dadaia_workspace/cli/main.py` returns empty |
| AC-03 | No `.dadaia/bugs/` directory inside `repos/` | `[ ! -d repos/.dadaia ]` exits 0 |
| AC-04 | `_MemoryHtmlSummary`, `_MemoryParser`, `_parse_memory_html` absent from codebase | `grep -r '_MemoryHtmlSummary\|_MemoryParser\|_parse_memory_html' dadaia_workspace/` returns empty |
| AC-05 | `activate`, `deactivate`, `promote`, `use` hidden commands absent from `context.py` | `grep -n 'def activate\|def deactivate\|def promote\|def use' dadaia_workspace/cli/commands/context.py` returns empty |
| AC-06 | No duplicate `test_contrast.py` + `test_panel_css_contrast.py`; only one file remains | directory listing shows exactly one contrast test file |
| AC-07 | `tests/unit/test_dashboard.py` deleted | `[ ! -f tests/unit/test_dashboard.py ]` exits 0 |
| AC-08 | `tests/test_orchestration_registry.py` deleted from root; relocated to `tests/unit/features/specs/` | file absent at old path, present at new path |
| AC-09 | `WorkflowsService(workspace_root)` instantiation absent from `PanelService.__init__` | `grep 'WorkflowsService(workspace_root)' dadaia_workspace/features/panel/service.py` returns empty |
| AC-10 | `container.py` does not access `service._workflows_service` | `grep '_workflows_service' dadaia_workspace/container.py` returns empty |
| AC-11 | `core/protocols/` contains at minimum `ContextProjectProvider`, `ServerRegistryProvider`, `WorkflowProvider` | `ls dadaia_workspace/core/protocols/*.py` shows these files |
| AC-12 | `panel/service.py` imports from `core/protocols/` not from sibling features | `grep -E 'from dadaia_workspace.features.(server_registry|spec_context|workflows)' dadaia_workspace/features/panel/service.py` returns empty |
| AC-13 | `ReportRetentionService` not instantiated inside any view closure | `grep 'ReportRetentionService(' dadaia_workspace/features/panel/views/api.py` returns empty |
| AC-14 | `core/lock_liveness.py` exports `is_stale_session`; `kanban.py` imports it | `grep 'is_stale_session' dadaia_workspace/features/panel/views/kanban.py` shows import |
| AC-15 | Triplicated guardrail-pair functions (`_install_workspace_guardrail_pair`, `_install_workspace_root_guardrail_pair`, `_install_consumer_repos_guardrail_pair`) replaced by single function | `grep 'def _install_workspace_guardrail_pair\|def _install_workspace_root_guardrail_pair\|def _install_consumer_repos_guardrail_pair' dadaia_workspace/infrastructure/public_assets.py` returns ≤1 hit |
| AC-16 | `dadaia public doctor` exits 0 after T-017-09 and T-017-11 | `dadaia public doctor && echo OK` |
| AC-17 | Full pytest suite exits 0 | `pytest` |
| AC-18 | `pyproject.toml` declares `version = "0.1.7"` | `grep 'version = ' pyproject.toml` |
| AC-19 | `sdd-spec-gate.sh` backlog branch resolves project-manager persona via session-pointer fallback | manual test: PM agent can write to `specs/backlog/` without gate error |
| AC-20 | `architecture.md:268` no longer claims session files were removed; states they are retained for Kanban | `grep 'sess_\*' specs/memory/architecture.md` shows retention claim |
| AC-21 | `quality-assurance.md` Dependências section references real `tests/unit/gate/` and `tests/integration/gate/` paths | `grep 'test_gate_session_locks' specs/memory/quality-assurance.md` shows corrected path |

---

## Out of Scope

- New user-visible features or behavioral changes
- Full W-8 god-module decomposition (T-017-11 is STAGED: either finish if safe in this release
  or make an explicit rc-gate decision to defer to 0.1.8; it is NOT dropped)
- Memory atoms beyond `architecture.md` and `quality-assurance.md`
- Codex/OpenCode projection changes (public_assets.py behavior preserved, only internal structure changes)
- `pyproject.toml` version history or changelog

---

## Dependencies and Risks

| Item | Risk | Mitigation |
|------|------|-----------|
| T-017-06..08 (panel DI) | Tests may fail if panel unit tests mock concrete classes | software-architect provides design notes; SE writes tests before flipping `[x]` |
| T-017-09 (guardrail collapse) | `dadaia public doctor` may show drift if hash comparison changes | Run `dadaia public doctor` after each collapsed function |
| T-017-11 (module split) | Module split changes import paths; any non-updated caller breaks | Must verify with `mypy --strict` and `pytest` green before closing; rc-gate defer is the safe option if not confident |
| T-017-15 (gate fix) | `sdd-spec-gate.sh` is lib-originated; must re-project after fix | Run `dadaia public stage && dadaia public install --target all` after fix |

---

## Grill Assumptions

The following assumptions were made inline (no blocking operator Q&A; operator mandate is "solve every finding"):

- **GA-01:** `CANONICAL_AGENTS` immediate fix strategy (strategy 2 from AR-05) is used. The
  medium-term registry-derived strategy is noted in AC-01 comments for the next refactor pass.
- **GA-02:** The backlog-ownership gate bug (T-017-15) is treated as a library bug in
  `dadaia_workspace/public/scripts/sdd-spec-gate.sh`. The fix adds a persona session-pointer
  fallback in the backlog branch so that a `project-manager` agent (whose persona may be
  resolved via a `.ptr` file) is correctly identified as the legitimate backlog owner.
- **GA-03:** pyproject version bumps from `0.1.5` directly to `0.1.7`. The 0.1.6 intermediate
  was never published to PyPI. This is consistent with the operator's decision to skip 0.1.6
  PyPI publication.
- **GA-04:** T-017-11 (W-8b module split) is included in this release as STAGED. The SE should
  attempt the split and provide an explicit decision at the end of the task: either "split
  complete, doctor exit 0" or "deferred to 0.1.8 due to [reason]". The latter is acceptable
  and must be documented in TASKS.md.
- **GA-05:** Memory fixes T-017-12 and T-017-13 are applied in the DEFINITION phase (not
  deferred to CLOSURE) because they correct current-truth inaccuracies that active agents are
  reading, per constitution §13 DEFINITION-phase authorization.
