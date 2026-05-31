/**
 * kanban-tab.spec.ts — PW-KAN-01 through PW-KAN-05 (panel-kanban-v1 K-2)
 *
 * Tests: 5 Playwright board scenarios (AC-2.1 through AC-2.5)
 * Surface:
 *   AC-2.1 (PW-KAN-01): 2 BOUND_IMPLEMENTATION sessions from distinct contexts →
 *     4 columns visible; implementation column has 2 cards with 2 distinct data-context.
 *   AC-2.2 (PW-KAN-02): 4 sessions, one per mode → each column exactly 1 card;
 *     session IDs match fixture.
 *   AC-2.3 (PW-KAN-03): Context with BOUND_IMPLEMENTATION session → review column
 *     has data-locked="true" + CSS class kanban-column--locked; 0 review cards.
 *   AC-2.4 (PW-KAN-04): No session files → 4 columns visible; each shows
 *     data-testid="kanban-empty-placeholder".
 *   AC-2.5 (PW-KAN-05): One stale session → card has data-stale="true".
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

const SCREENSHOTS_DIR = path.join(
  __dirname,
  '../../../../',
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

interface SessionCard {
  session_id: string;
  mode: string;
  release: string | null;
  runtime: string;
  pid: number;
  last_seen_at: string;
  is_stale: boolean;
}

function makeCard(
  sessionId: string,
  mode: string,
  opts: Partial<SessionCard> = {}
): SessionCard {
  return {
    session_id: sessionId,
    mode,
    release: opts.release ?? 'my-release-v1',
    runtime: opts.runtime ?? 'claude-code',
    pid: opts.pid ?? 12345,
    last_seen_at: opts.last_seen_at ?? '2026-05-31T10:00:00Z',
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

test('PW-KAN-01 (AC-2.1) — 2 BOUND_IMPLEMENTATION sessions from distinct contexts show 2 cards in implementation column', async ({
  page,
}) => {
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-alpha',
        columns: {
          research: [],
          spec: [],
          implementation: [makeCard('sess_alpha_impl', 'BOUND_IMPLEMENTATION', { runtime: 'claude-code' })],
          review: [],
        },
      },
      {
        context: 'ctx-beta',
        columns: {
          research: [],
          spec: [],
          implementation: [makeCard('sess_beta_impl', 'BOUND_IMPLEMENTATION', { runtime: 'codex' })],
          review: [],
        },
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // 2 swimlanes must be present.
  const laneCount = await page.$$eval('.kanban-lane', (els) => els.length);
  expect(laneCount).toBe(2);

  // 4 columns must be visible per lane (8 total).
  const colCount = await page.$$eval('.kanban-column', (els) => els.length);
  expect(colCount).toBe(8);

  // Implementation column cards: 2 cards total, from 2 distinct data-context values.
  // All cards in implementation columns (not locked ones) with non-empty data-context.
  const implCards = await page.$$eval(
    '.kanban-column:not(.kanban-column--locked) .kanban-card[data-context]',
    (cards) => cards.map((c) => c.getAttribute('data-context') ?? '')
  );
  // Filter to the 2 implementation cards: context values should be alpha and beta.
  const implContexts = implCards.filter((c) => c === 'ctx-alpha' || c === 'ctx-beta');
  expect(new Set(implContexts).size).toBe(2);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'pw-kan-01-two-impl-sessions.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// PW-KAN-02 (AC-2.2) — 4 sessions, one per mode, each column exactly 1 card
// ---------------------------------------------------------------------------

test('PW-KAN-02 (AC-2.2) — 4 sessions one-per-mode → each column exactly 1 card; session IDs match fixture', async ({
  page,
}) => {
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-main',
        columns: {
          research:       [makeCard('sess_read',   'READ')],
          spec:           [makeCard('sess_spec',   'SPEC')],
          implementation: [makeCard('sess_impl',   'BOUND_IMPLEMENTATION')],
          review:         [makeCard('sess_review', 'BOUND_REVIEW')],
        },
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // 1 swimlane.
  const laneCount = await page.$$eval('.kanban-lane', (els) => els.length);
  expect(laneCount).toBe(1);

  // Each column has exactly 1 card (no empty placeholders).
  const placeholders = await page.$$eval(
    '[data-testid="kanban-empty-placeholder"]',
    (els) => els.length
  );
  expect(placeholders).toBe(0);

  // Total 4 cards.
  const totalCards = await page.$$eval('.kanban-card', (els) => els.length);
  expect(totalCards).toBe(4);

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
// PW-KAN-03 (AC-2.3) — BOUND_IMPLEMENTATION → review column locked
// ---------------------------------------------------------------------------

test('PW-KAN-03 (AC-2.3) — BOUND_IMPLEMENTATION session causes review column to have data-locked="true" and kanban-column--locked', async ({
  page,
}) => {
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-locked',
        columns: {
          research:       [],
          spec:           [],
          implementation: [makeCard('sess_impl_lock', 'BOUND_IMPLEMENTATION')],
          review:         [],
        },
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // Review column must have data-locked="true".
  const reviewLockedAttr = await page.getAttribute(
    '[data-locked="true"]',
    'data-locked'
  );
  expect(reviewLockedAttr).toBe('true');

  // Review column must have class kanban-column--locked.
  const reviewHasLockedClass = await page.evaluate(() => {
    const cols = document.querySelectorAll('[data-locked="true"]');
    return Array.from(cols).some((col) => col.classList.contains('kanban-column--locked'));
  });
  expect(reviewHasLockedClass).toBe(true);

  // No review cards (review column is empty but has locked state).
  const reviewCards = await page.$$eval(
    '[data-locked="true"] .kanban-card',
    (cards) => cards.length
  );
  expect(reviewCards).toBe(0);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'pw-kan-03-review-locked.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// PW-KAN-04 (AC-2.4) — No session files → 4 columns visible, each empty
// ---------------------------------------------------------------------------

test('PW-KAN-04 (AC-2.4) — No session files (empty swimlane) → 4 empty-placeholder elements visible', async ({
  page,
}) => {
  // Simulate a context with no sessions: all columns empty.
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-empty',
        columns: {
          research:       [],
          spec:           [],
          implementation: [],
          review:         [],
        },
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // 4 empty-placeholder elements (one per column).
  const placeholders = await page.$$eval(
    '[data-testid="kanban-empty-placeholder"]',
    (els) => els.length
  );
  expect(placeholders).toBe(4);

  // 4 columns visible.
  const colCount = await page.$$eval('.kanban-column', (els) => els.length);
  expect(colCount).toBe(4);

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
// PW-KAN-05 (AC-2.5) — Stale session → card has data-stale="true"
// ---------------------------------------------------------------------------

test('PW-KAN-05 (AC-2.5) — Stale session → card has data-stale="true"', async ({
  page,
}) => {
  const staleCard = makeCard('sess_stale', 'READ', {
    is_stale: true,
    last_seen_at: '2026-05-31T08:00:00Z',
  });

  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-stale',
        columns: {
          research:       [staleCard],
          spec:           [],
          implementation: [],
          review:         [],
        },
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
