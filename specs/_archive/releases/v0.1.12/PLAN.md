# PLAN: v0.1.12 — Panel Auth Coherence + Memory Truth + Header

**Status:** Em revisão
**Release ID:** v0.1.12
**Owner:** product-engineer
**Created:** 2026-06-11

---

## Strategy

Five waves with a hard W1 → W2 spine: the server must accept the cookie before the
client can be rewritten to rely on it, and the binding cookie-jar e2e (the contract
that v0.1.11's reviews lacked) lands only after both halves exist. W3 (memory truth)
and W4 (chrome) are independent of each other but W3 shares `views/index.py` with the
header task and W2/W4 share `core.js` — sequencing is declared per file, not per
wave. W5 verifies the no-`public/**`-change claim and runs the final gate.

TDD-first throughout: every task lands its failing test before the fix. The route-
class auth matrix (AC-W1-01) is written as a table-driven test FIRST, against the
current handler — it must fail exactly on the cookie rows and pass on the Bearer
rows, proving the v0.1.11 Bearer semantics are untouched.

Cadence (ADR-2): single alpha-1 → qa-only commit → rc-1 ship-trio (qa + code +
security) → operator merge. Flat release dir; all work on `feature/v0.1.12`.

No state migration: the cookie already exists (v0.1.11 launch exchange); the only
client-side migration is the one-time `localStorage['panel_token']` purge (ADR-4).

## Layers affected

| Wave | Files | Layer |
|------|-------|-------|
| W1 | `features/panel/auth.py`, `features/panel/handler.py` | features |
| W2 | `features/panel/views/assets/js/core.js`, panel JS/views error texts, e2e tests | features (browser assets) + tests |
| W3 | `features/panel/views/memory.py`, `features/panel/views/index.py` | features |
| W4 | `features/panel/views/index.py` (header), `views/agents.py` / `views/workflows.py` / `views/kanban.py` + `views/assets/css/*`, `core.js` (hash routing), `handler.py` (CSP constants iff inline scripts change) | features (browser assets) |
| W5 | verification only (projection check + final gate) | none |

## Execution order and parallelism

```
PRE   T-012-00 (PE: release start — ACTIVE.md → v0.1.12 IMPLEMENTATION at approval)

W1 — auth server (spine root)
  T-012-01 (auth.py: cookie validation + custom-header predicate)
  T-012-02 (handler.py: route-class dispatch Bearer-OR-cookie + XHR header rule)
                                                  [after 01: consumes auth helpers]

W2 — auth client + honest errors + binding e2e
  T-012-03 (core.js: delete localStorage, cookie-implicit authedFetch, purge,
            panel-status via authedFetch)          [after 02: needs server cookie auth]
  T-012-04 (honest error texts, JS + views)        [after 03: shares core.js]
  T-012-05 (binding cookie-jar e2e)                [after 03; re-run after 04/10]

W3 — memory truth (parallel with W2)
  T-012-06 (memory.py: constitution allowlisted special-case)
  T-012-07 (index.py: five chips + render-quality tests)   [after 06: hrefs exist]

W4 — chrome
  T-012-08 (header/logo redesign + CSP hash sync)  [after 07: shares views/index.py]
  T-012-09 (agentic tab cards/grid layout)         [independent]
  T-012-10 (tab deep-linking via location.hash)    [after 04: shares core.js]

W5 — projection + gate + closure
  T-012-11 (projection verify: no public/** change expected; public doctor exit 0)
  T-012-12 (final gate — after all code tasks)
  T-012-13 (PE: memory truth + CLOSURE — CLOSURE phase, LAST)
```

Hard spine: 00 → 01 → 02 → 03 → {04, 05}; 06 → 07 → 08; 03 → 04 → 10;
{all code} → 11 → 12; 13 last (CLOSURE). T-012-05 is the release's binding
contract — it must be green at the final gate against the FINAL client (re-run
after 04 and 10 touch core.js).

## Technical approach (condensed)

### W1 — auth server
- **T-012-01:** `auth.py` gains `validate_cookie(cookie_header, expected_token)` —
  parse `panel_session` via stdlib `http.cookies`, constant-time compare
  (`hmac.compare_digest`) against the server Bearer; and
  `requires_custom_header(method, path)` (POST/DELETE or `/api/*` prefix). Pure
  functions, unit-tested in isolation. Bearer `validate` untouched.
- **T-012-02:** `handler.py` dispatch: for BEARER / BEARER_SECOND_LOOP /
  BEARER_TELEMETRY classes, auth passes when (a) valid `Authorization` header
  (today's path, unchanged), OR (b) valid cookie AND (`X-Dadaia-Panel: 1` present
  when `requires_custom_header` says so). Full-page GETs (memory-view, reports)
  fall outside the custom-header set by construction. BEARER_TELEMETRY keeps its
  503 branch after auth. Table-driven matrix test covers every class × credential
  × header combination (written first, failing on cookie rows only).

### W2 — auth client + e2e
- **T-012-03:** `core.js`: delete `bootstrapToken()` and all `panel_token` usage;
  `authedFetch` stops setting `Authorization`, always sets `X-Dadaia-Panel: 1`
  (cookies ride along same-origin by default); boot IIFE does
  `localStorage.removeItem('panel_token')` once; line-201 plain `fetch` →
  `authedFetch`. Residue contract test greps panel JS: no `localStorage` token
  access beyond the purge, no bare `fetch(` outside `authedFetch`.
- **T-012-04:** sweep panel JS + views for failure texts: `dadaia panel start` →
  `dadaia panel`; Servers-tab notice renders the actual HTTP status from the
  failed response; delete ad-blocker speculation. Grep contract pins both.
- **T-012-05:** e2e with a cookie jar mimicking the browser exactly
  (http.client/urllib with manual Cookie header per the received Set-Cookie):
  start panel on an ephemeral port → GET `?launch=` URL → capture cookie → call
  panel-status/contexts/kanban/academy/workflows/agents with cookie +
  `X-Dadaia-Panel: 1` asserting 200-with-data (or contractual 503) → GET
  `/memory-view/<slug>/architecture.md` with cookie only asserting 200 HTML →
  re-assert replay 401 + cookieless 401. This is the named regression test for
  bug B1.

### W3 — memory truth
- **T-012-06:** `memory.py`: before the memory-root resolution, special-case the
  literal request path `constitution.md` → resolve
  `repos/<slug>/specs/constitution.md` (`.resolve()` + `is_relative_to` the
  specs dir, mirroring the existing guard); all other paths unchanged. Tests:
  constitution 200; escapes/`releases/`/`bugs/` 404; memory-root behavior
  byte-identical (existing tests green).
- **T-012-07:** `index.py:246-249` chip nav grows to five entries in display
  order Architecture / Tech Stack / Quality Assurance / Product / Constitution
  (`quality-assurance.md`, `constitution.md` hrefs via `memory_view_url`). View
  tests assert the five hrefs; render-quality tests pass `quality-assurance.md`
  and `product/index.md` through the per-slug renderer asserting structured HTML
  (no raw `##`/`[[`), cache + wikilink tests stay green (feed contract, ADR-9).

### W4 — chrome
- **T-012-08:** new geometric inline SVG mark (`currentColor`, viewBox tuned for
  20-36 px legibility) + header markup hierarchy in `index.py`; CSS tokens reuse
  the brand palette. If any inline `<script>` changes, recompute
  `_CSP_SCRIPT_HASH_*` (`handler.py:72-77`) in the SAME commit (ADR-10); shell
  boot test (script-driven content present) backstops.
- **T-012-09:** agentic tab: section headers + responsive grid classes for the
  three stacked sections; CSS/markup only; Sessions tab regression assert
  (markup unchanged).
- **T-012-10:** `core.js` tab module: on `DOMContentLoaded`, if `location.hash`
  matches a tab id → activate it; tab clicks write `location.hash`; unknown hash
  → default. JS-testable via the e2e or a DOM-level unit (whichever the suite
  already supports — implementer picks, test pins behavior).

### W5 — projection + gate + closure
- **T-012-11:** assert `git status`/diff shows no `dadaia_workspace/public/**`
  change (panel is library code); run `dadaia public stage` no-op check +
  `dadaia public doctor` exit 0. If any public asset DID change, stage + install
  + doctor per the lib-guardrail workflow and record why.
- **T-012-12:** full battery (Validation plan) + the 2/2 bug →
  named-regression-test table for CLOSURE; T-012-05 re-run against final client.
- **T-012-13:** PE, CLOSURE phase: update `panel.md` atom (auth model v2, five
  chips + constitution allowlist, header, deep-linking, honest errors — replace
  superseded loopback/Bearer-only text, no changelog), `brand-identity.md` if the
  logo description changes, `token_estimate` regen if atoms changed; CLOSURE.md
  with Dispositions sweep (2 bugs → `Closed`; panel-ux-overhaul 2026-06-11 picks
  → `DELIVERED — v0.1.12` noted per PM coordination); archive via `git mv` after
  the operator merge gate.

## Validation plan

1. `pytest -p no:cacheprovider` full suite — 0 failures (new: auth helper units,
   route-class matrix, JS residue greps, error-text greps, constitution route +
   traversal, five-chip view tests, render-quality, header/CSP boot, agentic
   layout, hash routing, the binding cookie-jar e2e).
2. `ruff format --check && ruff check --no-cache` clean; `mypy --strict` clean.
3. `import-linter` 0 violations; ignore cap not increased.
4. `dadaia public doctor` exit 0; no unexplained `public/**` diff (T-012-11).
5. `dadaia specs doctor` exit 0; no NEW WARNs vs the release baseline.
6. `dadaia ci preflight` exit 0.
7. v0.1.11 panel contracts re-run green: launch replay 401, Bearer-not-in-URL
   grep, tokenless+cookieless 401.
8. Manual smoke at rc-1: fresh browser profile → printed launch URL → every tab
   shows data; memory chips render all five docs; `#agentic` deep-link works;
   header legible at 20-36 px in all 3 themes.
9. Reviewer cross-check at rc-1: memory deltas vs merged code; dispositions table.

## Technical risks

| Risk | L | Mitigation |
|------|---|-----------|
| Auth dispatch rework regresses v0.1.11 Bearer/launch contracts | M | matrix test written first against current handler (Bearer rows must pass pre-change); v0.1.11 suite kept green |
| CSRF model gap (cookie GET routes) | M | SameSite=Strict + custom header for XHR/state-changing; GETs are read-only by route audit; security-reviewer focus item at rc-1 |
| CSP hash drift kills panel JS silently | M | ADR-10 same-commit rule + shell-boot script-content test + e2e re-run |
| core.js churn across 3 tasks (03/04/10) | M | declared sequence 03 → 04 → 10; e2e re-run after each |
| Constitution allowlist accidentally widens specs/ exposure | L | literal-path special-case + traversal tests for releases/bugs/_archive 404 |
| Stale localStorage token masks failures in manual tests | L | boot purge + fresh-profile e2e (cookie jar starts empty) |
| Stacked branch rebase churn (v0.1.11 unmerged) | M | linear stack; operator owns merge order |
| views/index.py contention (chips vs header) | L | declared sequence 07 → 08 |
