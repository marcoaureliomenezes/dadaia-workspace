---
audit_id: 20260608T035551Z-da1a1b2c
auditor: project-auditor
context: dadaia-workspace
produced_at: 2026-06-08T03:55:51Z
scope: full — architecture, memory, dead/stale code, tests, CLI surface, file leakage
library_path: repos/dadaia-workspace/dadaia_workspace/
specs_path: repos/dadaia-workspace/specs/
---

# dadaia-workspace — Full Deep Audit

**Produced:** 2026-06-08T03:55:51Z
**Auditor:** project-auditor
**Scope:** full library source at `repos/dadaia-workspace/`

---

## Executive Summary

The library's foundational architecture is sound. The three-ring design (cli → features → core/infrastructure), the TTL-lease concurrency model, the asset-chain pipeline, and the SDD gate are all correctly implemented and largely consistent with their memory specifications.

The implementation has five material problems. Two are HIGH severity: (1) a stale canonical-agents list in `features/reports_next/service.py` that silently drops agent sequences for the 9-core topology, and (2) `cli/main.py`'s `_WORKSPACE_ROOT` derivation that routes bug reports into `repos/.dadaia/` instead of the actual workspace root when the CLI is run from source. Two are MEDIUM severity: dead HTML-era code (three classes/function in `specs/doctor.py`) and a confirmed memory inconsistency about `session/*.json` files. One is LOW: stale deprecated CLI verbs not yet removed.

Beyond these targeted bugs there is a systemic accumulation problem: `infrastructure/public_assets.py` has grown to 2446 lines and 27 top-level functions; it is the single biggest SRP violation and future-rot risk in the codebase. The test suite (230 files, 38 panel-unit test files alone) has pockets of duplication and low-value trivia tests, though overall coverage philosophy is sound.

**Consolidated score: 7.0 / 10** — minor drift, no security blockers, two specific HIGH bugs needing a targeted fix.

---

## Compliance Scorecard

| Dimension     | Score (1–10) | Drift items | Notes |
|---------------|-------------|-------------|-------|
| Architecture  | 7           | 3           | Panel feature-to-feature imports; public_assets.py god-module; small container protocol bypass |
| Product       | 7           | 3           | reports_next stale agents list; session-file memory claim contradiction; quality-assurance.md broken reference |
| Tech Stack    | 8           | 1           | pyproject.toml version stuck at 0.1.5 while v0.1.6 is CLOSURE |
| Security      | 8           | 1           | bug_reporter writes to wrong workspace root (no secret leak; dev path only) |
| Tests         | 6           | 4           | Duplicate contrast tests; dead dashboard.render_html tested; misplaced root-level test; moderate panel test overcount |
| Agent-surface | 8           | 1           | reports_next CANONICAL_AGENTS includes 4 removed agents |
| **Overall**   | **7.0**     | **13**      | No CRITICAL items; 2 HIGH, 6 MEDIUM, 5 LOW |

Score semantics: 10 = zero drift; 7–9 = minor drift, no blockers; 4–6 = moderate drift, some blockers; 1–3 = critical, immediate action.

**Weighting:** Architecture 0.20 × 7 + Product 0.25 × 7 + Tech-Stack 0.15 × 8 + Security 0.20 × 8 + Tests 0.15 × 6 + Agent-surface 0.05 × 8 = 7.25; floor = min(6) → capped at 8.  Applying floor+2 cap: min(7.25, 8) = **7.0** (rounded after floor cap).

---

## Drift Inventory

Full details per dimension are in the supporting files:
- [`architecture.md`](architecture.md) — layer/boundary analysis and spaghetti findings
- [`memory.md`](memory.md) — atom-by-atom memory vs. code comparison
- [`dead-code.md`](dead-code.md) — dead/stale symbols with caller evidence
- [`tests.md`](tests.md) — slop, duplication, and coverage gap analysis
- [`cli-surface.md`](cli-surface.md) — verb inventory and deprecated commands
- [`file-leakage.md`](file-leakage.md) — write-path leakage investigation

### Top-10 Most Severe Findings

| ID | Severity | Dimension | Finding | File:line |
|----|----------|-----------|---------|-----------|
| D-01 | HIGH | Agent-surface / Product | `CANONICAL_AGENTS` in `reports_next/service.py` lists 15 agents including 4 removed names (`backend-engineer`, `researcher`, `software-engineer-node`, `software-engineer-python`). Agent sequences for PLAN.md files using 9-core agent names will silently drop owners. | `dadaia_workspace/features/reports_next/service.py:23-41` |
| D-02 | HIGH | Security / File-leakage | `cli/main.py`'s `_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent` resolves to `repos/` (not the workspace root) when `dadaia` is run directly from source. `bug_reporter` then writes exceptions to `repos/.dadaia/bugs/reported.json` — confirmed by three real entries. | `dadaia_workspace/cli/main.py:68` — confirmed `repos/.dadaia/bugs/reported.json` |
| D-03 | MEDIUM | Architecture | `features/panel/service.py` imports three concrete service classes from other feature packages directly: `ServerRegistryService`, `SpecContextService`, `WorkflowsService`. Violates the architecture rule "features do not import other features — pass through the container." | `dadaia_workspace/features/panel/service.py:46-48` |
| D-04 | MEDIUM | Dead Code | `_MemoryHtmlSummary`, `_MemoryParser`, `_parse_memory_html` in `specs/doctor.py` are HTML-era remnants with zero callers. The comment says "retained for any callers that still…" but there are none in the codebase. | `dadaia_workspace/features/specs/doctor.py:266-350` |
| D-05 | MEDIUM | Memory | `architecture.md:268` states `.dadaia/sessions/<sess_*>.json` was "Removido em v0.1.6" but `cli/commands/context.py:bind` still writes them (line 334-335) and `panel/views/kanban.py` reads them. The claim is inaccurate; the sessions files serve the Kanban view and are not removed. | `specs/memory/architecture.md:268` vs `dadaia_workspace/cli/commands/context.py:334` |
| D-06 | MEDIUM | Architecture | `infrastructure/public_assets.py` is 2446 lines with 27 top-level functions. It is a god module mixing staging, install, doctor, privacy checking, Codex config rendering, OpenCode transform, AGENTS.md guardrail pair logic, and SHA256 hashing. Any change has a large blast radius. | `dadaia_workspace/infrastructure/public_assets.py` (entire file) |
| D-07 | MEDIUM | Memory | `quality-assurance.md` references `tests/integration/test_gate_session_locks.py` as a dependency but the file does not exist. Gate tests live at `tests/unit/gate/` and `tests/integration/gate/`. | `specs/memory/quality-assurance.md` (Dependências section) vs actual filesystem |
| D-08 | MEDIUM | Tests | `test_contrast.py` and `test_panel_css_contrast.py` both assemble the same PANEL_CSS composite and duplicate the WCAG contrast calculation logic. Neither references the other; the second was created without removing the first. | `tests/unit/features/panel/test_contrast.py` and `test_panel_css_contrast.py` |
| D-09 | LOW | Tests | `tests/unit/test_dashboard.py` tests `server_registry/dashboard.render_html()` which is dead code — `dashboard.py` itself is marked `DEPRECATED` and `render_html` has no callers. The deployed path uses `DashboardHandler`. | `tests/unit/test_dashboard.py` vs `dadaia_workspace/features/server_registry/dashboard.py:1` |
| D-10 | LOW | CLI | `context.py` contains four `hidden=True` deprecated commands (`activate`, `deactivate`, `promote`, `use`) that exist only to print removal messages. These carry zero future value and make the source harder to read. | `dadaia_workspace/cli/commands/context.py:428-469` |

---

## Remediation Plan

### Workstream W-1 — Fix CANONICAL_AGENTS (HIGH, 30 min)

**Problem:** `features/reports_next/service.py:CANONICAL_AGENTS` is a frozen 15-agent set from before the consolidation. It includes `backend-engineer`, `researcher`, `software-engineer-node`, `software-engineer-python`.

**Root cause:** The list was hardcoded at creation time and not updated when the 15→9 agent consolidation happened.

**Fix direction:** Replace `CANONICAL_AGENTS` with the actual 9-core + 3-plugin public set (12 names), or derive it from `MarkdownAgentStore` at runtime. The 9-core set is: `ai-engineer`, `code-reviewer`, `design-specialist`, `devops-engineer`, `frontend-engineer`, `product-engineer`, `project-auditor`, `project-manager`, `qa-engineer`, `security-reviewer`, `software-architect`, `software-engineer`.

**Blast radius:** narrow — one file, unit tests for `ReportsNextService`.

**Owner:** `software-engineer` dispatched by `project-manager`.

---

### Workstream W-2 — Fix _WORKSPACE_ROOT in cli/main.py (HIGH, 1 hour)

**Problem:** `_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent` is a static path derivation that yields `repos/` when `dadaia` is run directly from source. This causes `bug_reporter` to write to `repos/.dadaia/bugs/reported.json`.

**Root cause:** The path-walk assumption is only valid for the installed-wheel case. For the editable dev install (which is how the workspace uses it), the path resolution gives a different result.

**Fix direction:** Remove the static `_WORKSPACE_ROOT` derivation entirely. Use `resolve_workspace_root()` inside the `_safe_app()` exception handler instead (catch `WorkspaceNotInitializedError` gracefully). This is safe because `resolve_workspace_root()` looks for `.dadaia/states/spec_contexts.json`, which only exists at the real workspace root.

**Blast radius:** narrow — one file, one constant.

**Owner:** `software-engineer` dispatched by `project-manager`.

---

### Workstream W-3 — Correct memory atom contradictions (MEDIUM, 2 hours)

**Problem (D-05):** `architecture.md:268` falsely claims `session/<sess_*>.json` files were removed. They are still written by `bind` and read by `kanban`.

**Fix direction:** Correct the memory atom to say: "Session binding files `.dadaia/sessions/<sess_*>.json` are retained for the Kanban view and session display (context bind/release); they are no longer used as the locking mechanism (Lock-3 is removed). The locking layer is now exclusively the TTL-lease at `.dadaia/states/ctx_locks/<ctx>.lock.json`."

**Problem (D-07):** `quality-assurance.md` references `tests/integration/test_gate_session_locks.py` which does not exist. The actual gate tests are `tests/unit/gate/` and `tests/integration/gate/`.

**Fix direction:** Update the reference to point to the real file paths.

**Owner:** `product-engineer` dispatched by `project-manager` during CLOSURE phase.

---

### Workstream W-4 — Delete dead code (MEDIUM, 1 hour)

**Problem (D-04):** `_MemoryHtmlSummary`, `_MemoryParser`, `_parse_memory_html` in `specs/doctor.py:266-350` have no callers. The "retained for any callers" comment is stale.

**Fix direction:** Delete the three HTML-era constructs. Run the full test suite to confirm zero breakage. Update the retaining comment to document the deletion.

**Owner:** `software-engineer` dispatched by `project-manager`.

---

### Workstream W-5 — pyproject.toml version bump (LOW, 15 min)

**Problem:** `pyproject.toml` declares `version = "0.1.5"` while v0.1.6 is in CLOSURE phase per `specs/releases/ACTIVE.md`.

**Fix direction:** Bump `version` to `0.1.6` as part of v0.1.6 CLOSURE.

**Owner:** `software-engineer` (or `product-engineer` during CLOSURE), dispatched by `project-manager`.

---

### Workstream W-6 — Remove deprecated CLI stubs (LOW, 30 min)

**Problem (D-10):** Four hidden deprecated `context` subcommands (`activate`, `deactivate`, `promote`, `use`) exist only to print removal messages. Since they are hidden, there is no user-facing value.

**Fix direction:** Delete the four `@app.command(hidden=True)` functions. Add a one-line comment at the top of context.py noting the v2 removals for historical reference.

**Owner:** `software-engineer` dispatched by `project-manager`.

---

### Workstream W-7 — Fix panel cross-feature imports (MEDIUM, 4 hours)

**Problem (D-03):** `panel/service.py` imports concrete classes `ServerRegistryService`, `SpecContextService`, `WorkflowsService` directly from sibling features. This violates the architecture rule that features must not import other features; they receive dependencies through the container.

**Root cause:** The services are injected via constructor (DI is partially correct) but the import of concrete types creates a compile-time feature-to-feature dependency. If `SpecContextService` ever changes its module path, `panel/service.py` breaks.

**Fix direction:** Declare abstract protocols in `core/protocols/` for `ContextProjectProvider`, `ServerRegistryProvider`, `WorkflowProvider`, and inject those. The container wires the concrete implementations. This follows the same pattern already used by `OsProcessProbe`.

**Blast radius:** medium — `panel/service.py`, `container.py`, 3 new protocol files, panel tests.

**Owner:** `software-architect` review + `software-engineer` implementation, dispatched by `project-manager`.

---

### Workstream W-8 — Decompose public_assets.py god module (MEDIUM, 2+ releases)

**Problem (D-06):** `infrastructure/public_assets.py` is 2446 lines with 27 functions and zero sub-module decomposition. It handles: staging, install, doctor, privacy checking, Codex config rendering, OpenCode transform, guardrail-pair logic, SHA256, model mapping. Any change has a large blast radius and makes it nearly impossible to review a single logical concern.

**Root cause:** The file grew organically across many releases. Each feature added new functionality to the single "assets" module.

**Fix direction (proposed backlog items for PM to pick):**
1. Extract Codex rendering to `infrastructure/runtime_transforms/codex_assets.py` (the `runtime_transforms/` submodule already exists).
2. Extract the AGENTS.md/CLAUDE.md guardrail-pair logic to `infrastructure/workspace_guardrail.py`.
3. Extract `_load_privacy_denylist` + privacy scanning to `infrastructure/privacy_check.py`.
4. Keep staging/install/doctor as `infrastructure/public_assets_core.py`.

**Blast radius:** HIGH — many callers. This is a multi-release refactor requiring careful incremental extraction with no behavior change per step.

**Owner:** `software-architect` design + `software-engineer` implementation, dispatched by `project-manager`.

---

### Workstream W-9 — Clean up test slop (LOW, 3 hours)

**Problem (D-08, D-09):** Duplicate contrast tests, dead dashboard test, misplaced test at `tests/` root.

**Fix direction:**
1. Merge `test_contrast.py` into `test_panel_css_contrast.py` (keep the more complete one). Delete the other.
2. Delete `tests/unit/test_dashboard.py` — it tests a deprecated dead function.
3. Move `tests/test_orchestration_registry.py` to `tests/unit/features/specs/test_orchestration_registry.py`.
4. Delete or annotate with `@pytest.mark.tmp` any other test that asserts on deleted behavior.

**Owner:** `qa-engineer` review + `software-engineer` cleanup, dispatched by `project-manager`.

---

## Evidence Sources

All findings are based on direct code inspection with `Read`, `Bash`, and grep verification. No sub-agent was dispatched because nested agent dispatch is not supported in this runtime environment. All claims are independently verified: every "dead code" claim has a caller-grep showing zero callers; every "memory says X, code does Y" claim cites both the memory line and the code line.

The software-architect spawn was attempted but nested `Agent` tool dispatch is unavailable in this execution environment. The architectural review was performed directly by the project-auditor using the architect's anti-slop rubric, as authorized by the agent instruction: "If nested dispatch fails for any reason, say so explicitly in your report and perform the architect's review yourself using the same rubric."

Key evidence files examined:
- `dadaia_workspace/cli/main.py` — `_WORKSPACE_ROOT` derivation bug
- `dadaia_workspace/features/reports_next/service.py:23-41` — stale CANONICAL_AGENTS
- `dadaia_workspace/features/panel/service.py:45-48` — cross-feature concrete imports
- `dadaia_workspace/features/specs/doctor.py:263-350` — dead HTML classes
- `dadaia_workspace/infrastructure/public_assets.py` — god module (2446 lines)
- `repos/.dadaia/bugs/reported.json` — confirmed bug_reporter leak
- `specs/memory/architecture.md:268` — session file contradictory claim
- `specs/memory/quality-assurance.md` (Dependências section) — broken file reference
- `tests/unit/features/panel/test_contrast.py` and `test_panel_css_contrast.py` — duplication
- `tests/unit/test_dashboard.py` — tests dead code
