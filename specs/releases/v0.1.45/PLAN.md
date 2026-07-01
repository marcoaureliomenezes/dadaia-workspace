# PLAN — Release: v0.1.45

**Status:** Aprovado
**Release ID:** v0.1.45
**Owner:** product-engineer

---

## 1. Strategy

Pure presentation redesign of the server-rendered Python panel. No template engine, no
React, no build step, no CDN, no CSP relaxation. All work is against verified anchors in
`dadaia_workspace/features/panel/` and `dadaia_workspace/features/workflows/`.

**Iterate against a live visual preview.** AC-4 (restyle) and AC-1/AC-2 layout are best
judged by the operator's eye. Sequence so a **previewable first cut lands early**: build
the Workflows fluxogram cards + Agentic two-roster view + restyle baseline, spin up
`dadaia panel`, show the operator, then refine. Do not chase pixel-perfection before the
first preview.

**Verified current-state anchors (cite when implementing):**

| Concern | Anchor |
|---|---|
| Tabs / SSR index | `views/index.py` (nav tabs: memories/Projects, workflows, ops/Agentic, sessions, reports, academy, servers) |
| Workflow cards | `views/workflows.py` — `render_dadaia_workflows_section()` (line 106), `_render_dadaia_workflow_card(wf)` (line 76, emits SVG + **dead** Mermaid block at line 100), `render_workflows_first_class_section()` (line 130) |
| Workflow data | `features/workflows/dadaia_catalog.py` — `DadaiaWorkflowDTO` / `DadaiaWorkflowStepDTO` (order, label, role, purpose, is_gate, harness_options, model_options, runtime_kind, fragment_id, default_harness, shared_fragment_ids), `list_dadaia_workflows()`, `render_step_mermaid()` (line 446) |
| Server SVG DAG | `features/workflows/dag.py` — `render_dag_svg(stages: list[StageDTO])` (line 334, pure fn, `role="img"`, `<title>`, per-node data attrs, embedded CSS) |
| Agentic tab | `views/agents.py` — `render_agents_subsection()` (line 47, static scaffold + runtime switcher + empty `#agents-grid`); `assets/js/agents.js` `renderCard()`; API `/api/agents` in `views/api.py` (exposes `gate_role` etc.) |
| Role column (existing) | `assets/js/workflow-policy.js:162,189` (role already in the step matrix) |
| Model picker | `views/workflow_policy.py` / `assets/js/workflow-policy.js`; `GET /api/workflow-model-profiles`, `PUT /api/workflow-model-policy`, `POST /api/workflow-model-policy/validate` |
| Model set | `core/harness_models.py` — `LAYER2_EXTRA_MODEL_IDS = frozenset({"kimi-2.7"})` (line 99), `known_layer2_model_ids()` (line 107) = registry codex ids ∪ extra. **`model_choices('pi')` (line 169) returns effort-suffixed `id:effort` strings; catalog entry `HarnessModelOption("kimi-2.7", "high")` → selectable/persisted value `kimi-2.7:high`.** |
| Shared DTO | `features/workflows/service.py` — `StageDTO` (74-83) = {id, agent, needs, parallel_group, gate, expected_output_path, must_include, on_failure}; SHARED with `WorkflowDetailDTO` — **must NOT be widened** |
| Orphaned diagram | `render_step_mermaid` (dadaia_catalog.py:446, `__all__` 857, call 724), `diagram_mermaid` field (136), consumers workflows.py:84 + api.py:732/771 — removed by this release |
| Personas | `public/personas/<role>.md` (8 non-PM: ai-engineer, code-reviewer, product-engineer, project-auditor, qa-engineer, security-reviewer, software-architect, software-engineer); `features/lifecycle/personas/loader.py` `PersonaLoader`. **`Persona` dataclass (loader.py:96-107) = {id, role, summary, source_agent, harness_universal, body, path} — NO `model`, NO `tier`.** |
| Claude sub-agents | `public/agents/*.md` (12: incl. project-manager + plugin stubs design-specialist/devops-engineer/frontend-engineer) |
| CSP | `handler.py` — `_CSP_SCRIPT_HASH_1` (line 111), `_CSP_SCRIPT_HASH_2` (line 116), applied line 824: `script-src 'self' {H1} {H2}`. Recompute per changed inline script (base64 sha256 of the exact inline body). |
| Static assets | `views/static.py` `_ASSETS` (registry of `/static/<name>`); CSS = `assets/css/*.py` string modules; JS = `assets/js/*.js` |

---

## 2. Layers affected

Only the panel presentation layer + its read-only data adapters. No changes to the
lifecycle engine, resolver, overlay store, or `core/harness_models.py` allowed-set logic
(out of scope). Read paths into personas/agents/catalog only.

---

## 3. Module-by-module changes

### 3.1 AC-1 — Workflows tab redesign

- **`features/workflows/dag.py` — enhance `render_dag_svg` via an optional `node_meta`
  param (arch finding #2, PINNED contract).** `_render_node` (dag.py:231) already renders
  stage-id + agent + gate marker (⊙); **only harness/model is new**. Add an **optional
  second parameter** `node_meta: dict[str, NodeMeta] | None = None` (keyed by stage id,
  carrying harness/model) with `NodeMeta` a small local dataclass; default `None` so the
  first-class detail view (which calls `render_dag_svg(stages)` with no meta) is byte-for-
  byte unchanged. `_render_node` reads `node_meta.get(stage_id)` and draws harness/model
  when present. **`StageDTO` (service.py:74-83) is SHARED with `WorkflowDetailDTO` and
  MUST NOT be widened** — do not add fields to it. Keep the function pure (same inputs →
  same SVG), keep `role="img"` + `<title>` + per-node `aria-label`, keep text escaped and
  truncated.
- **`features/workflows/dadaia_catalog.py` — build the `node_meta` map.** In the
  card-side builder, map each `DadaiaWorkflowStepDTO` (role, is_gate, default
  harness/model) → `{stage_id: NodeMeta(harness, model)}` and pass it to
  `render_dag_svg(stages, node_meta=…)`. This keeps enrichment on the catalog side, not
  in `dag.py`'s shared contract.
- **`views/workflows.py` — `_render_dadaia_workflow_card`.** Remove the dead Mermaid
  block (line 84/100, `dadaia-wf-diagram-mermaid` + `render_md_to_html(wf.diagram_mermaid)`).
  Restructure the card as a big grid cell: header (display-name, availability badge, step
  count), purpose, the enhanced SVG fluxogram, and a compact step summary. The full step
  list moves into the expand/detail.
- **Clean orphaned-Mermaid removal (arch finding #5).** After the card no longer renders
  Mermaid, sweep the now-orphaned producer chain so no second stale diagram layer remains:
  `render_step_mermaid` (dadaia_catalog.py:446 + `__all__` export at 857 + its call at
  724), the `diagram_mermaid` DTO field (dadaia_catalog.py:136), and the detail-path
  consumers at api.py:732 (`base["diagram_mermaid"]`) and 771. The enhanced server-SVG is
  the single diagram source on both card and detail view. **Guard:** grep for every
  `diagram_mermaid` / `render_step_mermaid` reference before deleting; if one is still
  genuinely live (not CSP-dead) at implementation, keep that minimal reference and
  document the exception (SPEC R7).
- **Click-to-expand — DECIDED (accepted PE decision): reuse the existing detail route.**
  `#workflows?detail=<name>` / `GET /api/workflows/<name>` +
  `render_workflows_first_class_section()` machinery (already server-rendered, already
  CSP-clean, no new inline script). The `<dialog>` alternative is rejected to avoid a new
  CSP hash. Detail view lists each step fully: fragment id, role → persona, harness,
  model, purpose, gate flag (all already in `DadaiaWorkflowStepDTO`).
- **`assets/css/workflows.py`** — card-grid layout (responsive, no wrap/overflow),
  fluxogram viewport styling, detail/expand styling. Consistent with AC-4 tokens.

### 3.2 AC-2 — Agentic tab rework

- **`views/agents.py` — `render_agents_subsection`.** Replace the single sparse grid with
  two labelled sections keyed by the **role column**:
  - **Claude sub-agents** — from `public/agents/*.md` (already surfaced via `/api/agents`
    / `MarkdownAgentStore`); render role, tier, model, description (these fields exist on
    the agent entity).
  - **Layer-2 personas** — from `public/personas/*.md` via `PersonaLoader`. Needs a new
    read-only data source into the panel.
- **Persona field reality is PINNED (arch finding #1).** The `Persona` dataclass
  (`features/lifecycle/personas/loader.py:96-107`) = `{id, role, summary, source_agent,
  harness_universal, body, path}` — **no `model`, no `tier`**. The personas reader
  surfaces exactly these fields plus `layer = "Layer-2"` as a **constant**. It must
  **NOT** invent `persona.model` or `persona.tier`. A Layer-2 persona's model is a
  per-workflow-**STEP** binding, not a persona attribute.
- **New read-only personas endpoint.** Add a panel-side reader that calls `PersonaLoader`
  to enumerate the 8 personas (id, role, summary, source_agent, harness_universal).
  Expose via `GET /api/personas` in `views/api.py` + `container.py build_panel_views()`,
  bearer-only + loopback-bypass consistent with existing routes. (Accepted PE decision:
  a separate endpoint, not folded into `/api/agents`, keeps the two rosters cleanly typed.)
- **Persona "where used" + any derived model (arch finding #1).** For each persona role,
  list the workflow steps whose `DadaiaWorkflowStepDTO.role` matches (from
  `list_dadaia_workflows()`). If a model is shown for a persona at all, derive it **ONLY**
  from those step bindings' harness/model — never from `PersonaLoader`. Render "not
  referenced by any governed step" explicitly when the role maps to 0 steps (R5).
- **`assets/js/agents.js`** — render the two rosters (or a new `personas.js` registered
  via `window.Panel.register`); data-dense card layout, no wrapping. Reuse `window.escHtml`.
- **`assets/css/agents.py`** — two-section layout, role-keyed columns, fix overflow/wrap.

### 3.3 AC-3 — Model picker incl. OpenRouter `kimi-2.7`

- **`views/workflow_policy.py` / `assets/js/workflow-policy.js` / `GET /api/workflow-model-profiles`.**
  Confirm the per-step model dropdown for pi steps surfaces the **full**
  `known_layer2_model_ids()` set (registry codex ids ∪ `kimi-2.7`). If the profiles
  endpoint already derives from `known_layer2_model_ids()`, this is a verification +
  UI-affordance task (ensure the id is visible/selectable and labelled as OpenRouter);
  if it hardcodes a narrower set, widen it to read `known_layer2_model_ids()`.
- **Model id is effort-suffixed (arch finding #3).** `model_choices('pi')`
  (`core/harness_models.py:169`) returns `id:effort` strings — the catalog entry is
  `HarnessModelOption("kimi-2.7", "high")`, so the selectable/persisted value is
  **`kimi-2.7:high`**, not bare `kimi-2.7`. Label it **"OpenRouter — kimi-2.7 (high)"** in
  the dropdown. Do not strip the effort suffix (the resolver's `validate(harness, model)`
  expects the suffixed form).
- **Persistence path is unchanged and must be verified end-to-end:** select
  `kimi-2.7:high` → `PUT /api/workflow-model-policy` → validated overlay
  `.dadaia/states/workflow_model_policy.json` (validate-before-write, `.last-good.json`
  backup) → resolver honors it (`GET /api/workflow-model-policy`). No changes to the
  overlay store or resolver (out of scope) — only surface + confirm.

### 3.4 AC-4 — Overall restyle

- **`assets/css/tokens.py`** — audit/normalize spacing, radius, shadow, typography tokens;
  keep the 3-palette theme system (`[data-theme]`) and brand-identity base tokens intact.
- **`assets/css/structure.py`** — consistent buttons, spacing, nav, card frames; eliminate
  row-wrapping/horizontal overflow at desktop widths.
- **Consistency is token-anchored, not taste-anchored (arch finding #4).** Every touched
  control style (buttons, spacing, typography) must consume `tokens.py` CSS variables —
  **no ad-hoc CSS literals** (hard-coded hex colors, px spacing, radii, font sizes) in the
  restyled control rules. Consistency is then reviewable by grepping the CSS modules for
  literals rather than eyeballing. Add any missing semantic token to `tokens.py` rather
  than inlining a literal.
- Touch per-tab CSS modules only as needed to remove wrap/overflow and align to the token
  pass; avoid behavioral changes to Projects/Sessions/Kanban/Reports/Academy/Servers.
- Preserve WCAG AA contrast on badges/text (brand-identity constraint).

### 3.5 AC-5 — CSP + tests + Playwright

- **CSP hash workflow.** For every changed or new inline `<script>` body, recompute
  `base64(sha256(exact-inline-bytes))` and update `_CSP_SCRIPT_HASH_1/2` (or add a hash)
  in `handler.py` (lines 111/116, applied 824). **Prefer reusing registered
  `/static/*.js` assets over new inline scripts** — external `'self'` scripts need no
  hash. Verify the served page has zero CSP-blocked scripts (browser console / Playwright).
- **Unit/API tests.** Update `tests/unit/features/panel/**` for the new
  Workflows/Agentic/personas/model-picker rendering; add tests for the new personas
  reader/endpoint and the enhanced `render_dag_svg` node content.
- **Playwright (GH-only).** Run the **full panel Playwright suite locally** after the
  nav/DOM changes (memory gotcha: e2e-panel is GH-only; must run locally after nav/DOM
  edits). Record the result in CLOSURE `## Validations`.
- **Projection.** Panel Python is not lib-projected, but if any `public/personas`-facing
  copy is touched, run `dadaia public stage && dadaia public install --target all &&
  dadaia public doctor` (`[ok] public-privacy`).

---

## 4. Execution order

1. **T-45-01..02** — enhance `render_dag_svg` (fluxogram nodes) + catalog adapter (AC-1 core).
2. **T-45-03** — rebuild Workflows cards, remove dead Mermaid, wire click-to-expand (AC-1).
3. **T-45-04..05** — personas reader + `/api/personas`; rebuild Agentic two-roster view (AC-2).
4. **T-45-06** — model picker surfaces `kimi-2.7`; verify persistence (AC-3).
5. **T-45-07** — restyle baseline: tokens + structure (AC-4).
6. **PREVIEW GATE** — spin up `dadaia panel`, operator visual sign-off; capture refinements.
7. **T-45-08** — refine per operator feedback (AC-1/AC-2/AC-4 polish).
8. **T-45-09** — CSP hashes recomputed; unit/API tests; local Playwright; doctors (AC-5).

Steps 1–5 produce the **previewable first cut**; step 6 is the operator preview; steps
7–9 harden and close.

---

## 5. Technical risks (see SPEC §6)

- **R1 CSP server-SVG (HARD):** enhance server SVG, not client Mermaid; recompute CSP
  hashes; prefer external `/static/*.js` over inline. Verify zero blocked scripts.
- **R2 e2e-panel GH-only:** run full panel Playwright locally before closure.
- **R3 SVG node readability:** iterate node layout under visual preview; escape+truncate.
- **R4 restyle regressions:** conservative token scope; preview every tab; WCAG AA re-check.

---

## 6. Validation plan

- `pytest tests/unit/features/panel` (+ workflows/personas units) green.
- `grep` served `/` HTML: no `<pre class="mermaid">` in Workflows; recomputed
  `_CSP_SCRIPT_HASH_*` match emitted inline scripts.
- Manual: `dadaia panel` — Workflows fluxogram cards + expand; Agentic two rosters keyed
  by role with persona "where used"; policy editor selects+persists `kimi-2.7`; no
  wrap/overflow at 1024px/1440px; 3 palettes cycle.
- Local full panel Playwright suite passes.
- `dadaia specs doctor` green; `dadaia public doctor` `[ok] public-privacy` (if public
  copy touched).
- Operator visual sign-off on the restyle (subjective AC-4 gate).
