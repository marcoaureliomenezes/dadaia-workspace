---
title: panel-integration-tests-couple-to-gitignored-staging
severity: MEDIUM
opened: 2026-05-30
session_id: null
---

# Bug: panel-integration-tests-couple-to-gitignored-staging

## Description

11 panel integration tests in `tests/integration/panel/test_api_agents.py` and
`tests/integration/panel/test_api_workflows.py` fail on a clean working tree because
they depend on a **gitignored staging directory** existing inside the repo:
`repos/dadaia-workspace/.dadaia/agentic/{agents,workflows}/`.

The fixture builds a real `PanelService` with
`workspace_root = _WORKSPACE_ROOT (= repos/dadaia-workspace/)`, and the service reads
agent/workflow definitions from `<workspace_root>/.dadaia/agentic/...`. When that staging
dir is absent the API returns 404 / empty lists, so the "contains real agents",
"real workflow", shape, telemetry-overlay, and `/prompt` tests fail.

`.dadaia/agentic/` is gitignored (`.gitignore:57`), so it does not exist on a fresh
clone or in CI — the tests only ever passed because a stale staging dir happened to be
on disk. The go-open-source hardening physically removed the lib's entire `.dadaia/`
(intended: the lib must not carry runtime projections/staging), which exposed the
hidden coupling.

**Impact:** suite is red on any clean checkout; the `dadaia public stage` CLI walks
*up* to the outer workspace `.dadaia/` and never recreates one inside the lib, so the
precondition cannot be restored through normal tooling.

## Steps to reproduce

1. Ensure `repos/dadaia-workspace/.dadaia/` does not exist (clean clone, or after the
   go-open-source cleanup).
2. `poetry run pytest tests/integration/panel/test_api_agents.py tests/integration/panel/test_api_workflows.py --no-cov`
3. Expected: green. Actual: 11 failed (404s, empty agent/workflow lists, shape
   assertions on missing data).

## Environment

- dadaia version: editable install (repos/dadaia-workspace), branch spec-context-tree-v2
- OS: Linux
- Python: 3.12

## Root cause hypothesis

Confirmed — **two coupled defects**, both stemming from asserting against a stale, on-disk
staged snapshot:

1. **Gitignored-staging coupling.** The panel API integration tests resolved their data
   source to the repo-root gitignored `.dadaia/agentic/` dir instead of provisioning a
   hermetic staging area. Absent on a clean checkout → 404s / empty lists.

2. **Stale agent name.** `test_api_agents.py` referenced a retired agent id
   `software-engineer` (stub telemetry summary + `/prompt` test + overlay/status
   assertions). The canonical roster was split into `software-engineer-python` /
   `software-engineer-node` in a prior release, so `software-engineer` no longer exists in
   `public/agents/`. The tests only passed because the deleted staging held a stale
   `software-engineer.md`. A hermetic re-stage alone would NOT have fixed this — the
   assertion itself was wrong.

## Resolution (applied 2026-05-30)

- Added a module-scoped `staged_root` fixture in both `test_api_agents.py` and
  `test_api_workflows.py` that stages the canonical, tracked `public/` assets into a
  `tmp_path_factory` workspace_root via `FileSystemPublicAssetManager().stage(root)`, and
  points `PanelService` at that tmp root. Tests are now self-contained — no dependency on
  any pre-existing on-disk `.dadaia/agentic/` (clean-checkout / CI safe). The
  `disk_ids` assertion reads from the staged root.
- Replaced the retired `software-engineer` id with `software-engineer-python` throughout
  `test_api_agents.py` (stub summaries, list/overlay/status assertions, `/prompt` tests).
- The lib's `.dadaia/` was **not** recreated — preserving the go-open-source cleanup
  intent.

Discovered while closing release `spec-context-tree-v2` (T-9). NOT caused by R1 (panel
test files were unchanged since before R1; T-9 is green in isolation). Status: **fixed**.
