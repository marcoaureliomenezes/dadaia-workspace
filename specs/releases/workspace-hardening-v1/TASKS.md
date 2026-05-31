# TASKS — workspace-hardening-v1

**Status:** Aprovado

## Phase A — Panel Auth Fix

## T-WH-01 — sessionStorage → localStorage in core.js [frontend-engineer]
[x] Replace all `sessionStorage` references for `panel_token` with `localStorage` in `dadaia_workspace/features/panel/views/assets/js/core.js`.
    File: `dadaia_workspace/features/panel/views/assets/js/core.js`

---

## Phase B — Agent Fixes + D-CX-SKILLS Validator

## T-WH-02 — Fix orphaned skill refs in code-reviewer.md [ai-engineer]
[x] Remove references to `architect-code-audit`, `architect-design-patterns`, `architecture-code-review` from body.
    Rewrite "Skills used:" as "Built-in methodology:".
    Add dispatch condition block.
    File: `dadaia_workspace/public/agents/code-reviewer.md`

## T-WH-03 — Fix orphaned skill refs in security-reviewer.md [ai-engineer]
[x] Remove reference to `security-audit-protocol` from body.
    Rewrite as built-in methodology. Add escalation threshold.
    File: `dadaia_workspace/public/agents/security-reviewer.md`

## T-WH-04 — Add D-CX-SKILLS validator to dadaia public doctor [software-engineer-python]
[x] Parse agent frontmatter `skills:` lists; validate each name exists in `public/skills/<name>/`.
    Emit `[drift]` on missing skills (hard failure).
    Emit `[warn]` for backtick-quoted names in body text that match `public/skills/` (best-effort, soft).
    File: `dadaia_workspace/infrastructure/public_assets.py`

## T-WH-05 — Fix design-specialist.md [ai-engineer]
[x] Remove "Plugins authorised" bullet (already in plugin-scope.md rule).
    Add dispatch condition.
    File: `dadaia_workspace/public/agents/design-specialist.md`

## T-WH-06 — Fix project-manager.md routing table [ai-engineer]
[x] Add Node vs frontend-engineer routing table in dispatch section.
    File: `dadaia_workspace/public/agents/project-manager.md`

## T-WH-07 — Fix project-auditor.md data-analyst contradiction [ai-engineer]
[x] Remove data-analyst from routine evidence dispatch list.
    Also fix orphaned `architect-code-audit` skill reference in Skills consumed section.
    File: `dadaia_workspace/public/agents/project-auditor.md`

## T-WH-08 — Fix product-engineer.md ACTIVE.md clarification [ai-engineer]
[x] Add inline note: "PE reads ACTIVE.md via Read tool (not shell)."
    File: `dadaia_workspace/public/agents/product-engineer.md`

## T-WH-09 — Fix researcher.md dispatch condition [ai-engineer]
[x] Add dispatch condition block with web-search vs inline-search guidance.
    File: `dadaia_workspace/public/agents/researcher.md`

## T-WH-10 — Propagate agent edits [software-engineer-python]
[x] Run: `dadaia public stage && dadaia public install --target all && dadaia public doctor`
    Doctor must exit 0. D-CX-SKILLS check must pass (no orphaned refs after fixes).

---

## Phase C — CLI Asset Granularity

## T-WH-11 — Implement dadaia public list [software-engineer-python]
[x] Add `list_all()` to `FileSystemPublicAssetManager` in `public_assets.py`.
    Add `list` Click command with `--format [table|json]` to `cli/commands/public.py`.
    Extend protocol in `core/protocols/storage.py` if applicable.
    Files: `dadaia_workspace/cli/commands/public.py`, `dadaia_workspace/infrastructure/public_assets.py`

## T-WH-12 — Implement dadaia public install --only [software-engineer-python]
[x] Add `only: str | None = None` to `install()` in `public_assets.py`.
    Add `--only click.Choice([...])` to `install` command in `cli/commands/public.py`.
    Files: `dadaia_workspace/cli/commands/public.py`, `dadaia_workspace/infrastructure/public_assets.py`

## T-WH-13 — Tests for CLI enhancements [qa-engineer]
[x] `test_list_all_returns_all_categories`, `test_install_only_rules_skips_agents`
    `test_list_table_output`, `test_list_json_output`, `test_install_only_flag`
    Files: `tests/unit/infrastructure/test_public_assets.py`, `tests/unit/cli/test_public_commands.py`

---

## Phase D — Panel Workflow Dispatcher

## T-WH-14 — Add POST route to handler [software-engineer-python]
[x] Add route `^/api/workflows/(?P<workflow_name>[^/]+)/run$` with POST guard and name validation.
    File: `dadaia_workspace/features/panel/handler.py`

## T-WH-15 — Add view factory [software-engineer-python]
[x] Add `render_api_workflow_run(workflow_name, panel_service)` to `api.py`.
    Register `"api_workflow_run"` in `container.py`.
    Files: `dadaia_workspace/features/panel/views/api.py`, `dadaia_workspace/container.py`

## T-WH-16 — Add run_workflow to service [software-engineer-python]
[x] Add `run_workflow(workflow_name: str) -> dict` with Popen + PID tracking + 409 guard.
    File: `dadaia_workspace/features/panel/service.py`

## T-WH-17 — Add Run button to workflows frontend [frontend-engineer]
[x] Add "Run" button per workflow card in `workflows.js`.
    Add `.workflow-run-btn` styles in `workflows.py` CSS.
    Files: `dadaia_workspace/features/panel/views/assets/js/workflows.js`
            `dadaia_workspace/features/panel/views/assets/css/workflows.py`

## T-WH-18 — Tests for workflow dispatcher [qa-engineer]
[x] `test_run_workflow_starts_subprocess`, `test_run_workflow_unknown_returns_error`, `test_run_workflow_already_running_409`
    `test_post_workflow_run_requires_auth`, `test_post_workflow_run_rejects_invalid_name`
    Files: `tests/unit/features/panel/test_service.py`, `tests/unit/features/panel/test_handler.py`

---

## Final Gate

## T-WH-19 — Full validation [software-engineer-python]
[x] `dadaia public doctor` → exit 0, all [ok], D-CX-SKILLS passes.
    `poetry run pytest` → all green, coverage 86.07% ≥ 80% threshold (1711 tests).
