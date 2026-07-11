---
name: panel-tab-reorg-agentic-layers
status: delivered
delivered_in: v0.1.79
opened: 2026-07-08
owner: project-manager (curates)
priority: P2
source: "operator-ratified demand 2026-07-08 (panel primary-tab reorg — name the two agentic layers explicitly after v0.1.65 L1 model governance shipped; Sessions telemetry dashboard merged into the L1 tab)"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/index.py#render_index" }
    change: "reorganize the panel primary tablist/tabpanel set from 7 tabs to 6. In render_index's nav-tabs + section markup: (1) rename the `tab-subagents` tab label `Sub-agents` -> `1º Agentic Layer` (governs Layer-1 Claude sub-agent model+effort — v0.1.65 L1 governance); keep its id `tab-subagents` (or rename to `tab-layer1`) and keep the Sub-agents control-plane body from `_render_subagents_section`; (2) MERGE the `tab-sessions` tab into the `1º Agentic Layer` tab as a sub-section — relocate the session cost/telemetry dashboard (`_render_sessions` / `render_sessions_section`) into the 1º Agentic Layer tabpanel body, then REMOVE the standalone `tab-sessions` button + `section-sessions` panel; (3) rename the `tab-workflows` tab label `Workflows` -> `2º Agentic Layer` (governs Layer-2 pi/codex workflow model policy); keep its id `tab-workflows` (or rename to `tab-layer2`) and keep the Workflows body (server-diagram cards + per-step model pickers); (4) keep `tab-memories` (already labeled `Projects`), `tab-reports`, `tab-academy`, `tab-servers` unchanged. Final primary tab order: Projects | 1º Agentic Layer | 2º Agentic Layer | Reports | Academy | Servers. The tab DOM contract must stay grep-parsable (role=tablist/tab/tabpanel, aria-selected, aria-labelledby) and honor the v0.1.59 semantic-token / one-control-language grep gates."
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/handler.py#make_handler_class" }
    change: "if ANY inline `<script>` served by make_handler_class changes as a side effect of the tab reorg (section wiring, tab-activation JS, relocated Sessions dashboard hydration), recompute the CSP inline-script sha256 allowlist. The `script-src` directive pins `_CSP_SCRIPT_HASH_1` and `_CSP_SCRIPT_HASH_2` (module-level constants in handler.py) — a stale hash silently blocks the inline script under CSP and breaks tab activation. Verify the served CSP header hashes still equal the sha256 of every inline script body after the change."
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/agent_policy.py#render_api_agent_model_policy" }
    change: "the 1º Agentic Layer tab is the Sub-agents control plane hydrated by these agent-model-policy API renderers (render_api_agent_model_policy + the templates/put/validate siblings); the merged Sessions cost/telemetry dashboard reads the unchanged `/api/sessions` aggregate (dashboard-only since v0.1.52). This is a UI-placement move only — the `/api/sessions` endpoint contract and the agent-policy API surface are UNCHANGED; verify no renderer signature changes are needed, only the client-side section that hosts them."
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/workflow_policy.py#render_api_workflow_catalog" }
    change: "the 2º Agentic Layer tab is the Workflows control plane backed by render_api_workflow_catalog (+ catalog_detail, model_profiles, model_policy renderers). This is a label-only rename of the enclosing tab — the workflow-catalog API surface, server-diagram cards, and per-step model pickers are UNCHANGED; verify no renderer signature changes are needed."
---

# BACKLOG — Panel primary-tab reorg: name the two agentic layers explicitly

**Priority:** LOW–MEDIUM. Reorganize the dadaia-workspace panel primary tabs so the two
agentic layers are named explicitly, and fold the standalone Sessions telemetry dashboard
into the Layer-1 tab. The panel is a **CORE** feature (server-rendered Python views +
JS/CSS assets under `features/panel/`) — **not** a plugin; do not route to
`frontend-engineer`.

## Live starting state (verified 2026-07-08)

Primary tabs in `views/index.py#render_index`:
`tab-memories` ("Projects"), `tab-workflows` ("Workflows"), `tab-subagents`
("Sub-agents"), `tab-sessions`, `tab-reports`, `tab-academy`, `tab-servers`.

## Confirmed target (operator answered clarifying question)

1. **Rename "Sub-agents" -> "1º Agentic Layer".** It governs Layer-1 Claude sub-agent
   model+effort (the L1 model governance shipped in v0.1.65). Keep id `tab-subagents` or
   rename to `tab-layer1`; keep the Sub-agents control-plane content.
2. **Merge "Sessions" INTO "1º Agentic Layer" as a sub-section.** The agent run
   cost/telemetry dashboard becomes a panel within the 1º Agentic Layer tab. The
   standalone Sessions tab is removed after the merge. The Sessions tab today renders the
   server-side `/api/sessions` cost aggregate (dashboard-only since v0.1.52); merging =
   relocating that dashboard into the 1º Agentic Layer tab body — the `/api/sessions`
   endpoint itself is unchanged, only the UI placement moves.
3. **Rename "Workflows" -> "2º Agentic Layer".** It governs Layer-2 pi/codex workflow
   model policy (the L2 governance). Keep id `tab-workflows` or rename to `tab-layer2`;
   keep the Workflows content (server-diagram cards + per-step model pickers).
4. **"Projects" tab stays** (currently id `tab-memories`, already labeled "Projects").
5. **Reports, Academy, Servers tabs stay unchanged.**

**Final primary tab order:** Projects | 1º Agentic Layer | 2º Agentic Layer | Reports |
Academy | Servers.

## GOTCHAS for the implementer

- **(a) CSP inline-script hashes.** If any inline `<script>` changes, recompute the
  sha256 allowlist: `_CSP_SCRIPT_HASH_1` / `_CSP_SCRIPT_HASH_2` in `handler.py`. A stale
  hash silently blocks the script under CSP and breaks tab activation.
- **(b) Tab DOM contract tests.** `tests/unit/features/panel/test_index_dom_contract.py`
  and `test_views_index.py` pin the tablist/tabpanel set — update them to the new
  6-primary-tab truth; do not leave them stale.
- **(c) Playwright e2e specs** reference tab ids/labels
  (`tests/e2e/panel/tab-navigation.spec.ts` and others) — update to the new labels.
- **(d) Hermetic e2e webserver harness.** The panel e2e harness is now hermetic
  (`tests/e2e/panel/run-panel-e2e-server.sh`, port 5065) — reuse it, do not spin a new
  server.
- **(e) Grep gates.** Semantic-token / one-control-language grep gates apply (v0.1.59
  law) — the new tab labels and any relocated dashboard markup must pass them.

## Acceptance sketch

- `views/index.py` renders exactly **6** primary tabs in the order above; no
  `tab-sessions` button or `section-sessions` panel remains; the Sessions cost/telemetry
  dashboard renders as a sub-section inside the 1º Agentic Layer tabpanel.
- DOM contract unit tests + Playwright e2e specs updated to the 6-tab truth and green.
- `/api/sessions`, agent-model-policy, and workflow-catalog API surfaces UNCHANGED
  (UI-placement + label move only).
- CSP header hashes equal the sha256 of every served inline script; v0.1.59 grep gates
  pass.

**Anchors:** `features/panel/views/index.py#render_index`,
`features/panel/handler.py#make_handler_class`,
`features/panel/views/agent_policy.py#render_api_agent_model_policy`,
`features/panel/views/workflow_policy.py#render_api_workflow_catalog`.
