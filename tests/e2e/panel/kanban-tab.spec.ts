/**
 * kanban-tab.spec.ts — PW-KAN-01 through PW-KAN-05 (panel-kanban-v1 K-2)
 * Updated for kanban-v2 (lifecycle-truth board, ab859c7 operator live-review
 * round 2). Backend contract: dadaia_workspace/features/panel/views/kanban.py.
 *
 * kanban-v2 column layout (the Backlog column is RETIRED):
 *   release_def  → "Release Definition"      (SPEC sessions; release card in DEFINITION/SPEC/PLAN)
 *   impl_review  → "Implementation + Review" (BOUND_IMPLEMENTATION + BOUND_REVIEW, combined)
 *   closure      → "Closure"                 (release card in CLOSURE)
 *   observers    → "Observers" strip         (live READ sessions — NOT a column;
 *                                             rendered below the columns, only when non-empty)
 * Stale-and-dead sessions are dropped by the backend and never become cards;
 * the FE keeps the per-card data-stale indicator pathway for is_stale flags.
 *
 * Tests: 5 Playwright board scenarios (AC-2.1 through AC-2.5)
 * Surface:
 *   AC-2.1 (PW-KAN-01): 2 BOUND_IMPLEMENTATION sessions from distinct contexts →
 *     3 columns per lane (6 total); impl_review has 2 cards with 2 distinct data-context.
 *   AC-2.2 (PW-KAN-02): 4 sessions, one per mode → correct placement; READ lands in
 *     the Observers strip; BOUND_REVIEW + BOUND_IMPLEMENTATION share impl_review;
 *     session IDs match fixture.
 *   AC-2.3 (PW-KAN-03): XOR-lock dimming retired; impl_review column has card from
 *     BOUND_IMPLEMENTATION; no data-locked="true" present anywhere.
 *   AC-2.4 (PW-KAN-04): Idle lane → 3 columns visible, each with an
 *     empty-placeholder, plus the "No active release or live sessions" lane message.
 *   AC-2.5 (PW-KAN-05): is_stale-flagged card (Observers strip) renders
 *     data-stale="true" — the FE stale-indicator pathway is preserved.
 *
 * Live FE mode (mirrors test_panel_sessions_tab.spec.ts pattern):
 *   1. Navigate to the panel origin (http://127.0.0.1:4999).
 *   2. Use page.route() to serve a crafted HTML page that hosts the real
 *      kanban section HTML and loads the real kanban.js from the filesystem.
 *   3. Mock /api/kanban with deterministic fixture payloads.
 *
 * Evidence screenshots → .dadaia/tmp/qa-engineer/panel-kanban-v1/
 *
 * Deterministic selectors only — NO waitForTimeout / time.sleep (CI grep gate).
 */

import { test, expect, type Page, type Route } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { BASE_URL, PANEL_TOKEN } from './helpers';

// Workspace-root .dadaia/tmp (mandated landing zone): five levels up from
// tests/e2e/panel/ → repos/dadaia-workspace → repos → <workspace-root>.
const SCREENSHOTS_DIR = path.join(
  __dirname,
  '../../../../../',
  '.dadaia/tmp/qa-engineer/panel-kanban-v1'
);

const JS_ASSETS_DIR = path.join(
  __dirname,
  '../../../dadaia_workspace/features/panel/views/assets/js'
);

// ---------------------------------------------------------------------------
// Ensure screenshots directory exists
// ---------------------------------------------------------------------------

if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

// ---------------------------------------------------------------------------
// Kanban section HTML scaffold
//
// Minimal scaffold that hosts the kanban board section and loads kanban.js.
// window.authedFetch is provided by core.js (loaded from the live panel).
// ---------------------------------------------------------------------------

function buildKanbanPageHtml(): string {
  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>dadaia panel — Kanban (live FE e2e scaffold)</title>
  <style>
    body { font-family: sans-serif; margin: 0; }
    .section { display: none; }
    .section.active { display: block; }
    .kanban-column--locked { opacity: 0.40; }
  </style>
</head>
<body>
  <nav class="nav-tabs" aria-label="Panel sections" role="tablist">
    <button class="nav-tab active" data-section="kanban" aria-selected="true"
            role="tab" id="tab-kanban">Kanban</button>
  </nav>
  <main class="main" role="main">
    <section id="section-kanban" class="section panel-section active"
             role="tabpanel" tabindex="0" aria-labelledby="tab-kanban">
      <header class="section-header">
        <h2>Kanban</h2>
        <span id="kanban-last-updated" aria-live="polite"></span>
      </header>
      <div id="kanban-board" class="kanban-board" aria-label="Kanban board" aria-live="polite">
      </div>
    </section>
  </main>
  <!-- core.js: provides window.authedFetch (served live at /static/core.js) -->
  <script src="/static/core.js"></script>
  <!-- kanban.js: intercepted from filesystem via page.route -->
  <script src="/static/kanban.js"></script>
</body>
</html>`;
}

// ---------------------------------------------------------------------------
// Session card fixture factory
// ---------------------------------------------------------------------------

// kanban-v2 session Card shape (views/kanban.py response schema). is_stale is
// not emitted by the v2 backend (stale sessions are dropped) but the FE retains
// the indicator pathway — PW-KAN-05 exercises it explicitly.
interface SessionCard {
  card_kind: 'session';
  session_id: string;
  mode: string;
  release: string | null;
  started_at: string | null;
  last_seen_at: string | null;
  age_seconds: number | null;
  is_stale?: boolean;
}

function makeCard(
  sessionId: string,
  mode: string,
  opts: Partial<SessionCard> = {}
): SessionCard {
  return {
    card_kind: 'session',
    session_id: sessionId,
    mode,
    release: opts.release ?? 'my-release-v1',
    started_at: opts.started_at ?? '2026-05-31T09:00:00Z',
    last_seen_at: opts.last_seen_at ?? '2026-05-31T10:00:00Z',
    age_seconds: opts.age_seconds ?? 120,
    is_stale: opts.is_stale ?? false,
  };
}

// ---------------------------------------------------------------------------
// Route installer
//
// Intercepts:
//   "/" — serves the crafted Kanban page HTML.
//   "/static/kanban.js" — served from filesystem.
//   "/api/kanban" — returns the fixture payload.
// ---------------------------------------------------------------------------

async function installKanbanRoutes(
  page: Page,
  kanbanPayload: object
): Promise<void> {
  const kanbanJsContent = fs.readFileSync(
    path.join(JS_ASSETS_DIR, 'kanban.js'),
    'utf-8'
  );

  const pageHtml = buildKanbanPageHtml();

  // 1. Panel root — serve the crafted page.
  await page.route(
    (url) => {
      const pathname = new URL(url).pathname;
      return pathname === '/' || pathname === '';
    },
    (route: Route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/html; charset=utf-8',
        body: pageHtml,
      });
    }
  );

  // 2. kanban.js — serve from filesystem.
  await page.route('**/static/kanban.js', (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: kanbanJsContent,
    });
  });

  // 3. /api/kanban — deterministic fixture payload.
  await page.route('**/api/kanban', (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify(kanbanPayload),
    });
  });
}

// ---------------------------------------------------------------------------
// Bootstrap: install routes, seed token, navigate, wait for board to render.
//
// We wait for at least one .kanban-lane or .kanban-board-empty to appear,
// which signals that kanban.js has fetched /api/kanban and rendered the board.
// ---------------------------------------------------------------------------

async function loadKanbanTab(page: Page, payload: object): Promise<void> {
  await installKanbanRoutes(page, payload);

  await page.goto(`${BASE_URL}/?token=${encodeURIComponent(PANEL_TOKEN)}`, {
    waitUntil: 'domcontentloaded',
  });

  // Wait for the board to render: either a lane or an empty-board message.
  await page.waitForSelector(
    '#kanban-board .kanban-lane, #kanban-board .kanban-board-empty',
    { timeout: 15_000 }
  );
}

// ---------------------------------------------------------------------------
// PW-KAN-01 (AC-2.1) — 2 BOUND_IMPLEMENTATION sessions from distinct contexts
// ---------------------------------------------------------------------------

test('PW-KAN-01 (AC-2.1) — 2 BOUND_IMPLEMENTATION sessions from distinct contexts show 2 cards in impl_review column', async ({
  page,
}) => {
  const payload = {
    schema: 'kanban-v2',
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-alpha',
        columns: {
          release_def: [],
          impl_review: [makeCard('sess_alpha_impl', 'BOUND_IMPLEMENTATION')],
          closure:     [],
        },
        observers: [],
      },
      {
        context: 'ctx-beta',
        columns: {
          release_def: [],
          impl_review: [makeCard('sess_beta_impl', 'BOUND_IMPLEMENTATION')],
          closure:     [],
        },
        observers: [],
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // 2 swimlanes must be present.
  const laneCount = await page.$$eval('.kanban-lane', (els) => els.length);
  expect(laneCount).toBe(2);

  // 3 lifecycle columns per lane (6 total) — Backlog is retired in kanban-v2.
  const colCount = await page.$$eval('.kanban-column', (els) => els.length);
  expect(colCount).toBe(6);

  // impl_review column cards: 2 cards total, from 2 distinct data-context values.
  // No XOR-lock dimming — all kanban-card elements are equally accessible.
  const allCards = await page.$$eval(
    '.kanban-card[data-context]',
    (cards) => cards.map((c) => c.getAttribute('data-context') ?? '')
  );
  // Filter to the 2 impl cards: context values should be alpha and beta.
  const implContexts = allCards.filter((c) => c === 'ctx-alpha' || c === 'ctx-beta');
  expect(new Set(implContexts).size).toBe(2);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'pw-kan-01-two-impl-sessions.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// PW-KAN-02 (AC-2.2) — 4 sessions across §7 lifecycle columns
// ---------------------------------------------------------------------------

test('PW-KAN-02 (AC-2.2) — 4 sessions across §7 lifecycle columns; BOUND_REVIEW and BOUND_IMPLEMENTATION share impl_review; session IDs match fixture', async ({
  page,
}) => {
  // Note: BOUND_IMPLEMENTATION and BOUND_REVIEW both map to impl_review (combined
  // column). READ sessions are routed to the Observers strip in kanban-v2 (the
  // Backlog column is retired). The payload reflects the server-side grouping.
  const payload = {
    schema: 'kanban-v2',
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-main',
        columns: {
          release_def: [makeCard('sess_spec',   'SPEC')],
          impl_review: [
            makeCard('sess_impl',   'BOUND_IMPLEMENTATION'),
            makeCard('sess_review', 'BOUND_REVIEW'),
          ],
          closure:     [],
        },
        observers: [makeCard('sess_read', 'READ')],
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // 1 swimlane.
  const laneCount = await page.$$eval('.kanban-lane', (els) => els.length);
  expect(laneCount).toBe(1);

  // closure column has 1 empty placeholder (the 2 other columns have cards).
  const placeholders = await page.$$eval(
    '[data-testid="kanban-empty-placeholder"]',
    (els) => els.length
  );
  expect(placeholders).toBe(1);

  // Total 4 cards (release_def: 1, impl_review: 2, closure: 0, observers: 1).
  const totalCards = await page.$$eval('.kanban-card', (els) => els.length);
  expect(totalCards).toBe(4);

  // The READ session must render inside the Observers strip, not a column.
  const observerIds = await page.$$eval(
    '.kanban-observers .kanban-card',
    (els) => els.map((el) => el.textContent ?? '')
  );
  expect(observerIds.length).toBe(1);
  expect(observerIds[0]).toContain('sess_read');

  // Session IDs must appear somewhere in the board.
  const boardText = await page.textContent('#kanban-board');
  expect(boardText).toContain('sess_read');
  expect(boardText).toContain('sess_spec');
  expect(boardText).toContain('sess_impl');
  expect(boardText).toContain('sess_review');

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'pw-kan-02-four-modes.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// PW-KAN-03 (AC-2.3) — XOR-lock dimming retired; impl_review column has card
// ---------------------------------------------------------------------------

test('PW-KAN-03 (AC-2.3) — XOR-lock dimming retired; BOUND_IMPLEMENTATION card in impl_review column; no data-locked attribute anywhere', async ({
  page,
}) => {
  const payload = {
    schema: 'kanban-v2',
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-combined',
        columns: {
          release_def: [],
          impl_review: [makeCard('sess_impl_combined', 'BOUND_IMPLEMENTATION')],
          closure:     [],
        },
        observers: [],
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // XOR-lock dimming is retired: no column should have data-locked="true".
  const lockedCount = await page.$$eval('[data-locked="true"]', (els) => els.length);
  expect(lockedCount).toBe(0);

  // No locked CSS class anywhere.
  const lockedClassCount = await page.$$eval('.kanban-column--locked', (els) => els.length);
  expect(lockedClassCount).toBe(0);

  // The impl_review card must be present.
  const allCards = await page.$$eval('.kanban-card', (els) => els.length);
  expect(allCards).toBe(1);

  // Session ID appears in the board.
  const boardText = await page.textContent('#kanban-board');
  expect(boardText).toContain('sess_impl_combined');

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'pw-kan-03-no-xor-lock.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// PW-KAN-04 (AC-2.4) — No session files → 4 columns visible, each empty
// ---------------------------------------------------------------------------

test('PW-KAN-04 (AC-2.4) — No session files (empty swimlane) → 3 empty-placeholder elements visible (§7 lifecycle columns)', async ({
  page,
}) => {
  // Simulate an idle context: no release card, no sessions, no observers.
  const payload = {
    schema: 'kanban-v2',
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-empty',
        columns: {
          release_def: [],
          impl_review: [],
          closure:     [],
        },
        observers: [],
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // 3 empty-placeholder elements (one per kanban-v2 lifecycle column).
  const placeholders = await page.$$eval(
    '[data-testid="kanban-empty-placeholder"]',
    (els) => els.length
  );
  expect(placeholders).toBe(3);

  // 3 columns visible (Backlog retired in kanban-v2).
  const colCount = await page.$$eval('.kanban-column', (els) => els.length);
  expect(colCount).toBe(3);

  // The idle-lane message must be shown.
  const emptyMsg = await page.textContent('.kanban-lane-empty');
  expect(emptyMsg).toContain('No active release or live sessions');

  // No cards.
  const cardCount = await page.$$eval('.kanban-card', (els) => els.length);
  expect(cardCount).toBe(0);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'pw-kan-04-empty-board.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// PW-KAN-04-empty-board variant — /api/kanban returns no swimlanes
// ---------------------------------------------------------------------------

test('PW-KAN-04-variant — /api/kanban empty swimlanes → "No Spec Context Projects available"', async ({
  page,
}) => {
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [],
  };

  await loadKanbanTab(page, payload);

  // Empty-board message must appear.
  await page.waitForSelector('.kanban-board-empty', { timeout: 10_000 });
  const emptyText = await page.textContent('.kanban-board-empty');
  expect(emptyText).toContain('No Spec Context Projects available');

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'pw-kan-04-no-swimlanes.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// PW-KAN-05 (AC-2.5) — is_stale-flagged card renders data-stale="true"
//
// kanban-v2 backend drops stale-and-dead sessions entirely (they never become
// cards), but the FE retains the per-card data-stale indicator pathway for an
// is_stale flag. This test pins that FE contract: a READ card flagged is_stale
// (Observers strip) must render data-stale="true".
// ---------------------------------------------------------------------------

test('PW-KAN-05 (AC-2.5) — Stale-flagged session card renders data-stale="true" (FE indicator pathway)', async ({
  page,
}) => {
  const staleCard = makeCard('sess_stale', 'READ', {
    is_stale: true,
    last_seen_at: '2026-05-31T08:00:00Z',
    age_seconds: 7200,
  });

  const payload = {
    schema: 'kanban-v2',
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-stale',
        columns: {
          release_def: [],
          impl_review: [],
          closure:     [],
        },
        observers: [staleCard],
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // The stale card must exist with data-stale="true".
  await page.waitForSelector('.kanban-card[data-stale="true"]', { timeout: 10_000 });

  const staleAttr = await page.getAttribute('.kanban-card[data-stale="true"]', 'data-stale');
  expect(staleAttr).toBe('true');

  // Verify the session id appears in the board.
  const boardText = await page.textContent('#kanban-board');
  expect(boardText).toContain('sess_stale');

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'pw-kan-05-stale-card.png'),
    fullPage: false,
  });
});
