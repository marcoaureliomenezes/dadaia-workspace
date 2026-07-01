# SPEC — Release: v0.1.45

**Status:** Aprovado
**Release ID:** v0.1.45
**Owner:** product-engineer
**Opened:** 2026-07-01

---

## 1. Problem and context

`dadaia panel` is the operator's single-window control surface for the workspace
(feature atom `specs/memory/product/panel/panel.md`). It is server-rendered Python:
HTML/CSS/JS are emitted as Python string constants under
`dadaia_workspace/features/panel/views/` (`assets/css/*.py`, `assets/js/*.js`), served
via `views/static.py` `_ASSETS`. There is no template engine, no React, no build step,
and a strict CSP (`script-src 'self'` + exactly two sha256 inline-script hashes — no
CDN).

After v0.1.44 shipped the Layer-2 **persona** entity (`public/personas/<role>.md`, 8
non-PM roles) alongside the existing Claude sub-agents (`public/agents/*.md`), the panel
does not do this surface justice. The operator's verdict on the current UI:

- **Workflows tab is a confusing list.** Each `_render_dadaia_workflow_card` emits a
  server-SVG DAG *and* a dead client-Mermaid `<pre class="mermaid">` block (blocked by
  CSP — Mermaid CDN never loads), plus a flat `<ol>` step list. There is no big,
  scannable per-workflow card with a clear readable fluxogram and click-to-expand step
  detail.
- **Agentic tab "makes no sense."** `render_agents_subsection` renders a static scaffold
  + runtime switcher into an empty `#agents-grid` populated client-side by `agents.js`
  `renderCard()` — a sparse 4-fact card. It surfaces neither the Claude sub-agent roster
  nor the new Layer-2 personas coherently.
- **Model picker is incomplete.** v0.1.44 widened the pi model set to
  `known_layer2_model_ids()` = registry codex ids ∪ `LAYER2_EXTRA_MODEL_IDS`
  (`kimi-2.7`, an OpenRouter id). The per-workflow/per-step picker must surface these.
- **Overall style is dated.** The operator calls it "very ugly / 2005 / ugly buttons /
  rows wrap / bad layout."

This is a fast-follow to v0.1.44 and is a **pure panel-presentation redesign**: it
surfaces existing data better. It does not add backend model governance, does not
introduce a template engine or client framework, and does not relax the CSP.

**Hard design constraint (load-bearing).** Diagrams MUST stay **server-rendered SVG**
(`features/workflows/dag.py` `render_dag_svg(stages)`, a pure function with
`role="img"`). The CSP forbids CDN Mermaid; the existing client-Mermaid block is already
dead. Any new inline `<script>` requires its sha256 to be added to the CSP allowlist in
`handler.py` (`_CSP_SCRIPT_HASH_1/2` at lines 111/116, used at line 824) — recompute the
hash or the script is blocked (known CSP sha256 trap).

---

## 2. Objective

Redesign the `dadaia panel` Workflows and Agentic surfaces plus the overall visual
style so the operator can, at a glance: see every dadaia-workflow as a big card with a
readable server-SVG fluxogram and click-to-expand step detail; understand the full
agentic surface (Claude sub-agents AND Layer-2 personas via the role column); pick
per-workflow/per-step models including the newly-allowed OpenRouter ids (`kimi-2.7`);
all under a cohesive, modern, non-wrapping visual pass — without a CDN, React, or build
step, and without relaxing the CSP.

---

## 3. Scope

Five acceptance clusters. Each is stated with a mechanical "how to verify". Full
module-by-module design is in `PLAN.md`.

### AC-1 — Workflows tab redesign (big diagram cards + click-to-expand)

- Per-workflow cards render in a clean responsive grid; each card shows workflow
  display-name, purpose, availability badge, step count, and an **enhanced
  server-rendered SVG fluxogram**: ordered steps as nodes with **role + gate marker +
  harness/model**, edges left→right (or top→down), readable at card size.
- **SVG contract is pinned (arch finding #2).** `_render_node` (dag.py:231) already
  renders stage-id + agent + gate marker (⊙); only harness/model is new.
  `render_dag_svg(stages: list[StageDTO])` gains an **optional** second parameter
  `node_meta: dict[str, NodeMeta] | None = None` (keyed by stage id, carrying
  harness/model), defaulting to `None` so the first-class detail view is unchanged.
  **`StageDTO` (service.py:74-83) is shared with `WorkflowDetailDTO` and MUST NOT be
  widened.** The Workflows card passes the enriched `node_meta` map; `_render_node`
  reads it; the function stays pure.
- **The dead client-Mermaid layer is removed cleanly (arch finding #5).** Remove the
  card's Mermaid block (`dadaia-wf-diagram-mermaid` /
  `render_md_to_html(wf.diagram_mermaid)`, workflows.py:84) **and** the now-orphaned
  producer chain in the same sweep — `render_step_mermaid` (dadaia_catalog.py:446, its
  `__all__` export at 857, its call at 724), the `diagram_mermaid` DTO field
  (dadaia_catalog.py:136), and its detail-path consumers (api.py:732, 771) — because the
  enhanced server-SVG replaces the diagram on both the card and the detail view. Do not
  leave a second stale diagram layer. (If any consumer proves still live at
  implementation, keep only that minimal reference and document the exception.)
- **Click-to-expand** a card opens a detail view where every step is fully detailed:
  fragment id, role → persona, harness, model, purpose, and gate flag. **Decided (PE):**
  reuse the existing detail route (`#workflows?detail=<name>` /
  `GET /api/workflows/<name>` + `render_workflows_first_class_section()`) — already
  server-rendered and CSP-clean; the `<dialog>` alternative is rejected to avoid a new CSP
  inline-script hash.
- CSP-safe: diagrams stay server-SVG; any new inline script has its sha256 added to the
  `handler.py` allowlist.
- **How to verify:** `dadaia panel`; Workflows tab shows a card grid with a labelled SVG
  fluxogram per workflow (nodes carry role + gate + harness/model); no
  `<pre class="mermaid">` in the emitted Workflows HTML (`grep` the rendered `/` output);
  clicking a card reveals per-step detail; `pytest tests/unit/features/panel` green;
  `dadaia panel` served page passes CSP with no console-blocked scripts.

### AC-2 — Agentic tab rework (Claude sub-agents + Layer-2 personas via role column)

- Replace the sparse `#agents-grid` with a coherent, organized view of the agentic
  surface, split/sectioned into:
  - **Claude sub-agents** — roster from `public/agents/*.md` (12 entries incl.
    project-manager and the 3 plugin stubs), and
  - **Layer-2 personas** — roster from `public/personas/*.md` (8 non-PM roles), loaded
    via `features/lifecycle/personas/loader.py` `PersonaLoader`.
- Each entity uses the **role column** to key the two rosters together. **Persona field
  reality is pinned (arch finding #1):** the `Persona` dataclass
  (`features/lifecycle/personas/loader.py:96-107`) = `{id, role, summary, source_agent,
  harness_universal, body, path}` — it has **no `model` and no `tier`**. A Layer-2
  persona has no single model (model is a per-workflow-**STEP** binding). Therefore:
  - **Claude sub-agents** show: role, tier, model (these exist on the agent entity).
  - **Layer-2 personas** show: role, `summary`, `source_agent`, and `layer = Layer-2`
    rendered as the **constant it is** — never a per-persona `model` column.
  - If a model is shown for a persona at all, it is derived **ONLY** from that persona's
    where-used **STEP** bindings (`DadaiaWorkflowStepDTO` from `list_dadaia_workflows()`),
    never from `PersonaLoader`. The implementer must not fabricate `persona.model`.
- **Where-used** — for each persona role, list the workflow steps whose
  `DadaiaWorkflowStepDTO.role` matches; render "not referenced by any governed step"
  explicitly when empty (R5).
- Data-dense but organized; the wrapping/overflow the operator dislikes is fixed.
- **How to verify:** `dadaia panel`; Agentic tab shows two labelled rosters (Claude
  sub-agents with role/tier/model; Layer-2 personas with role/summary/source_agent and a
  constant `Layer-2` label, no fabricated model column) keyed by role; each persona lists
  the workflow steps that use its role (any derived model comes from those step
  bindings); `GET /api/agents` and the new `GET /api/personas` endpoint return the
  expected rosters; no row-wrap/overflow at ≥1024px; `pytest tests/unit/features/panel`
  green.

### AC-3 — Model picker surfaces the full allowed set (incl. OpenRouter `kimi-2.7`)

- The per-workflow/per-step model picker (`views/workflow_policy.py` /
  `assets/js/workflow-policy.js`, `GET /api/workflow-model-profiles`) surfaces the full
  allowed model set per harness. For **pi**, that includes `LAYER2_EXTRA_MODEL_IDS`
  (`kimi-2.7`) via `known_layer2_model_ids()`.
- **Model ids are effort-suffixed (arch finding #3).** `model_choices('pi')`
  (`core/harness_models.py:169`) returns `id:effort` strings, not bare ids — the catalog
  entry is `HarnessModelOption("kimi-2.7", "high")`, so the selectable/persisted value is
  **`kimi-2.7:high`**. The picker labels it **"OpenRouter — kimi-2.7 (high)"**.
- Choosing `kimi-2.7:high` **persists** through the existing validated overlay/policy path
  (`PUT /api/workflow-model-policy` → `.dadaia/states/workflow_model_policy.json`,
  validate-before-write) and is honored by the resolver.
- **How to verify:** in the panel policy editor, select the OpenRouter kimi-2.7 (high)
  option for a pi step, save; reload → the choice persists;
  `cat .dadaia/states/workflow_model_policy.json` shows **`kimi-2.7:high`**; the resolver
  returns it (`GET /api/workflow-model-policy`); `pytest` for the workflow-policy view/api
  green (round-trip assertion is on `kimi-2.7:high`).

### AC-4 — Overall visual restyle

- A cohesive visual pass over `assets/css/tokens.py` + `assets/css/structure.py` (and the
  per-tab CSS modules touched); no row-wrapping/horizontal overflow at normal desktop
  widths; modern look. **Keep the existing 3-palette theme system**
  (`[data-theme="mint|sage|warm"]`) and the brand-identity tokens ([[brand-identity]]).
- **"Consistent" is anchored to the token set, not taste (arch finding #4):** buttons,
  spacing, and typography are consistent **because controls consume `tokens.py` CSS
  variables** (spacing/radius/shadow/color/typography tokens) — **no ad-hoc CSS literals**
  in the touched control styles. This makes consistency reviewable by `grep` for literal
  values instead of eyeballing.
- **How to verify (falsifiable):** `grep` the touched CSS modules — no hard-coded
  color/spacing/radius/font-size literals in control styles (they reference `var(--…)`
  tokens); no wrapping/overflow at 1024px and 1440px; theme switcher still cycles all 3
  palettes; WCAG AA contrast preserved on badges/text. The subjective operator sign-off
  (see PLAN preview gate) is additive polish on top of this mechanical DoD, not a
  replacement for it.

### AC-5 — Guardrails and tests

- Panel API/unit tests updated for the new Workflows/Agentic/model-picker rendering.
- CSP hashes recomputed in `handler.py` for **any** changed or new inline script
  (`_CSP_SCRIPT_HASH_*`); the served page has zero CSP-blocked scripts.
- e2e-panel Playwright is **GH-only** in CI; because this release changes panel nav/DOM,
  the **full panel Playwright suite must be run locally** before closure (memory
  gotcha), and the result recorded in CLOSURE `## Validations`.
- **How to verify:** `pytest` (panel unit/api) green; `grep` confirms recomputed
  `_CSP_SCRIPT_HASH_*` match the emitted inline scripts; local Playwright panel run
  passes; `dadaia public doctor` `[ok] public-privacy`; `dadaia specs doctor` green.

---

## 4. Out of scope

- **No React, no CDN, no build step, no template engine.** The panel stays
  server-rendered Python strings + stdlib.
- **No new backend model or model-governance semantics.** This release only *surfaces*
  the model set already produced by `known_layer2_model_ids()` / the existing
  `WorkflowExecutionPolicyResolver`. No changes to `core/harness_models.py` allowed-set
  logic, the overlay store, or the resolver.
- **No client-side Mermaid / client-side graph layout.** Diagrams remain server-SVG.
- **No CSP relaxation.** `script-src` stays `'self'` + explicit sha256 hashes; no
  `'unsafe-inline'` for scripts, no external origins.
- **No changes to other tabs' behavior** (Projects, Sessions, Kanban, Reports, Academy,
  Servers) beyond the shared restyle (tokens/structure) in AC-4.
- **No new persona/agent entities.** Personas and agents are consumed as-is from
  `public/personas/` and `public/agents/`; authoring copy is limited to panel-facing
  labels/descriptions.
- **No auth model change.** Loopback bypass + Bearer + Host-guard for mutations stay as-is.

---

## 5. Memory files affected at closure

- `specs/memory/product/panel/panel.md` — update the Workflows-tab and Agentic-tab
  descriptions (server-SVG fluxogram cards + click-to-expand; two-roster Agentic view
  keyed by role; model picker surfacing `kimi-2.7`) and the restyle notes. **Atomic
  snapshot only — no changelog.** (Written by product-engineer in CLOSURE phase.)
- No change expected to `architecture.md` (no layer/dependency contract change) or
  `tech-stack.md` (no new runtime dependency — stdlib + existing `mistune`). Confirm at
  closure.

---

## 6. Dependencies and risks

**Upstream / sequencing**

- Depends on v0.1.44 (persona entity + `known_layer2_model_ids()`), already shipped.
- Consumes existing anchors: `features/workflows/dag.py` `render_dag_svg` /
  `_render_node`, `features/workflows/service.py` `StageDTO` (shared, not widened),
  `features/workflows/dadaia_catalog.py` (`DadaiaWorkflowDTO`/`DadaiaWorkflowStepDTO`,
  `list_dadaia_workflows`; `render_step_mermaid` + `diagram_mermaid` are **removed** by
  this release, not consumed), `features/lifecycle/personas/loader.py` `PersonaLoader`
  (`Persona` = id/role/summary/source_agent/harness_universal/body/path — no model/tier),
  `core/harness_models.py` `known_layer2_model_ids` / `model_choices` (effort-suffixed) /
  `LAYER2_EXTRA_MODEL_IDS`.

**Risk table**

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | **CSP server-SVG constraint (hard).** Diagrams must be server-SVG; any new inline script needs its sha256 added to `handler.py` `_CSP_SCRIPT_HASH_*`. A stale hash silently blocks the script. | HIGH | Enhance `render_dag_svg`, not client Mermaid. Recompute `_CSP_SCRIPT_HASH_*` for every changed inline script; verify zero CSP-blocked scripts on the served page. Prefer no new inline script (reuse existing registered JS assets). |
| R2 | **e2e-panel is GH-only** — CI does not run panel Playwright; nav/DOM changes can regress unnoticed. | HIGH | Run the full panel Playwright suite **locally** before closure; record evidence in CLOSURE. |
| R3 | **Enhanced SVG fluxogram readability at card size** — packing role + gate + harness/model into nodes can overflow. | MEDIUM | Iterate `render_dag_svg` node layout; validate with operator visual preview; keep node text escaped and truncated. |
| R4 | **Restyle regressions across 8 tabs** — shared token/structure edits can break other tabs' layout. | MEDIUM | Scope token changes conservatively; keep 3-palette theme system; visual-preview each tab; WCAG AA re-check. |
| R5 | **Persona→workflow "where used" mapping** may be ambiguous if a role maps to 0 catalog steps. | LOW | Derive from `dadaia_catalog` step `role`; render "not referenced by any governed step" explicitly rather than an empty cell. |
| R6 | **Operator taste for AC-4** is subjective, but must not be the *only* gate. | MEDIUM | AC-4 now carries a falsifiable token DoD (controls consume `tokens.py` vars, no literals — arch finding #4). Operator visual preview is additive polish on top: land a first cut, spin up `dadaia panel`, refine (see PLAN sequencing). |
| R7 | **Orphaned Mermaid removal (arch finding #5) may hit a still-live consumer** — `diagram_mermaid` is read at api.py:732/771 (detail path), not only the card. | MEDIUM | Sweep all references (card + api.py + field + producer + `__all__`) once the enhanced SVG covers the detail view; if a consumer is still live at implementation, keep only that minimal reference and document the exception in CLOSURE. |
