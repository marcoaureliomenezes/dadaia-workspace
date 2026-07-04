# SPEC — v0.1.59 — Panel UX Overhaul

**Status:** Aprovado
**Branch:** `feature/v0.1.59` (base: v0.1.58 closure — the orchestrator branches after `Aprovado`)
**Origin:** R11 of the operator-approved 12-release plan; **third** release of the operator's R9→R12
continuation mandate (2026-07-04). A visual/layout redesign on the stabilized post-v0.1.52 panel.
**Consumes:** backlog `panel-ux-overhaul` (FEAT-PANEL-UX-200; 2 intents — `render_index` layout/IA + theme
switcher; `TOKENS_CSS` design system). Sole R11 pick.
**Bug debt at pick:** none (ledger 0).

> **PLUGIN-SCOPE DEVIATION (operator 2026-07-02 — recorded prominently).** Browser HTML/CSS/JS + UX
> redesign is normally the `frontend-engineer` / `design-specialist` plugin domain (`frontend-design` pack).
> **No `dadaia plugin install` command exists yet** (tracked by backlog `plugin-packs-and-install-command`,
> R12), so the plugin agents cannot be enabled. The operator **authorized core agents** (`software-engineer`
> for implementation; `product-engineer` for definition/memory) to do this work directly under a recorded
> deviation. The deviation **dissolves** if `plugin-packs-and-install-command` ships first (it has not). All
> panel work is library-source edits under `dadaia_workspace/features/panel/`, projected/validated on the
> live instance.

**Definition-time inspection** (product-engineer code read, 2026-07-04) — every claim below is a read fact
from the current post-v0.1.58 source, not a restatement of the backlog dossier (several dossier claims are
stale; corrected in §9). **Release-definition grill** (mandatory, from-backlog) run on the picked set before
this SPEC — `.dadaia/reports/dadaia-workspace/product-engineer/2026-07-04T170000Z-refine-specs-v0159.html`.
**Dual definition review 2026-07-04 (software-architect REJECT A1–A6 + qa-engineer REJECT Q1–Q7 — folded):** all
amendments are folded into this Draft with grep-able `(A#)`/`(Q#)` reconciliation markers. Two PM binding
rulings resolve the decision points (§9 PM Binding Rulings: Ruling 1 = A1/Q1 AGENTS_CSS COORDINATED REFACTOR;
Ruling 2 = Q2 width-e2e Option A / author-in-W3). QA + architect re-verify before `Aprovado`.

## 1. Problem

The operator's standing verdict on the working panel (2026-06-27, post-v0.1.30, folded into
`panel-ux-overhaul`): **functionality is OK but the visual style is bad — "crap", "trash", "looks like a
2005 website".** Named complaints: **ugly, unstyled buttons**; **header/control rows that wrap onto two or
more lines**; **poor layout organization** (weak grouping/hierarchy); overall dated and incohesive. This is a
**UX/visual overhaul of existing, working surfaces** — keep behavior, re-skin and re-organize.

**Read facts (source, post-v0.1.58):**

1. **A full token system already exists** — `views/assets/css/tokens.py#TOKENS_CSS` carries a semantic set
   (typography scale `--text-2xs..xl`, spacing, radius incl. `--radius-lg`, shadows incl. `--shadow-card-rest`/
   `--shadow-card-hover`/`--lift-hover`, motion, 3 palettes mint/sage/warm, runtime tokens). The problem is
   not the absence of tokens; it is **inconsistent, low-craft application** and residual dated styling.
2. **Inline `style=` hacks + a wrapping shared row.** `views/sessions.py:36` renders `.section-header` with a
   `.runtime-switcher` positioned by an inline `style="margin-left:auto;"`; `views/index.py:82-83` uses inline
   `style="margin-left:auto;display:flex;…"` on the topbar-right. These are CSP-legal (`style-src 'self'
   'unsafe-inline'`) but low-craft; the shared `.section-header` + control-row pattern is where rows wrap on
   narrow widths.
3. **Dead / orphan CSS from removed features.** `views/assets/css/structure.py` still ships CSS for surfaces
   deleted in v0.1.45/v0.1.52: `.ops-subsection*` (Agentic/Ops tab), `.card-header`/`.card-primary-badge`/
   `.card-links`/`.memory-link*`/`.context-card.primary`/`.context-count` (the OLD card anatomy — the live
   card uses `.card-zone-a/b/c/d` + `.memory-chip` from `projects.css`), `.agents-grid--compact` (agents grid
   gone). **(A1/Q1 CORRECTION — the AGENTS_CSS false-orphan, PM Binding Ruling 1)**
   `views/assets/css/agents.py#AGENTS_CSS` is dead as **served CSS** (absent from `static._ASSETS`, not linked
   by `index.py`) **BUT it is a live Python symbol with THREE importers** verified on disk:
   `views/assets/__init__.py:8` (`from ...css.agents import AGENTS_CSS`, re-exported in `__all__` line 16);
   `tests/unit/features/panel/test_palette.py:7,13` (`PANEL_CSS = TOKENS_CSS + STRUCTURE_CSS + AGENTS_CSS +
   WORKFLOWS_CSS + SESSIONS_CSS`); `tests/unit/features/panel/test_panel_css_contrast.py:17,23` (same import +
   concat). Deleting the module raises `ImportError` at panel-package/pytest-collection time — so its removal
   is a **coordinated Category-B module refactor with co-edits** (FR6), NOT a served-CSS-only purge. Dead CSS
   (served rules + the unserved module) is part of the incoherence.
4. **The visual layer never touches API behavior.** The overhaul lives entirely in SSR HTML (`views/index.py`
   + the section-scaffold views `sessions.py`/`academy.py`/`reports.py`/`workflows.py`) and the CSS-in-Python
   modules under `views/assets/css/`. **No `render_api_*` response is touched.**
5. **The behavior locks that gate this release are already in place:** the `api_golden_v0155.json`
   byte-invariant (JSON API bodies only — NOT the index HTML/CSS), the CSP inline-script coverage test
   (exactly two pre-paint scripts), the GH-only Playwright suite `tests/e2e/panel/` (response-guard 4xx/5xx +
   console-error gate; theme-switcher; tab-navigation; workflows; sessions-dashboard; axe-core per theme).

## 2. Goals

1. A **cohesive, modern design system** applied uniformly from `TOKENS_CSS` (typography scale, spacing
   rhythm, restrained brand-palette color, elevation/radius) so the panel reads as one designed product —
   under **golden-first** discipline (the api-golden byte-invariant declared ZERO-DIFF; a NEW structural
   DOM-contract lock captured before the SSR-HTML restyle).
2. **Properly styled buttons/controls** — every interactive control (nav tabs, theme button, runtime buttons,
   workflow per-step pickers, report/CTA buttons) styled uniformly from tokens; **no ad-hoc hex/px/font-size
   literals** in the restyled control rules (grep-falsifiable).
3. **Single-line header/control rows** — the shared `.section-header` + `.runtime-switcher` pattern lays out
   responsively on one line by default with deliberate truncation/overflow at 1024px and 1440px; the inline
   `style=` hacks are moved into token-anchored CSS.
4. **Layout/IA hierarchy + density** — restructured section grouping, alignment, and density across the live
   tabs so the panel reads as designed, not stacked fragments — **without changing the 6-tab nav set**
   (Ruling A).
5. **A polished theme switcher** — refine the switcher button/popover from tokens (a polish, not a functional
   fix — it already applies + persists; §9 S1), preserving every `theme-switcher.spec.ts` selector,
   `localStorage`, FOUC pre-paint, Escape-close, and axe cleanliness.
6. **A grep-gated dead-CSS purge** — remove CSS orphaned by removed features, each removal proven by a grep of
   the served HTML + all JS (Ruling F), with the full e2e suite as backstop.
7. **A preserved, extended e2e acceptance bar** — the GH-only Playwright suite stays green (response-guard +
   axe per theme), extended with deep-interaction restyle assertions (single-line rows; button styling
   present); the ship wave runs the **full panel suite locally** + a **live registered panel** + operator
   screenshots (e2e-panel is GH-only; ADR-H / server-registration law).

## 3. Functional requirements

### FR1 — Design-system foundation (golden-first) + structural DOM-contract lock

- **Golden discipline (behaviour lock).** The `api_golden_v0155.json` byte-invariant
  (`tests/unit/features/panel/test_api_golden.py`) is declared a **ZERO-DIFF INVARIANT** for this entire
  release: it captures only `render_api_*` `(status, content_type, body)` — NOT the index HTML or any CSS.
  Every wave replays it byte-identical; **a byte diff is adjudicated as a behavior regression and fixed at the
  source — NEVER regenerated with `UPDATE_API_GOLDEN`** (Ruling C).
- **NEW structural DOM-contract lock (the real index-HTML behavior lock).** Because the golden does not cover
  the index page, add a NEW test `tests/unit/features/panel/test_index_dom_contract.py` that renders the real
  index (via `render_index` over fixed fakes) and asserts the presence of the **e2e selector contract**
  (§9 stale-proof list): the 6 tab ids `#tab-{memories,workflows,sessions,reports,academy,servers}` +
  `data-section`; the 6 `#section-*` panels; `.nav-tab`; `.memory-chip`; the theme switcher (`#theme-btn` with
  `aria-haspopup="menu"`, `#theme-menu`, three `[data-theme-value="mint|sage|warm"]`, `.theme-swatch-dot`);
  the runtime switcher (`.runtime-switcher`, `.runtime-btn`, `[data-runtime-value]`); and the
  workflows/sessions mounts rendered in-index.
- **(A3 — fixture must render the data-dependent selectors.)** `.memory-chip`/`.context-card`/`.card-zone-*`/
  `.card-name` are emitted ONLY by `_render_context_card`, run once per context. The fixed fakes MUST therefore
  include **≥1 `SpecContextProject`** (and ≥1 server row) — model them on `test_views_index._make_context` /
  `_build_service`, **NOT** the empty `test_security_headers._render_index_html` fake (whose
  `_FakeSpecContext.list_all()` returns `[]`, rendering zero cards → `.memory-chip` would never render and the
  lock would silently drop the assertion). Reuse only the **render mechanics** of `_render_index_html`, never
  its empty fixture. The unconditional selectors (6 tabs/sections, `.nav-tab`, theme + runtime switchers)
  render with any fake; only the card selectors need the populated context.
- **(A4/Q6 — CONSOLIDATES, does not replace, the existing index locks.)** The index HTML is ALREADY partially
  locked by `test_views_index.py` (6 tab ids + labels + active default; 6 tabpanels; all 6 sections keyed on
  the marker strings `sessions-dashboard`/`reports-list`/`academy-content`; the 5 memory chips + card zones;
  every `/static/*.{css,js}` link). `test_index_dom_contract.py` **CONSOLIDATES** those into one e2e-selector
  presence invariant — it does NOT replace `test_views_index.py`, which SURVIVES unchanged (AC-11).
- Captured BEFORE the SSR-HTML restyle begins (W1) so a dropped selector fails loudly. It is a **contract test
  (presence-invariant), not a byte-golden** — it survives an intentional restyle.
- **(Q5 — never re-baselined.)** The DOM-contract lock is **NEVER re-baselined in v0.1.59** (symmetric with
  Ruling C for the api-golden). Any wave that must change one of the asserted selectors is a **STOP-and-rescope**,
  declared on that wave's AC-11 ledger line — never a silent regen. By design FR2–FR6 rename none of the
  asserted selectors, so the lock should never move.
- **Design-system pass on `tokens.py`.** Consolidate/rationalize `TOKENS_CSS` into a coherent system:
  a clear typographic scale, spacing rhythm, restrained brand-palette color usage, and elevation/radius tokens
  — **additive/rationalizing only** (no palette hex change; brand-identity 5-color palette + 3 themes
  preserved; WCAG AA/AAA contrast preserved). New tokens are token-named (no ad-hoc literals leak into the
  restyled rules).
- **No new dependency** (Ruling D). No JS lib, no CSS framework. Stdlib + hand-authored CSS.
- **Anchor note.** The backlog intents' subject anchors `views/index.py#render_index` and
  `tokens.py#TOKENS_CSS` **survive** (restyled in place) → archival at CLOSURE.

### FR2 — Controls / buttons restyle from tokens

- Restyle every interactive control uniformly from `TOKENS_CSS`: nav tabs (`.nav-tab`), the theme button
  (`.theme-btn`) + popover rows, the runtime buttons (`.runtime-btn`), the workflows per-step model pickers
  (`.wfp-picker`/`.wfp-profile-select` styling in `workflow-policy.css`/`workflows.css`), report + academy
  CTAs and the report delete/trash button — proper padding rhythm, radius, hover/active/focus-visible states,
  and a consistent button visual language.
- **Token-anchored, grep-falsifiable (the v0.1.45 discipline, extended).** The restyled control rules consume
  `var(--…)` from `tokens.py` with **no ad-hoc hex / px / rem-font-size / radius literals**.
- **(Q3 — the grep mechanism is concrete, not prose.)** `test_control_tokens.py` delimits the "restyled control
  blocks" by an **explicit selector allowlist** (grounded in the `test_palette.py` PANEL_CSS-grep pattern, so it
  is a real extension, not a new unproven harness): it iterates the allowlist `{.nav-tab, .theme-btn,
  .runtime-btn, .wfp-picker, .wfp-profile-select, and the report/academy CTA + report trash-button selectors}`,
  extracts each matching rule body from the served stylesheet strings, and FAILS on any ad-hoc literal via the
  reject regexes: hex `#[0-9a-fA-F]{3,8}`, a `font-size:` value carrying a `px`/`rem` literal, and a
  `border-radius:` value carrying a `px` literal. **Token-DEFINITION files are EXCLUDED** — the scan runs over
  the control rule bodies in `structure.py`/`workflows.py`/`workflow_policy.py`/`reports.py`/`academy.py`, NOT
  over `tokens.py` (where `--color-accent: #9cddc8` etc. legitimately DEFINE the tokens). Every allowed rule
  body must contain `var(--…)` and zero rejected literals.
- **CSP-clean (Ruling B).** No control restyle adds or edits an inline `<script>`; the two pre-paint inline
  scripts stay **byte-identical** so `_CSP_SCRIPT_HASH_1/2` need **no recompute**. Inline `style=` attributes
  removed in FR3 are replaced by CSS classes (style-src keeps `'unsafe-inline'`; no CSP change).

### FR3 — Single-line header / control-row layout

- Fix the shared `.section-header` + `.runtime-switcher` pattern so the control row lays out **responsively on
  one line by default** with deliberate truncation/overflow (`min-width:0` + `text-overflow: ellipsis` /
  `flex-wrap` guards), at **1024px and 1440px** (the panel's `--main` cap is 1024px, centered) — the operator's
  "rows breaking onto two or more lines" complaint.
- **De-inline the hacks — THREE inline styles (A5).** Move all three inline `style=` attributes into
  token-anchored CSS classes: (1) `views/index.py:82` topbar-right
  `style="margin-left:auto;display:flex;align-items:center;gap:0.5rem;"`; (2) `views/index.py:83`
  `.theme-switcher style="position:relative;"`; (3) `views/sessions.py:36` `.runtime-switcher
  style="margin-left:auto;"` (`structure.css`/`sessions.css`). The SSR-HTML edit is CSP-clean (no script change)
  and preserves the runtime-switcher + theme-switcher DOM contracts (Q5 selectors).
- **Falsifiable — authored RED-first in W3 (Q2/PM Ruling 2, Option A).** The width e2e spec is authored **in W3
  co-located with the fix** (NOT deferred to W6): it measures the shared `.section-header`/`.runtime-switcher`
  control row's bounding box and fails if it wraps (height exceeds a single-row threshold), on all three themes,
  and is captured **RED against the pre-fix wrapping tree BEFORE the de-inline+single-line CSS lands**, then
  GREEN after. **The RED width is empirically pinned:** the topbar-right row is full-viewport-width while the
  Sessions `.runtime-switcher` row is inside the `--main` 1024px-capped centered column, so the width that
  forces the pre-fix wrap must be **verified against the pre-fix tree** — test at 1024px and 1440px, and **if
  neither forces the wrap, pin the width that does and document it on the AC-4/T-59-30 line** (never assert a
  RED that is not genuinely red).

### FR4 — Layout / IA hierarchy + density

- Restructure section grouping, alignment, and density across the live tabs (Projects / Workflows / Sessions /
  Reports / Academy / Servers): consistent `.section-header` hierarchy, card density/spacing rhythm, and
  visual grouping so the panel reads as one designed product.
- **The 6-tab nav set is unchanged (Ruling A).** "Consolidation / IA" here means visual density + grouping
  WITHIN tabs, NOT nav reduction — the 6 tabs are pinned by memory (`panel.md`) and the e2e tour
  (`response-guard.spec.ts` visits all six). No tab is added or removed.
- **No behavior change.** Card/section markup edits stay SSR-HTML + CSS; no `render_api_*` change (Ruling C);
  the DOM-contract lock (FR1) stays green.
- **(A4 — preserve the marker strings `test_views_index.py` keys on.)** The FR4 density/grouping restructure of
  the section-scaffold views (`sessions.py`/`academy.py`/`reports.py`/`workflows.py`) + `index.py` MUST NOT
  rename the container marker strings `sessions-dashboard` / `reports-list` / `academy-content` (asserted by
  `test_views_index.py::test_index_renders_panel_sections`) — or, if a rename is genuinely required, it is a
  STOP-and-rescope (Q5) that EDITs `test_views_index.py` in the SAME wave and records it on the W4 ledger line.
  Default: markers preserved, `test_views_index.py` SURVIVES unchanged.

### FR5 — Theme-switcher polish

- Refine the theme switcher button + popover visual (spacing, radius, elevation, active-row treatment) from
  tokens. This is a **polish, not a functional fix** — the switcher already applies + persists cleanly
  (localStorage + FOUC pre-paint + Escape-close; §9 S1).
- **Preserve every `theme-switcher.spec.ts` contract:** `#theme-btn` (`aria-haspopup="menu"`, inside
  `.topbar`), `#theme-menu` (`role="menu"`, `[hidden]` toggle), three `[role="menuitemradio"]` with labels
  Mint/Sage/Warm + `[data-theme-value]` + `.theme-swatch-dot`, `localStorage["dadaia-panel-theme"]`,
  `data-theme` on `<html>`, Escape closes + returns focus to `#theme-btn`, `--color-accent-dark` warm
  focus-ring token, and **axe-core zero critical/serious** on all 3 themes (color-contrast excluded per the
  suite). The two inline pre-paint scripts stay byte-identical (Ruling B).

### FR6 — Grep-gated dead-CSS purge (two categories — A2)

The purge has **two structurally distinct categories** with **distinct grep-gates** (A2 — a single served-HTML+JS
gate is safe for one but NOT the other):

- **Category A — dead CSS *rules* inside a served stylesheet string.** In `structure.py#STRUCTURE_CSS`:
  `.ops-subsection*`, `.card-header`, `.card-primary-badge`, `.card-links`, `.memory-link*`,
  `.context-card.primary`, `.context-count`, `.agents-grid--compact`, `.workflows-grid--compact` (verify vs
  `workflows.py` first). Removing these edits the string BODY; the `STRUCTURE_CSS` symbol stays; **no Python
  import breaks.** **Gate (Category A):** remove a selector ONLY when a grep proves **zero live references**
  across served HTML (all `views/*.py` render output) + all JS (`views/assets/js/*.js`) + JS template strings +
  `tests/`. Ambiguous (e.g. referenced in a JS template string) ⇒ **KEEP** with a recorded reason.
- **Category B — a whole CSS-in-Python *module symbol*: `agents.py#AGENTS_CSS` (A1/Q1, PM Binding Ruling 1 —
  COORDINATED REFACTOR, not KEEP).** AGENTS_CSS is dead as SERVED CSS but is a **live Python symbol with 3
  importers**. This is a Python-refactor, NOT a CSS-rule edit, so the served-HTML+JS gate is **insufficient** —
  the gate is **Python-import-aware**: `grep -rn AGENTS_CSS dadaia_workspace/ tests/` must return **ZERO after
  the co-edits**. The refactor deletes `agents.py` AND, in the SAME wave, applies the 3 co-edits:
  1. `views/assets/__init__.py` — remove the `from ...css.agents import AGENTS_CSS` import + its `__all__` entry.
  2. `tests/unit/features/panel/test_palette.py` — drop `+ AGENTS_CSS` from the `PANEL_CSS` concatenation
     (import removed).
  3. `tests/unit/features/panel/test_panel_css_contrast.py` — same (drop `+ AGENTS_CSS`; import removed).
  These 3 files are reclassified **EDITED** in AC-11 (the false SURVIVE-unchanged claim for
  `test_panel_css_contrast.py` is removed; its WCAG + token behaviour is preserved because AGENTS_CSS carries no
  live rule the WCAG assertions depend on — verified: it is unserved). Rationale (PM Ruling 1): keeping dead
  served-CSS concatenated into `PANEL_CSS` contradicts the release's own purge purpose; the co-edit is 3 small
  mechanical changes.
- **Backstop:** the full e2e suite (FR7) + full unpiped pytest are green after the purge — a removed live
  selector surfaces as a broken tour/console error; a missed Python importer surfaces as an ImportError at
  collection.

### FR7 — E2E extension + evidence bar (ADR-H)

- **Preserve** the GH-only Playwright suite `tests/e2e/panel/` green: response-guard (E2E-GUARD-01/02 — no
  4xx/5xx, no console error on the full 6-tab tour + memory-chip click); theme-switcher (E2E-THM-01..10);
  tab-navigation; workflows-tab; sessions-dashboard; axe-core per theme (E2E-THM-09).
- **Extend** with deep-interaction restyle assertions: (a) the shared header/control row does NOT wrap at the
  wrap-triggering width(s) on all 3 themes (FR3 bounding-box check) — **this spec is authored in W3 co-located
  with the fix (Q2/Option A), captured RED against the pre-fix wrapping tree first**, NOT deferred to W6; (b)
  the restyled buttons carry the token-driven styling (computed `border-radius`/padding non-default; a smoke
  assertion the controls are visibly styled, not browser-default) — added in W6. Artifacts (`outputDir`/
  `reporter`) redirect via `PLAYWRIGHT_OUTPUT_DIR`/`PLAYWRIGHT_REPORT_DIR` →
  `.dadaia/tmp/product-engineer/<YYYYMMDD>/` — never the repo tree.
- **Local run mechanism (Q3).** `cd tests/e2e && npm ci && npx playwright install --with-deps chromium &&
  PLAYWRIGHT_OUTPUT_DIR=… PLAYWRIGHT_REPORT_DIR=… npm run test:e2e`, driving the panel via
  `PANEL_WEB_SERVER_COMMAND` (+ `PANEL_TEST_PORT`). The e2e-panel job is **GH-only** (not in `ci preflight`) —
  run the full suite locally before declaring done.
- **Live-panel + screenshots evidence (server-registration law, ADR-H).** The ship wave runs a **live panel**
  registered via `dadaia server register` and captures **operator-facing screenshots** (all 3 themes; the
  restyled controls; a 1024px and 1440px width to prove no row-wrap) to
  `.dadaia/tmp/product-engineer/<YYYYMMDD>/` for PR-review sign-off.

## 4. Non-goals

- **No API / behavior change (Ruling C).** No `render_api_*` edit; `api_golden_v0155.json` stays byte-identical.
- **No nav-set change (Ruling A).** The 6-tab nav is preserved; no tab added/removed/renamed.
- **No inline-script change (Ruling B).** The two pre-paint scripts stay byte-identical; `_CSP_SCRIPT_HASH_*`
  is a zero-touch invariant. No new inline script (all real scripts stay external `/static/*.js`).
- **No new dependency (Ruling D).** No JS lib / CSS framework; hand-authored tokens + CSS.
- **No palette re-theme (Ruling E).** Brand-identity 5-color palette + the 3 themes (mint/sage/warm) are
  preserved; no new colors beyond brand tokens; WCAG AA/AAA preserved.
- **No telemetry / SQLite change (Ruling G).** Zero new DB access; the read-only factory is untouched.
- **No memory write during implementation.** Memory (`panel.md` primary, `brand-identity.md`) is updated only
  in the CLOSURE phase (constitution §13).
- **No lease/gate/spec_context change.** This release lives entirely in `features/panel/**` + its tests +
  the panel e2e. The v0.1.50 frozen no-steal lease/gate suite is expected **zero-diff** (§6).

## 5. Acceptance criteria

- **AC-1 (golden zero-diff + DOM-contract lock — RED-safe):** `api_golden_v0155.json` replays **byte-identical**
  in every wave (`test_api_routes_are_byte_identical_to_golden` green; `UPDATE_API_GOLDEN` never used). The NEW
  `test_index_dom_contract.py` (captured in W1 BEFORE the SSR-HTML restyle) asserts the full §3-FR1 selector
  contract on the rendered index and stays green through every wave. **(A3)** its fakes include **≥1
  `SpecContextProject`** (+ ≥1 server row) so `.memory-chip`/`.context-card`/`.card-zone-*`/`.card-name`
  actually render — the empty `_render_index_html` fake would silently drop those assertions. **(A4)** it
  CONSOLIDATES (does not replace) `test_views_index.py`, which SURVIVES. **(Q5)** it is **never re-baselined**;
  any asserted-selector change is a STOP-and-rescope declared on that wave's ledger line. A byte diff in the
  api-golden is adjudicated as a regression (Ruling C), never regenerated.
- **AC-2 (CSP inline-script invariant + equality lock — RED-safe):**
  `test_security_headers.py::TestInlineScriptCspCoverage` stays green — the rendered index carries **exactly
  two** inline scripts and each recomputed `base64(sha256)` is covered by `script-src`. `test_html_csp_value`
  (`style-src 'self' 'unsafe-inline'`, no `unsafe-inline` in `script-src`) stays green. **(Q4 — explicit
  zero-touch equality lock, NEW in W1):** an assertion freezes `_CSP_SCRIPT_HASH_1` and `_CSP_SCRIPT_HASH_2`
  (`handler.py:111,116`) to their **hardcoded W1 baseline values** (or byte-freezes the two extracted inline
  `<script>` bodies against a small captured baseline). This catches an **edit-WITH-recompute** — the actual
  zero-touch violation `TestInlineScriptCspCoverage` (which passes when both script and hash change together)
  does NOT catch. The two pre-paint scripts stay byte-identical; both hashes stay at their W1 values.
- **AC-3 (controls restyle is token-anchored — grep-falsifiable, Q3):** `test_control_tokens.py` iterates the
  **explicit selector allowlist** `{.nav-tab, .theme-btn, .runtime-btn, .wfp-picker, .wfp-profile-select,
  report/academy CTA + report trash-button selectors}`, extracts each rule body from the served stylesheet
  strings (EXCLUDING token-definition files like `tokens.py`), and FAILS on any ad-hoc literal via the reject
  regexes (hex `#[0-9a-fA-F]{3,8}`; `font-size:` with a px/rem literal; `border-radius:` with a px literal);
  every allowed rule body contains `var(--…)`. Buttons carry uniform hover/active/focus-visible states.
- **AC-4 (single-line header/control row — RED-first, Q2/A5):** the width e2e (authored **in W3** co-located
  with the fix, Option A) asserts the shared `.section-header`/`.runtime-switcher` control row does NOT wrap
  (single-row height) at the **empirically-pinned wrap-triggering width(s)** on all 3 themes. **RED-first:
  captured to FAIL against the pre-fix wrapping tree in W3 BEFORE the fix lands** (topbar-right is
  full-viewport-width; the Sessions row is inside the `--main` 1024px cap — so the RED width is verified against
  the pre-fix tree: test 1024px and 1440px, and if neither wraps, pin + document the width that does). **(A5)**
  `grep 'style=' index.py sessions.py` returns **ZERO** after FR3 — all three inline styles gone (topbar-right,
  theme-switcher `position:relative`, runtime-switcher `margin-left:auto`), each replaced by a token-anchored
  CSS class.
- **AC-5 (layout/IA hierarchy — nav-set preserved):** the 6-tab nav set is unchanged (DOM-contract lock AC-1
  proves all 6 tabs/sections present); the restructured section/card density renders with no row-wrap/overflow
  at 1024/1440px (FR7) and no `render_api_*` change (AC-1).
- **AC-6 (theme-switcher polish preserves contract):** the full `theme-switcher.spec.ts` (E2E-THM-01..10)
  stays green — button visible in topbar, 3 options, apply/persist/reload, FOUC, Escape-close-with-focus,
  warm focus-ring token, **axe-core zero critical/serious on all 3 themes** (color-contrast excluded).
- **AC-7 (dead-CSS purge is grep-proven, two categories — A1/A2/Q1):** **Category A** (dead rules in
  `STRUCTURE_CSS`) — each removed selector has a committed grep proving **zero live references** in served HTML
  + all JS + JS template strings + `tests/`; ambiguous ⇒ KEPT with a recorded reason. **Category B**
  (`agents.py#AGENTS_CSS`, PM Ruling 1 coordinated refactor) — the module is deleted WITH its 3 co-edits
  (`views/assets/__init__.py` import+`__all__`; `test_palette.py` + `test_panel_css_contrast.py` `PANEL_CSS`
  concat), gated by `grep -rn AGENTS_CSS dadaia_workspace/ tests/` returning **ZERO after the co-edits** (a
  served-HTML+JS grep alone is insufficient — it cannot see a Python import). The full e2e suite **and the full
  unpiped pytest** are green after the purge (backstop — an ImportError would red-bar collection).
- **AC-8 (e2e suite green + extended + evidence):** the full GH-only Playwright suite passes locally
  (response-guard + theme + tab-nav + workflows + sessions + axe), including the NEW FR3 width assertions;
  artifacts land under `.dadaia/tmp/product-engineer/<YYYYMMDD>/` (never the repo tree). A **live panel**
  registered via `dadaia server register` + operator screenshots (3 themes; controls; 1024/1440px) are
  captured to `.dadaia/tmp/product-engineer/<YYYYMMDD>/` for PR sign-off.
- **AC-9 (mutation-sanity per new/changed test — sabotage → FAIL → revert):** (a) drop a §3-FR1 selector from
  `index.py` (e.g. remove a `[data-theme-value]`) ⇒ `test_index_dom_contract.py` FAILS; (b) edit one inline
  pre-paint script without recomputing its hash ⇒ `TestInlineScriptCspCoverage` FAILS; **(b′/Q4)** edit one
  inline pre-paint script AND recompute its hash (the edit-with-recompute zero-touch violation) ⇒ the AC-2
  equality lock (frozen `_CSP_SCRIPT_HASH_*` values) FAILS; (c) reintroduce an ad-hoc hex literal into a
  restyled control rule ⇒ AC-3 `test_control_tokens.py` FAILS; **(d/Q2 — runnable in W3)** restore the inline
  `margin-left:auto` wrapping row (re-inline) ⇒ the W3-co-located FR3 width e2e FAILS (row wraps at the pinned
  width) — the e2e EXISTS in W3, so this sabotage is runnable where declared; **(e)** delete a Category-A
  selector the purge KEPT-as-live (still-referenced) ⇒ the full e2e response-guard FAILS (broken tour/console
  error); **(f/A1)** delete `agents.py#AGENTS_CSS` WITHOUT the 3 co-edits ⇒ `test_palette.py` +
  `test_panel_css_contrast.py` FAIL at collection (ImportError). Each captured on its task line, then reverted.
- **AC-10 (full gates, Q7 hygiene):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, the
  full **unpiped** `pytest -p no:cacheprovider` (real exit; the `-p no:cacheprovider` is mandatory so the two
  NEW unit tests do not materialize `.pytest_cache/` in the repo tree — repo-cleanliness law), `lint-imports
  --no-cache` (`8 kept, 0 broken`; **ignore-cap UNCHANGED** — the panel restyle adds no import edge; the
  AGENTS_CSS refactor removes an import, never adds one), `dadaia specs doctor` (exit 0), `dadaia backlog
  doctor` (exit 0), and the **full GH-only Playwright panel suite** (AC-8). **(Q7) Repo-hygiene check:** `git
  status --short` shows **no `.pytest_cache/`, no repo-local `.dadaia/`, no `playwright-report/`, no
  `test-results/`** before ship (Playwright artifacts redirected to `.dadaia/tmp/…` via
  `PLAYWRIGHT_OUTPUT_DIR`/`PLAYWRIGHT_REPORT_DIR`). The ship wave runs `dadaia public stage` → `dadaia public
  doctor` (`[ok] public-privacy`) → `dadaia public install --target all` → confirming `dadaia public doctor`
  **only if a `public/**` asset actually changed** (the panel is package code, not a projected asset — verify
  no `public/**` diff; if none, no re-projection is needed but confirm `public doctor` is clean). Public assets
  stay GENERIC (public-privacy law).
- **AC-11 (surviving/dead behavior ledger, per wave — file-enumerated, A4/Q6):** each wave records a ledger on
  its task line naming **concrete files + fates** (not a generic description); every move/rename/purge grep
  includes `tests/` **and** non-import textual references (JS template strings, docstrings) **and, for a
  CSS-in-Python module symbol, Python `import` statements** (A1/A2). **No** implementation-wave commit stages
  any `specs/backlog/**` (the anchor is dispositioned at CLOSURE). Named fates:
  - **INVARIANT (never regenerated):** `test_api_golden.py` + `api_golden_v0155.json` (SURVIVE byte-identical);
    `test_index_dom_contract.py` (never re-baselined, Q5).
  - **SURVIVE unchanged:** `test_security_headers.py` (CSP hashes unchanged — plus the NEW W1 equality lock);
    `test_views_index.py` (selectors + marker strings preserved — the NEW lock CONSOLIDATES it, A4); the 11
    `tests/e2e/panel/*.spec.ts` (SURVIVE/EXTEND, selectors preserved); `test_theme_switcher.py`,
    `test_theme_palettes.py`, `test_runtime_switcher_pi.py`, `test_static.py`, `test_views_static.py`,
    `test_svg_validity.py` (HTML/CSS/asset structure the restyle does not perturb — SURVIVE).
  - **EDITED (A1/Q1 — AGENTS_CSS Category-B co-edits):** `views/assets/__init__.py` (drop import + `__all__`
    entry), `tests/unit/features/panel/test_palette.py` (drop `+ AGENTS_CSS` from `PANEL_CSS`),
    `tests/unit/features/panel/test_panel_css_contrast.py` (drop `+ AGENTS_CSS`; **the prior false SURVIVE
    claim is REMOVED** — behavior/WCAG preserved because AGENTS_CSS carries no served rule the WCAG assertions
    depend on).
- **AC-12 (self-hosting drift reconciled):** because this release changes **package code** under
  `dadaia_workspace/features/panel/` (not a `public/**` asset), the live instance needs **no re-projection** —
  confirm `git diff -- dadaia_workspace/public/` is empty and `dadaia public doctor` reports `[ok]`; if any
  `public/**` file did change, run `stage` → `public doctor` → `install --target all` → confirming doctor and
  re-verify `[ok] public-privacy`. Instance files are never hand-edited. The v0.1.50 frozen no-steal suite is
  zero-diff.

## 6. Consumed backlog

| Item | Kind | Priority | Consumed → FR | Anchor fate |
|---|---|---|---|---|
| `panel-ux-overhaul` (FEAT-PANEL-UX-200) | backlog (candidate) | MEDIUM | design-system foundation + DOM-contract lock → FR1; controls/buttons restyle → FR2; single-line header/control row → FR3; layout/IA hierarchy → FR4; theme-switcher polish → FR5; dead-CSS purge → FR6; e2e extension + evidence → FR7 | Intent anchors `views/index.py#render_index` (survives, restyled) + `tokens.py#TOKENS_CSS` (survives, rationalized) → **CLOSURE** |

**Archival timing.** The consumed anchor SURVIVES (restyled in place) → dispositioned + archived at CLOSURE
(`DELIVERED — v0.1.59`). No dead anchor this release → no SHIP-time archival. Discipline: **no
`specs/backlog/**` staged in W1–W7** (AC-11).

**Frozen-suite check — NO interaction.** The v0.1.50 no-steal lease/gate suite
(`tests/unit/features/spec_context/test_lease_*`, `test_gate_policy.py`) is untouched: this release lives in
`features/panel/**` + its unit/e2e tests. Expect **zero** frozen-file diff.

## 7. Risks

- **CSP inline-script hash trap (FR2/FR5, the highest-risk mechanical trap).** Any edit to an inline pre-paint
  script silently CSP-blocks it in the browser unless `_CSP_SCRIPT_HASH_*` is recomputed. Mitigation: Ruling B
  keeps the two scripts **byte-identical** (zero recompute); the falsifiable `TestInlineScriptCspCoverage`
  (`len==2` + recompute) is the backstop; AC-9(b) sabotages it.
- **Silent API-golden regression (FR1/FR4).** A restyle that inadvertently perturbs a section view feeding an
  `api_*` response would break the byte-invariant — the temptation is to regenerate. Mitigation: Ruling C
  forbids regeneration; the golden is declared INVARIANT; the restyle is confined to SSR-HTML + CSS with no
  `render_api_*` edit; AC-1 replays byte-identical every wave.
- **Dropped e2e selector (FR2/FR4/FR6).** A restyle or purge that drops a class/id the Playwright suite keys
  on breaks the GH-only suite (which is not in `ci preflight`, so it can slip locally). Mitigation: the NEW
  DOM-contract lock (FR1) fails in unit CI on a dropped selector; the full local suite run is mandatory before
  ship (ADR-H); FR6 purge is grep-gated with the e2e as backstop.
- **Row-wrap fix asserted subjectively (FR3).** "Looks better" is not falsifiable. Mitigation: FR7 measures
  the control-row bounding box at 1024/1440px on all 3 themes; AC-4 is RED-first (fails against the pre-fix
  wrapping row).
- **Dead-CSS purge removes a live selector / breaks the build (FR6 — A1/A2, the review's CRITICAL finding).**
  Two failure modes: (Category A) a rule referenced only in a JS template string mis-classified dead; (Category
  B) a CSS-in-Python module symbol (`agents.py#AGENTS_CSS`) that *looks* orphan on the served surface but has 3
  live Python importers — deleting it is an ImportError at pytest collection that breaks
  `test_panel_css_contrast.py` (a named survivor). Mitigation: the two-category split-gate (FR6) — Category A
  greps served HTML + JS + JS template strings + tests; Category B is a coordinated refactor gated by `grep -rn
  AGENTS_CSS dadaia_workspace/ tests/ == 0` after the 3 co-edits; ambiguous Category-A ⇒ KEEP; full e2e + full
  unpiped pytest backstop; AC-9(e)/(f) sabotage both modes.
- **Plugin-scope deviation drift.** Doing frontend work with core agents risks scope creep. Mitigation: the
  deviation is recorded in the header; scope is strictly re-skin + re-organize (no behavior); operator signs
  off visual direction at PR (ADR-E) with screenshots.

## 8. Memory files affected at CLOSURE

- `specs/memory/product/panel/panel.md` — **primary edit.** The v0.1.59 visual/layout overhaul: cohesive
  token-driven design system, uniformly styled controls, single-line header/control rows (inline `style=`
  hacks removed), layout/IA density pass, theme-switcher polish, dead-CSS purge. Memory describes the product
  **as it is now** (no changelog). Fix the drift found in the grill: the memory card renders **five** memory
  chips (Constitution, Architecture, Tech Stack, Quality, Product), not three (§9 S6). Confirm the 6-tab nav +
  the strict-CSP + read-only-telemetry statements remain accurate. `release_origin` → v0.1.59; assess
  `tldr`/`summary` (regen `catalog.json` + `index.md` only if they change, keeping `tldr` within the length
  cap).
- `specs/memory/product/panel/brand-identity.md` — **assess/edit.** If FR1 rationalizes the token system
  (typography scale / spacing / elevation), note the tokens' current shape (palette hex unchanged — the
  5-color canon is preserved). `release_origin` → v0.1.59 only if edited.
- `specs/memory/architecture.md` — **assess.** The panel module map is unchanged structurally (no new module;
  `agents.py` orphan removed if purged); likely no edit or a one-line note. Confirm.
- `specs/memory/quality-assurance.md` — **assess.** If the DOM-contract structural lock + the token-anchor
  grep discipline + the FR3 width-e2e pattern warrant a QA note, add it. Confirm.
- `specs/memory/tech-stack.md` — **assess.** No dependency change (Ruling D); likely a no-change-confirm.

## 9. Definition rulings (grill, operator-unavailable — OPERATOR-OVERRIDABLE)

The operator is unavailable mid-flow; code-unanswerable decisions (esp. visual direction) are pre-ruled here
with rationale and marked overridable at PR review with screenshots. Full evidence: the grill report cited in
the header.

- **Ruling A — the 6-tab nav set is preserved.** "Tab consolidation / IA" means visual density + grouping
  WITHIN tabs, not nav reduction (the 6 tabs are pinned by memory + the e2e tour). **Override:** operator
  requests a nav change (re-baselines the e2e).
- **Ruling B — the two inline pre-paint scripts stay byte-identical; `_CSP_SCRIPT_HASH_*` is a zero-touch
  invariant.** All real scripts stay external `/static/*.js`; no new inline script. **Override:** a redesign
  genuinely needing an inline script recomputes the hash + bumps the `==2` assert (checklisted in TASKS).
- **Ruling C — zero API changes; `api_golden_v0155.json` is a ZERO-DIFF INVARIANT.** A byte diff is adjudicated
  as a regression, never regenerated. **Override:** if an API change is discovered necessary, STOP and
  re-scope (not a silent regen).
- **Ruling D — no new dependency.** Hand-authored tokens + CSS; no JS lib / CSS framework. **Override:**
  operator approves a dep in a follow-up (needs security review — a new JS lib is flagged loudly).
- **Ruling E — conservative cohesive modernization.** Keep the 3 palettes + brand-identity 5-color palette;
  improve type scale, spacing rhythm, elevation, radius, button styling; no wholesale re-theme, no new colors
  beyond brand tokens; WCAG AA/AAA preserved. **Override:** operator redirects palette/typography at PR (with
  screenshots).
- **Ruling F — dead-CSS purge is grep-gated, TWO categories (amended per A1/A2 + PM Binding Ruling 1).**
  Category A (dead rules in a served stylesheet string): remove a selector only when grep proves zero live
  references in served HTML + all JS + JS template strings + tests; ambiguous ⇒ KEEP with a reason. Category B
  (a whole CSS-in-Python module symbol, e.g. `agents.py#AGENTS_CSS`): the served-HTML+JS gate is insufficient —
  a Python-import-aware gate (`grep -rn <SYMBOL> dadaia_workspace/ tests/ == 0` after co-edits) applies, and
  the removal is a coordinated refactor editing every importer in the same wave. Full e2e + full unpiped pytest
  backstop. **Override:** operator widens/narrows the purge set.
- **Ruling G — telemetry + read-only SQLite factory untouched.** Zero new DB access; the v0.1.52 corruption
  fix is preserved by construction. **Override:** none reasonable.
- **Ruling H — evidence bar = local full Playwright suite + live registered panel + operator screenshots**
  (e2e-panel is GH-only). Artifacts → `.dadaia/tmp/product-engineer/<YYYYMMDD>/`. The plugin-scope deviation
  stands (dissolves only if `plugin-packs-and-install-command` ships first — it has not). **Override:** operator
  adjusts the evidence bar.

### PM Binding Rulings (dual definition review 2026-07-04 — both halves REJECTED; operator-overridable)

The architect (A1–A6) and QA (Q1–Q7) reviews both REJECTED the first Draft; all amendments are folded above
with greppable `(A#)`/`(Q#)` markers. Two PM binding rulings resolve the decision points:

- **PM Binding Ruling 1 — A1/Q1 AGENTS_CSS: COORDINATED REFACTOR, not KEEP (CRITICAL on both halves).**
  `agents.py#AGENTS_CSS` is dead as served CSS but has 3 live Python importers. It is NOT dropped from the purge
  under Ruling F's "ambiguous ⇒ KEEP"; instead it becomes a **Category-B module deletion WITH co-edits**
  (`views/assets/__init__.py` import+`__all__`; `test_palette.py` + `test_panel_css_contrast.py` `PANEL_CSS`
  concat), gated by `grep -rn AGENTS_CSS dadaia_workspace/ tests/ == 0` after the co-edits; those 3 files are
  reclassified **EDITED** in AC-11 (the false SURVIVE claim removed). Rationale: keeping dead served-CSS
  concatenated into `PANEL_CSS` contradicts the release's own purge purpose; the co-edit is 3 small mechanical
  changes. Folded at FR6, AC-7, AC-9(f), AC-11, Ruling F. **Override:** operator prefers minimal churn → KEEP
  `agents.py` under Ruling F and drop it from the purge set entirely (do NOT half-delete).
- **PM Binding Ruling 2 — Q2 width-e2e RED-first: OPTION A (author in W3).** The FR3 width spec is authored **in
  W3 co-located with the fix**; genuine RED captured at the wrap-triggering width(s) × 3 themes against the
  pre-fix tree BEFORE the fix lands; sabotage AC-9(d) becomes runnable in W3. **Verify (and state in AC-4) that
  the narrow viewport actually forces the wrap** given `--main` caps at 1024px — if 1024/1440px do not wrap,
  the RED anchor pins the real wrap-triggering width and documents it. Folded at FR3, FR7, AC-4, AC-9(d), and
  the wave map. **Override:** operator elects Option B (retroactive scratch-revert RED in W6).

- **Stale-claim corrections (dossier / briefing vs source).** (S1) the backlog "theme-switcher applies +
  persists cleanly" framing is stale — it already does (full `theme-switcher.spec.ts` green); FR5 is polish.
  (S2) the "runtime switcher + meta + filters/cost banner across Sessions/Agents/Workflows" shared-row claim is
  stale — no Agents tab (deleted v0.1.45), no Sessions filter toolbar/cost banner (deleted v0.1.52); the live
  pattern is `.section-header` + `.runtime-switcher`. (S3) "tab consolidation" was DELIVERED by v0.1.45
  (self-flagged in the entry); residual is visual density (Ruling A). (S4) the briefing's `PANEL_TEST_REGISTRY`
  is stale — the Playwright env is `PANEL_WEB_SERVER_COMMAND` (+ `PANEL_TEST_PORT`). (S5) the "24-route api
  golden" is `api_golden_v0155.json` — 8 domains + error paths, JSON bodies only, NOT index HTML/CSS →
  zero-diff for a pure-frontend overhaul (Ruling C). (S6) memory `panel.md` says "three memory pill chips" —
  `_render_context_card` now renders five; fixed at CLOSURE. (S7) `helpers.ts` token model is stale-but-harmless
  (no-auth; empty token, inert query param) — out of scope.
