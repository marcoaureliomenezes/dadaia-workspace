---
release: workspace-hardening-v1
---

# PLAN — workspace-hardening-v1

**Status:** Aprovado

## Phase A — Panel Auth Fix

**Owner:** frontend-engineer / software-engineer-python
**File:** `dadaia_workspace/features/panel/views/assets/js/core.js`

Replace all three `sessionStorage` references for `panel_token` with `localStorage`. No other files change.

## Phase B — Agent Fixes + D-CX-SKILLS Validator

**Owner:** ai-engineer (agent files) + software-engineer-python (doctor check)

### B1 — Agent body text fixes (lib-originated; propagate after all edits)
- `public/agents/code-reviewer.md` — remove orphaned skill references; rewrite as built-in methodology; add dispatch condition
- `public/agents/security-reviewer.md` — same pattern; add escalation thresholds
- `public/agents/design-specialist.md` — remove duplicate plugin rule bullet; add dispatch condition
- `public/agents/project-manager.md` — add Node/frontend routing table
- `public/agents/project-auditor.md` — fix data-analyst dispatch contradiction
- `public/agents/product-engineer.md` — clarify Read vs shell for ACTIVE.md
- `public/agents/researcher.md` — add dispatch condition block

### B2 — D-CX-SKILLS doctor validator (root cause fix)
- `dadaia_workspace/infrastructure/public_assets.py` — parse agent frontmatter `skills:` and validate each name exists in `public/skills/<name>/`; emit `[drift]` on mismatch
- Add best-effort body-text scan: backtick-quoted names cross-referenced against `public/skills/`; emit `[warn]` (not `[drift]`)

### B3 — Propagation
```
dadaia public stage && dadaia public install --target all && dadaia public doctor
```
Doctor must exit 0 with new D-CX-SKILLS check passing.

## Phase C — CLI Asset Granularity

**Owner:** software-engineer-python

### C1 — `dadaia public list`
- `dadaia_workspace/cli/commands/public.py` — new `list` Click command with `--format [table|json]`
- `dadaia_workspace/infrastructure/public_assets.py` — new `list_all() -> dict[str, list[str]]` on `FileSystemPublicAssetManager`
- `dadaia_workspace/core/protocols/storage.py` — extend protocol (check if applicable first)

### C2 — `dadaia public install --only <type>`
- `dadaia_workspace/cli/commands/public.py` — `--only click.Choice([...])` on `install`
- `dadaia_workspace/infrastructure/public_assets.py` — `only: str | None = None` param on `install()`; filter `_COPY_DIRS`

### C3 — Tests
- `tests/unit/infrastructure/test_public_assets.py`
- `tests/unit/cli/test_public_commands.py`

## Phase D — Panel Workflow Dispatcher

**Owner:** software-engineer-python + frontend-engineer

### D1 — Route
- `dadaia_workspace/features/panel/handler.py` — POST route `^/api/workflows/(?P<workflow_name>[^/]+)/run$` with name validation regex `^[a-zA-Z0-9\-]+$`

### D2 — View factory
- `dadaia_workspace/features/panel/views/api.py` — `render_api_workflow_run(workflow_name, panel_service)`
- `dadaia_workspace/container.py` — register `"api_workflow_run"` in `build_panel_views()`

### D3 — Service
- `dadaia_workspace/features/panel/service.py` — `run_workflow(workflow_name) -> dict`; `subprocess.Popen`; `_running_workflows: dict[str, int]`

### D4 — Frontend
- `dadaia_workspace/features/panel/views/assets/js/workflows.js` — "Run" button per card; `authedFetch` POST; spinner + status badges
- `dadaia_workspace/features/panel/views/assets/css/workflows.py` — button + badge styles

### D5 — Tests
- `tests/unit/features/panel/test_service.py`
- `tests/unit/features/panel/test_handler.py`

## Commit Strategy

One commit per phase (A, B, C, D) after all tests pass within that phase.
Final: `dadaia public stage && install && doctor` then full `poetry run pytest`.
