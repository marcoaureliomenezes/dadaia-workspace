# SPEC: v0.1.12 — Panel Auth Coherence + Memory Truth + Header

**Status:** Em revisão
**Release ID:** v0.1.12
**Owner:** product-engineer
**Created:** 2026-06-11
**Branch:** `feature/v0.1.12` (stacked on `feature/v0.1.11`, operator holds merges)

---

## Objective

One release that makes the panel **actually work in a real browser**. The operator's
2026-06-11 live review found the v0.1.11 panel shell loads but every `/api/*` call
returns 401 on a fresh profile (auth theater: the minted `panel_session` cookie is
never read by any server route, and `core.js` lost its credential source when
`?token=` was removed), project memory has never been viewable from the browser in
any version, and the chrome (logo/header, agentic layout, error texts) is below bar.

Scope: (1) auth model v2 — "cookie session done right" — so the browser can
authenticate to every tab API and full-page memory/report navigations; (2) memory
truth — the chip set covers all five memory surfaces including `constitution.md` and
`quality-assurance.md`, served through an explicit allowlist; (3) the four
operator-picked UX items (header/logo redesign, agentic tab layout, tab deep-linking,
honest error states).

**Grill-me:** satisfied by the operator's live-review directive (2026-06-11, "review
the full panel solution… you can do better") plus the coordinator's code audit
recorded in the two bug files and pre-answered as Decisions ADR-1..ADR-10 below, per
release-governance (v0.1.10/v0.1.11 precedent).

---

## Bug inventory and resolution map (2/2)

| Bug | Sev | Resolution |
|-----|-----|-----------|
| `panel-cookie-auth-theater-browser-apis-unreachable` | CRITICAL | W1 (T-012-01/02 server cookie auth) + W2 (T-012-03 client, T-012-05 binding e2e) |
| `panel-memory-view-unreachable-and-incomplete` | HIGH | W1/W2 (auth half) + W3 (T-012-06 constitution route, T-012-07 five chips) |

No bug is silently dropped (bug-always-solved law). Per-bug acceptance: the repro in
the bug file now passes (behavior matches its **Expected** section) and each bug
closes with a named regression test.

## Backlog inventory (4 picked UX items — `specs/backlog/panel-ux-overhaul.md`, "Operator demand 2026-06-11")

| # | Item | Resolution |
|---|------|-----------|
| U1 | Header + logo redesign (rhino blob unreadable at 36px) | T-012-08 |
| U2 | Agentic tab layout (stacked Agents/Workflows/Kanban) | T-012-09 |
| U3 | Tab deep-linking (`#agentic` hash routing) | T-012-10 |
| U4 | Honest error states (no `dadaia panel start`, no ad-blocker speculation) | T-012-04 |

---

## Workstreams

### W1 — Auth server: cookie session done right (bug B1 server half)

**Grounding:** `features/panel/handler.py` route table (`_ROUTE_TABLE`, lines
139-178: PUBLIC / BEARER / BEARER_SECOND_LOOP / BEARER_TELEMETRY classes); only
`Authorization` is ever validated (`_validate_bearer` on `self.headers`); the
v0.1.11 launch exchange mints `panel_session` (`SESSION_COOKIE_NAME`) but no route
reads a Cookie header — zero consumers.

**Functional requirements:**
- FR-W1-01: every GET route currently classed BEARER / BEARER_SECOND_LOOP accepts
  EITHER a valid `Authorization: Bearer` header (CLI/tools path, semantics
  unchanged) OR a valid `panel_session` cookie. Cookie validation is a
  constant-time compare of the cookie value against the server Bearer
  (`hmac.compare_digest` or equivalent — same discipline as `auth.validate`).
- FR-W1-02: state-changing routes (POST/DELETE) and all `/api/*` XHR routes, when
  authenticating **via cookie**, additionally require the custom request header
  `X-Dadaia-Panel: 1` (CSRF defense-in-depth on top of `SameSite=Strict`:
  cross-origin pages cannot attach custom headers without a CORS preflight the
  server never grants). Bearer-header callers are exempt from the custom header.
- FR-W1-03: full-page navigations (`/memory-view/...`, `/reports/...`) authenticate
  via cookie alone (GET, read-only, `SameSite=Strict`) — no custom header required
  (a browser navigation cannot carry one).
- FR-W1-04: BEARER_TELEMETRY routes keep their 503-when-telemetry-None semantics;
  their auth check gains the same Bearer-OR-cookie acceptance.
- FR-W1-05: launch flow unchanged (single-use ≤60 s `?launch=` → Set-Cookie,
  v0.1.11 T-011-13/ADR-10). The v0.1.11 contracts stay green: launch-token replay
  ⇒ 401; the Bearer appears in no URL; a caller with neither header nor cookie ⇒
  401 on non-PUBLIC routes.

### W2 — Auth client + honest errors + the binding e2e (bug B1 client half, U4)

**Grounding:** `views/assets/js/core.js` — `bootstrapToken()` (line 36) still reads
the removed `?token=` param into `localStorage['panel_token']`; `authedFetch`
(line 51) sends that stale token; the Servers tab polls `/api/panel-status` with a
plain `fetch` (line 201) that 401'd in every version; failure texts cite the
nonexistent `dadaia panel start` and speculate about ad blockers.

**Functional requirements:**
- FR-W2-01: the localStorage token mechanism is DELETED — `bootstrapToken()` and
  every `localStorage['panel_token']` read/write removed. `authedFetch` becomes
  cookie-implicit (`credentials: 'same-origin'` semantics) and always sets
  `X-Dadaia-Panel: 1`. On boot, a one-time purge removes any stale
  `localStorage['panel_token']` left by ≤v0.1.10 (credential-hygiene migration).
- FR-W2-02: ALL fetches go through `authedFetch` — the plain-`fetch`
  `/api/panel-status` hole is closed; a residue grep/test pins "no bare `fetch(`"
  in panel JS outside `authedFetch` itself.
- FR-W2-03 (U4): every auth-failure text names the real command (`dadaia panel`);
  the Servers-tab failure text names the real cause (the HTTP status received) —
  no ad-blocker speculation anywhere in panel JS/views.
- FR-W2-04: the **binding e2e** proves the real client flow end-to-end with a
  cookie jar that mimics the browser exactly: open the printed `?launch=` URL →
  receive `Set-Cookie` → subsequent tab API calls (cookie + `X-Dadaia-Panel: 1`)
  return 200 **with data** for at least: panel-status, contexts, kanban, academy,
  workflows, agents (or 503-telemetry where contractually allowed) → a
  `/memory-view/<slug>/architecture.md` full-page navigation (cookie only, no
  custom header) renders HTML 200. A Playwright-driven test is welcome but NOT
  required in CI; the cookie-jar e2e is the binding contract.

### W3 — Memory truth: five chips + constitution route (bug B2)

**Grounding:** `views/index.py:246-249` hardcodes exactly three chips
(architecture / tech-stack / product); `quality-assurance.md` exists in every live
context's `specs/memory/` and is not linked; `views/memory.py` resolves only under
`repos/<slug>/specs/memory/` (traversal guard `memory.py:95-99`) so
`constitution.md` (one level up) is unservable.

**Functional requirements:**
- FR-W3-01: the per-project chip set is exactly five: Architecture, Tech Stack,
  Quality Assurance, Product, Constitution — in that display order.
- FR-W3-02: `views/memory.py` serves `constitution.md` through an EXPLICIT
  allowlisted special-case: the single path `constitution.md` resolves to
  `repos/<slug>/specs/constitution.md`; every other path keeps the existing
  memory-root resolution; the traversal guard stays intact for both branches; NO
  blanket `specs/` exposure (e.g. `releases/`, `bugs/`, `_archive/` remain 404).
- FR-W3-03: render quality verified for the two newly-linked chips:
  `quality-assurance.md` and `product/index.md` render through the per-slug
  renderer (headings, wikilinks) without raw-markdown artifacts — asserted by view
  tests, not eyeballs.

**Memory feed contract (documented here per ADR-9; reviewed end-to-end in W3):**
- *Source:* `repos/<slug>/specs/memory/**` plus the single allowlisted
  `repos/<slug>/specs/constitution.md`. Nothing else under `specs/` is reachable.
- *Served:* `.md` files are rendered to HTML **in-memory** via the per-slug mistune
  renderer with wikilink resolution and the per-slug renderer cache (T-016-P04);
  no HTML is ever written to disk (D-4). Non-`.md` files under the memory root
  (e.g. `catalog.json`, referenced images) are served bytes-verbatim with their
  content type.
- *Never served:* paths escaping the resolved roots (404, no information
  disclosure); any write path (the feed is strictly read-only); operator-local
  absolute paths in rendered output.

### W4 — Chrome: header/logo, agentic layout, deep-linking (U1, U2, U3)

**Functional requirements:**
- FR-W4-01 (U1): the rhino blob is replaced by a clean, geometric inline SVG mark —
  legible at 20-36 px, drawn with `currentColor` so it follows all three themes —
  plus a refined header: title hierarchy (product name + context), theme switcher
  kept, status dot kept. **CSP trap (explicit):** if any inline `<script>` content
  changes, the `_CSP_SCRIPT_HASH_*` constants in `handler.py` (lines 72-77) MUST be
  recomputed in the same task — a stale hash silently kills panel scripts.
- FR-W4-02 (U2): the Agentic tab's stacked Agents/Workflows/Kanban layout becomes a
  cards/grid presentation with clear section headers. Modest scope: CSS/markup
  only, no framework, no data/behavior change, Sessions tab untouched.
- FR-W4-03 (U3): `location.hash` deep-linking — on load, a hash matching a tab id
  (e.g. `#agentic`) activates that tab; switching tabs updates the hash; unknown
  hash falls back to the default tab.

### W5 — Projection + final gate

The panel is library code under `dadaia_workspace/features/panel/` — NO `public/**`
assets are expected to change; T-012-11 verifies that claim and runs
`dadaia public doctor` regardless (exit 0). The final gate re-runs the full
validation battery and assembles the 2/2 bug → named-regression-test table.

---

## Decisions (ADR-1..ADR-10 — operator pre-answers + coordinator audit, recorded at definition; architect reviews ADR-3 centrally)

- **ADR-1 Scope = 2 open panel bugs + 4 picked UX items.** Operator live-review
  directive 2026-06-11; the bugs carry the coordinator's code audit; the UX picks
  are recorded in `specs/backlog/panel-ux-overhaul.md` §"Operator demand
  2026-06-11". Bugs-always-solved law applies.
- **ADR-2 Cadence: single alpha-1 → rc-1 ship-trio.** alpha-1 end = qa-only review
  commit; rc-1 end = qa + code-reviewer + security-reviewer all APPROVE → push +
  PR. Operator holds the merge. Flat release dir, v0.1.11 precedent.
- **ADR-3 Auth model v2 — "cookie session done right" (central ADR).** GET routes
  in the BEARER*/BEARER_SECOND_LOOP classes accept Bearer header OR a valid
  `panel_session` cookie (constant-time compare against the Bearer).
  State-changing routes and `/api/*` XHR additionally require `X-Dadaia-Panel: 1`
  when authenticating via cookie (CSRF defense-in-depth over `SameSite=Strict`;
  custom headers force a preflight the server never grants). Full-page navigations
  authenticate via cookie alone. BEARER_TELEMETRY keeps 503 semantics. Launch flow
  (single-use ≤60 s) unchanged. This supersedes v0.1.11 ADR-10's "sensitive APIs
  remain Bearer-only" pin — that pin made the browser unauthenticatable by
  construction; the v0.1.11 e2e *contracts* (replay 401, no Bearer in URLs,
  headerless+cookieless ⇒ 401) all remain binding.
- **ADR-4 The client credential store is the cookie, period.** `core.js` deletes
  the localStorage token mechanism entirely; `authedFetch` is cookie-implicit +
  custom header; one-time boot purge of stale `localStorage['panel_token']`
  (unswept credential found by the audit); all fetches go through `authedFetch`.
- **ADR-5 Constitution via explicit allowlist, not a wider root.**
  `views/memory.py` special-cases the single literal path `constitution.md` →
  `repos/<slug>/specs/constitution.md`. Traversal guard intact on both branches;
  no blanket `specs/` exposure. Constitution is "the main file of a project"
  (operator) and joins the chip set.
- **ADR-6 Chip set is exactly five.** Architecture, Tech Stack, Quality Assurance,
  Product, Constitution. `quality-assurance.md` and `product/index.md` verified
  present in all live contexts at definition time. The operator's "memory with
  quality-assurance included never worked" complaint is resolved by the QA chip +
  the auth fix — no extra scope.
- **ADR-7 The binding e2e drives the real client flow.** A cookie-jar e2e that
  mimics the browser exactly (launch URL → cookie → tab APIs 200 with data +
  memory-view full-page HTML) is the binding contract; Playwright is welcome but
  not required in CI. This closes the review hole that let v0.1.11 ship auth
  theater (crafted-request e2es never exercised the shipped JS client).
- **ADR-8 Plugin-scope deviation, operator-authorized.** Browser HTML/CSS/JS and
  UX redesign would route to the `frontend-design` plugin; no plugin pack is
  distributable (v0.1.11 ADR-4 honest-relabel). The operator authorizes
  `software-engineer` to do this panel frontend work directly as library source
  edits. Recorded explicitly per the backlog item's §4 constraint.
- **ADR-9 The memory feed contract is documented in this SPEC** (W3 section):
  source roots, in-memory mistune render with per-slug cache (T-016-P04) +
  wikilink resolution retained, bytes-verbatim for non-`.md`, never-served set.
  W3 reviews the feed end-to-end against this contract.
- **ADR-10 CSP hashes are a declared trap, not a hope.** Any task changing inline
  panel scripts must recompute `_CSP_SCRIPT_HASH_*` in `handler.py` in the same
  commit; the e2e (real client, console-error-free boot implied by 200s + data)
  backstops it.

---

## Architecture deltas

- `features/panel/auth.py` — cookie validation helper (constant-time), custom-
  header requirement predicate; Bearer `validate` unchanged.
- `features/panel/handler.py` — auth dispatch per route class accepts Bearer OR
  cookie (+ `X-Dadaia-Panel` rule for XHR/state-changing via cookie); CSP hash
  constants recomputed if inline scripts change.
- `features/panel/views/assets/js/core.js` — localStorage mechanism deleted;
  `authedFetch` cookie-implicit + custom header; boot purge; panel-status poll
  through `authedFetch`; hash-based tab routing.
- `features/panel/views/index.py` — five memory chips; header/logo redesign
  (inline geometric SVG, `currentColor`).
- `features/panel/views/memory.py` — `constitution.md` allowlisted special-case.
- Agentic tab views/CSS (`views/agents.py`, `views/workflows.py`,
  `views/kanban.py`, `views/assets/css/*`) — layout only.
- No new route classes; no route table additions beyond auth semantics; no lease/
  gate/session changes; no `public/**` asset changes expected (verified W5).

## Tech-stack deltas

None. stdlib `http.cookies`/`hmac` only; no new dependencies, no framework.

## Security/operations deltas

- Browser credential moves from JS-readable localStorage (unswept Bearer) to the
  `HttpOnly; SameSite=Strict` cookie exclusively — plus an active purge of the
  legacy stored token.
- CSRF posture: SameSite=Strict primary + custom-header requirement for
  cookie-authenticated XHR/state-changing calls (defense-in-depth).
- Constitution exposure is a single allowlisted read-only file per context —
  traversal guard re-asserted by tests on both resolution branches.
- v0.1.11 security contracts re-asserted: Bearer in no URL; launch replay 401;
  headerless+cookieless 401.

## Memory files affected at closure

- `specs/memory/product/panel/panel.md` — auth model v2 (cookie+header matrix),
  five-chip memory feed + constitution allowlist, header/logo, deep-linking,
  honest error states. (Atom currently describes the v0.1.10 loopback-bypass
  posture — superseded text replaced, no changelog.)
- `specs/memory/product/panel/brand-identity.md` — new logo mark (currentColor
  geometric SVG) if the brand atom's logo description changes.
- `specs/memory/product/catalog.json` + atom frontmatter — `token_estimate`
  regeneration IF atoms change (mechanical, PE-only, CLOSURE).
- `specs/memory/architecture.md` — only if the panel auth description there
  drifts; else "no change" with reason.
- `specs/constitution.md` — no edit expected.

---

## Acceptance criteria

Each AC is evidence-triple friendly: {description, command, evidence}.

- **AC-W1-01** Route-class auth matrix unit tests: for each class
  (BEARER, BEARER_SECOND_LOOP, BEARER_TELEMETRY) — valid Bearer ⇒ 200/503;
  valid cookie + `X-Dadaia-Panel: 1` ⇒ 200/503 on `/api/*`; valid cookie WITHOUT
  the header ⇒ 401/403 on `/api/*` and POST/DELETE but 200 on full-page GET
  (`/memory-view/...`, `/reports/...`); invalid/absent cookie + no header ⇒ 401;
  cookie compare is constant-time (code-reviewed + test asserts compare_digest
  path). (FR-W1-01..04)
- **AC-W1-02** v0.1.11 contract regression: launch replay ⇒ 401; expired launch ⇒
  401; Bearer grep corpus (panel views + launch/registry + tests) finds no Bearer
  in any URL; tokenless+cookieless `/api/*` ⇒ 401. Existing tests stay green
  unmodified or with documented re-classification only. (FR-W1-05)
- **AC-W2-01** Grep contracts on panel JS: zero `localStorage` token reads/writes
  except the one-time purge; zero bare `fetch(` outside `authedFetch`;
  `authedFetch` sets `X-Dadaia-Panel: 1`. Pinned by a residue contract test.
  (FR-W2-01/02)
- **AC-W2-02** Error-text honesty: grep zero `panel start` and zero ad-blocker
  wording in panel JS/views; Servers-tab failure path renders the received HTTP
  status (unit/view test with a stubbed 401). (FR-W2-03)
- **AC-W2-03** The binding cookie-jar e2e (FR-W2-04) passes: launch → Set-Cookie →
  ≥6 tab APIs 200-with-data (or contractual 503) → memory-view full-page 200 HTML.
  Named test closes bug B1. (FR-W2-04)
- **AC-W3-01** `/memory-view/<slug>/constitution.md` ⇒ 200 rendered HTML;
  `/memory-view/<slug>/../constitution.md`-style escapes and
  `releases/ACTIVE.md`, `bugs/<any>.md` ⇒ 404; memory-root paths unaffected.
  Named test closes bug B2 (with AC-W3-02). (FR-W3-02)
- **AC-W3-02** Project cards render exactly five chips in order (Architecture,
  Tech Stack, Quality Assurance, Product, Constitution); view tests assert hrefs;
  `quality-assurance.md` and `product/index.md` render without raw-markdown
  artifacts via the per-slug renderer (cache + wikilinks behavior unchanged —
  existing renderer tests stay green). (FR-W3-01/03)
- **AC-W4-01** Header: inline SVG mark present, uses `currentColor`, no `<img>`/
  external fetch; renders in all 3 themes (view test asserts markup + CSS tokens);
  if inline scripts changed, recomputed CSP hashes verified by an e2e/unit that
  boots the shell and gets script-driven content (no CSP block). (FR-W4-01)
- **AC-W4-02** Agentic tab: section headers + grid classes asserted by view test;
  Sessions tab markup byte-unchanged (regression assert). (FR-W4-02)
- **AC-W4-03** Hash routing: JS unit/e2e — load with `#agentic` activates the
  Agentic tab; switching tabs updates `location.hash`; unknown hash ⇒ default
  tab. (FR-W4-03)
- **AC-W5-01** Final gate: (1) `pytest -p no:cacheprovider` 0 failures; (2) `ruff
  format --check && ruff check --no-cache` clean; (3) `mypy --strict` clean;
  (4) import-linter 0 violations, ignore cap not increased; (5) `dadaia public
  doctor` exit 0 + verification that no `public/**` asset changed (or, if one
  did, it was staged+installed); (6) `dadaia specs doctor` exit 0, no NEW WARNs
  vs baseline; (7) `dadaia ci preflight` exit 0; (8) 2/2 bug →
  named-regression-test table assembled for CLOSURE.

---

## Out of scope

- Sessions tab changes (operator: "good — leave it untouched").
- Any frontend framework adoption; the panel stays stdlib-served vanilla JS/CSS.
- Blanket `specs/` serving (only the single constitution allowlist lands).
- Playwright as a CI requirement (welcome locally, not binding — ADR-7).
- Plugin packs / `dadaia plugin` command (backlogged `plugin-packs-and-install-command`).
- Telemetry service changes (503 semantics kept as-is).
- PyPI publish; merging `feature/v0.1.11`/`v0.1.12` (operator-gated).
- The pre-2026-06-11 panel-ux-overhaul items already delivered in 0.1.6 (tab
  consolidation, theme switcher) — only the four 2026-06-11 picks are in scope.

## Dependencies and risks

- **Stacked branch:** `feature/v0.1.12` stacks on unmerged `feature/v0.1.11`.
  Rebase risk if rc feedback lands below; mitigation: linear stack, operator owns
  merge order.
- **Auth dispatch rework** touches every route: the v0.1.11 contract suite +
  AC-W1-01 matrix must both be green before any client work lands (W1 → W2 spine).
- **CSP hash drift** (ADR-10): header task recomputes hashes in the same commit;
  the real-client e2e backstops.
- **Cookie semantics across versions:** a stale ≤v0.1.10 localStorage token could
  mask failures during manual testing — the boot purge (FR-W2-01) plus
  fresh-profile e2e remove the intermittence class.
- **Shared files:** `handler.py` (T-012-02, possibly T-012-08 CSP constants),
  `core.js` (T-012-03 → T-012-04 → T-012-10), `views/index.py` (T-012-07 →
  T-012-08) are sequenced, not parallel — declared in TASKS.
