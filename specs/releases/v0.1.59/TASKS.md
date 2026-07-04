# TASKS — v0.1.59 — Panel UX Overhaul

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files use FULL paths (A6 — disambiguate
`views/sessions.py` from `views/assets/css/sessions.py`): `views/assets/css/structure.py` (W2+W3+W5),
`views/assets/css/tokens.py` (W1+W2), `views/index.py` (W3+W4), `views/sessions.py` (W3+W4),
`views/assets/css/sessions.py` (W3+W4) are sequential — one owner, no parallel `[-]`. The 3 AGENTS_CSS
importers (`views/assets/__init__.py`, `test_palette.py`, `test_panel_css_contrast.py`) are W5-only co-edits
(A1). Every implementation-wave task: **NO `specs/backlog/**` paths staged** (the surviving anchor is
dispositioned at CLOSURE — T-59-70). Every purge/rename grep **includes `tests/` AND non-import textual
references** (JS template strings, docstrings) **+ Python `import` for a module-symbol removal** (A1/A2).
AC-9 mutation-sanity: each new/changed test is sabotaged → shown to FAIL → reverted, captured on the task line.
**FR1 lands FIRST** — the DOM-contract lock + api-golden zero-diff baseline + CSP equality lock are the behavior
locks FR2–FR7 build on. This release is **pure SSR-HTML + CSS**: no `render_api_*` edit (Ruling C), no
inline-script edit (Ruling B), no new dependency (Ruling D).

## W0 — definition

- [ ] T-59-01 SPEC/PLAN/TASKS authored from the 2026-07-04 **code read** (not a dossier restatement): a full
  token system already exists in `tokens.py`; the `api_golden_v0155.json` byte-invariant captures ONLY
  `render_api_*` JSON bodies (NOT index HTML/CSS) ⇒ a pure-frontend overhaul is zero-diff by construction; the
  CSP covers exactly two inline pre-paint scripts (`_CSP_SCRIPT_HASH_1/2`) guarded by
  `TestInlineScriptCspCoverage`'s `len==2` assert; the GH-only Playwright suite `tests/e2e/panel/` (11 specs) is
  the acceptance bar with a hard selector contract; `index.py`/`sessions.py` carry THREE inline `style=` hacks;
  `structure.py` carries DEAD served CSS from removed features; `agents.py#AGENTS_CSS` is dead as SERVED CSS but
  has 3 live Python importers (`views/assets/__init__.py` + `test_palette.py` + `test_panel_css_contrast.py`) →
  a Category-B coordinated refactor, not a served-CSS-only purge; the panel is package code (no `public/**`
  projection). Mandatory release-definition grill on the picked set (report:
  `.dadaia/reports/dadaia-workspace/product-engineer/2026-07-04T170000Z-refine-specs-v0159.html`). **Rulings
  recorded (§9, operator unavailable — overridable at PR with screenshots):** A 6-tab nav preserved; B inline
  scripts byte-identical (CSP zero-touch); C zero API change (golden INVARIANT); D no new dep; E conservative
  cohesive modernization (palette unchanged); F two-category grep-gated dead-CSS purge; G telemetry/SQLite
  untouched; H local-suite + live-registered-panel + screenshots evidence bar. Plugin-scope deviation recorded
  in the SPEC header. **Dual definition review 2026-07-04 (software-architect REJECT A1–A6 + qa-engineer REJECT
  Q1–Q7) — all amendments folded into SPEC/PLAN/TASKS with `(A#)`/`(Q#)` markers; PM Binding Ruling 1 (A1/Q1
  AGENTS_CSS coordinated refactor with 3 co-edits) + Ruling 2 (Q2 width-e2e authored in W3, Option A) recorded
  in §9.** `Aprovado` after the confirming dual re-review; definition commit. Owner: product-engineer
  (orchestrated).

## W1 — FR1 design-system foundation + DOM-contract lock (golden-first)

- [x] T-59-10 Capture the DOM-contract lock + confirm the api-golden zero-diff baseline BEFORE any restyle.
  Checklist:
  - **NEW `tests/unit/features/panel/test_index_dom_contract.py`** — render the real index (`render_index` over
    fixed fakes) and assert the §3-FR1 selector contract: the 6 tab ids
    `#tab-{memories,workflows,sessions,reports,academy,servers}` + each `data-section`; the 6 `#section-*`
    panels; `.nav-tab`; `.memory-chip`; the theme switcher (`#theme-btn` with `aria-haspopup="menu"` inside
    `.topbar`, `#theme-menu` `role="menu"`, three `[data-theme-value="mint|sage|warm"]`, `.theme-swatch-dot`);
    the runtime switcher (`.runtime-switcher`, `.runtime-btn`, `[data-runtime-value]`).
  - **(A3 — fixture MUST render the data-dependent selectors.)** The fixed fakes MUST include **≥1
    `SpecContextProject`** (+ ≥1 server row), modelled on `test_views_index._make_context` / `_build_service` —
    **NOT** the empty `test_security_headers._render_index_html` fake (whose `_FakeSpecContext.list_all()`
    returns `[]`, rendering zero context cards, so `.memory-chip`/`.context-card`/`.card-zone-*`/`.card-name`
    would NEVER render and the lock would silently drop those assertions). Reuse only the RENDER MECHANICS of
    `_render_index_html`, never its empty fixture.
  - **(A4 — CONSOLIDATES `test_views_index.py`, does not replace it.)** The index HTML is already partially
    locked by `test_views_index.py` (tabs/tabpanels/6 sections keyed on `sessions-dashboard`/`reports-list`/
    `academy-content`/5 chips + card zones/static links); the NEW lock CONSOLIDATES those into one
    e2e-selector presence invariant. `test_views_index.py` SURVIVES unchanged.
  - **(Q5 — never re-baselined.)** This is a presence-invariant contract test (survives an intentional restyle),
    NOT a byte-golden, and is **NEVER re-baselined in v0.1.59** (symmetric with Ruling C). Any wave that must
    change an asserted selector is a STOP-and-rescope declared on that wave's AC-11 ledger line. Commit BEFORE
    the SSR-HTML restyle — the AC-1 index-HTML behavior lock.
  - **Confirm the api-golden zero-diff baseline** — run `test_api_golden.py` green on the pre-restyle tree;
    declare `api_golden_v0155.json` a ZERO-DIFF INVARIANT (Ruling C — `UPDATE_API_GOLDEN` is NEVER used this
    release; a byte diff is adjudicated as a behavior regression).
  - **(Q4 — CSP zero-touch equality lock, NEW.)** Add to `test_security_headers.py` an assertion freezing
    `_CSP_SCRIPT_HASH_1` and `_CSP_SCRIPT_HASH_2` (`handler.py:111,116`) to their **hardcoded W1 baseline values**
    (or byte-freeze the two extracted inline `<script>` bodies against a captured baseline). This catches the
    **edit-WITH-recompute** violation that `TestInlineScriptCspCoverage` (which passes when script + hash change
    together) does NOT catch.
  - **Design-system pass on `tokens.py`** — rationalize `TOKENS_CSS` into a coherent system (typographic scale,
    spacing rhythm, restrained brand-palette color usage, elevation/radius). **Additive/rationalizing only:** no
    palette hex change (brand-identity 5-color + 3 themes preserved), WCAG AA/AAA preserved, new tokens
    token-named. Do NOT touch the two inline pre-paint scripts (Ruling B).
  - **Tests — AC-1** `test_index_dom_contract.py` green (populated fakes) + `test_api_golden.py` byte-identical;
    **AC-2** `TestInlineScriptCspCoverage` + `test_html_csp_value` + the NEW equality lock green (no index-script
    edit; CSP hashes unchanged).
  - **AC-9(a) sabotage:** remove one §3-FR1 selector from `index.py` (e.g. drop a `[data-theme-value]`) ⇒
    `test_index_dom_contract.py` FAILS → revert. **(b′/Q4) sabotage:** edit one inline pre-paint script AND
    recompute its hash ⇒ the equality lock FAILS (proving edit-with-recompute is caught) → revert. Capture each
    command + failing test on this line.
  - **existing-test fate ledger (file-enumerated, A4/Q6):** INVARIANT never regenerated —
    `tests/unit/features/panel/test_api_golden.py` + `_golden/api_golden_v0155.json`; `test_index_dom_contract.py`
    (never re-baselined). SURVIVE unchanged — `test_security_headers.py` (CSP hashes unchanged + NEW equality
    lock), `test_views_index.py` (CONSOLIDATED, selectors + markers preserved), `test_panel_css_contrast.py`
    (WCAG preserved — **its AGENTS_CSS EDIT is scheduled in W5**, not here), `test_theme_switcher.py`,
    `test_theme_palettes.py`, `test_runtime_switcher_pi.py`, `test_static.py`, `test_views_static.py`,
    `test_svg_validity.py`.
  - **AC-11 ledger** — NEW: `test_index_dom_contract.py`; EDITED: `tokens.py` (design-system rationalization,
    palette unchanged), `test_security_headers.py` (equality lock added). Gates: ruff + mypy --strict +
    lint-imports 8/0 (no import edge) + full unpiped `pytest -p no:cacheprovider`. No `specs/backlog/**` staged.
  - **W1 EVIDENCE (T-59-10 DONE 2026-07-04, software-engineer).**
    - **AC-9(a)** DOM-contract sabotage: `sed -i 's/data-theme-value="sage"/data-theme-value="SABOTAGED"/'
      views/index.py` ⇒ `test_index_dom_contract.py::test_three_theme_values_present[sage]` FAILED
      (`AssertionError: missing data-theme-value=sage`) ⇒ reverted (`git checkout`).
    - **AC-9(b′)** edit-with-recompute sabotage: appended `void 0;` to the theme pre-paint script body in
      `views/index.py` AND recomputed `_CSP_SCRIPT_HASH_1` in `handler.py`
      (`'sha256-p92XWe7yPRUpQcNZtXGiFCrBKEC7zQLtDidh/RL8Jmo='`) ⇒
      `test_security_headers.py::TestCspHashEqualityLock::test_csp_script_hashes_frozen_to_w1_baseline`
      FAILED (constant off baseline) while `TestInlineScriptCspCoverage` PASSED (script+hash moved together —
      the exact gap the equality lock closes) ⇒ reverted (`git checkout` both files).
    - **Fate ledger verified:** `test_views_index.py` SURVIVES unchanged (new lock CONSOLIDATES it, A4);
      `test_api_golden.py` + `api_golden_v0155.json` INVARIANT byte-identical (`UPDATE_API_GOLDEN` never used);
      AGENTS_CSS importers untouched (6 refs intact — W5 co-edits). `test_panel_css_contrast.py` GREEN (WCAG
      AA/AAA preserved: 0 palette-hex changes; tokens.py tail byte-identical; 14 additive token-named tokens).
    - **Gates:** `ruff format --check` clean · `ruff check --no-cache` passed · `mypy --strict` 309 files clean ·
      `lint-imports --no-cache` 8 kept/0 broken · full unpiped `pytest -p no:cacheprovider` 4593 passed / 17
      skipped. `git status --short`: no `.pytest_cache/`, no repo-local `.dadaia/`, no `playwright-report/`,
      no `test-results/` (Q7).

## W2 — FR2 controls / buttons restyle from tokens

- [ ] T-59-20 Restyle all interactive controls uniformly from `TOKENS_CSS`. Checklist:
  - **Restyle controls** — nav tabs (`.nav-tab` in `structure.css`), theme button (`.theme-btn` + popover rows
    in `structure.css`), runtime buttons (`.runtime-btn` in `tokens.py` — sequential after W1), workflows
    per-step pickers (`.wfp-picker`/`.wfp-profile-select` in `workflows.css`/`workflow_policy.css`), report +
    academy CTAs and the report delete/trash button (`reports.css`/`academy.css`): consistent padding rhythm,
    radius, hover/active/focus-visible states, one button visual language.
  - **NEW `tests/unit/features/panel/test_control_tokens.py` (Q3 — concrete delimiter + regexes).** Delimit the
    "restyled control blocks" by an **explicit selector allowlist** `{.nav-tab, .theme-btn, .runtime-btn,
    .wfp-picker, .wfp-profile-select, report/academy CTA + report trash-button selectors}` (grounded in the
    `test_palette.py` PANEL_CSS-grep pattern — a real extension, not a new harness): extract each matching rule
    body from the served stylesheet strings (`structure.py`/`workflows.py`/`workflow_policy.py`/`reports.py`/
    `academy.py`), **EXCLUDE token-definition files (`tokens.py`)**, assert every allowed body contains
    `var(--…)`, and FAIL on the reject regexes: hex `#[0-9a-fA-F]{3,8}`, a `font-size:` value with a `px`/`rem`
    literal, a `border-radius:` value with a `px` literal.
  - **CSP-clean (Ruling B):** no control restyle edits an inline `<script>`; the two pre-paint scripts stay
    byte-identical (`_CSP_SCRIPT_HASH_1/2` unchanged). Inline `style=` removal is deferred to FR3.
  - **Tests — AC-3** `test_control_tokens.py` green + control-state coverage. **AC-1/AC-2 replay** (api-golden
    byte-identical + DOM-contract + CSP unchanged).
  - **AC-9(c) sabotage:** reintroduce an ad-hoc hex literal (e.g. `#9cddc8`) into a restyled control rule ⇒
    `test_control_tokens.py` FAILS → revert. Capture the command + failing test.
  - **existing-test fate ledger:** SURVIVE — `tests/e2e/panel/*.spec.ts` (selectors preserved — restyle, not
    re-structure); `test_panel_css_contrast.py` (WCAG preserved). AC-11 ledger — EDITED: the control-styling
    CSS modules. No `specs/backlog/**` staged.

## W3 — FR3 single-line header / control-row layout (width e2e authored HERE — Q2/Option A)

- [ ] T-59-30 De-inline THREE inline styles + responsive single-line row + RED-first width e2e. Checklist:
  - **De-inline THREE inline styles (A5)** — move all three into token-anchored CSS classes: (1)
    `views/index.py:82` topbar-right `style="margin-left:auto;display:flex;align-items:center;gap:0.5rem;"`; (2)
    `views/index.py:83` `.theme-switcher style="position:relative;"`; (3) `views/sessions.py:36`
    `.runtime-switcher style="margin-left:auto;"` → `views/assets/css/structure.py` / `views/assets/css/sessions.py`.
    CSP-clean (no script change); preserve the `.runtime-switcher` + `.theme-switcher` DOM contract (Q5 selectors
    intact).
  - **Responsive single-line CSS** — `.section-header` + `.runtime-switcher` lay out on one line by default with
    `min-width:0` + ellipsis/flex-guard overflow.
  - **Grep-proof (A5):** `grep 'style=' index.py sessions.py` returns **ZERO** (all three inline styles gone) —
    record the grep on this line.
  - **(Q2/Option A) Author the FR3 width e2e HERE, RED-first.** Add the Playwright bounding-box width spec to
    `tests/e2e/panel/` **co-located with the fix**: it measures the shared `.section-header`/`.runtime-switcher`
    control row's height and fails if it wraps, on all 3 themes. **Capture it RED against the pre-fix wrapping
    tree BEFORE the de-inline+single-line CSS lands** (record the failing output), then GREEN after.
    **Empirically pin the wrap width:** topbar-right is full-viewport-width, the Sessions row is inside the
    `--main` 1024px cap — run at 1024px AND 1440px; **if neither forces the pre-fix wrap, pin + document the
    width that does** on this line (never assert a non-red RED).
  - **AC-9(d) sabotage — RUNNABLE IN W3:** restore the inline `margin-left:auto` wrapping row (re-inline) ⇒ the
    W3-co-located width e2e FAILS (row wraps at the pinned width) → revert. Capture the command + failing test.
  - **AC-1/AC-2 replay.** AC-11 ledger — EDITED: `views/sessions.py`, `views/index.py` (de-inline 3 styles),
    `views/assets/css/structure.py` / `views/assets/css/sessions.py` (single-line rule); NEW:
    `tests/e2e/panel/<width>.spec.ts`. No `specs/backlog/**` staged.

## W4 — FR4 layout / IA hierarchy + density

- [ ] T-59-40 Restructure section/card grouping, alignment, density across the live tabs. Checklist:
  - **Layout/IA pass** — consistent `.section-header` hierarchy, card density/spacing rhythm, and visual
    grouping across Projects / Workflows / Sessions / Reports / Academy / Servers (SSR-HTML in `index.py` +
    section-scaffold views `sessions.py`/`academy.py`/`reports.py`/`workflows.py` + their CSS). SSR-HTML + CSS
    only; no `render_api_*` edit.
  - **6-tab nav unchanged (Ruling A)** — no tab added/removed/renamed; the DOM-contract lock (AC-1) proves all 6
    tabs/sections present.
  - **(A4 — preserve the marker strings.)** Do NOT rename the container marker strings `sessions-dashboard` /
    `reports-list` / `academy-content` that `test_views_index.py::test_index_renders_panel_sections` keys on. If
    a rename is genuinely required it is a STOP-and-rescope (Q5) that EDITs `test_views_index.py` in THIS wave
    and records it on the ledger line; default = markers preserved, `test_views_index.py` SURVIVES unchanged.
  - **Tests — AC-5:** `test_index_dom_contract.py` green (all 6 tabs/sections); `test_views_index.py` green
    (markers preserved); the W3 width e2e shows no row-wrap at the pinned width; `test_api_golden.py`
    byte-identical (no API change).
  - **AC-1/AC-2 replay.** AC-11 ledger — EDITED: `views/index.py` (layout/IA, sequential after W3), the section
    scaffold views (`views/sessions.py`/`views/academy.py`/`views/reports.py`/`views/workflows.py`) + their CSS;
    SURVIVE unchanged: `test_views_index.py` (markers preserved). No `specs/backlog/**` staged.

## W5 — FR5 theme-switcher polish + FR6 two-category dead-CSS purge

- [ ] T-59-50 Theme-switcher polish + two-category dead-CSS purge (Cat-A rules + Cat-B AGENTS_CSS refactor).
  Checklist:
  - **FR5 polish** — refine the `.theme-btn` + `#theme-menu` popover from tokens (spacing, radius, elevation,
    active-row treatment). **Preserve every `theme-switcher.spec.ts` contract:** `#theme-btn`
    (`aria-haspopup="menu"`, in `.topbar`), `#theme-menu` (`role="menu"`, `[hidden]`), three
    `[role="menuitemradio"]` labelled Mint/Sage/Warm + `[data-theme-value]` + `.theme-swatch-dot`,
    `localStorage["dadaia-panel-theme"]`, `data-theme` on `<html>`, Escape closes + focus returns to
    `#theme-btn`, the `--color-accent-dark` warm focus-ring token. Two inline pre-paint scripts byte-identical
    (Ruling B).
  - **FR6 Category A — dead CSS RULES in `structure.py#STRUCTURE_CSS`** — remove `.ops-subsection*`,
    `.card-header`, `.card-primary-badge`, `.card-links`, `.memory-link*`, `.context-card.primary`,
    `.context-count`, `.agents-grid--compact`, `.workflows-grid--compact` (verify vs `workflows.py` first).
    **For EACH: grep served HTML (all `views/*.py` render output) + all `views/assets/js/*.js` + JS template
    strings + `tests/`** and remove ONLY on zero live references; ambiguous ⇒ **KEEP + record why**. Removing
    these edits the STRUCTURE_CSS string body — no Python import breaks.
  - **FR6 Category B — `agents.py#AGENTS_CSS` COORDINATED REFACTOR (A1/Q1, PM Binding Ruling 1 — NOT a
    served-CSS-only purge).** AGENTS_CSS is dead as served CSS but has 3 live Python importers. DELETE
    `views/assets/css/agents.py` **AND, in this SAME wave, apply the 3 co-edits:**
    1. `views/assets/__init__.py` — remove `from ...css.agents import AGENTS_CSS` (line 8) + its `__all__` entry
       (line 16).
    2. `tests/unit/features/panel/test_palette.py` — remove the import (line 7) + drop `+ AGENTS_CSS` from the
       `PANEL_CSS` concat (line 13).
    3. `tests/unit/features/panel/test_panel_css_contrast.py` — remove the import (line 17) + drop `+ AGENTS_CSS`
       from `PANEL_CSS` (line 23).
    **Gate (Python-import-aware):** `grep -rn AGENTS_CSS dadaia_workspace/ tests/` returns **ZERO after the
    co-edits** (a served-HTML+JS grep alone cannot see a Python import). Confirm AGENTS_CSS was also absent from
    `static._ASSETS` + `index.py` (it never served).
  - **Tests — AC-6** `theme-switcher.spec.ts` green incl. axe-core zero critical/serious on 3 themes (W6 run).
    **AC-7** Category-A per-selector grep proofs committed + Category-B `grep -rn AGENTS_CSS == 0` proof; full
    e2e **AND full unpiped pytest** backstop green (an ImportError would red-bar collection).
  - **AC-9(e) sabotage:** delete a Category-A selector the purge KEPT-as-live (still-referenced, e.g.
    `.memory-chip`) ⇒ the response-guard e2e FAILS (broken tour/console error) → revert. **(f/A1) sabotage:**
    delete `agents.py` WITHOUT the 3 co-edits ⇒ `test_palette.py` + `test_panel_css_contrast.py` FAIL at
    collection (ImportError) → revert. Capture each command + failing test.
  - **AC-1/AC-2 replay.** AC-11 **file-enumerated ledger** — Category A: REMOVED selectors + grep evidence, KEPT
    candidates + reason. Category B: DELETED `views/assets/css/agents.py`; **EDITED** `views/assets/__init__.py`,
    `tests/unit/features/panel/test_palette.py`, `tests/unit/features/panel/test_panel_css_contrast.py`
    (AGENTS_CSS concat dropped — the prior false SURVIVE-unchanged claim for `test_panel_css_contrast.py` is
    REMOVED; WCAG/token behavior preserved because AGENTS_CSS carries no served rule the WCAG assertions depend
    on). No `specs/backlog/**` staged.

## W6 — FR7 e2e extension + gates + ship

- [ ] T-59-60 Extend the Playwright suite, run full gates + self-hosting verify, then ship. Checklist:
  - **Extend `tests/e2e/panel/` — button smoke ONLY (the FR3 width spec is authored in W3, Q2/Option A, NOT
    here).** Add a restyled-button smoke assertion (computed `border-radius`/padding non-default — the controls
    are styled, not browser-default). Artifacts via `PLAYWRIGHT_OUTPUT_DIR`/`PLAYWRIGHT_REPORT_DIR` →
    `.dadaia/tmp/product-engineer/<YYYYMMDD>/`.
  - **Full local gates (AC-10, Q7):** unpiped `pytest -p no:cacheprovider` (real exit — the `-p no:cacheprovider`
    is mandatory so the NEW unit tests do not materialize `.pytest_cache/` in the repo tree) — full suite green;
    `ruff format --check`; `ruff check --no-cache`; `mypy --strict dadaia_workspace`; `lint-imports --no-cache`
    → **8 kept / 0 broken**, ignore-cap UNCHANGED (the panel restyle adds no import edge; the AGENTS_CSS refactor
    removes an import, never adds one); `dadaia specs doctor` exit 0; `dadaia backlog doctor` exit 0.
  - **(Q7) Repo-hygiene check:** `git status --short` shows **no `.pytest_cache/`, no repo-local `.dadaia/`, no
    `playwright-report/`, no `test-results/`** before ship (Playwright artifacts are redirected to
    `.dadaia/tmp/…` via `PLAYWRIGHT_OUTPUT_DIR`/`PLAYWRIGHT_REPORT_DIR`).
  - **Full GH-only Playwright panel suite locally** — `cd tests/e2e && npm ci && npx playwright install
    --with-deps chromium && PLAYWRIGHT_OUTPUT_DIR=.dadaia/tmp/product-engineer/<date> PLAYWRIGHT_REPORT_DIR=…
    npm run test:e2e` (driving via `PANEL_WEB_SERVER_COMMAND`): response-guard (no 4xx/5xx + no console error),
    theme (incl. axe per theme), tab-nav, workflows, sessions, + the W3 width check + the button smoke — ALL
    green. e2e-panel is GH-only (not in `ci preflight`); this local run is mandatory before ship.
  - **Self-hosting reconcile (AC-12):** confirm `git diff -- dadaia_workspace/public/` is **EMPTY** (panel is
    package code, not a projected asset) and `dadaia public doctor` reports `[ok] public-privacy`, exit 0; if
    any `public/**` file changed, run `dadaia public stage → dadaia public doctor → dadaia public install
    --target all → confirming dadaia public doctor`. Instance files never hand-edited. Confirm the v0.1.50
    frozen no-steal suite is **zero-diff**.
  - **Live-panel + screenshots (server-registration law, ADR-H):** run a live `dadaia panel`, register it via
    `dadaia server register --port <p> --project dadaia-workspace`, and capture operator-facing screenshots (all
    3 themes; the restyled controls; a 1024px and a 1440px width proving no control-row wrap) →
    `.dadaia/tmp/product-engineer/<YYYYMMDD>/` for PR sign-off.
  - QA ship-gate APPROVE; security push-gate keyed to the pushed sha; push; **watch CI until every job green**
    (incl. the `e2e-panel` job); PR; merge. No dead anchor this release → **no SHIP-time backlog archival** (the
    surviving anchor is archived at CLOSURE). Verify no W1–W5 commit staged `specs/backlog`. *(PE runs no shell —
    surfaces the npm/Playwright + `server register` + git commands to PM/operator or requests devops-engineer.)*

## W7 — closure (CLOSURE phase)

- [ ] T-59-70 CLOSURE.md + memory truth + disposition + archive. Checklist:
  - Set `ACTIVE.md` phase = `CLOSURE`. Write `CLOSURE.md` (Summary, Tasks completed w/ SHAs, Validations triples
    incl. the e2e run + the screenshot paths under `.dadaia/tmp/…`, Drifts, Memory updates, Dispositions,
    Backlog returns, Archive decision).
  - **MEMORY (§SPEC 8):** `specs/memory/product/panel/panel.md` → the v0.1.59 visual/layout overhaul as current
    truth (cohesive token-driven design system, uniformly styled controls, single-line header/control rows —
    inline `style=` hacks removed, layout/IA density pass, theme-switcher polish, dead-CSS purge). **Fix the
    grill-found drift (S6): the memory card renders FIVE memory chips** (Constitution, Architecture, Tech Stack,
    Quality, Product), not three. Confirm the 6-tab nav + strict-CSP + read-only-telemetry statements remain
    accurate. `specs/memory/product/panel/brand-identity.md` → assess (token rationalization; palette hex
    unchanged). `architecture.md` / `quality-assurance.md` / `tech-stack.md` → assess (likely no-change-confirm;
    `agents.py` removal is a panel-internal detail). Regen `catalog.json` + `index.md` ONLY if
    `tldr`/`summary`/`area` change — **keep the regenerated `tldr` within the length cap** so the catalog regen
    + `dadaia specs doctor` at W7 stays clean. `release_origin` → v0.1.59 on each edited atom.
  - **Dispositions**: archive `panel-ux-overhaul` → `specs/_archive/v0.1.59/consumed-backlog/` +
    `consumed_backlog.json`; terminal status `DELIVERED — v0.1.59` (anchor survives → CLOSURE archival; no
    SHIP-time archival). Record in the CLOSURE `## Dispositions` table.
  - **Backlog returns**: none required (all residual scope consumed). If any implementation discovery surfaced
    (e.g. a follow-up polish), route it through PM curation and record in `## Backlog returns`.
  - `dadaia specs doctor` clean; request `git mv specs/releases/v0.1.59 → specs/_archive/releases/`
    (devops/operator); set `ACTIVE.md` → next release (`v0.1.60` / R12 Capability tail) or `release: none`; mark
    candidates R11 row **SHIPPED — v0.1.59**.
