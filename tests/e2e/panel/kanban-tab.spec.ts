/**
 * kanban-tab.spec.ts — PW-KAN-01 through PW-KAN-05 (panel-kanban-v1 K-2)
 * Updated for T-016-P13: canonical §7 lifecycle columns.
 *
 * New column layout: Backlog | Release Definition | Implementation + Review | Closure
 *   backlog      → "Backlog"                (READ sessions)
 *   release_def  → "Release Definition"     (SPEC sessions)
 *   impl_review  → "Implementation + Review" (BOUND_IMPLEMENTATION + BOUND_REVIEW, combined)
 *   closure      → "Closure"               (present-but-empty; no session mode maps here yet)
 *
 * Tests: 5 Playwright board scenarios (AC-2.1 through AC-2.5)
 * Surface:
 *   AC-2.1 (PW-KAN-01): 2 BOUND_IMPLEMENTATION sessions from distinct contexts →
 *     4 columns visible; impl_review column has 2 cards with 2 distinct data-context.
 *   AC-2.2 (PW-KAN-02): 4 sessions, one per mode → correct column placement;
 *     BOUND_REVIEW and BOUND_IMPLEMENTATION share the impl_review column;
 *     session IDs match fixture.
 *   AC-2.3 (PW-KAN-03): XOR-lock dimming retired; impl_review column has card from
 *     BOUND_IMPLEMENTATION; no data-locked="true" present anywhere.
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

test('PW-KAN-01 (AC-2.1) — 2 BOUND_IMPLEMENTATION sessions from distinct contexts show 2 cards in impl_review column', async ({
  page,
}) => {
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-alpha',
        columns: {
          backlog:     [],
          release_def: [],
          impl_review: [makeCard('sess_alpha_impl', 'BOUND_IMPLEMENTATION', { runtime: 'claude-code' })],
          closure:     [],
        },
      },
      {
        context: 'ctx-beta',
        columns: {
          backlog:     [],
          release_def: [],
          impl_review: [makeCard('sess_beta_impl', 'BOUND_IMPLEMENTATION', { runtime: 'codex' })],
          closure:     [],
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
  // Note: BOUND_IMPLEMENTATION and BOUND_REVIEW both map to impl_review (combined column).
  // The payload here reflects the server-side grouping (both in impl_review).
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-main',
        columns: {
          backlog:     [makeCard('sess_read',   'READ')],
          release_def: [makeCard('sess_spec',   'SPEC')],
          impl_review: [
            makeCard('sess_impl',   'BOUND_IMPLEMENTATION'),
            makeCard('sess_review', 'BOUND_REVIEW'),
          ],
          closure:     [],
        },
      },
    ],
  };

  await loadKanbanTab(page, payload);

  // 1 swimlane.
  const laneCount = await page.$$eval('.kanban-lane', (els) => els.length);
  expect(laneCount).toBe(1);

  // closure column has 1 empty placeholder (3 other columns have cards).
  const placeholders = await page.$$eval(
    '[data-testid="kanban-empty-placeholder"]',
    (els) => els.length
  );
  expect(placeholders).toBe(1);

  // Total 4 cards (backlog: 1, release_def: 1, impl_review: 2, closure: 0).
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
// PW-KAN-03 (AC-2.3) — XOR-lock dimming retired; impl_review column has card
// ---------------------------------------------------------------------------

test('PW-KAN-03 (AC-2.3) — XOR-lock dimming retired; BOUND_IMPLEMENTATION card in impl_review column; no data-locked attribute anywhere', async ({
  page,
}) => {
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-combined',
        columns: {
          backlog:     [],
          release_def: [],
          impl_review: [makeCard('sess_impl_combined', 'BOUND_IMPLEMENTATION')],
          closure:     [],
        },
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

test('PW-KAN-04 (AC-2.4) — No session files (empty swimlane) → 4 empty-placeholder elements visible (§7 lifecycle columns)', async ({
  page,
}) => {
  // Simulate a context with no sessions: all columns empty.
  const payload = {
    generated_at: '2026-05-31T10:00:00Z',
    swimlanes: [
      {
        context: 'ctx-empty',
        columns: {
          backlog:     [],
          release_def: [],
          impl_review: [],
          closure:     [],
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
          backlog:     [staleCard],
          release_def: [],
          impl_review: [],
          closure:     [],
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
