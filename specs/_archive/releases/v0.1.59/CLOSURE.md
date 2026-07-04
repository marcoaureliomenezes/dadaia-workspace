# Closure: Release — v0.1.59 — Panel UX Overhaul

> **Status:** Aprovado
> **Release ID:** v0.1.59
> **Owner:** product-engineer
> **Closed:** 2026-07-04
> **Branch:** `feature/v0.1.59` · **Base:** v0.1.58 closure · **Merged:** `e6634996` (PR #108, squash of `feature/v0.1.59`) · **Closure branch:** `closure/v0.1.59`
> **Ship gates:** qa-engineer **APPROVE** (12/12 ACs falsifiable + spot-run green; the three release invariants independently confirmed at ship — api-golden ZERO commits since definition, DOM-contract single-commit history never re-baselined, CSP baselines == `handler.py` values, purge zero-grep re-run; 2 LOW non-blocking → 1 closure note + 1 backlog return) · security-reviewer **APPROVED** (zero findings; XSS posture **strictly improved** — three inline `style=` hacks removed, no new inline script, CSP hashes byte-frozen) · CI 35 checks, 0 failures on PR #108.

## Summary

v0.1.59 is R11 of the operator-approved 12-release plan — the **third** release of the
R9→R12 continuation mandate — and it answers the operator's standing verdict on the working
panel (2026-06-27: *"functionality is OK but the visual style is bad — crap, trash, looks like a
2005 website"*). It is a **UX/visual overhaul of existing, working surfaces**: behavior is kept
byte-for-byte; the panel is re-skinned and re-organized so it reads as one designed product.

The release lands a **cohesive, token-driven design system** on `tokens.py` (14 additive,
token-named tokens — typography scale, spacing rhythm, elevation/radius — with **zero palette
hex change**: the brand-identity 5-color canon, the three themes, and WCAG AA/AAA are all
preserved), **uniformly styled controls** driven from those tokens (nav tabs, theme button +
popover, runtime buttons, workflow per-step pickers, report/academy CTAs and the report trash
button — grep-gated so no ad-hoc hex/px/radius literal can leak into a restyled control rule),
**single-line header/control rows** (all three inline `style=` hacks in `index.py`/`sessions.py`
removed and replaced by token-anchored CSS classes; the shared `.section-header` + `.runtime-switcher`
row now lays out on one line by default), a **layout/IA density pass** that promotes every
top-level section header to a `<header class="section-header">` landmark and tightens card
density/grouping across the six tabs, a **theme-switcher polish** (popover spacing/radius/elevation
refined from tokens), and a **two-category dead-CSS purge** (eight dead selector groups removed from
`STRUCTURE_CSS`; the orphaned `agents.py#AGENTS_CSS` module **deleted** as a coordinated Python
refactor with its three importer co-edits).

The overhaul is **behavior-locked golden-first**: the `api_golden_v0155.json` byte-invariant was
declared a ZERO-DIFF INVARIANT and replayed byte-identical in every wave (never regenerated); a NEW
`test_index_dom_contract.py` presence-invariant captured the full e2e selector contract BEFORE any
restyle and was **never re-baselined**; and a NEW CSP zero-touch equality lock froze the two
inline-script hashes to their W1 baseline. The **6-tab nav set is unchanged** (Ruling A), there is
**no API / behavior change** (Ruling C), **no inline-script change** (Ruling B), **no new dependency**
(Ruling D), and **no palette re-theme** (Ruling E). All work was library-source edits under
`dadaia_workspace/features/panel/**` (package code — no `public/**` asset changed, so the live
instance needs no re-projection), performed by core agents under the recorded **`plugin-scope`
deviation** (operator 2026-07-02; the deviation dissolves only if `plugin-packs-and-install-command`
ships first — it has not). This CLOSURE records the overhaul into memory as the panel's current
truth (fixing the S6 three→five memory-chip drift the grill found), dispositions the sole consumed
backlog anchor (survives → CLOSURE archival), and files one backlog return (the QA LOW
defence-in-depth hardening of the response-guard e2e's chip assertion).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-59-01 | W0 definition — SPEC/PLAN/TASKS from the 2026-07-04 code read; mandatory release-definition grill on the picked set; eight operator-unavailable rulings (A–H) + two PM binding rulings (1 = AGENTS_CSS coordinated refactor; 2 = width-e2e authored in W3) recorded; dual definition review (architect REJECT A1–A6 + qa REJECT Q1–Q7) folded → `Aprovado` | `3d9c5534` · phase-flip `832cb38b` (squash `e6634996`) |
| T-59-10 | W1 FR1 — DOM-contract lock `test_index_dom_contract.py` (populated fakes, A3) captured BEFORE any restyle + api-golden ZERO-DIFF baseline confirmed + NEW CSP zero-touch equality lock + design-system rationalization of `tokens.py` (14 additive tokens, palette unchanged); AC-9(a)/(b′) sabotages | `b065c7f0` (squash `e6634996`) |
| T-59-20 | W2 FR2 — every interactive control restyled uniformly from `TOKENS_CSS` + NEW `test_control_tokens.py` allowlist token-anchor grep (Q3); AC-9(c) sabotage; `.runtime-*` component rules relocated `tokens.py`→`structure.py` for allowlist self-consistency (drift below) | `991465d0` (squash `e6634996`) |
| T-59-30 | W3 FR3 — three inline `style=` de-inlined into token-anchored classes (`grep 'style=' index.py sessions.py` == 0) + responsive single-line `.section-header:has(.runtime-switcher)` rule + NEW RED-first `header-row-width.spec.ts` (6 combos, structural wrap pinned at every width); AC-9(d) sabotage runnable in W3 | `8c830a55` (squash `e6634996`) |
| T-59-40 | W4 FR4 — every top-level section header promoted to a `<header class="section-header">` landmark + card density/elevation/grouping pass across the six tabs; marker strings preserved (`test_views_index.py` SURVIVES); AC-9 live-panel density self-check | `c8410072` (squash `e6634996`) |
| T-59-50 | W5 FR5 theme-switcher popover polish (contract preserved, axe-clean) + FR6 two-category dead-CSS purge — Category A: 8 dead `STRUCTURE_CSS` selector groups removed (per-selector grep proofs; `.ops-subsection*` KEPT-as-live); Category B: `agents.py#AGENTS_CSS` deleted with its 3 importer co-edits (`grep -rn AGENTS_CSS` == 0); AC-9(e)/(f) sabotages | `1a6a1ce0` (squash `e6634996`) |
| T-59-60 | W6 FR7 — NEW `button-smoke.spec.ts` restyled-button assertion; full local gates (AC-10); AC-12 self-hosting reconcile (no `public/**` diff); full local Playwright suite; live registered panel + 17 operator screenshots; QA ship gate; security push gate; push; CI watch; PR #108; merge | W6 engineering `849aa30b` · ship evidence `1e2e8d14` (squash `e6634996`) |
| T-59-70 | W7 closure — this CLOSURE.md + memory truth (panel.md primary + quality-assurance.md note) + disposition sweep + one backlog return + candidates R11 row shipped | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path). Gate
evidence captured at the W6 ship tree (`849aa30b` engineering, `1e2e8d14` ship-evidence) and
re-verified on the merged PR #108 (`e6634996`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-10 full suite green (unpiped, real exit) | `pytest -p no:cacheprovider` (no pipe) | `4596 passed, 17 skipped, exit 0` (447.69s) — ship tree `849aa30b`; re-verified on PR #108 `e6634996` — QA ship-gate handoff `2026-07-04T180947Z-qa-engineer-v0159-ship-gate` |
| AC-10 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 (796 files ruff format) — W6 |
| AC-10 types clean | `mypy --strict dadaia_workspace` | exit 0, 308 files — W6 |
| AC-10 import contracts + ignore-cap unchanged | `lint-imports --no-cache` | `8 kept, 0 broken`; ignore-cap **UNCHANGED** — the panel restyle adds no import edge and the AGENTS_CSS refactor **removes** an import, never adds one — W6 |
| AC-1 api-golden ZERO-DIFF INVARIANT (never regenerated) | `pytest …/test_api_golden.py` | `api_golden_v0155.json` replays **byte-identical** in every wave; `UPDATE_API_GOLDEN` never used; QA independently confirmed at ship the golden had **ZERO commits since definition** — W1..W6 |
| AC-1 DOM-contract presence-invariant (never re-baselined) | `pytest …/test_index_dom_contract.py` | green in every wave over populated fakes (≥1 `SpecContextProject`, A3); QA confirmed a **single-commit history**, never re-baselined; STOP-and-rescope count = 0 — W1..W6 |
| AC-2 CSP inline-script invariant + zero-touch equality lock | `pytest …/test_security_headers.py` | `TestInlineScriptCspCoverage` (len==2 + recompute) + `test_html_csp_value` + the NEW equality lock all green; the two pre-paint scripts stay byte-identical; QA confirmed the frozen baselines **== the `handler.py` `_CSP_SCRIPT_HASH_1/2` values** — W1..W6 |
| AC-3 controls token-anchored (grep-falsifiable) | `pytest …/test_control_tokens.py` | 3 green: the selector allowlist `{.nav-tab, .theme-btn, .runtime-btn, .wfp-picker, .wfp-profile-select, academy/report CTA + trash selectors}` rule bodies are `var(--…)`-anchored with zero reject-literals (hex / px-font-size / px-radius); `tokens.py` excluded — W2 |
| AC-4 single-line header/control row (RED-first) | `header-row-width.spec.ts` | RED-first: all 6 combos (3 themes × {1024,1440}) FAILED on the pre-fix tree (the wrap was **structural** — `.section-header` was `display:block`, drift below), GREEN post-fix; `grep 'style=' index.py sessions.py` == 0 — W3 |
| AC-6 theme-switcher polish preserves contract | `theme-switcher.spec.ts` | E2E-THM-01..10 green incl. **E2E-THM-09 axe-core zero critical/serious on all 3 themes** — W5/W6 |
| AC-7 dead-CSS purge grep-proven (two categories) | Category-A per-selector greps · `grep -rn AGENTS_CSS dadaia_workspace/ tests/` | Category A: 8 selector groups removed, each with a committed zero-live-reference grep (served HTML + all JS + JS template strings + `tests/`); `.ops-subsection*` KEPT (live at `workflows.py:202-204`). Category B: `agents.py#AGENTS_CSS` deleted + 3 importer co-edits ⇒ `grep -rn AGENTS_CSS` == **0** — W5 |
| AC-8 full local GH-only Playwright suite | `npm run test:e2e` (venv panel via `PANEL_WEB_SERVER_COMMAND`) | **53 passed / 1 env-skip** (13 spec files: response-guard, theme incl. axe ×3, tab-nav, workflows ×3, sessions, servers, spec-context ×2, api-contracts, the W3 `header-row-width` ×6, the NEW `button-smoke` ×2); the 1 skip = LAN non-loopback IPv4 check (no non-loopback addr) — W6 |
| AC-8 live panel + operator screenshots (ADR-H) | `dadaia panel --port 3742` + `dadaia server register` | live panel **registered on :3742** (HTTP 200, left running for PR sign-off); **17 operator screenshots** (3 themes full-page; restyled controls; theme popover; the 3×2 width matrix all measured single-row) at `.dadaia/tmp/software-engineer/20260704/w6-screenshots/` — W6 |
| AC-10 SDD doctor | `dadaia specs doctor` | exit 0 (0 errors; 11 WARN — pre-existing SPEC-DOC-031 backlog-slug-mention false-positives, ADR-6 class, not this release) — W6 |
| AC-10 backlog doctor | `dadaia backlog doctor` | exit 0 (no `specs/backlog/**` staged in W1–W6) — W6 |
| AC-12 zero `public/**` change + projection clean | `git diff -- dadaia_workspace/public/` · `dadaia public doctor` | diff **EMPTY** (panel is package code, not a projected asset — no re-projection needed); `dadaia public doctor` exit 0 with **`[ok] public-privacy`** — W6 |
| Frozen v0.1.50 no-steal suite untouched | `git diff main..HEAD -- tests/` (lease/gate/spec_context) | **zero-diff** — the release lives entirely in `features/panel/**` + its tests + the panel e2e; it never enters `spec_context`/lease/gate — W6 |
| (Q7) repo hygiene | `git status --short` | no `.pytest_cache/`, no repo-local `.dadaia/`, no `playwright-report/`, no `test-results/` (Playwright artifacts redirected via `PLAYWRIGHT_OUTPUT_DIR`/`PLAYWRIGHT_REPORT_DIR`; the `.ruff_cache/`/`.mypy_cache/` gate-run residue gitignored + removed) — W6 |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVE**, zero blockers (12/12 ACs falsifiable; three invariants independently confirmed; purge zero-grep re-run; 2 LOW non-blocking → 1 closure note + 1 backlog return) — handoff `2026-07-04T180947Z-qa-engineer-v0159-ship-gate` |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED**, zero findings; XSS posture **strictly improved** (three inline `style=` removed; no new inline script; `_CSP_SCRIPT_HASH_*` byte-frozen) — keyed to the pushed ref sha |
| CI (PR #108) | GitHub Actions | **35 checks, 0 failures** — merge gate `e6634996` |

## Drifts

### w2-runtime-btn-css-relocated-tokens-to-structure

**Description:** FR2 restyles `.runtime-btn` uniformly from tokens, and the Q3 grep harness
(`test_control_tokens.py`) delimits the "restyled control blocks" by an explicit selector allowlist
that **excludes token-definition files** (`tokens.py`) so that legitimate `--color-…: #hex` token
DEFINITIONS are not mis-flagged as ad-hoc literals. But the `.runtime-switcher` / `.runtime-btn` /
`.runtime-btn-icon` **component rules** (not the `--color-runtime-*` token defs) lived in `tokens.py`.
Left there, either the allowlist grep would skip the live `.runtime-btn` rule body (a hole in the
lock) or it would scan `tokens.py` and false-fail on the color token definitions.

**Resolution:** The `.runtime-*` **component** rules were relocated `tokens.py`→`structure.py` (both
in the W2 write set) so the allowlist (`.runtime-btn`) and the `tokens.py`-exclusion stay
self-consistent — the grep scans the real control rule body in `structure.py` while the
`--color-runtime-*` token DEFINITIONS + `[data-runtime]` theme overrides remain in `tokens.py`. This
is the FR2/Q3 self-consistency resolution. No HTML/selector renamed; the DOM-contract lock did not
move; `api-golden` byte-identical (only CSS relocated).

**Memory updates:** none required (an internal CSS-module boundary detail; `panel.md`'s
token-anchored-controls statement remains accurate — the controls are token-anchored regardless of
which CSS module hosts the rule).

### w3-header-wrap-is-structural-not-width-responsive

**Description:** FR3/AC-4 was written expecting the operator's "rows breaking onto two lines" to be a
**width-responsive** wrap — the RED width to be *pinned* to a viewport that forces the shared row to
overflow. W3's empirical measurement against the pre-fix tree found the wrap was **STRUCTURAL, not
width-responsive**: the pre-fix `.section-header` was `display:block`, so the `.runtime-switcher`
stacked **below** the title at **every** width, not just at a narrow one. The RED was genuine at both
1024px and 1440px (all 6 combos FAILED: e.g. `theme=warm @1024px` — `h2 bottom=155.7; runtime-switcher
y=155.7; header h=81.9`, switcher top == heading bottom = stacked).

**Resolution:** No "pinned wrap width" was needed — the RED was captured at every tested width because
the defect was unconditional. The fix is the token-anchored `.section-header:has(.runtime-switcher)
{display:flex; flex-wrap:nowrap; …}` single-line rule (scoped via `:has()` so the plain
title/description headers stay untouched); GREEN post-fix on all 6 combos. AC-4's language was
honored — the RED anchor is genuinely red (indeed *more* red than anticipated), documented on the
T-59-30 evidence line.

**Memory updates:** captured in `panel.md` (the shared `.section-header`+`.runtime-switcher` row lays
out on one line; the inline `style=` hacks removed; no row-wrap/overflow at 1024/1440px, enforced by
`header-row-width.spec.ts`).

### w5-response-guard-null-guards-a-missing-chip

**Description:** AC-9(e) sabotage (rename the live `.memory-chip` → `.memory-chip-SABOTAGED`, expecting
a guardrail to FAIL) revealed that `tests/e2e/panel/response-guard.spec.ts` does **not** catch a
dropped `.memory-chip` selector: at `response-guard.spec.ts:76-77` it null-guards a missing chip
(`const firstChip = await page.$('.memory-chip'); if (firstChip) { … }`) and degrades gracefully — the
tour still passes (2 passed) even with the chip dropped. What DID catch the sabotage was the FR1
**DOM-contract unit lock** (`test_index_dom_contract.py::test_memory_chip_present_with_populated_context`
FAILED, exit 1). This confirms by construction that the DOM-contract presence-invariant — not the
response-guard e2e — is the **real dropped-selector guardrail** for this release.

**Resolution:** No production change — the DOM-contract lock is the intended primary guardrail and it
fired correctly (this is precisely why FR1 lands FIRST, golden-first). The e2e null-guard is a
defence-in-depth gap, not a hole in the release's lock coverage. Filed as the QA LOW backlog return
`response-guard-chip-presence-hardening` (assert chip presence instead of null-guarding, as a second,
browser-level guard behind the DOM contract).

**Memory updates:** none (no product-behavior change; the guardrail posture is already captured by
`quality-assurance.md`'s note on the DOM-contract presence-invariant lock added this closure).

### w5-agents-css-coordinated-refactor-commit-sequencing

**Description:** FR6 Category B deletes `agents.py#AGENTS_CSS`, which is dead as *served* CSS but is a
**live Python symbol with three importers** (`views/assets/__init__.py`, `test_palette.py`,
`test_panel_css_contrast.py`). Deleting the module and editing an importer in separate steps would
leave an **intermediate tree that ImportErrors at pytest collection** (the module gone while an
importer still references `AGENTS_CSS`) — exactly the failure AC-9(f) sabotages. The obvious
sequencing (delete, then fix importers) is therefore invalid as an atomic unit.

**Resolution:** The delete + the three importer co-edits were **sequenced into a single atomic W5
commit** (the wave commit was amended to fold all four changes together) so that no committed tree
ever left `agents.py` deleted while an importer still imported `AGENTS_CSS`. The Python-import-aware
gate `grep -rn AGENTS_CSS dadaia_workspace/ tests/` == 0 was the acceptance; the full unpiped pytest
green (no collection ImportError) is the backstop. Recorded as a coordinated-refactor sequencing
note per PM Binding Ruling 1.

**Memory updates:** none (the AGENTS_CSS module was never served; its removal is a panel-internal CSS
cleanup captured in `panel.md`'s dead-CSS-purge statement).

### t-59-01-w0-marker-nit-fixed-at-ship

**Description:** The QA ship gate flagged a LOW, non-blocking marker-discipline nit on **T-59-01** (the
W0 definition task): its `[ ]/[-]/[x]` marker state was not fully reconciled to `[x]` at
definition-approval time, leaving a small human-auditable-trace inconsistency (the marker discipline
is traceability, not a gate check — no hook reads TASKS.md).

**Resolution:** The T-59-01 marker was reconciled to `[x]` at the ship commit (flipped alongside the
T-59-60 completion flip), so the TASKS.md trace is consistent at closure. No behavioral impact; QA
adjudicated it LOW and non-blocking.

**Memory updates:** none.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in `_archive/`.
Written this CLOSURE (phase = CLOSURE, MEMORY gate open). **No atom's `tldr`/`summary`/`area` changed
this closure** — both edited atoms are **body-only** edits (the visual/layout overhaul does not change
the panel's functional catalog description), so **no `catalog.json` / `index.md` regeneration is
triggered**. PE hand-edits neither `catalog.json` nor `index.md` (no shell).

- `specs/memory/product/panel/panel.md` — **primary edit; body-only, `tldr`/`summary` UNCHANGED (no
  catalog regen).** Recorded the v0.1.59 overhaul as current truth: the token-driven design system on
  `tokens.py` (14 additive token-named tokens; **no palette hex change** — 5-color canon + 3 themes +
  WCAG AA/AAA preserved), uniformly styled controls consumed from tokens (grep-gated by
  `test_control_tokens.py`), single-line header/control rows (all three inline `style=` hacks removed →
  token-anchored classes; `.section-header:has(.runtime-switcher)` single-line rule; no row-wrap at
  1024/1440px, enforced by `header-row-width.spec.ts`), `<header class="section-header">` landmarks +
  card density/elevation across the six tabs, theme-popover polish, and the two-category dead-CSS purge
  (8 dead `STRUCTURE_CSS` selector groups removed; the `agents.py#AGENTS_CSS` module deleted). **Fixed
  the S6 grill drift** — the memory card renders **FIVE** memory chips (Constitution, Architecture,
  Tech Stack, Quality, Product), not three. **Removed a stale line** — the panel-ux-fix-v1 "agent
  cards visual identity" sentence (the agent-card surface + its CSS were purged; no Agents tab exists).
  Confirmed the **6-tab nav**, **strict-CSP** (two inline sha256 hashes, `script-src 'self'`), and
  **read-only-telemetry** (per-call `mode=ro` factory) statements remain accurate — unchanged.
  `release_origin` → v0.1.59.
- `specs/memory/quality-assurance.md` — **body + `release_origin` only; `tldr`/`summary`/`area`
  UNCHANGED (no catalog regen).** Added the **intentional-restyle lock pattern** as design-of-record:
  for a release that deliberately restyles a rendered surface, lock the structure with a
  **presence-invariant contract test** (assert selectors present on the real render over populated
  fakes) that is **NEVER re-baselined** — it survives the restyle where a byte-golden would force a
  regeneration that defeats the lock — and freeze anything that must **not** move (e.g. CSP
  inline-script hashes) with an explicit **zero-touch equality lock**, which catches an
  edit-with-recompute that a `len==N`+recompute coverage check passes. `release_origin` → v0.1.59.
- `specs/memory/product/panel/brand-identity.md` — **no change (assessed).** Ruling E preserved the
  canonical 5-color palette and the CSS-token→palette mapping exactly; the 14 additive v0.1.59 tokens
  are non-palette semantic tokens (typography/spacing/elevation/radius) already captured in `panel.md`.
  Nothing in the palette atom is stale. `release_origin` stays v0.1.48.
- `specs/memory/architecture.md` — **no change for v0.1.59 (assessed).** The panel HTTP summary is a
  feature-level view; it enumerates the eight per-domain `api_*` view modules, not CSS-in-Python
  modules, so the `agents.py#AGENTS_CSS` deletion (a panel-internal CSS module) is not reflected there —
  no edit. **Flagged (unrelated, pre-existing):** line 63 states the `GET /api/kanban` endpoint +
  `views/kanban.py` "remain served", which **contradicts** `panel.md` (kanban chain DELETED in v0.1.52).
  A verification `grep -i kanban dadaia_workspace/features/panel/` returns **zero** matches ⇒ `panel.md`
  is correct and `architecture.md` is stale. This is a v0.1.52-era drift, unrelated to v0.1.59 scope —
  **not fixed here** (folding an unrelated correction would misattribute it to this UX release);
  surfaced for PM to route to a dedicated memory-correction. `release_origin` stays v0.1.58.
- `specs/memory/tech-stack.md` — **no change (assessed).** Ruling D added no dependency; `mistune~=3.0`
  stays the panel's only non-stdlib runtime dep. `release_origin` stays v0.1.58.
- `specs/memory/product/catalog.json` + `index.md` — **no hand-edit, no regen.** No atom's
  `tldr`/`summary`/`area` changed this closure (both edits are body-only), so no catalog regeneration
  is required.

## Dispositions

Disposition-sweep ledger. The sole consumed backlog anchor SURVIVES this release restyled in place
(`views/index.py#render_index` restyled; `tokens.py#TOKENS_CSS` rationalized — no dead anchor) →
archived **at CLOSURE** by the orchestrator `git mv`. No consumed anchor DIED this release, so there
was **no SHIP-time backlog archival**. No implementation-wave commit (W1–W6) staged any
`specs/backlog/**` (AC-11 verified). Bug ledger: **0 open** at pick, **0 open** after — no bug
consumed, none introduced.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/panel-ux-overhaul.md` → `specs/_archive/v0.1.59/consumed-backlog/` | backlog | `DELIVERED — v0.1.59` | this CLOSURE (FR1 design system + DOM-contract lock; FR2 controls restyle; FR3 single-line rows; FR4 layout/IA density; FR5 theme polish; FR6 two-category dead-CSS purge; FR7 e2e + evidence). Both intent anchors survive (restyled in place) → orchestrator `git mv` + `consumed_backlog.json` at CLOSURE |

## Backlog returns

One item discovered during implementation (W5 AC-9(e)), filed as `specs/backlog/<slug>.md`
(status `candidate`), routed through PM curation:

- `backlog/candidates.md` (LOW, QA/defence-in-depth) ← **`response-guard-chip-presence-hardening`** —
  the AC-9(e) sabotage proved `tests/e2e/panel/response-guard.spec.ts` **null-guards** a missing
  `.memory-chip` (line 76-77: `const firstChip = await page.$('.memory-chip'); if (firstChip) { … }`)
  and degrades gracefully, so it does **not** fail on a dropped chip. The FR1 DOM-contract unit lock is
  the real dropped-selector guardrail (and fired correctly). Harden the e2e to **assert chip presence**
  instead of null-guarding, as a second browser-level guard behind the DOM contract. Anchored at
  `tests/e2e/panel/response-guard.spec.ts`.

## Archive decision

**MOVE** — `specs/releases/v0.1.59/` will be moved to `specs/_archive/releases/v0.1.59/` via `git mv`
(by the orchestrator / devops-engineer; PE issues no git mutations), together with the CLOSURE-archived
consumed backlog entry → `specs/_archive/v0.1.59/consumed-backlog/` + `consumed_backlog.json`
(`DELIVERED — v0.1.59`). `specs/releases/ACTIVE.md` is then advanced by the orchestrator to the next
release (R12 "Capability tail" — `v0.1.60`) or `release: none` if the operator pauses. (PE does not
edit `ACTIVE.md` at this closure per the dispatch scope.)
