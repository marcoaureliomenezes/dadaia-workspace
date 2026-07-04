# PLAN — v0.1.59 — Panel UX Overhaul

**Status:** Aprovado

Eight waves. **FR1 (design-system foundation + the DOM-contract lock) lands FIRST** — the structural lock is
captured golden-first, BEFORE any SSR-HTML restyle, so a dropped e2e selector fails loudly in unit CI. The
whole release is **pure SSR-HTML + CSS**: no `render_api_*` edit (Ruling C), no inline-script edit (Ruling B),
no new dependency (Ruling D). The panel CSS-in-Python modules are largely disjoint per wave, but
`structure.py` is shared across FR3 (de-inline row) and FR6 (dead-CSS purge) → those waves are **sequential**.
`views/index.py` is shared across FR3 (topbar-right de-inline) and FR4 (layout/IA) → sequential too. **No
parallel `[-]`.**

## Wave map

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-04 code read; mandatory release-definition grill on the
  picked set (report emitted); eight operator-unavailable ADRs recorded (§9). **Dual definition review
  2026-07-04 (software-architect REJECT A1–A6 + qa-engineer REJECT Q1–Q7 — all folded with `(A#)`/`(Q#)`
  markers; PM Binding Ruling 1 = A1/Q1 AGENTS_CSS coordinated refactor; Ruling 2 = Q2 width-e2e author-in-W3).**
  `Aprovado` after the confirming dual re-review; definition commit. Owner: product-engineer (orchestrated).

- **W1 — FR1 design-system foundation + DOM-contract lock (golden-first, the identity seam).**
  1. **DOM-contract lock FIRST.** Add `tests/unit/features/panel/test_index_dom_contract.py` rendering the real
     index (`render_index` over fixed fakes) and asserting the full §3-FR1 selector contract (6 tab ids +
     `data-section`; 6 `#section-*`; `.nav-tab`; `.memory-chip`; theme switcher
     `#theme-btn`/`#theme-menu`/three `[data-theme-value]`/`.theme-swatch-dot`; runtime switcher
     `.runtime-switcher`/`.runtime-btn`/`[data-runtime-value]`). **(A3) The fakes include ≥1
     `SpecContextProject`** (+ ≥1 server row) modelled on `test_views_index._make_context`/`_build_service` —
     NOT the empty `test_security_headers._render_index_html` fake (which renders zero cards, so `.memory-chip`
     would never render). **(A4)** it CONSOLIDATES (does not replace) `test_views_index.py`, which SURVIVES.
     **(Q5)** it is a presence-invariant **never re-baselined** this release. Committed BEFORE the SSR-HTML
     restyle — the AC-1 behavior lock.
  2. **Confirm the api-golden zero-diff baseline.** Run `test_api_golden.py` green on the pre-restyle tree;
     declare `api_golden_v0155.json` a ZERO-DIFF INVARIANT (Ruling C — never `UPDATE_API_GOLDEN`).
  3. **(Q4) CSP zero-touch equality lock.** Add to `test_security_headers.py` an assertion freezing
     `_CSP_SCRIPT_HASH_1/2` (`handler.py:111,116`) to hardcoded W1 baseline values (or byte-freeze the two
     extracted inline `<script>` bodies) — catches the edit-WITH-recompute violation `TestInlineScriptCspCoverage`
     misses.
  4. **Design-system pass on `tokens.py`.** Rationalize `TOKENS_CSS` (typographic scale, spacing rhythm,
     restrained brand-palette color, elevation/radius) — additive/rationalizing only; no palette hex change; 3
     themes + WCAG preserved. New tokens are token-named.
  - Tests: AC-1 (`test_index_dom_contract.py` green w/ populated fakes + api-golden byte-identical); AC-2 CSP
    unchanged + equality lock green (no index-script edit). AC-9(a) DOM-contract sabotage + (b′/Q4) equality-lock
    sabotage. AC-11 ledger. NO `specs/backlog`.

- **W2 — FR2 controls / buttons restyle from tokens.**
  1. Restyle interactive controls uniformly from `TOKENS_CSS` across `structure.css` (nav tabs, theme button),
     `tokens.py` (runtime buttons), `workflows.css`/`workflow-policy.css` (per-step pickers), `reports.css`/
     `academy.css` (CTAs + delete/trash) — padding rhythm, radius, hover/active/focus-visible.
  2. **Token-anchored, grep-falsifiable (Q3).** Add `tests/unit/features/panel/test_control_tokens.py` that
     iterates an **explicit selector allowlist** (`.nav-tab`, `.theme-btn`, `.runtime-btn`, `.wfp-picker`,
     `.wfp-profile-select`, report/academy CTA + trash selectors), extracts each rule body from the served
     stylesheet strings (EXCLUDING `tokens.py`), and FAILS on hex `#[0-9a-fA-F]{3,8}` / `font-size:`-with-px|rem
     / `border-radius:`-with-px; every allowed rule body contains `var(--…)` (grounded in the `test_palette.py`
     PANEL_CSS-grep pattern).
  - Tests: AC-3 token-anchor grep + control-state coverage. AC-9(c) ad-hoc-literal sabotage. AC-1/AC-2 replay
    (api-golden + DOM-contract + CSP + equality-lock unchanged). AC-11 ledger. NO `specs/backlog`.

- **W3 — FR3 single-line header / control-row layout (width e2e authored HERE — Q2/Option A).**
  1. **De-inline THREE inline styles (A5).** Move (1) `views/index.py:82` topbar-right `style=`, (2)
     `views/index.py:83` `.theme-switcher style="position:relative;"`, (3) `views/sessions.py:36`
     `.runtime-switcher style="margin-left:auto;"` into token-anchored CSS classes (`views/assets/css/structure.py`
     / `views/assets/css/sessions.py`). CSP-clean (no script change); preserves the runtime + theme switcher DOM
     contracts.
  2. **Responsive single-line CSS.** `.section-header`/`.runtime-switcher` lays out on one line by default with
     `min-width:0` + ellipsis/flex guards.
  3. **(Q2/Option A) Author the FR3 width e2e HERE, RED-first.** Add the Playwright bounding-box width spec in
     W3 co-located with the fix; run it RED at the wrap-triggering width(s) × 3 themes against the pre-fix
     wrapping tree BEFORE the de-inline lands (capture the failure), then GREEN after. **Empirically pin the
     wrap width:** topbar-right is full-viewport-width, the Sessions row is inside the `--main` 1024px cap — test
     1024 and 1440; if neither wraps, pin+document the width that does (never a non-red RED).
  - Tests: AC-4 RED-first (the W3-co-located width e2e FAILS on the pre-fix wrapping tree, GREEN post-fix) +
    `grep 'style=' index.py sessions.py == 0` (all three inline styles gone, A5). AC-9(d) restore-wrapping
    sabotage — **runnable in W3** (the e2e exists). AC-1/AC-2 replay. AC-11 ledger. NO `specs/backlog`.

- **W4 — FR4 layout / IA hierarchy + density.**
  1. Restructure section/card grouping, alignment, density across the live tabs (SSR-HTML in `views/index.py` +
     section-scaffold views + their CSS). **6-tab nav unchanged (Ruling A).** **(A4) Do NOT rename the container
     marker strings `sessions-dashboard`/`reports-list`/`academy-content`** that
     `test_views_index.py::test_index_renders_panel_sections` keys on — or, if a rename is genuinely required,
     it is a STOP-and-rescope (Q5) that EDITs `test_views_index.py` in the SAME wave and records it on the ledger.
  - Tests: AC-5 — DOM-contract lock proves all 6 tabs/sections present; `test_views_index.py` SURVIVES (markers
    preserved); no row-wrap/overflow at the pinned width (W3 e2e); api-golden byte-identical. AC-1/AC-2 replay.
    AC-11 ledger. NO `specs/backlog`.

- **W5 — FR5 theme-switcher polish + FR6 two-category dead-CSS purge.**
  1. **FR5**: refine the theme button + popover from tokens; preserve every `theme-switcher.spec.ts` selector +
     localStorage + FOUC + Escape + warm focus-ring token + axe. Two inline pre-paint scripts byte-identical.
  2. **FR6 Category A** (dead rules in `structure.py#STRUCTURE_CSS`: `.ops-subsection*`/`.memory-link*`/
     `.card-header`/`.card-primary-badge`/`.card-links`/`.context-card.primary`/`.context-count`/
     `.agents-grid--compact`/`.workflows-grid--compact`): remove each only when grep proves zero live refs in
     served HTML + all JS + JS template strings + tests; ambiguous ⇒ KEEP with a reason.
  3. **FR6 Category B — `agents.py#AGENTS_CSS` COORDINATED REFACTOR (A1/Q1, PM Ruling 1).** Delete `agents.py`
     WITH its 3 co-edits in the SAME wave: `views/assets/__init__.py` (drop import + `__all__` entry);
     `tests/unit/features/panel/test_palette.py` + `test_panel_css_contrast.py` (drop `+ AGENTS_CSS` from the
     `PANEL_CSS` concat + the import). Gate: `grep -rn AGENTS_CSS dadaia_workspace/ tests/` returns ZERO after
     the co-edits.
  - Tests: AC-6 `theme-switcher.spec.ts` green incl. axe. AC-7 Category-A per-selector grep proofs + Category-B
    `grep -rn AGENTS_CSS == 0` proof; full e2e + full unpiped pytest backstop green. AC-9(e) delete-a-live-Cat-A
    selector sabotage (response-guard FAILS) + (f) delete AGENTS_CSS without co-edits ⇒ `test_palette.py` +
    `test_panel_css_contrast.py` ImportError at collection. AC-1/AC-2 replay. AC-11 file-enumerated ledger
    (Cat-A removed + KEPT; Cat-B module DELETED + 3 importers EDITED). NO `specs/backlog`.

- **W6 — FR7 e2e extension (button smoke) + gates + ship.**
  1. **Extend** `tests/e2e/panel/` with the restyled-button smoke assertion (computed `border-radius`/padding
     non-default). **(The FR3 width spec is authored in W3, not here — Q2/Option A.)** Artifacts →
     `.dadaia/tmp/product-engineer/<date>/` via `PLAYWRIGHT_OUTPUT_DIR`/`PLAYWRIGHT_REPORT_DIR`.
  2. **Full local gates (AC-10, Q7):** unpiped `pytest -p no:cacheprovider` + `ruff format --check` + `ruff check
     --no-cache` + `mypy --strict` + `lint-imports --no-cache` (8 kept / 0 broken; ignore-cap UNCHANGED — the
     AGENTS_CSS refactor removes an import, adds none) + `dadaia specs doctor` + `dadaia backlog doctor` + the
     **full GH-only Playwright panel suite** (response-guard + theme + tab-nav + workflows + sessions + axe + the
     W3 width checks). **(Q7) Repo-hygiene:** `git status --short` shows no `.pytest_cache/`, no repo-local
     `.dadaia/`, no `playwright-report/`, no `test-results/`.
  3. **Self-hosting reconcile (AC-12):** confirm `git diff -- dadaia_workspace/public/` is EMPTY (panel is
     package code, not a projected asset) and `dadaia public doctor` reports `[ok] public-privacy`; if any
     `public/**` file changed, run `stage → public doctor → install --target all → confirming doctor`. Instance
     files never hand-edited.
  4. **Live-panel + screenshots (server-registration law, ADR-H):** run a live panel, `dadaia server register`,
     capture operator screenshots (3 themes; controls; 1024/1440px) → `.dadaia/tmp/product-engineer/<date>/`.
  5. QA ship-gate APPROVE; security push-gate keyed to the pushed sha; push; **watch CI until every job green**
     (incl. the `e2e-panel` job); PR; merge. *(PE runs no shell — surfaces the npm/Playwright + git + server-
     register commands to PM/operator or requests devops-engineer.)*

- **W7 — closure (CLOSURE phase).** `ACTIVE.md` phase = `CLOSURE`; CLOSURE.md (Summary, Tasks + SHAs,
  Validations triples incl. e2e + screenshot paths, Drifts, Memory updates, Dispositions, Backlog returns,
  Archive). MEMORY (§SPEC 8): `panel.md` (primary — visual/layout overhaul as current truth; fix the
  three→five memory-chip drift S6); `brand-identity.md` (assess — token rationalization; palette unchanged);
  `architecture.md` / `quality-assurance.md` / `tech-stack.md` (assess). Regen `catalog.json` + `index.md` only
  if `tldr`/`summary`/`area` change (keep `tldr` within the length cap). `release_origin` → v0.1.59 on each
  edited atom. **Dispositions**: archive `panel-ux-overhaul` → `specs/_archive/v0.1.59/consumed-backlog/` +
  `consumed_backlog.json` (`DELIVERED — v0.1.59`; anchor survives → CLOSURE archival, no SHIP-time archival).
  No backlog return required (all residual scope consumed). `dadaia specs doctor` clean; request `git mv
  specs/releases/v0.1.59 → specs/_archive/releases/` (devops/operator); set `ACTIVE.md` → next release
  (`v0.1.60` / R12 Capability tail) or `release: none`; mark candidates R11 row **SHIPPED — v0.1.59**.

## Write sets (disjoint per wave; shared files force sequential order)

Paths are FULL to disambiguate `views/sessions.py` (SSR view) from `views/assets/css/sessions.py` (CSS module)
(A6).

| Wave | Files |
|---|---|
| W1 | NEW `tests/unit/features/panel/test_index_dom_contract.py` (fakes with ≥1 SpecContextProject, A3); `dadaia_workspace/features/panel/views/assets/css/tokens.py` (design-system rationalization); `tests/unit/features/panel/test_security_headers.py` (Q4 CSP equality lock added) |
| W2 | `views/assets/css/structure.py` (nav-tab/theme-btn control styling); `views/assets/css/tokens.py` (runtime-btn — shared with W1, sequential); `views/assets/css/workflows.py` + `views/assets/css/workflow_policy.py` (pickers); `views/assets/css/reports.py` + `views/assets/css/academy.py` (CTAs/trash); NEW `tests/unit/features/panel/test_control_tokens.py` (Q3 allowlist token-anchor grep) |
| W3 | `views/sessions.py` (de-inline runtime-switcher row) + `views/index.py` (de-inline topbar-right + theme-switcher — shared with W4, sequential); `views/assets/css/structure.py` + `views/assets/css/sessions.py` (single-line CSS — shared with W2/W5, sequential); **NEW FR3 width e2e spec in `tests/e2e/panel/` authored HERE (Q2/Option A), captured RED against the pre-fix tree** |
| W4 | `views/index.py` (layout/IA — shared with W3, sequential); `views/sessions.py` + `views/academy.py` + `views/reports.py` + `views/workflows.py` (section-scaffold density — marker strings PRESERVED, A4); `views/assets/css/*` (grouping/density — sequential per shared file) |
| W5 | `views/assets/css/structure.py` (theme-switcher polish + Category-A dead-CSS purge — shared, sequential); **Category-B refactor (A1/Q1): DELETE `views/assets/css/agents.py` + co-edit `views/assets/__init__.py` + `tests/unit/features/panel/test_palette.py` + `tests/unit/features/panel/test_panel_css_contrast.py`**; grep-proof artifacts |
| W6 | `tests/e2e/panel/*.spec.ts` (button-styling smoke — the width spec is W3, not here); gates + `public doctor` verify; live panel + screenshots; no `specs/**` change |
| W7 | `specs/releases/v0.1.59/CLOSURE.md` + `specs/memory/**` + `specs/_archive/v0.1.59/consumed-backlog/` + `ACTIVE.md` |

**`views/assets/css/structure.py` shared W2 (controls) + W3 (single-line CSS) + W5 (theme polish + Cat-A purge)**
— sequential; disjoint symbols, one file. **`views/assets/css/tokens.py` shared W1 (design system) + W2
(runtime-btn)** — sequential. **`views/index.py` shared W3 (de-inline) + W4 (layout/IA)** — sequential.
**`views/sessions.py` W3 + W4** — sequential. **`views/assets/css/sessions.py` W3 + W4** — sequential. **The 3
AGENTS_CSS importers (`views/assets/__init__.py`, `test_palette.py`, `test_panel_css_contrast.py`) are W5-only
co-edits** (A1). **No parallel `[-]`.**

## Test strategy

- **Golden-first / lock-first (FR1, the spine).** The api-golden `api_golden_v0155.json` is a ZERO-DIFF
  INVARIANT declared W1 and replayed byte-identical every wave (Ruling C — never `UPDATE_API_GOLDEN`). The NEW
  `test_index_dom_contract.py` is captured W1 BEFORE the SSR-HTML restyle as the index-HTML behavior lock (a
  contract test, not a byte-golden — it survives an intentional restyle).
- **CSP inline-script invariant + zero-touch equality lock (the highest-risk trap, Q4).**
  `TestInlineScriptCspCoverage` (`len==2` + recompute) and `test_html_csp_value` stay green every wave; PLUS the
  NEW W1 **equality lock** freezing `_CSP_SCRIPT_HASH_1/2` to hardcoded W1 baseline values (catches
  edit-WITH-recompute, which `TestInlineScriptCspCoverage` alone passes). `_CSP_SCRIPT_HASH_1/2` unchanged (two
  pre-paint scripts byte-identical, Ruling B). AC-9(b) sabotages the recompute-miss; AC-9(b′) sabotages the
  edit-with-recompute against the equality lock. The default path touches no inline script.
- **DOM-contract lock (Q5 — never re-baselined).** `test_index_dom_contract.py` is a presence-invariant with
  fakes carrying ≥1 SpecContextProject (A3); it CONSOLIDATES `test_views_index.py` (A4), which SURVIVES; it is
  NEVER re-baselined this release — any asserted-selector change is a STOP-and-rescope declared per-wave.
- **Token-anchored controls, grep-falsifiable (FR2, Q3).** `test_control_tokens.py` iterates an explicit selector
  allowlist, extracts each rule body (EXCLUDING `tokens.py`), and fails on hex/px-font-size/px-radius literals.
  AC-9(c) sabotages it.
- **RED-first width e2e authored in W3 (FR3, Q2/Option A).** The control-row bounding-box check on all 3 themes
  is authored co-located with the fix and captured to FAIL against the pre-fix wrapping tree at the
  empirically-pinned wrap width (AC-4), passes post-fix. AC-9(d) restores the wrap — runnable in W3.
- **Two-category dead-CSS purge (FR6, A1/A2/Q1).** Category A (dead rules in a served string) — grep served HTML
  + JS + tests. Category B (`agents.py#AGENTS_CSS` module symbol) — Python-import-aware `grep -rn AGENTS_CSS
  dadaia_workspace/ tests/ == 0` after 3 co-edits; AC-9(f) proves an uncoordinated delete ImportErrors at
  collection.
- **Preserve + extend the GH-only Playwright suite (FR7).** response-guard (E2E-GUARD-01/02: no 4xx/5xx, no
  console error), theme-switcher (E2E-THM-01..10 incl. axe per theme), tab-navigation, workflows, sessions —
  all SURVIVE with selectors preserved; the new width spec EXTENDS. Run the **full suite locally** before ship
  (e2e-panel is GH-only, not in `ci preflight`); artifacts → `.dadaia/tmp/product-engineer/<date>/`.
- **AC-9 mutation-sanity per new/changed test** (a DOM-contract, b CSP-hash-recompute-miss, b′ CSP
  edit-with-recompute equality lock, c token-anchor, d row-wrap [runnable in W3], e Cat-A live-selector-delete,
  f Cat-B AGENTS_CSS uncoordinated-delete ImportError): one-line sabotage ⇒ FAIL, captured on the task line,
  reverted.
- **AC-11 surviving/dead ledger per wave — FILE-ENUMERATED (A4/Q6 completeness)**; greps include `tests/` + JS
  template strings + docstrings **+ Python imports for a module-symbol removal**. Named fates: INVARIANT (never
  regenerated) — `test_api_golden.py`/`api_golden_v0155.json`, `test_index_dom_contract.py`; SURVIVE unchanged —
  `test_security_headers.py` (+ NEW equality lock), `test_views_index.py` (markers preserved),
  the 11 `*.spec.ts`, `test_theme_switcher.py`, `test_theme_palettes.py`, `test_runtime_switcher_pi.py`,
  `test_static.py`, `test_views_static.py`, `test_svg_validity.py`; EDITED (A1) — `views/assets/__init__.py`,
  `test_palette.py`, `test_panel_css_contrast.py` (AGENTS_CSS concat dropped; WCAG/token behavior preserved —
  the prior false SURVIVE claim for `test_panel_css_contrast.py` removed).
- **Frozen suite:** the v0.1.50 no-steal lease/gate suite is untouched (this release never enters
  `spec_context`/lease/gate) — confirm zero-diff.
- **Repo hygiene (Q7).** Full **unpiped** `pytest -p no:cacheprovider` (no `.pytest_cache/` materialized) + ruff
  + `mypy --strict` + `lint-imports --no-cache` (8 kept / 0 broken; ignore-cap unchanged — no import edge; the
  AGENTS_CSS refactor removes an import) + `specs doctor` + `backlog doctor` + the **full Playwright panel
  suite** locally before push (AC-10); a `git status --short` check shows no `.pytest_cache/`, repo-local
  `.dadaia/`, `playwright-report/`, or `test-results/`.

## Platform seam note (3-OS CI)

The panel is stdlib-only Python + CSS-in-Python strings + browser JS/CSS. No new filesystem/path work is
introduced. The unit tests (DOM-contract, CSP-coverage, token-anchor grep) render in-memory over fixed fakes —
OS-agnostic. The Playwright e2e runs on `ubuntu-latest` (GH-only) with artifacts redirected out of the repo via
`PLAYWRIGHT_OUTPUT_DIR`/`PLAYWRIGHT_REPORT_DIR`. No goldens carry host paths (the api-golden already normalizes
`<WS>`); no new golden with paths is added.

## Rollback

Single feature branch `feature/v0.1.59` (base v0.1.58 closure). Every wave is CSS/SSR-HTML only, behind the
committed api-golden ZERO-DIFF invariant + the DOM-contract lock (revert = restore the prior CSS/HTML strings).
FR1 is additive (new lock test + token rationalization + CSP equality lock). FR2–FR5 are re-skins (revert
restores the prior control/section CSS). FR6 Category A is a rule deletion (revert restores the dead CSS —
harmless); FR6 Category B is a coordinated module refactor (revert restores `agents.py` + the 3 importer
co-edits together). FR7 is test-only. No data
migration, no dependency, no API change, no projected-asset change (package code only — no `public install`
needed unless a `public/**` diff appears). The CLOSURE dispositions are recoverable by reverting the closure
commit.
