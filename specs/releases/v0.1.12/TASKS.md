# TASKS: v0.1.12 — Panel Auth Coherence + Memory Truth + Header

**Status:** Em revisão
**Release ID:** v0.1.12
**Owner:** product-engineer
**Created:** 2026-06-11

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

Waves W1–W5 parallelize across disjoint write sets EXCEPT the declared shared
files: `features/panel/handler.py` (T-012-02 → T-012-08 iff CSP constants change),
`views/assets/js/core.js` (T-012-03 → T-012-04 → T-012-10), and
`views/index.py` (T-012-07 → T-012-08). Hard spine:
T-012-00 → 01 → 02 → 03 → {04, 05}; 06 → 07 → 08; {all code} → 11 → 12;
T-012-13 runs LAST (CLOSURE phase). Maximum one `[-]` per owner unless tasks are
in different waves with disjoint write sets as declared here. TDD-first: each task
lands its failing test before the fix.

---

## Pre-work

### [ ] T-012-00 — Release start: ACTIVE.md → v0.1.12 IMPLEMENTATION
- **Owner:** product-engineer · **Maps:** v0.1.11 release-start precedent
- **Write set:** `specs/releases/ACTIVE.md`
- **Preconditions:** SPEC+PLAN+TASKS `**Status:** Aprovado` (coordinator flips
  after spec-review).
- **Acceptance:** `ACTIVE.md` reads `release: v0.1.12` / `phase: IMPLEMENTATION`
  before any W1 work begins. Authored at DEFINITION as `phase: DEFINITION`; this
  task is the flip.
- **Parallelism:** first, before all waves.

---

## W1 — Auth server: cookie session done right (bug B1 server half)

### [ ] T-012-01 — auth.py: cookie validation + custom-header predicate
- **Owner:** software-engineer · **Maps:** FR-W1-01/02; ADR-3; bug
  `panel-cookie-auth-theater-browser-apis-unreachable` (server half)
- **Write set:** `dadaia_workspace/features/panel/auth.py`,
  `tests/unit/features/panel/test_auth*.py`
- **Preconditions:** T-012-00.
- **Acceptance:** `validate_cookie(cookie_header, expected)` parses
  `panel_session` via stdlib and compares constant-time
  (`hmac.compare_digest`); absent/malformed/mismatched cookie ⇒ False;
  `requires_custom_header(method, path)` ⇒ True for POST/DELETE and `/api/*`,
  False for full-page GETs (`/memory-view/...`, `/reports/...`); Bearer
  `validate` byte-untouched; unit tests cover all branches; `mypy --strict`
  green.
- **Parallelism:** spine root; before T-012-02.

### [ ] T-012-02 — handler.py: Bearer-OR-cookie dispatch per route class
- **Owner:** software-engineer · **Maps:** FR-W1-01..05; ADR-3; AC-W1-01/02
- **Write set:** `dadaia_workspace/features/panel/handler.py`,
  `tests/unit/features/panel/test_handler*.py` (table-driven matrix test, new)
- **Preconditions:** T-012-01.
- **Acceptance (AC-W1-01 + AC-W1-02):** matrix test (written FIRST, failing only
  on cookie rows pre-change) covers every {BEARER, BEARER_SECOND_LOOP,
  BEARER_TELEMETRY} × {Bearer, cookie+header, cookie-only, none} × {GET XHR,
  POST/DELETE, full-page GET} combination: valid Bearer ⇒ 200/503 unchanged;
  cookie + `X-Dadaia-Panel: 1` ⇒ 200/503 on `/api/*`; cookie WITHOUT header ⇒
  401 on `/api/*` and POST/DELETE, 200 on `/memory-view/...` + `/reports/...`;
  no credential ⇒ 401; BEARER_TELEMETRY 503-when-None preserved after auth;
  v0.1.11 contracts green (launch replay 401, expired 401, Bearer-not-in-URL
  grep, tokenless+cookieless 401); suite + `mypy --strict` green.
- **Parallelism:** after 01; gates all of W2.

---

## W2 — Auth client + honest errors + binding e2e (bug B1 client half, U4)

### [ ] T-012-03 — core.js: cookie-implicit authedFetch, localStorage deletion, purge
- **Owner:** software-engineer · **Maps:** FR-W2-01/02; ADR-4/ADR-8
  (operator-authorized plugin-scope deviation)
- **Write set:** `dadaia_workspace/features/panel/views/assets/js/core.js`,
  `tests/unit/features/panel/` JS-residue contract test (new)
- **Preconditions:** T-012-02.
- **Acceptance (AC-W2-01):** `bootstrapToken()` and every `panel_token`
  read/write deleted; `authedFetch` sends no `Authorization`, always sets
  `X-Dadaia-Panel: 1`, relies on the same-origin cookie; boot performs a
  one-time `localStorage.removeItem('panel_token')`; the line-201 plain
  `fetch('/api/panel-status')` goes through `authedFetch`; residue grep test
  pins: no `localStorage` token access beyond the purge, no bare `fetch(` in
  panel JS outside `authedFetch` itself.
- **Parallelism:** after 02; before 04 and 10 (shares core.js).

### [ ] T-012-04 — Honest error states (real commands, real causes)
- **Owner:** software-engineer · **Maps:** FR-W2-03 (U4); AC-W2-02
- **Write set:** `dadaia_workspace/features/panel/views/assets/js/*.js` (failure
  texts), `dadaia_workspace/features/panel/views/*.py` (server-rendered notices),
  error-text grep contract test
- **Preconditions:** T-012-03 (shares core.js).
- **Acceptance (AC-W2-02):** grep zero `panel start` and zero ad-blocker wording
  across panel JS/views; auth-failure texts name `dadaia panel`; the Servers-tab
  failure notice renders the actual HTTP status of the failed response (view/JS
  test with stubbed 401); suite green.
- **Parallelism:** after 03; before 10.

### [ ] T-012-05 — Binding cookie-jar e2e: the real client flow
- **Owner:** software-engineer · **Maps:** FR-W2-04; ADR-7; AC-W2-03; closes bug
  `panel-cookie-auth-theater-browser-apis-unreachable`
- **Write set:** `tests/e2e/` panel e2e module (new/extend)
- **Preconditions:** T-012-03 (re-run after T-012-04 and T-012-10 land).
- **Acceptance (AC-W2-03):** e2e mimics the browser exactly with a cookie jar:
  launch panel → GET the printed `?launch=` URL → capture `Set-Cookie` →
  panel-status, contexts, kanban, academy, workflows, agents called with cookie
  + `X-Dadaia-Panel: 1` ⇒ 200 **with data** (or contractual 503 telemetry) →
  `/memory-view/<slug>/architecture.md` with cookie only ⇒ 200 rendered HTML →
  replay of the consumed launch token ⇒ 401 → cookieless+headerless `/api/*` ⇒
  401. Named regression test recorded in the bug file. Playwright variant
  optional, NOT CI-binding (ADR-7).
- **Parallelism:** after 03; final-gate re-run mandated by T-012-12.

---

## W3 — Memory truth: constitution route + five chips (bug B2)

### [ ] T-012-06 — memory.py: constitution allowlisted special-case
- **Owner:** software-engineer · **Maps:** FR-W3-02; ADR-5; AC-W3-01
- **Write set:** `dadaia_workspace/features/panel/views/memory.py`,
  `tests/unit/features/panel/test_views_memory*.py`
- **Preconditions:** T-012-00.
- **Acceptance (AC-W3-01):** literal request path `constitution.md` resolves to
  `repos/<slug>/specs/constitution.md` (`.resolve()` + `is_relative_to` guard
  mirroring `memory.py:95-99`); any other path keeps memory-root resolution
  byte-identically (existing tests green); traversal escapes and
  `releases/ACTIVE.md` / `bugs/<any>.md` / `_archive/...` ⇒ 404; rendered
  constitution HTML 200; suite green.
- **Parallelism:** independent; before 07 (hrefs need the route).

### [ ] T-012-07 — index.py: five memory chips + render-quality tests
- **Owner:** software-engineer · **Maps:** FR-W3-01/03; ADR-6/ADR-9; AC-W3-02;
  closes bug `panel-memory-view-unreachable-and-incomplete` (with T-012-06)
- **Write set:** `dadaia_workspace/features/panel/views/index.py` (`:246-249`
  chip nav), `tests/unit/features/panel/test_views_index*.py`
- **Preconditions:** T-012-06.
- **Acceptance (AC-W3-02):** project cards render exactly five chips in order
  Architecture / Tech Stack / Quality Assurance / Product / Constitution with
  `memory_view_url` hrefs (`quality-assurance.md`, `constitution.md` added);
  render-quality tests: `quality-assurance.md` and `product/index.md` produce
  structured HTML via the per-slug renderer (no raw `##`/`[[` artifacts);
  renderer cache (T-016-P04) + wikilink tests stay green (feed contract per SPEC
  W3); named regression test recorded in the bug file; suite green.
- **Parallelism:** after 06; before 08 (shares views/index.py).

---

## W4 — Chrome: header/logo, agentic layout, deep-linking (U1, U2, U3)

### [ ] T-012-08 — Header + logo redesign (geometric SVG mark, CSP sync)
- **Owner:** software-engineer · **Maps:** FR-W4-01 (U1); ADR-8/ADR-10; AC-W4-01
- **Write set:** `dadaia_workspace/features/panel/views/index.py` (header/logo
  markup), `dadaia_workspace/features/panel/views/assets/css/*` (header styles),
  `dadaia_workspace/features/panel/handler.py` (`_CSP_SCRIPT_HASH_*`, `:72-77` —
  ONLY iff inline scripts change), view/boot tests
- **Preconditions:** T-012-07 (shares views/index.py); T-012-02 if handler.py
  CSP constants are touched.
- **Acceptance (AC-W4-01):** rhino blob replaced by a clean geometric inline SVG
  mark, drawn with `currentColor`, legible at 20-36 px; header gains title
  hierarchy; theme switcher + status dot preserved; no `<img>`/external fetch;
  view test asserts markup + theming in all 3 palettes; **CSP trap honored:**
  any inline `<script>` change recomputes the handler hash constants in the SAME
  commit, verified by a shell-boot test that asserts script-driven content
  renders (no CSP block); suite green.
- **Parallelism:** after 07.

### [ ] T-012-09 — Agentic tab layout: cards/grid + section headers
- **Owner:** software-engineer · **Maps:** FR-W4-02 (U2); ADR-8; AC-W4-02
- **Write set:** `dadaia_workspace/features/panel/views/agents.py`,
  `dadaia_workspace/features/panel/views/workflows.py`,
  `dadaia_workspace/features/panel/views/kanban.py`,
  `dadaia_workspace/features/panel/views/assets/css/*` (agentic styles),
  view tests
- **Preconditions:** T-012-00.
- **Acceptance (AC-W4-02):** the stacked Agents/Workflows/Kanban sections render
  as a cards/grid layout with clear section headers; CSS/markup only — no data,
  endpoint, or behavior change; no framework; Sessions tab markup
  regression-asserted unchanged; suite green.
- **Parallelism:** independent (disjoint from index.py/core.js chains).

### [ ] T-012-10 — Tab deep-linking via location.hash
- **Owner:** software-engineer · **Maps:** FR-W4-03 (U3); AC-W4-03
- **Write set:** `dadaia_workspace/features/panel/views/assets/js/core.js` (tab
  module), JS/e2e test
- **Preconditions:** T-012-04 (shares core.js).
- **Acceptance (AC-W4-03):** loading with `#agentic` (or any tab id) activates
  the matching tab; tab switches update `location.hash`; unknown hash falls back
  to the default tab; behavior pinned by test (DOM-level unit or e2e — pick one,
  pin it); suite green.
- **Parallelism:** after 04; triggers T-012-05 re-run.

---

## W5 — Projection + final gate + closure

### [ ] T-012-11 — Projection verify: no public/** change expected
- **Owner:** software-engineer · **Maps:** SPEC W5; lib-guardrail workflow
- **Write set:** none expected (verification; CLI-only if a public asset changed)
- **Preconditions:** all W1-W4 tasks `[x]`.
- **Acceptance:** `git diff` shows no `dadaia_workspace/public/**` change (panel
  is library code); `dadaia public doctor` exit 0. If any public asset DID
  change: `dadaia public stage && dadaia public install --target all && dadaia
  public doctor` exit 0 and the reason recorded for CLOSURE.
- **Parallelism:** after W1-W4; before 12.

### [ ] T-012-12 — Release final gate
- **Owner:** software-engineer · **Maps:** AC-W5-01; all
- **Write set:** none (verification)
- **Preconditions:** T-012-11; all code tasks `[x]` except T-012-13.
- **Acceptance (AC-W5-01):** (1) `pytest -p no:cacheprovider` 0 failures;
  (2) `ruff format --check && ruff check --no-cache` clean; (3) `mypy --strict`
  clean; (4) import-linter 0 violations, ignore cap not increased; (5) `dadaia
  public doctor` exit 0; (6) `dadaia specs doctor` exit 0, no NEW WARNs vs
  baseline; (7) `dadaia ci preflight` exit 0; (8) T-012-05 e2e re-run green
  against the final client (post-04/10); (9) v0.1.11 panel contracts green;
  (10) 2/2 bug → named-regression-test table assembled for CLOSURE.
- **Parallelism:** last code-side task; gates rc-1 ship-trio (ADR-2).

### [ ] T-012-13 — Memory truth + dispositions + CLOSURE (PE, CLOSURE phase)
- **Owner:** product-engineer · **Maps:** SPEC "Memory files affected"; ADR-11
  disposition vocabulary (v0.1.11); bug/backlog sweep
- **Write set:** `specs/memory/product/panel/panel.md`,
  `specs/memory/product/panel/brand-identity.md` (iff logo description changes),
  `specs/memory/product/catalog.json` + atom frontmatter `token_estimate`
  (mechanical regen via `public/scripts/generate-memory-catalog.py`, iff atoms
  changed), `specs/memory/architecture.md` (iff panel-auth text drifts; else
  "no change" with reason), `specs/releases/v0.1.12/CLOSURE.md`, bug/backlog
  disposition frontmatter
- **Preconditions:** ALL tasks `[x]`; alpha-1 qa commit + rc-1 ship-trio
  APPROVE; ACTIVE.md phase CLOSURE.
- **Acceptance:** `panel.md` describes the post-fix product atomically — auth
  model v2 (Bearer-OR-cookie + `X-Dadaia-Panel` matrix, launch flow), five-chip
  memory feed + constitution allowlist + feed contract, header/logo,
  deep-linking, honest errors — superseded loopback/Bearer-only text replaced,
  no changelog; `token_estimate` regenerated with zero WARNs if atoms changed;
  CLOSURE.md carries `## Dispositions`: both bugs `Closed` with named regression
  tests, the panel-ux-overhaul 2026-06-11 picked items marked
  `DELIVERED — v0.1.12` (coordinated with PM, backlog owner); `dadaia specs
  doctor` exit 0; archive via `git mv` after the operator merge gate.
- **Parallelism:** LAST.
