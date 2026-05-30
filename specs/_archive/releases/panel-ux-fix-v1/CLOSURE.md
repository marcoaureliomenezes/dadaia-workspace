# Closure: Release — panel-ux-fix-v1

> **Status:** Aprovado
> **Release ID:** panel-ux-fix-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-30

## Summary

Esta release corrigiu 5 bugs UX/visual reportados no panel dadaia-workspace, estabelecendo identidade visual consistente em cards de agentes e páginas de memory, e eliminando a friction de autenticação Bearer para uso dev-local.

A tabela Sessions foi refatorada para usar `min-width` por célula via seletores CSS de classe (`.cell-session`, `.cell-project`, etc.) — abordagem correta sob `table-layout:fixed`, onde `min-width` em `<col>` é silenciosamente ignorado pelo algoritmo de layout. Codex sessions agora renderizam `PROJECT = '—'` com `<span class="cell-placeholder">` com contraste AA (5.52:1), em vez de colapsar a coluna inteira. O container recebeu `overflow-x: auto` garantindo h-scroll abaixo de 792px total.

O toggle Claude/Codex foi corrigido em todas as abas com `querySelectorAll` (antes `querySelector` conectava só o primeiro switcher). Memory pages e agent cards receberam identidade visual alinhada ao brand palette do panel (mint/sage/warm, tokens CSS canônicos, contraste WCAG AA em badges). O bypass de autenticação Bearer foi implementado para bind loopback (`127.0.0.1`): quando o panel inicia em loopback, `loopback_bypass=True` é passado via `make_handler_class()` e `GET /api/*` retorna 200 sem token — deliberate dev-local trade-off documentado; `POST` e mutações continuam exigindo autenticação. Esta mudança desbloqueia o endpoint `/api/kanban` planejado em `panel-kanban-v1` (R3).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-PUX-01 | Fix Sessions table column widths (per-cell min-width + Codex placeholder) | `3212e70` |
| T-PUX-02 | Fix Claude/Codex toggle — querySelectorAll on all tabs | (earlier commit, branch release/panel-ux-fix-v1) |
| T-PUX-03 | Memory pages visual identity — memory.css + /memory-view/ wrapper | (earlier commit, branch release/panel-ux-fix-v1) |
| T-PUX-04 | Agent cards visual identity — brand palette, WCAG AA status badges | (earlier commit, branch release/panel-ux-fix-v1) |
| T-PUX-05 | QA validation gate — APPROVED | `3212e70` |
| T-PUX-06 | Loopback no-token auth bypass — loopback_bypass flag in make_handler_class() | `3212e70` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Sessions table: 8 column headers visible, every `tr.session-row` has 8 `<td>` children | Playwright DOM assertion via `waitForSelector` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T144557Z-panel-ux-fix-v1-qa.html` |
| Codex sessions: PROJECT cell renders '—' (em-dash), not blank or 'None' | Playwright `.cell-placeholder` assertion | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T144557Z-panel-ux-fix-v1-qa.html` |
| Loopback auth bypass: GET /api/sessions with no Authorization → 200 on loopback_bypass=True handler | HTTP unit test — 19 handler tests green | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T144557Z-panel-ux-fix-v1-qa.html` |
| Loopback auth bypass: GET /api/sessions with no Authorization → 401 on loopback_bypass=False handler | HTTP unit test — 19 handler tests green | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T144557Z-panel-ux-fix-v1-qa.html` |
| Full Python test suite passes — no regressions | `pytest` | 1963 passed / 89.37% coverage — commit `3212e70` |
| 112 session unit tests green | `pytest tests/unit/features/panel/` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T144557Z-panel-ux-fix-v1-qa.html` |

## Drifts

### codex-fixture-not-seeded

**Description:** The Codex SQLite fixture seeding script (`tests/fixtures/telemetry/seed_codex_fixture.py`) was not actually seeded during QA. The Playwright Codex gate assertions were validated against real no-project rows (sessions without a project sub-slug) rather than the fixture helper.

**Resolution:** The placeholder behaviour was confirmed correct by the real data path: Codex sessions without a project context trigger the `cell-placeholder` rendering path. QA DOM assertions (8 columns visible, `cell-placeholder` '—' present) passed. No functional gap exists; the fixture seeding gap is a test hygiene item only.

**Memory updates:** None — the rendering behaviour is correctly captured in `specs/memory/product/panel.html` (sessions section updated to reflect per-cell min-width approach and Codex placeholder).

### horizontal-scroll-not-screenshotted

**Description:** The 600px horizontal-scroll assertion (table container overflows-x at 600px, does not collapse below 792px) was not captured as a Playwright screenshot. The `min-width` rules and `overflow-x: auto` are present in the served CSS, and the DOM assertion on column count passed, but no screenshot evidence at 600px viewport was produced.

**Resolution:** Non-blocking. The CSS rules are in production and the column min-width assertions at 900px viewport passed. An optional full visual pass at 600px is recommended before the eventual public release of dadaia-workspace.

**Memory updates:** None — `overflow-x: auto` on `.sessions-table-container` is documented in the updated `panel.html` memory atom.

## Memory updates

- `specs/memory/product/panel.html` — updated to reflect: (1) per-cell `min-width` CSS class selectors on Sessions table (`.cell-session` etc.) replacing the ineffective `<col>` percentage approach; (2) Codex `cell-placeholder` rendering for PROJECT column with muted styling and AA contrast; (3) loopback no-token auth bypass (`loopback_bypass` flag in `make_handler_class()`, detection at bind level not request level, startup warning, deliberate dev-local trade-off); (4) memory pages served with panel CSS identity via `/memory-view/` wrapper + `memory.css`; (5) agent cards updated to brand palette with WCAG AA badge contrast.
- `specs/memory/architecture.html` — updated bearer-only route description to reflect loopback bypass: `GET /api/*` returns 200 on loopback-bound panel without Bearer token (loopback_bypass=True); POST and mutating endpoints still require auth.
- `specs/memory/product/index.html` — `meta` updated to closure: panel-ux-fix-v1 / 2026-05-30. No catalog order changes.

## Backlog returns

- `backlog/candidates.md` ← **panel-kanban-v1 (R3) unblocked**: T-PUX-06 loopback bypass is now shipped; `/api/kanban` endpoint in panel-kanban-v1 may now be implemented without requiring Bearer tokens from local bot clients. Move to IMPLEMENTATION when ready.
- `backlog/ideas.md` ← Optional 600px h-scroll screenshot visual pass before public release of dadaia-workspace (non-blocking; CSS rules confirmed present, only screenshot evidence missing).
- `backlog/ideas.md` ← Codex SQLite fixture seeding hygiene: `tests/fixtures/telemetry/seed_codex_fixture.py` should be run in CI to seed deterministic Codex rows for QA Playwright gate (current gate uses real no-project rows as proxy).

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/panel-ux-fix-v1/` via `git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.

## Downstream note

**panel-kanban-v1 (R3)** was blocked on T-PUX-06. With this release archived, `panel-kanban-v1` may advance to IMPLEMENTATION. The loopback bypass allows any local process to call `GET /api/kanban` without a Bearer token — the deliberate trade-off accepted by the operator in this release extends to all GET endpoints on a loopback-bound panel, including future `/api/kanban`.
