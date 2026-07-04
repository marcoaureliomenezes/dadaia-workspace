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

- [x] T-59-20 Restyle all interactive controls uniformly from `TOKENS_CSS`. Checklist:
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
  - **W2 EVIDENCE (T-59-20 DONE 2026-07-04, software-engineer).**
    - **AC-3** `test_control_tokens.py` GREEN (3 tests): allowlist `{.nav-tab, .theme-btn, .runtime-btn,
      .wfp-picker, .wfp-profile-select, .academy-card__cta, .academy-back-btn, .reports-row__trash,
      .reports-back-btn, .reports-confirm-delete, .reports-confirm-cancel}`; each matched rule body extracted
      from the served surfaces (`structure.py`/`workflows.py`/`workflow_policy.py`/`reports.py`/`academy.py`,
      EXCLUDING `tokens.py`) is `var(--…)`-anchored with zero reject-literals; control-state coverage asserts
      `:hover` + `:focus-visible` + active/selected (`.active`/`:active`/`[aria-checked]`) for the button subset
      `{.nav-tab, .theme-btn, .runtime-btn}`.
    - **AC-9(c) sabotage:** `sed -i 's/  border-bottom-color: var(--color-accent, var(--color-accent-dark));/
      border-bottom-color: #9cddc8;/' .../css/structure.py` (into `.nav-tab.active`) ⇒
      `test_control_tokens.py::test_control_rules_are_token_anchored` FAILED
      (`AssertionError: ad-hoc hex literal in structure.py :: .nav-tab.active … #9cddc8`; `re.Match '#9cddc8'`)
      while the other 2 tests passed ⇒ reverted via inverse `sed`; re-ran GREEN.
    - **Design deviation (recorded):** the `.runtime-switcher`/`.runtime-btn`/`.runtime-btn-icon` COMPONENT
      rules were relocated from `tokens.py` → `structure.py` so the allowlist (`.runtime-btn`) and the
      `tokens.py` exclusion stay self-consistent; the `--color-runtime-*` token defs + `[data-runtime]` overrides
      remain in `tokens.py`. Both files are in the W2 write set. `views/assets/css/workflows.py` needed NO edit —
      its per-step picker CSS (`.wf-step-picker*`, `.dadaia-wf-step-model*`) was already fully token-anchored.
    - **Fate verified:** SURVIVE green in the same full run — `test_panel_css_contrast.py` (WCAG AA/AAA preserved:
      0 palette-hex changes; brand tokens in PANEL_CSS use nested-var fallbacks, not bare, not hex),
      `test_palette.py`, `test_theme_palettes.py` (warm focus-visible override untouched),
      `test_theme_switcher.py`, `test_runtime_switcher_pi.py` (`id="sessions-runtime-btn-pi"` HTML intact),
      `test_static.py`/`test_views_static.py`, `test_svg_validity.py`, `test_views_index.py`. INVARIANT
      byte-identical — `test_api_golden.py` + `api_golden_v0155.json` (no `render_api_*` edit),
      `test_index_dom_contract.py` (never re-baselined — no index HTML/selector changed; runtime-btn HTML
      unchanged, only its CSS relocated), `test_security_headers.py` incl. the W1 CSP equality lock (no
      inline-script edit; `_CSP_SCRIPT_HASH_1/2` unchanged). e2e `tests/e2e/panel/*.spec.ts` SURVIVE (touched
      selectors `.wfp-picker`/`.wfp-profile-select`/`.wfp-seg-btn`/`.theme-btn`/`.runtime-btn`/`.nav-tab` all
      preserved — bodies restyled, no selector renamed, no HTML change).
    - **AC-11 ledger** — NEW: `tests/unit/features/panel/test_control_tokens.py`; EDITED:
      `views/assets/css/structure.py` (`.nav-tab` + `.theme-btn` restyle + relocated runtime-switcher block),
      `views/assets/css/tokens.py` (runtime-switcher component rules removed — relocated; token defs retained),
      `views/assets/css/workflow_policy.py` (`.wfp-*` picker controls token-cleaned + added select/reset/seg
      focus-visible + hovers), `views/assets/css/reports.py` (trash/back/confirm buttons),
      `views/assets/css/academy.py` (card CTA + back-btn). No `specs/backlog/**` staged.
    - **Gates:** `ruff format --check` clean · `ruff check --no-cache` passed · `mypy --strict` 309 files clean ·
      `lint-imports --no-cache` 8 kept / 0 broken · full unpiped `pytest -p no:cacheprovider` 4596 passed / 17
      skipped (exit 0). `git status --short`: no `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, repo-local
      `.dadaia/`, `playwright-report/`, or `test-results/` (Q7); no `public/**` diff (AC-12: panel is package
      code — no re-projection needed).

## W3 — FR3 single-line header / control-row layout (width e2e authored HERE — Q2/Option A)

- [x] T-59-30 De-inline THREE inline styles + responsive single-line row + RED-first width e2e. Checklist:
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
  - **W3 EVIDENCE (T-59-30 DONE 2026-07-04, software-engineer).**
    - **De-inline (A5)** — all THREE inline `style=` attributes removed and replaced by token-anchored CSS
      classes: (1) `views/index.py:82` `.topbar-right` `margin-left:auto;display:flex;align-items:center;gap:0.5rem;`
      → `.topbar-right` rule in `structure.py` (`gap: var(--space-sm)`); (2) `views/index.py:83` `.theme-switcher`
      `position:relative;` → `.theme-switcher` rule in `structure.py`; (3) `views/sessions.py:36`
      `.runtime-switcher` `margin-left:auto;` → folded into the existing `.runtime-switcher` component rule in
      `structure.py` (`margin-left: auto; flex-shrink: 0;`). The `.runtime-switcher`/`.theme-switcher`/
      `[data-runtime-value]`/`[data-theme-value]` DOM-contract selectors are all preserved (Q5) — only `style=`
      attrs removed, no class renamed. CSP-clean (no `<script>` touched; `_CSP_SCRIPT_HASH_1/2` unchanged).
    - **Responsive single-line CSS** — new `structure.py` rule `.section-header:has(.runtime-switcher){display:flex;
      align-items:center;flex-wrap:nowrap;gap:var(--space-md);min-width:0}` + `> h2{min-width:0;overflow:hidden;
      text-overflow:ellipsis;white-space:nowrap}`. Scoped via `:has()` so the plain title/description headers
      (Servers, Projects) are untouched — this is the surgical W3 fix, not the W4 layout/IA pass. Token-anchored;
      no colour/type/radius literals.
    - **Grep-proof (A5):** `grep -n 'style=' views/index.py views/sessions.py` → ZERO (exit 1, no matches);
      `grep -c` → `index.py:0`, `sessions.py:0`. Recorded.
    - **AC-4 width e2e — RED-FIRST, empirically pinned.** NEW spec `tests/e2e/panel/header-row-width.spec.ts`
      measures the Sessions `#section-sessions .section-header` control row on all 3 themes × {1024px, 1440px}
      (6 combos), asserting the `.runtime-switcher` shares the `<h2>` band (`rsBox.y < h2Bottom`) AND the header is
      a single row (`headerBox.height < max(h2,rs)+24`). **PINNED WRAP WIDTH:** the pre-fix wrap is STRUCTURAL, not
      width-responsive — the pre-fix `.section-header` is `display:block`, so the switcher stacks below the title at
      EVERY width; RED captured at BOTH 1024px and 1440px (all 6 combos). **RED capture (pre-fix tree, before CSS
      landed):** all 6 FAILED — e.g. `theme=warm @1024px :: h2 y=127.2 h=28.5 bottom=155.7; runtime-switcher
      y=155.7 h=42.8; header h=81.9` → `expect(155.7).toBeLessThan(155.7)` FAILS (switcher top == heading bottom =
      stacked). **GREEN post-fix:** all 6 passed (6.6s). Artifacts under
      `.dadaia/tmp/software-engineer/20260704/pw-{red,green}-*`.
    - **AC-9(d) sabotage — RUNNABLE IN W3 (proven):** `sed -i 's/\.section-header:has(\.runtime-switcher) {/
      .section-header:has(.runtime-switcher-SABOTAGED) {/'` (neutralize the `:has()` single-line rule ⇒ restore the
      pre-fix wrapping arrangement) ⇒ `header-row-width.spec.ts` FAILED all 6 (`runtime-switcher WRAPS below the
      heading … h2 bottom=155.7; runtime-switcher y=155.7; header h=81.9`) ⇒ reverted via inverse `sed`
      (`grep SABOTAGED` → reverted-clean; `.section-header:has(.runtime-switcher)` rule restored at line 146/153).
    - **AC-1/AC-2 replay + fate ledger (panel unit subset, 180 passed):** `test_api_golden.py` +
      `api_golden_v0155.json` INVARIANT byte-identical (no `render_api_*` edit); `test_index_dom_contract.py`
      never re-baselined (theme/runtime switcher selectors preserved — only `style=` attrs dropped);
      `test_security_headers.py` incl. the W1 CSP equality lock GREEN (no inline-script edit; `_CSP_SCRIPT_HASH_1/2`
      unchanged); `test_views_index.py` SURVIVES (markers + selectors preserved); `test_control_tokens.py`,
      `test_palette.py`, `test_panel_css_contrast.py`, `test_theme_switcher.py`, `test_theme_palettes.py`,
      `test_runtime_switcher_pi.py`, `test_static.py`, `test_views_static.py`, `test_svg_validity.py` all GREEN.
      **Changed-surface e2e (28 passed):** `header-row-width.spec.ts` (6) + `theme-switcher.spec.ts` (10) +
      `sessions-dashboard.spec.ts` + `response-guard.spec.ts` + `tab-navigation.spec.ts` — all SURVIVE, selectors
      preserved. AGENTS_CSS importers untouched (W5 co-edits). No frozen-suite interaction.
    - **AC-11 ledger** — EDITED: `views/index.py` (de-inline `.topbar-right` + `.theme-switcher` `style=`),
      `views/sessions.py` (de-inline `.runtime-switcher` `style=`), `views/assets/css/structure.py`
      (`.topbar-right`/`.theme-switcher` rules + `.section-header:has(.runtime-switcher)` single-line rule +
      `margin-left:auto`/`flex-shrink:0` on `.runtime-switcher`). `views/assets/css/sessions.py` NEEDED NO EDIT
      (the single-line rule is structural → `structure.py`). NEW: `tests/e2e/panel/header-row-width.spec.ts`.
      No `specs/backlog/**` staged.
    - **Gates:** `ruff format --check` clean (797 files) · `ruff check --no-cache` passed · `mypy --strict` 309
      files clean · `lint-imports --no-cache` 8 kept/0 broken (ignore-cap UNCHANGED — no import edge) · full unpiped
      `pytest -p no:cacheprovider` 4596 passed / 17 skipped (exit 0). `git status --short`: no `.pytest_cache/`,
      `.mypy_cache/`, `.ruff_cache/`, repo-local `.dadaia/`, `playwright-report/`, or `test-results/` (Q7 — the
      `.mypy_cache/`/`.ruff_cache/` materialized by the gate runs were gitignored + removed); no `public/**` diff
      (AC-12: panel is package code — no re-projection needed).

## W4 — FR4 layout / IA hierarchy + density

- [x] T-59-40 Restructure section/card grouping, alignment, density across the live tabs. Checklist:
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
  - **W4 EVIDENCE (T-59-40 DONE 2026-07-04, software-engineer).**
    - **Layout/IA pass (SSR-HTML)** — every top-level section header standardized to a proper `<header
      class="section-header">` landmark for a consistent structural hierarchy across the six tabs (Sessions was
      already `<header>`; Servers + Projects in `views/index.py`, `views/academy.py`, `views/reports.py`,
      `views/workflows.py` changed `<div class="section-header">` → `<header ...>`). CSP-clean (no `<script>`
      touched); NO inline `style=` reintroduced (`grep -c 'style=' index.py sessions.py` → `0`/`0`). No
      `render_api_*` edit. 6-tab nav UNCHANGED (Ruling A).
    - **Marker strings PRESERVED (A4)** — `sessions-dashboard` / `reports-list` / `academy-content` untouched;
      `<div>`→`<header>` only changes the container element, never a marker/selector. `test_views_index.py`
      SURVIVES unchanged (`<h2>Projects</h2>`, `projects-count-badge`, `section-desc`, `About this section`,
      `Active Spec Context Projects`, all card zones + 5 memory chips intact). **STOP-and-rescope (Q5): NONE** —
      no asserted DOM-contract selector changed; the DOM-contract lock was NOT re-baselined.
    - **Density/hierarchy pass (CSS)** — (1) `structure.py`: `.section-header h2`/`p` given tokenized rhythm
      (`--line-height-tight`/`-snug`, `--text-base`, `--space-2xs`); NEW FR4 rule
      `.section-header:has(.projects-count-badge)` lays the Projects title + count badge on ONE aligned row
      (title left, count right) — the same single-row pattern W3 gave the Sessions `.runtime-switcher` header,
      scoped so Servers/Reports/Academy keep their stacked title+description flow. (2) `projects.py`:
      `.context-card` upgraded to the shared card-elevation language (`--shadow-card-rest` →
      `--shadow-card-hover` + `--lift-hover`, softer `--radius-lg`), motion-guarded; `.projects-count-badge`
      gets `margin-left:auto`+`flex-shrink:0` for the right-aligned header row (`border-left` + `--space-md`
      padding preserved). (3) `academy.py` CSS: `.academy-card` aligned to the same rest→hover-lift elevation +
      `--radius-lg`, motion-guarded. (4) `sessions.py` CSS: `.sessions-stat-card` given `--shadow-card-rest`
      resting elevation (non-interactive → no hover lift). (5) `workflows.py` CSS: NEW `.section-meta` rule
      (the workflows subsection description was emitted unstyled) → muted `--color-muted`/`--text-sm` treatment
      consistent with a `.section-header <p>`. All token-anchored; no palette-hex change (Ruling E); no control
      rule touched with an ad-hoc literal.
    - **AC-5 replay + fate ledger (panel unit subset, 578 passed):** `test_index_dom_contract.py` GREEN (all 6
      tabs/sections + `.nav-tab`/`.memory-chip`/`.context-card`/`.card-zone-*` + theme + runtime switchers
      present — never re-baselined); `test_views_index.py` SURVIVES unchanged (markers + `projects-count-badge`
      + `section-desc` + card contract preserved); `test_api_golden.py` + `api_golden_v0155.json` INVARIANT
      byte-identical (`UPDATE_API_GOLDEN` never used); `test_security_headers.py` incl. the W1 CSP equality lock
      GREEN (no inline-script edit; `_CSP_SCRIPT_HASH_1/2` unchanged); `test_control_tokens.py` GREEN (no control
      rule literal); `test_palette.py` + `test_panel_css_contrast.py` GREEN (WCAG AA/AAA preserved — 0 palette-hex
      change; brand-token fallbacks intact; new structure/workflows/sessions rules use no bare brand-var);
      `test_theme_switcher.py`, `test_theme_palettes.py`, `test_runtime_switcher_pi.py`, `test_static.py`,
      `test_views_static.py`, `test_svg_validity.py`, `test_projects_css_contract.py` all GREEN. AGENTS_CSS
      importers untouched (W5 co-edits). No frozen-suite interaction.
    - **Changed-surface e2e (16 passed, artifacts `.dadaia/tmp/software-engineer/20260704/pw-out|report`):**
      `header-row-width.spec.ts` (6 — the W3 Sessions single-line row STILL green; my Projects header-row rule is
      a separate `:has(.projects-count-badge)` rule and does not perturb the Sessions `:has(.runtime-switcher)`
      rule) + `theme-switcher.spec.ts` (10 — incl. E2E-THM-09 axe-core zero critical/serious on all 3 themes).
    - **AC-9 self-check (optional/preferred — DONE):** live registered panel (`dadaia server register --port
      3742`); with FR4 the Projects `7 projects` badge sits inline-right on the title row
      (`w4-projects-with-grouping.png`); sabotaging the FR4 rule
      (`sed 's/:has(.projects-count-badge)/:has(.projects-count-badge-SABOTAGED)/'`) visibly regresses density —
      the badge STACKS onto a second line below the title (`w4-projects-SABOTAGED-density-regressed.png`),
      exactly the "stacked fragments / weak grouping" complaint — then reverted (grep `SABOTAGED` → 0). Panel
      released. Screenshots + academy grouping under `.dadaia/tmp/software-engineer/20260704/`.
    - **AC-11 ledger** — EDITED: `views/index.py` (Servers + Projects header → `<header>`), `views/academy.py`,
      `views/reports.py`, `views/workflows.py` (top-level `.section-header` → `<header>`),
      `views/assets/css/structure.py` (section-header rhythm + FR4 Projects header-row rule),
      `views/assets/css/projects.py` (context-card elevation + count-badge alignment),
      `views/assets/css/academy.py` (academy-card elevation), `views/assets/css/sessions.py` (stat-card resting
      shadow), `views/assets/css/workflows.py` (`.section-meta` rule). NEEDED NO EDIT: `views/sessions.py`
      (already `<header class="section-header">`; its runtime-switcher row is the W3 fix). SURVIVE unchanged:
      `test_views_index.py`. No `specs/backlog/**` staged.
    - **Gates:** `ruff format --check` clean (797 files) · `ruff check --no-cache` passed · `mypy --strict` 309
      files clean · `lint-imports --no-cache` 8 kept/0 broken (ignore-cap UNCHANGED — no import edge) · full
      unpiped `pytest -p no:cacheprovider` 4596 passed / 17 skipped (exit 0). `git status --short`: no
      `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, repo-local `.dadaia/`, `playwright-report/`, or
      `test-results/` (Q7); no `public/**` diff (AC-12: panel is package code — no re-projection needed).

## W5 — FR5 theme-switcher polish + FR6 two-category dead-CSS purge

- [x] T-59-50 Theme-switcher polish + two-category dead-CSS purge (Cat-A rules + Cat-B AGENTS_CSS refactor).
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

  - **W5 EVIDENCE (T-59-50 DONE 2026-07-04, software-engineer).**
    - **FR5 theme-switcher polish (CSS, `structure.py`)** — `.theme-btn` + `#theme-menu` popover refined
      from tokens: `#theme-menu` panel now `border: var(--border-width)`, `border-radius: var(--radius-lg,10px)`
      (softer, matches the W4 card language), `box-shadow: var(--shadow-card-hover)` (the lifted card elevation,
      replacing a hardcoded two-layer shadow), `padding: var(--space-2xs) 0`, `top: calc(100% + var(--space-2xs))`;
      rows tokenized (`gap: var(--space-sm)`, `padding: var(--space-sm) var(--space-md)`, `font-size: var(--text-base)`,
      `transition: … var(--duration-fast) var(--easing-standard)`); active-row `font-weight: var(--font-weight-semibold)`
      (brand `--color-primary-bg` fallback PRESERVED); `.theme-btn-label` `font-size: var(--text-md)`. The four
      grep-gated `.theme-btn`/`:hover`/`:active`/`:focus-visible` rules stayed literal-free (test_control_tokens
      GREEN). **Every `theme-switcher.spec.ts` contract preserved** — `#theme-btn` (aria-haspopup=menu, in
      `.topbar`), `#theme-menu` (role=menu, `[hidden]`), 3 `[role="menuitemradio"]` Mint/Sage/Warm +
      `[data-theme-value]` + `.theme-swatch-dot`, localStorage, `data-theme`, Escape-close+focus, warm
      `--color-accent-dark` focus-ring. Two inline pre-paint scripts BYTE-IDENTICAL (no `index.py`/`handler.py`
      edit; `_CSP_SCRIPT_HASH_1/2` unchanged → AC-2 equality lock GREEN).
    - **AC-6 — `theme-switcher.spec.ts` GREEN locally: 12 passed** (E2E-THM-01..10 + response-guard's 2), incl.
      **E2E-THM-09 axe-core zero critical/serious on all 3 themes**. Harness: venv-python panel on :4994,
      artifacts → `.dadaia/tmp/software-engineer/20260704/pw-report`. (WebServer `BrokenPipeError` in logs = benign
      telemetry-teardown client-disconnect noise, not a test failure; e2e exit 0.)
    - **AC-7 Category-A — file-enumerated REMOVE / KEEP ledger (grep: served HTML = all `views/*.py` render
      output; JS = `views/assets/js/*.js` incl. template strings; `tests/`).** All edits in
      `views/assets/css/structure.py#STRUCTURE_CSS` (string BODY only; symbol survives, no import breaks):

      | Candidate selector | Fate | Grep evidence |
      |---|---|---|
      | `.context-count` (+ `strong`) | **REMOVED** | zero refs views/JS/tests; live projects count is `.projects-count-badge` (W4) |
      | `.context-card.primary` | **REMOVED** | `index.py:226` renders only `class="context-card"`; the `.primary` modifier is never emitted (`.context-card` + `:hover` KEPT live) |
      | `.card-header` | **REMOVED** | zero exact bare `card-header`; only served token is the DISTINCT `.dadaia-wf-card-header` (workflows.py:177), a different class |
      | `.card-primary-badge` | **REMOVED** | zero HTML/JS; sole `tests/` ref is a `not in` ABSENCE guard (`test_views_index.py:354`) that PROVES the class is dead in markup — stays green |
      | `.card-links` | **REMOVED** | zero refs views/JS/tests |
      | `.memory-link*` (`.memory-link`, `:last-child`, `:hover,:focus`, `:focus-visible`, `-icon`, `-label`, `-arrow`) | **REMOVED** | zero refs views/JS/tests; live memory pills are `.memory-chip` (projects.py). The now-dangling `.memory-link:focus-visible` selector also dropped from the Warm-theme focus-visible override compound |
      | `.agents-grid--compact` (+ `@media`) | **REMOVED** | zero refs views/JS/tests (removed Agentic/Ops agents grid) |
      | `.workflows-grid--compact` (+ 2×`@media`) | **REMOVED** | zero refs views/JS/tests (verified vs `workflows.py` first — the live workflows catalog is `.dadaia-wf-catalog`/`.dadaia-wf-card`, not this) |
      | `.ops-subsection` / `.ops-subsection-header` / `.ops-subsection-title` | **KEPT (live)** | **LIVE — `workflows.py:202-204` renders `class="ops-subsection"`, `ops-subsection-header`, `<h3 class="ops-subsection-title">`.** Not ambiguous — a confirmed live reference. `.ops-subsection{min-width:0}` overflow-safety rule also KEPT |

      Out-of-scope note: `.card-meta` (exact) is not a served class (`index.py` uses `.card-meta-row`) but is NOT
      an enumerated candidate → left untouched (no scope creep).
    - **AC-7 Category-B — AGENTS_CSS coordinated refactor (PM Binding Ruling 1).** DELETED
      `dadaia_workspace/features/panel/views/assets/css/agents.py`; co-edited its 3 live importers in the SAME
      wave: `views/assets/__init__.py` (dropped `from ...css.agents import AGENTS_CSS` + the `"AGENTS_CSS"`
      `__all__` entry); `tests/unit/features/panel/test_palette.py` (dropped import + `+ AGENTS_CSS` from the
      `PANEL_CSS` concat); `tests/unit/features/panel/test_panel_css_contrast.py` (same). **Gate PASS:**
      `grep -rn AGENTS_CSS dadaia_workspace/ tests/` → **ZERO** after co-edits. Confirmed AGENTS_CSS/`agents.css`
      never served (absent from `static._ASSETS` + not linked by `index.py`). WCAG/token behavior preserved —
      `test_panel_css_contrast.py` GREEN (AGENTS_CSS carried no served rule the WCAG assertions depend on).
    - **AC-9(e) sabotage (delete a KEPT-as-live selector ⇒ guardrail FAILS ⇒ revert).** Renamed the live
      `.memory-chip` (`index.py:234-238`) → `.memory-chip-SABOTAGED`:
      `pytest test_index_dom_contract.py::test_memory_chip_present_with_populated_context` **FAILED**
      (`AssertionError: .memory-chip absent`, exit 1) → `git checkout` reverted (0 SABOTAGED refs). Evidence:
      `.dadaia/tmp/software-engineer/20260704/ac9e-sabotage-domcontract-fail.txt`. **Finding:** the response-guard
      e2e does NOT catch this (it null-guards `if (firstChip)` at `response-guard.spec.ts:77` and degrades
      gracefully — 2 passed even sabotaged), which is exactly why the FR1 DOM-contract lock is the primary
      dropped-live-selector guardrail (the task's explicit "or the DOM contract" path).
    - **AC-9(f) sabotage (delete `agents.py` WITHOUT co-edits ⇒ ImportError at collection ⇒ revert).** With the
      2 test files restored to their AGENTS_CSS-importing state and `agents.py` removed,
      `pytest test_palette.py test_panel_css_contrast.py --collect-only` **FAILED at collection** on both
      (`ModuleNotFoundError: No module named '…css.agents'`, "2 errors during collection", exit 2) → restored +
      re-applied the coordinated co-edits. Evidence:
      `.dadaia/tmp/software-engineer/20260704/ac9f-sabotage-importerror.txt`.
    - **AC-1/AC-2 replay + panel unit fate ledger (578 panel unit passed):** `test_api_golden.py` +
      `api_golden_v0155.json` INVARIANT byte-identical (`UPDATE_API_GOLDEN` never used — no `render_api_*` edit);
      `test_index_dom_contract.py` GREEN + NEVER re-baselined (no asserted selector changed — the purge only
      removed non-asserted dead rules; STOP-and-rescope: NONE); `test_security_headers.py` incl. the W1 CSP
      equality lock GREEN (`_CSP_SCRIPT_HASH_1/2` unchanged); `test_control_tokens.py` GREEN (`.theme-btn` still
      literal-free); `test_palette.py` + `test_panel_css_contrast.py` GREEN after the AGENTS_CSS drop (WCAG AA/AAA
      preserved); `test_theme_switcher.py`, `test_theme_palettes.py`, `test_views_index.py`,
      `test_runtime_switcher_pi.py`, `test_static.py`, `test_views_static.py`, `test_svg_validity.py`,
      `test_projects_css_contract.py` GREEN. No frozen-suite interaction.
    - **AC-11 ledger — DELETED:** `dadaia_workspace/features/panel/views/assets/css/agents.py`. **EDITED:**
      `dadaia_workspace/features/panel/views/assets/css/structure.py` (FR5 popover polish + 8 Cat-A selector
      groups purged + Warm-override `.memory-link` selector dropped), `views/assets/__init__.py` (AGENTS_CSS
      import + `__all__` dropped), `tests/unit/features/panel/test_palette.py` (AGENTS_CSS import + concat
      dropped), `tests/unit/features/panel/test_panel_css_contrast.py` (AGENTS_CSS import + concat dropped — the
      prior false SURVIVE-unchanged claim is REMOVED; WCAG behavior preserved). **KEPT live:** `.ops-subsection*`
      (workflows.py). No `specs/backlog/**` staged. AC-12: no `public/**` diff — panel is package code, no
      re-projection needed.
    - **Gates:** `ruff format --check` clean (796 files) · `ruff check --no-cache` all passed · `mypy --strict`
      308 files clean · `lint-imports --no-cache` **8 kept / 0 broken** (ignore-cap UNCHANGED — the AGENTS_CSS
      refactor removed an import, added none) · full unpiped `pytest -p no:cacheprovider` **4596 passed / 17
      skipped** (exit 0). `git status --short`: no `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, repo-local
      `.dadaia/`, `playwright-report/`, or `test-results/`; no `public/**` diff.

## W6 — FR7 e2e extension + gates + ship

- [-] T-59-60 Extend the Playwright suite, run full gates + self-hosting verify, then ship. Checklist:
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

  - **W6 ENGINEERING EVIDENCE (T-59-60 engineering sub-items DONE 2026-07-04, software-engineer — marker stays
    `[-]`; the ship ladder QA/security-gate → push → PR → merge completes it).**
    - **FR7 button smoke (NEW `tests/e2e/panel/button-smoke.spec.ts`, 2 tests, GREEN).** Reads the computed
      `border-radius`/padding of the three restyled control families and asserts token-driven values a
      browser-default `<button>` (padTop≈1px, padLeft≈6px, radius 0px) does NOT carry: (1) `.nav-tab`/`.theme-btn`/
      `.runtime-btn` padTop>4 AND padLeft>8 (shipped: nav-tab 9.6/16, theme+runtime 6.4/12); (2) `.theme-btn`
      radius>4 (var(--radius-pill)=9999px pill) + `.runtime-btn` radius>4 (var(--control-radius)=6px). Small +
      honest; artifacts via `PLAYWRIGHT_OUTPUT_DIR`/`PLAYWRIGHT_REPORT_DIR` → `.dadaia/tmp/software-engineer/20260704/pw-w6/`.
    - **AC-9 mutation-sanity (button smoke sabotage → FAIL → revert):** edited `.theme-btn` in `structure.py`
      (`padding: 0; border-radius: 0;`) ⇒ BOTH button-smoke tests FAILED (`.theme-btn :: padTop=0 padLeft=0
      radius=0` — "control is unstyled" / "pill styling missing") ⇒ reverted `git checkout -- structure.py`
      (grep SABOTAGE → 0; `border-radius: var(--radius-pill)` restored at line 348). No production file left changed.
    - **AC-8 full local GH-only Playwright panel suite — 53 passed / 1 skipped (54 total, 13 spec files, 58.1s).**
      Harness: venv-python panel on :4993 via `PANEL_WEB_SERVER_COMMAND`. Green specs: `response-guard`
      (E2E-GUARD-01/02 — no 4xx/5xx + no console error on the 6-tab tour + memory chip), `theme-switcher`
      (E2E-THM-01..10 incl. **E2E-THM-09 axe-core zero critical/serious on all 3 themes**), `tab-navigation`
      (E2E-TAB-01..06), `workflows-tab` + `workflow-policy-editor` + `workflow-policy-harness-toggle`,
      `sessions-dashboard` (E2E-SES-DASH-01..04), `servers-tab`, `spec-context-tab`/`-operation-journey`,
      `api-contracts`, the W3 **`header-row-width`** width spec (6 combos), and the NEW **`button-smoke`** (2). The
      1 skip = the LAN non-loopback IPv4 check (`test_panel.py:345`, no non-loopback addr). The WebServer
      `BrokenPipeError` in logs = benign telemetry-teardown client-disconnect noise, e2e exit 0.
    - **AC-10 full local gates:** `ruff format --check` clean (796 files) · `ruff check --no-cache` all passed ·
      `mypy --strict dadaia_workspace/` 308 files clean · `lint-imports --no-cache` **8 kept / 0 broken** (ignore-cap
      UNCHANGED — no import edge added) · full **unpiped** `pytest -p no:cacheprovider` **4596 passed / 17 skipped**
      (exit 0, 447.69s). `dadaia specs doctor` **exit 0** (0 errors, 11 WARN — all pre-existing SPEC-DOC-031
      backlog slug-mention false-positives, ADR-6 class, not this release). `dadaia backlog doctor` **clean** (exit 0).
    - **AC-12 self-hosting reconcile:** `git diff -- dadaia_workspace/public/` **EMPTY** (panel is package code, not
      a projected asset — no re-projection needed) · `dadaia public doctor` **exit 0** with **`[ok] public-privacy`**.
      **Frozen v0.1.50 no-steal suite zero-diff:** `git diff --name-only main..HEAD -- tests/` matching
      `lease|gate_policy|spec_context` (excl. `release`) → **none**. **(Q7) repo hygiene:** `git status --short` =
      only `M specs/releases/v0.1.59/TASKS.md` + `?? tests/e2e/panel/button-smoke.spec.ts`; the `.ruff_cache/` +
      `.mypy_cache/` gate-run residue (gitignored) removed; no `.pytest_cache/`, no repo-local `.dadaia/`, no
      `playwright-report/`, no `test-results/`.
    - **Live-panel + screenshots (ADR-H / server-registration law):** live `dadaia panel --port 3742` (venv dadaia)
      registered via `dadaia server register --port 3742 --project dadaia-workspace --pid <pid>` — **LEFT RUNNING +
      REGISTERED** (● running) for PR sign-off (end-of-work dev-server law). **17 operator screenshots** →
      `.dadaia/tmp/software-engineer/20260704/w6-screenshots/`: all 3 themes full-page (`01-panel-{mint,sage,warm}-1440`);
      restyled controls (`02-controls-topbar-*`, `03-controls-navtabs-*`, `04-controls-theme-popover-mint`,
      `06-controls-runtime-switcher-warm`); the Sessions header/control row `05-sessions-row-{theme}-{1024,1440}`
      across 3 themes × {1024px,1440px} — **all measured single-row=true** (rsTop 127.2 < h2Bottom 159.6, header
      h 53.4 — no wrap at either width, matching the W3 width-spec invariant).
    - **AC-11 ledger** — NEW: `tests/e2e/panel/button-smoke.spec.ts`. No production source edited (the `structure.py`
      sabotage was reverted). No `specs/backlog/**` staged. Verified: no W1–W6 commit staged `specs/backlog`.

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
