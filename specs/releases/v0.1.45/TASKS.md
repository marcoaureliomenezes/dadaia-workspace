# TASKS — Release: v0.1.45

**Status:** Aprovado
**Release ID:** v0.1.45
**Owner:** product-engineer

---

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]` per owner unless
disjoint write sets are declared. Ordered so a **previewable first cut** (T-45-01..07)
lands before the operator PREVIEW GATE, then refine + harden.

Owners: **software-engineer** (panel Python/JS/CSS + tests); **ai-engineer** for any
persona/agentic-facing copy authored into `public/`.

---

## AC-1 — Workflows tab redesign

- [x] **T-45-01** — Add optional `node_meta` to `render_dag_svg` for the fluxogram.
  - Owner: software-engineer
  - Files: `dadaia_workspace/features/workflows/dag.py`
  - Precondition: none.
  - Done (arch finding #2 — PINNED contract): `render_dag_svg(stages, node_meta=None)`
    gains an **optional** `node_meta: dict[str, NodeMeta] | None = None` param (keyed by
    stage id, carrying harness/model), default `None` so the first-class detail view
    (called with no meta) is byte-for-byte unchanged. `_render_node` (dag.py:231) already
    draws stage-id + agent + gate ⊙ — it additionally draws harness/model when `node_meta`
    has an entry for the stage. **`StageDTO` (service.py:74-83) is SHARED and MUST NOT be
    widened.** Function stays pure; `role="img"` + `<title>` + `aria-label`; text
    escaped/truncated. Unit test asserts: (a) no-meta output identical to pre-change;
    (b) with-meta output carries harness/model.
  - Parallelism: independent of AC-2/AC-3.

- [x] **T-45-02** — Build the `node_meta` map from workflow steps (catalog side).
  - Owner: software-engineer
  - Files: `dadaia_workspace/features/workflows/dadaia_catalog.py`
  - Precondition: T-45-01 (`NodeMeta` shape known).
  - Done: card-side builder maps each `DadaiaWorkflowStepDTO` (role, is_gate, default
    harness/model) → `{stage_id: NodeMeta(harness, model)}` and calls
    `render_dag_svg(stages, node_meta=…)`. Enrichment lives on the catalog side, **not** in
    `dag.py`'s shared contract; `StageDTO` untouched. Unit-tested.

- [x] **T-45-03** — Rebuild Workflows cards + clean orphaned-Mermaid sweep + wire expand.
  - Owner: software-engineer
  - Files: `dadaia_workspace/features/panel/views/workflows.py`,
    `dadaia_workspace/features/panel/views/assets/css/workflows.py`,
    `dadaia_workspace/features/workflows/dadaia_catalog.py`,
    `dadaia_workspace/features/panel/views/api.py`
  - Precondition: T-45-01, T-45-02.
  - Done: `_render_dadaia_workflow_card` emits big card (header + fluxogram + compact
    summary); click-to-expand reuses `#workflows?detail=<name>` / `GET /api/workflows/<name>`
    (accepted PE decision — NOT a `<dialog>`); responsive grid, no wrap/overflow.
    **Clean orphaned-Mermaid removal (arch finding #5):** remove the card Mermaid block
    (workflows.py:84) AND sweep the orphaned producer chain — `render_step_mermaid`
    (dadaia_catalog.py:446 + `__all__` 857 + call 724), `diagram_mermaid` field
    (dadaia_catalog.py:136), and detail-path consumers api.py:732/771 — since the enhanced
    SVG is the single diagram source on card + detail. Guard: grep every
    `diagram_mermaid`/`render_step_mermaid` ref before deleting; if one is genuinely live,
    keep only that minimal ref and note it (SPEC R7). `grep` of served Workflows/detail
    HTML shows no `<pre class="mermaid">` and no `diagram_mermaid` residue. Unit tests
    updated.

## AC-2 — Agentic tab rework

- [x] **T-45-04** — Personas reader + read-only `/api/personas` endpoint.
  - Owner: software-engineer
  - Files: `dadaia_workspace/features/panel/views/api.py`,
    `dadaia_workspace/features/panel/service.py` (or `container.py build_panel_views()`),
    new panel-side persona reader module if needed.
  - Precondition: none (independent of AC-1).
  - Done (arch finding #1): panel reads the 8 personas via
    `features/lifecycle/personas/loader.py` `PersonaLoader`, surfacing EXACTLY the real
    `Persona` fields `{id, role, summary, source_agent, harness_universal}` plus a constant
    `layer = "Layer-2"`. It **must NOT** invent `persona.model` or `persona.tier` (those
    fields do not exist on `Persona`). `GET /api/personas` returns the roster, bearer-only
    + loopback-bypass consistent with existing routes; unit/API test asserts no
    fabricated `model`/`tier` key in the persona payload.

- [x] **T-45-05** — Rebuild Agentic tab as two role-keyed rosters + persona "where used".
  - Owner: software-engineer
  - Files: `dadaia_workspace/features/panel/views/agents.py`,
    `dadaia_workspace/features/panel/views/assets/js/agents.js` (or new `personas.js`
    registered via `window.Panel.register`),
    `dadaia_workspace/features/panel/views/assets/css/agents.py`
  - Precondition: T-45-04.
  - Done (arch finding #1): Agentic tab shows **Claude sub-agents** (from `/api/agents`,
    with role/tier/model — these exist on the agent entity) and **Layer-2 personas** (from
    `/api/personas`, with role/summary/source_agent and a **constant `Layer-2` label — no
    per-persona model/tier column**) as two labelled sections keyed by role. Each persona
    lists the workflow steps referencing its role (via `list_dadaia_workflows()`); any
    model shown for a persona is derived ONLY from those STEP bindings' harness/model,
    never from `PersonaLoader`; render "not referenced by any governed step" when empty.
    Data-dense, no wrap/overflow; uses `window.escHtml`. Unit tests updated.

## AC-3 — Model picker

- [x] **T-45-06** — Surface full pi model set (incl. `kimi-2.7`) + verify persistence.
  - Owner: software-engineer
  - Files: `dadaia_workspace/features/panel/views/workflow_policy.py`,
    `dadaia_workspace/features/panel/views/assets/js/workflow_policy.js`,
    `dadaia_workspace/features/panel/views/api.py` (only if `/api/workflow-model-profiles`
    hardcodes a narrower set — widen to `known_layer2_model_ids()`).
  - Precondition: none (independent of AC-1/AC-2).
  - Done (arch finding #3): per-step pi model dropdown lists the full
    `known_layer2_model_ids()` set. Model ids are **effort-suffixed** — `model_choices('pi')`
    returns `id:effort`, so the kimi option's value is **`kimi-2.7:high`** (catalog entry
    `HarnessModelOption("kimi-2.7", "high")`), labelled **"OpenRouter — kimi-2.7 (high)"**;
    the effort suffix is NOT stripped (`validate()` expects the suffixed form). Selecting +
    saving persists through `PUT /api/workflow-model-policy` →
    `.dadaia/states/workflow_model_policy.json`; the resolver returns it
    (`GET /api/workflow-model-policy`). No changes to `core/harness_models.py` allowed-set
    logic, the overlay store, or the resolver. API/unit test asserts the round-trip value is
    exactly `kimi-2.7:high`.

## AC-4 — Restyle

- [x] **T-45-07** — Restyle baseline: tokens + structure.
  - Owner: software-engineer
  - Files: `dadaia_workspace/features/panel/views/assets/css/tokens.py`,
    `dadaia_workspace/features/panel/views/assets/css/structure.py` (+ minimal per-tab CSS
    only to remove wrap/overflow).
  - Precondition: T-45-03, T-45-05 (so new markup exists to style).
  - Done (arch finding #4 — token-anchored, falsifiable): every touched control style
    consumes `tokens.py` CSS variables — **no ad-hoc CSS literals** (hard-coded
    hex/px/radius/font-size) in restyled control rules; missing values are added as
    semantic tokens, not inlined. Verified by `grep` of the touched CSS modules for
    literals in control styles. No row-wrap/horizontal overflow at 1024px/1440px; 3-palette
    theme system + brand-identity tokens preserved; WCAG AA contrast held. Produces the
    **previewable first cut**.

## PREVIEW GATE

- [x] **T-45-08** — Operator visual preview + refinement.
  - Owner: software-engineer
  - Files: any of the AC-1/AC-2/AC-4 view/CSS/JS modules (polish only).
  - Precondition: T-45-01..07 (first cut complete).
  - Done: `dadaia panel` spun up and shown to the operator; refinements captured and
    applied; operator sign-off recorded (feeds CLOSURE `## Validations`). Register the
    dev server via `dadaia server register` while previewing.
  - **Preview outcome (operator-directed refinement pass, 2026-07-01).** After previewing
    the first cut the operator directed three refinements, all applied:
    1. **Workflows tab IA flip** — the diagram-card catalog now LEADS the tab
       (prominent, default-visible top of `render_workflows_first_class_section`); the
       per-step model-governance policy MATRIX is demoted below the cards into a
       collapsed `Model policy` `<details>` disclosure. Both stay fully functional
       (`#wfp-root` is populated on load regardless of the disclosure state). Section
       intro copy is now cards-first. New unit test
       `test_diagram_cards_lead_and_policy_matrix_is_secondary` pins the order.
    2. **Stronger modern restyle** — token-anchored: added `--radius-lg`,
       `--shadow-card-rest`, `--shadow-card-hover`, `--lift-hover`; applied card
       elevation + hover lift (motion-guarded) + softer radius to the Workflows diagram
       cards, Agentic persona cards, and sub-agent cards; accent pill on gate markers;
       tighter title hierarchy. No ad-hoc literals in touched control rules; 3-palette
       theme + brand tokens + WCAG AA preserved; no row-wrap/overflow at 1024/1440px.
    3. **kimi selectable via governed pi profile (closes T-45-06)** — added built-in
       `pi-openrouter-kimi-high` profile; picker offers it; PUT/GET/resolver round-trip
       proven; bug `v0145-t4506-…` marked Resolved.

## AC-5 — Guardrails

- [x] **T-45-09** — CSP hashes + tests + local Playwright + doctors.
  - Owner: software-engineer
  - Files: `dadaia_workspace/features/panel/handler.py` (`_CSP_SCRIPT_HASH_*`),
    `tests/unit/features/panel/**`.
  - Precondition: all preceding tasks (final markup/scripts settled).
  - Done: `_CSP_SCRIPT_HASH_1/2` recomputed for every changed/new inline script and match
    the emitted bodies (zero CSP-blocked scripts on the served page); `pytest` panel
    unit/API green; **full panel Playwright suite run locally** and passing (GH-only in
    CI); `dadaia specs doctor` green; `dadaia public doctor` `[ok] public-privacy` (if any
    `public/` copy was touched, run stage+install first).
  - **Completion (2026-07-01, software-engineer).**
    - **CSP:** the refinement added NO new inline scripts (all real scripts stay external
      `/static/*.js`). The served index page carries exactly TWO inline scripts (theme
      pre-paint + runtime-detect in `index.py`); recomputing base64(sha256(body)) yields
      `GRTndW6m1zCm5uxB5kEDoOXw05c1c9MDdem3TFqSMfQ=` and
      `rrb6m84iyHOhA+A1XebxK17XtUkbhWfR95KsYvJgmpA=`, matching `_CSP_SCRIPT_HASH_1/2` in
      `handler.py` byte-for-byte. ZERO CSP-blocked scripts. Added a falsifiable test —
      `tests/unit/features/panel/test_security_headers.py::TestInlineScriptCspCoverage` —
      that renders the real index HTML, extracts every inline `<script>` (no `src`),
      recomputes its hash, and asserts CSP `script-src` covers it (fails loudly if a new
      un-hashed inline script appears).
    - **Panel tests:** `tests/unit/features/panel/`, `tests/integration/panel/`,
      `tests/unit/features/workflows/` — 783 passed.
    - **Playwright (local, fresh panel):** full panel suite **69 passed / 0 failed**.
      Fixed 3 stale specs broken by the T-45-08 markup changes: (a) `ops-tab.spec.ts`
      OPS-02 now expects the new `ops-subsection-personas` between agents and workflows;
      (b) `workflow-policy-editor.spec.ts` + `workflow-policy-harness-toggle.spec.ts` now
      expand the collapsed `Model policy` `<details>` disclosure (new shared
      `openModelPolicy` helper) before touching step rows, and assert the pi/codex
      dropdown filter on the option **value** prefix (`pi-`/`codex-`) rather than label
      text — robust to the new labelled `pi-openrouter-kimi-high` option
      ("OpenRouter — kimi-2.7 (high)"). Playwright outputs redirected to `.dadaia/tmp/`.
    - **Doctors:** no `public/` asset was touched this release, so `public stage/install/
      doctor` was not required. `dadaia specs doctor` shows 0 v0.1.45-relevant errors; the
      8 `SPEC-DOC-016` errors are pre-existing legacy `_archive/releases/` SemVer folder
      names (FROZEN, dated 2026-06-04, shipped identically in v0.1.44) — orthogonal to
      this release and untouchable.

- [x] **T-45-10** — (conditional) Persona/agentic panel-facing copy.
  - Owner: ai-engineer
  - Files: `dadaia_workspace/public/personas/*.md` and/or `public/agents/*.md` labels
    ONLY IF the Agentic redesign needs new short panel-facing descriptions; then
    `dadaia public stage && dadaia public install --target all && dadaia public doctor`.
  - Precondition: T-45-05 (surface requirements known).
  - Done: any new persona/agent panel copy authored at source, projected, doctor
    `[ok] public-privacy`. If no copy change is needed, mark `[x]` with note "no copy
    change required."
  - **No copy change required (2026-07-01, software-engineer).** All 8 v0.1.44 persona
    summaries (`public/personas/*.md` frontmatter `summary`) surface cleanly and read well
    in the reworked Agentic tab — verified via `GET /api/personas` (8/8 personas, zero
    empty summaries, each a clear single-line role description). No `public/` asset was
    touched this release; no new panel-facing copy is needed. No ai-engineer follow-up.
