---
name: panel-ux-overhaul
status: candidate
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/index.py#render_index" }
    change: "layout/IA reorganization of the LIVE tab set (Projects / Workflows / Reports / Academy / Servers + the cost-dashboard section surviving from the sessions decision): section grouping, density, hierarchy; redesign the theme switcher in the page shell; fix the shared header/control-row pattern that wraps onto two or more lines (runtime switcher + meta + filters/cost banner): responsive single-line layout with deliberate truncation/overflow"
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/assets/css/tokens.py#TOKENS_CSS" }
    change: "modern cohesive design system (operator verdict 2026-06-27): replace the dated '2005-website' look — proper typography scale, spacing rhythm, restrained color, and properly styled buttons/controls driven uniformly from the CSS tokens"
---

# BACKLOG — Panel UX overhaul (tab consolidation + theme switcher)

**ID:** FEAT-PANEL-UX-200
**Priority:** MEDIUM
**Owner:** project-manager (curates) → product-engineer authors SPEC/PLAN/TASKS after the
mandatory release-definition grill.
**Status:** OPEN — candidate; filed for intake, no release scoped yet.

> **Re-baselined 2026-07-02 (operator sessions decision):** the "Sessions tab
> untouched" constraint is VOID — the operator decided the session list is removed and
> only the aggregated cost dashboard survives, owned by
> `panel-sessions-cost-dashboard-only`. This item's row-wrapping fix now targets the
> shared row pattern on the surviving tabs only; any Sessions-specific styling scope is
> dropped here.

> **Re-baselined 2026-07-01 (v0.1.47 sanitization):** the two "fold Agents/Workflows
> sections into the consolidated tab" intents were DELIVERED by v0.1.45 (Agentic tab
> deleted; Workflows leads with diagram cards; `views/agents.py`/`views/workflows.py`
> removed) and were dropped here — their anchors no longer exist. Remaining scope:
> visual-quality/layout overhaul (tokens) + wrapping control rows + shell/theme switcher.

> **Re-baselined 2026-06-26** against the current panel (post-v0.1.24, including the
> read-only dadaia-workflow catalog tab). The dated "PICKED for 0.1.6" / v0.1.11 framing and
> the shipped-bug cross-references have been dropped — they referenced closed releases.

> **Operator verdict 2026-06-27 (post-v0.1.30), folded in here instead of a duplicate item.**
> Functionality is OK so far (needs more testing) but **the visual style is bad — "crap",
> "trash", "looks like a 2005 website".** Specific complaints: **ugly buttons**; **header/
> control rows breaking onto two or more lines**; **bad layout organization** (poor grouping/
> hierarchy); overall dated and incohesive. The operator believes it can be done much better
> and may take the visual direction themselves. This broadens the item from "IA + theme
> switcher" to a full **visual-quality + layout** overhaul of the (working) panel surfaces.
> (The PI runtime switcher + styling shipped in v0.1.30; this item now owns making the whole
> panel look good.)

## Thesis

The `dadaia panel` information architecture is too spread out, its controls/buttons look
dated and unstyled, header rows wrap badly, and the overall layout is poorly organized — it
reads like a low-craft 2005 website. The operator wants a modern, cohesive visual redesign:
consolidate the workflow-state tabs into a denser view, redesign the theme switcher, restyle
all controls from a real design system, fix row wrapping, and reorganize the layout for clear
hierarchy. This is a **UX/visual** overhaul of existing, working surfaces — keep behavior,
re-skin and re-organize.

## Residual scope

1. **Layout/IA reorganization of the live tab set.** *(Re-scoped 2026-07-02 — the
   originally named Agents / Kanban / separate workflow-catalog tabs NO LONGER EXIST;
   v0.1.45 delivered that consolidation. The live nav is Projects / Workflows /
   Sessions / Reports / Academy / Servers.)* Reorganize grouping, density, and
   hierarchy across the live tabs. The Sessions surface is owned by
   `panel-sessions-cost-dashboard-only` (2026-07-02) and is out of scope here.
2. **Theme-switcher UX overhaul.** Visually redesign the theme switcher so it applies and
   persists a theme selection cleanly.
3. **Design system + button/control restyle (operator 2026-06-27).** Establish a modern,
   cohesive design system driven from `TOKENS_CSS` (typography scale, spacing rhythm,
   restrained color, properly styled buttons/controls) consumed uniformly across views.
4. **Fix multi-line row wrapping (operator 2026-06-27).** Header/control rows (runtime
   switcher + meta + filters/cost banner — the shared pattern across Sessions/Agents/
   Workflows) must lay out responsively on one line by default with deliberate truncation;
   fix the shared row component/CSS once.
5. **Layout/IA reorganization (operator 2026-06-27).** Restructure section grouping,
   alignment, and density so the panel reads as one designed product, not stacked fragments.

## Where this lives (current panel, no plugin)

The panel is `dadaia_workspace/features/panel/` — Python views in `views/*.py`, browser JS
in `views/assets/js/*.js`, CSS-in-Python in `views/assets/css/*.py`. Done as library source
edits, then projected/validated on this live instance.

**Operator-authorized `plugin-scope` deviation:** browser HTML/CSS/JS + UX redesign would
normally route to the `frontend-design` plugin, but no `dadaia plugin install` command
exists yet (tracked by `plugin-packs-and-install-command`). The operator authorized doing
this directly; record the deviation in the SPEC.

## Constraint — no unvalidated panel UI ships

Any panel UI change MUST land with deep-interaction e2e tests **and** the global
4xx/5xx-and-console-error gate (click through the consolidated tab and the theme control;
fail on any failed response or console error). Label-deep assertions are insufficient.
The restyle MUST preserve the strict-CSP posture (per-inline-script sha256 hashes in
`panel/handler.py`) and the loopback/Host-guard security model — no `unsafe-inline`, no new
un-hashed inline scripts. The panel Playwright e2e is **GH-only** (not in `ci preflight`) —
run the full panel suite locally before declaring done.

## Out of scope

- The Sessions surface (owned by `panel-sessions-cost-dashboard-only`).
- New panel features beyond tab consolidation and the theme-switcher redesign.
- Publishing/deploying externally — operator-gated.

## Release-definition note

Intake only. When picked, the mandatory grill must resolve the layout/IA direction for
the live tab set, the card-density target, and the `plugin-scope` deviation +
e2e/deploy-gate evidence bar (the deviation dissolves if `plugin-packs-and-install-command`
ships first). No implementation before SPEC/PLAN/TASKS approval.
