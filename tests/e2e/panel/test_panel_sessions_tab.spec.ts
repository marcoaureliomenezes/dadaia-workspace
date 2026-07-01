/**
 * Browser journeys for the Sessions tab.
 *
 * Surface:
 *   E2E-SES-01..05: Sessions tab — table population, drawer detail,
 *     sort by Cost, "Last updated" badge ticking, auto-refresh suspension.
 *
 * v0.1.45 panel redesign note: the runtime switcher (claude/codex toggle) and the
 * Agentic tab that hosted the agents/workflows grids were removed. The former
 * E2E-RT-01..04 / E2E-COD-01 runtime-switcher matrix tests and their multi-tab
 * scaffolds were deleted with that feature.
 *
 * Live FE mode:
 *   Each test isolates the browser journey from dev-server asset timing:
 *     1. Navigates to the REAL panel origin so page.route() intercepts have a
 *        concrete origin for relative URL resolution.
 *     2. Uses page.route() to intercept the panel root ("/") and serve a crafted
 *        HTML page that embeds the REAL sessions section HTML (generated from
 *        render_sessions_section() via a helper constant) and loads the REAL
 *        sessions.js via a <script> tag that is intercepted from the filesystem.
 *     3. Mocks /api/sessions* with deterministic fixture payloads.
 *
 *   This drives the REAL views/sessions.py DOM contract and REAL sessions.js logic —
 *   the only synthetic element is the surrounding minimal HTML scaffold.
 *
 * Coverage: sessions list/detail, refresh timing, and auto-refresh suspension.
 */

import { test, expect, type Page, type Route } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { BASE_URL, PANEL_TOKEN } from './helpers';

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const JS_ASSETS_DIR = path.join(
  __dirname,
  '../../../dadaia_workspace/features/panel/views/assets/js'
);

// ---------------------------------------------------------------------------
// Real sessions section HTML — generated from render_sessions_section().
//
// This is the canonical DOM contract produced by the real Python view function
// (dadaia_workspace/features/panel/views/sessions.py). When sessions.py changes,
// regenerate this fixture so the browser harness stays aligned with the view.
//
// To regenerate:
//   python -c "from dadaia_workspace.features.panel.views.sessions \
//              import render_sessions_section; print(render_sessions_section())"
// ---------------------------------------------------------------------------
const REAL_SESSIONS_SECTION_HTML = `<section id="section-sessions" class="section panel-section active" role="tabpanel" tabindex="0" aria-labelledby="tab-sessions">
  <header class="section-header">
    <h2>Sessions</h2>
    <p class="section-meta" id="sessions-meta" aria-live="polite"></p>
  </header>
  <div class="sessions-toolbar">
    <label for="sessions-filter" class="sr-only">Filter sessions</label>
    <input id="sessions-filter" type="text" class="sessions-filter-input"
           placeholder="filter by project or session id"
           autocomplete="off" spellcheck="false"
           aria-label="Filter sessions by project or session id" />
    <span id="sessions-last-updated" class="sessions-last-updated"
          aria-live="polite" data-testid="sessions-last-updated">Never</span>
  </div>
  <div id="sessions-banner" class="sessions-banner"
       role="status" aria-live="polite" hidden></div>
  <div id="sessions-table-container" class="sessions-table-container"
       aria-busy="true">
    <table class="sessions-table" aria-label="Sessions">
      <thead>
        <tr>
          <th scope="col" data-sort-key="session_id">Session</th>
          <th scope="col" data-sort-key="project">Project</th>
          <th scope="col" data-sort-key="model">Model</th>
          <th scope="col" data-sort-key="message_count">AI Turns</th>
          <th scope="col" data-sort-key="context_size_tokens">Context</th>
          <th scope="col" data-sort-key="cumulative_cost_usd"
              data-sort="cost" data-sort-dir="none">Cost</th>
          <th scope="col" data-sort-key="last_activity_at">Last activity</th>
          <th scope="col" data-sort-key="status">Status</th>
        </tr>
      </thead>
      <tbody id="sessions-tbody">
      </tbody>
    </table>
  </div>
  <aside id="session-drawer" class="session-drawer" hidden
         role="dialog" aria-modal="true"
         aria-label="Session detail">
    <div class="session-drawer__header">
      <h3 class="session-drawer__title" id="session-drawer-title">Session detail</h3>
      <button type="button" id="drawer-close"
              class="session-drawer__close-btn"
              aria-label="Close session detail">Close</button>
    </div>
    <div class="session-drawer__content">
      <!-- Populated by JS after /api/sessions/<runtime>/<id> fetch -->
    </div>
  </aside>
</section>`;

// ---------------------------------------------------------------------------
// Full panel page HTML — minimal shell that hosts the real sessions section
// and loads the real JS modules (core.js for authedFetch, sessions.js).
//
// core.js is served by the live panel at /static/core.js.
// sessions.js is intercepted from the filesystem so the test uses the checked
// out asset even when another panel process is already running.
//
// The token bootstrap in core.js reads from sessionStorage ('panel_token');
// we seed that via page.addInitScript before navigation so authedFetch works.
// ---------------------------------------------------------------------------
function buildPanelPageHtml(sessionsSection: string): string {
  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>dadaia panel — Sessions (live FE e2e scaffold)</title>
  <style>
    /* Minimal structural styles so sessions.js can find its landmarks */
    body { font-family: sans-serif; margin: 0; }
    .section { display: none; }
    .section.active { display: block; }
    .session-drawer { display: none; }
    .session-drawer:not([hidden]).open { display: block; }
  </style>
</head>
<body>
  <nav class="nav-tabs" aria-label="Panel sections" role="tablist">
    <button class="nav-tab" data-section="sessions" aria-selected="true"
            role="tab" id="tab-sessions">Sessions</button>
  </nav>
  <main class="main" role="main">
    ${sessionsSection}
  </main>
  <!-- core.js: provides window.authedFetch (served live at /static/core.js) -->
  <script src="/static/core.js"></script>
  <!-- sessions.js: intercepted from filesystem via page.route -->
  <script src="/static/sessions.js" defer></script>
</body>
</html>`;
}

// ---------------------------------------------------------------------------
// Mock fixture data — mirrors sessions_seeded.sqlite shape (FR3 contract).
// Source of truth: tests/integration/test_panel_sessions_endpoint.py
// ---------------------------------------------------------------------------

const MOCK_SESSION_ID_1 = 'claude-session-aaa111bbb222ccc3';
const MOCK_SESSION_ID_2 = 'claude-session-ddd444eee555fff6';
const MOCK_SESSION_ID_3 = 'claude-session-ggg777hhh888iii9';

/** Three Claude sessions: active (cost $0.45), idle (cost $1.20), ended (cost $0.08). */
const MOCK_SESSIONS_LIST = {
  generated_at: '2026-05-19T18:00:00+00:00',
  runtime: 'claude',
  project: null,
  limit: 50,
  total_count: 3,
  sessions: [
    {
      session_id: MOCK_SESSION_ID_1,
      runtime: 'claude',
      project: 'dadaia-workspace',
      cwd: '/home/user/workspace/dadaia/repos/dadaia-workspace',
      model: 'claude-sonnet-4-6',
      started_at: '2026-05-19T10:00:00+00:00',
      last_activity_at: '2026-05-19T17:55:00+00:00',
      message_count: 42,
      context_size_tokens: 38000,
      cumulative_cost_usd: 0.45,
      cost_known: true,
      status: 'active',
      agent_name: 'qa-engineer',
      ai_title: 'E2E spec authoring for panel-r5-v1',
    },
    {
      session_id: MOCK_SESSION_ID_2,
      runtime: 'claude',
      project: 'example-game',
      cwd: '/home/user/workspace/dadaia/repos/example-game',
      model: 'claude-opus-4-7',
      started_at: '2026-05-19T08:00:00+00:00',
      last_activity_at: '2026-05-19T12:30:00+00:00',
      message_count: 18,
      context_size_tokens: 12000,
      cumulative_cost_usd: 1.20,
      cost_known: true,
      status: 'idle',
      agent_name: 'product-engineer',
      ai_title: null,
    },
    {
      session_id: MOCK_SESSION_ID_3,
      runtime: 'claude',
      project: 'dadaia-workspace',
      cwd: '/home/user/workspace/dadaia',
      model: 'claude-sonnet-4-6',
      started_at: '2026-05-18T20:00:00+00:00',
      last_activity_at: '2026-05-18T22:00:00+00:00',
      message_count: 7,
      context_size_tokens: 5000,
      cumulative_cost_usd: 0.08,
      cost_known: true,
      status: 'ended',
      agent_name: 'software-engineer',
      ai_title: 'Backfill telemetry implementation',
    },
  ],
};

/** Full SessionDetail for the first session — adds event_timestamps. */
const MOCK_SESSION_DETAIL = {
  session_id: MOCK_SESSION_ID_1,
  runtime: 'claude',
  project: 'dadaia-workspace',
  cwd: '/home/user/workspace/dadaia/repos/dadaia-workspace',
  model: 'claude-sonnet-4-6',
  started_at: '2026-05-19T10:00:00+00:00',
  last_activity_at: '2026-05-19T17:55:00+00:00',
  message_count: 42,
  context_size_tokens: 38000,
  cumulative_cost_usd: 0.45,
  cost_known: true,
  status: 'active',
  agent_name: 'qa-engineer',
  ai_title: 'E2E spec authoring for panel-r5-v1',
  event_timestamps: [
    '2026-05-19T10:00:00+00:00',
    '2026-05-19T12:00:00+00:00',
    '2026-05-19T15:00:00+00:00',
    '2026-05-19T17:55:00+00:00',
  ],
};

// ---------------------------------------------------------------------------
// Route interceptors
//
// Three interception layers are installed before any navigation:
//   1. Panel root ("/") — serves the crafted page with real sessions HTML.
//   2. "/static/sessions.js" — serves the real sessions.js from the filesystem
//      (handles the case where the running panel instance has older assets).
//   3. "/api/sessions*" — returns deterministic mock payloads so the test is
//      hermetic and does not depend on live telemetry data.
//
// All interceptors must be installed BEFORE page.goto().
// ---------------------------------------------------------------------------

async function installLiveFERoutes(page: Page): Promise<void> {
  const sessionsJsContent = fs.readFileSync(
    path.join(JS_ASSETS_DIR, 'sessions.js'),
    'utf-8'
  );

  const panelPageHtml = buildPanelPageHtml(REAL_SESSIONS_SECTION_HTML);

  // 1. Panel root — serve the crafted live-FE page.
  await page.route(
    (url) => {
      const pathname = new URL(url).pathname;
      return pathname === '/' || pathname === '';
    },
    (route: Route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/html; charset=utf-8',
        body: panelPageHtml,
      });
    }
  );

  // 2. sessions.js — serve from filesystem.
  await page.route('**/static/sessions.js', (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: sessionsJsContent,
    });
  });

  // 3. /api/sessions* — deterministic mock payloads.
  await page.route(
    /\/api\/sessions/,
    (route: Route, request) => {
      const url = new URL(request.url());
      const pathParts = url.pathname.split('/').filter(Boolean);
      // /api/sessions/<runtime>/<session_id> → pathParts length ≥ 4
      if (
        pathParts.length >= 4
        && pathParts[0] === 'api'
        && pathParts[1] === 'sessions'
      ) {
        const runtime = decodeURIComponent(pathParts[2]);
        const sessionId = decodeURIComponent(pathParts[3]);
        if (runtime === 'claude' && sessionId === MOCK_SESSION_ID_1) {
          route.fulfill({
            status: 200,
            contentType: 'application/json; charset=utf-8',
            body: JSON.stringify(MOCK_SESSION_DETAIL),
          });
        } else {
          route.fulfill({
            status: 404,
            contentType: 'application/json; charset=utf-8',
            body: JSON.stringify({ error: 'not_found', message: 'Session not found.' }),
          });
        }
        return;
      }
      // /api/sessions (list)
      route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: JSON.stringify(MOCK_SESSIONS_LIST),
      });
    }
  );
}

// ---------------------------------------------------------------------------
// Bootstrap: install routes, seed token, navigate, wait for sessions to load.
//
// Token seeding strategy:
//   core.js reads the token from sessionStorage('panel_token').
//   The URL ?token=<value> is consumed by core.js on first load; since we
//   intercept the root route, core.js still runs and picks up the token from
//   the URL query-param before stripping it.
// ---------------------------------------------------------------------------

async function loadLiveSessionsTab(page: Page): Promise<void> {
  await installLiveFERoutes(page);

  // Navigate with the token in the URL so core.js can bootstrap sessionStorage.
  await page.goto(`${BASE_URL}/?token=${encodeURIComponent(PANEL_TOKEN)}`, {
    waitUntil: 'domcontentloaded',
  });

  // Wait for the initial sessions fetch to complete (aria-busy flips to false).
  await page.waitForSelector('#sessions-table-container[aria-busy="false"]', {
    timeout: 15_000,
  });
}

// ---------------------------------------------------------------------------
// E2E-SES-01 (a) — Sessions tab populates from /api/sessions?runtime=claude
// ---------------------------------------------------------------------------
test('E2E-SES-01 — Sessions tab populates with Claude sessions from /api/sessions?runtime=claude', async ({
  page,
}) => {
  const sessionFetchUrls: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/sessions')) {
      sessionFetchUrls.push(req.url());
    }
  });

  await loadLiveSessionsTab(page);

  // The sessions module must have fetched /api/sessions?runtime=claude.
  const claudeListRequests = sessionFetchUrls.filter(
    (url) => url.includes('/api/sessions') && url.includes('runtime=claude')
      && !url.match(/\/api\/sessions\/[^/]+\/[^/]+/)
  );
  expect(claudeListRequests.length).toBeGreaterThan(0);

  // Three rows (one per mock session).
  const rowCount = await page.$$eval(
    '.sessions-table tbody tr.session-row',
    (rows) => rows.length
  );
  expect(rowCount).toBe(3);

  // First session's slug must appear in the table.
  const tableText = await page.textContent('.sessions-table');
  expect(tableText).toBeTruthy();
  expect(tableText).toContain(MOCK_SESSION_ID_1.substring(0, 8));

  // Status dots for all three statuses must be present.
  const activeStatusDots = await page.$$eval(
    '.status-dot[data-status="active"]',
    (els) => els.length
  );
  expect(activeStatusDots).toBeGreaterThanOrEqual(1);

  const idleStatusDots = await page.$$eval(
    '.status-dot[data-status="idle"]',
    (els) => els.length
  );
  expect(idleStatusDots).toBeGreaterThanOrEqual(1);

  const endedStatusDots = await page.$$eval(
    '.status-dot[data-status="ended"]',
    (els) => els.length
  );
  expect(endedStatusDots).toBeGreaterThanOrEqual(1);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'sessions-tab-populated.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-SES-02 (b) — Row click opens drawer with SessionDetail content
// ---------------------------------------------------------------------------
test('E2E-SES-02 — Clicking a session row opens the detail drawer with SessionDetail content', async ({
  page,
}) => {
  await loadLiveSessionsTab(page);

  const detailRequests: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes(`/api/sessions/claude/${MOCK_SESSION_ID_1}`)) {
      detailRequests.push(req.url());
    }
  });

  // Click the first session row.
  const firstRow = page.locator(`[data-session-id="${MOCK_SESSION_ID_1}"]`).first();
  await expect(firstRow).toBeVisible({ timeout: 8_000 });
  await firstRow.click();

  // The drawer must open: hidden attribute is removed and .open class is added.
  // sessions.js: drawer.removeAttribute('hidden'); drawer.classList.add('open');
  await page.waitForSelector('#session-drawer.open', { timeout: 10_000 });
  await page.waitForSelector('#session-drawer:not([hidden])', { timeout: 10_000 });

  // Wait for drawer content to include the session-id slug (rendered by
  // renderDrawerContent → .drawer-session-id element).
  await page.waitForFunction(
    (expectedSlug: string) => {
      const content = document.querySelector('#session-drawer .session-drawer__content');
      return content !== null && content.textContent?.includes(expectedSlug) === true;
    },
    MOCK_SESSION_ID_1.substring(0, 8),
    { timeout: 8_000 }
  );

  // A detail API request must have fired.
  expect(detailRequests.length).toBeGreaterThan(0);

  // Drawer content must include expected SessionDetail fields.
  const drawerContent = await page.textContent('#session-drawer .session-drawer__content');
  expect(drawerContent).toBeTruthy();
  expect(drawerContent).toContain(MOCK_SESSION_ID_1.substring(0, 8));
  expect(drawerContent).toContain('claude-sonnet-4-6');  // model
  expect(drawerContent).toContain('qa-engineer');         // agent_name

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'sessions-drawer-open.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-SES-03 (c) — Sort by Cost (desc) reorders rows
//
// sessions.js sort logic:
//   - sortKey is toggled on th[data-sort-key] clicks.
//   - First click: _sortDir = 'asc' (new key, no prior direction).
//   - Second click on same key: 'asc' → 'desc'.
//   - Rows are re-rendered by renderTable() with applySort() applied.
//
// Selector: th[data-sort-key="cumulative_cost_usd"] (the Cost column header).
// ---------------------------------------------------------------------------
test('E2E-SES-03 — Sorting by Cost (desc) reorders session rows correctly', async ({
  page,
}) => {
  await loadLiveSessionsTab(page);

  // Mock data costs in insertion order: $0.45, $1.20, $0.08.
  // Expected cost-desc order: $1.20, $0.45, $0.08.

  // The Cost column header uses data-sort-key="cumulative_cost_usd".
  const costHeader = page.locator('th[data-sort-key="cumulative_cost_usd"]');
  await expect(costHeader).toBeVisible({ timeout: 5_000 });

  // First click → asc (sort key is null before, so direction starts at 'asc').
  await costHeader.click();
  await page.waitForTimeout(200);

  // Second click → desc.
  await costHeader.click();
  await page.waitForTimeout(200);

  // The header must now declare data-sort-dir="desc".
  const finalDir = await costHeader.getAttribute('data-sort-dir');
  expect(finalDir).toBe('desc');

  // Read cost cell values.
  const costTexts = await page.$$eval(
    '.sessions-table tbody tr.session-row .cell-cost',
    (cells) => cells.map((el) => el.textContent?.trim() ?? '')
  );
  expect(costTexts.length).toBe(3);

  // Parse cost values — sessions.js renders "$1.20", "$0.45", "$0.08".
  const parseCost = (s: string): number => parseFloat(s.replace(/[^0-9.]/g, '')) || 0;
  const costs = costTexts.map(parseCost);

  // Assert descending order.
  expect(costs[0]).toBeGreaterThanOrEqual(costs[1]);
  expect(costs[1]).toBeGreaterThanOrEqual(costs[2]);

  // Highest cost ($1.20) must be first.
  expect(costs[0]).toBeCloseTo(1.20, 1);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'sessions-sorted-cost-desc.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-SES-04 (d) — "Last updated" badge ticks at ≤11 s
// ---------------------------------------------------------------------------
test('E2E-SES-04 — "Last updated" badge text updates within 11 seconds of initial load', async ({
  page,
}) => {
  await loadLiveSessionsTab(page);

  // Badge must exist.
  await page.waitForSelector('#sessions-last-updated', { timeout: 12_000 });

  // sessions.js calls updateLastUpdatedBadge() after fetchSessions() succeeds.
  // Badge text must no longer be "Never" (the initial placeholder from sessions.py).
  await page.waitForFunction(
    () => {
      const el = document.getElementById('sessions-last-updated');
      return el !== null
        && el.textContent?.trim() !== 'Never'
        && el.textContent?.trim() !== '';
    },
    {},
    { timeout: 11_000 }
  );

  const badgeText = await page.textContent('#sessions-last-updated');
  expect(badgeText).toBeTruthy();
  // sessions.js renders "Updated: <time>" via updateLastUpdatedBadge().
  expect(badgeText?.toLowerCase()).toContain('updated');

  // Wait for a second update within 11 s (the 10 s auto-refresh interval).
  const badgeAfterFirstUpdate = await page.textContent('#sessions-last-updated');
  let secondUpdateSeen = false;
  const deadline = Date.now() + 11_000;
  while (Date.now() < deadline) {
    await page.waitForTimeout(500);
    const current = await page.textContent('#sessions-last-updated');
    if (current !== badgeAfterFirstUpdate) {
      secondUpdateSeen = true;
      break;
    }
  }
  expect(secondUpdateSeen).toBe(true);
});

// ---------------------------------------------------------------------------
// E2E-SES-05 (e) — Auto-refresh suspends when document.hidden
// ---------------------------------------------------------------------------
test('E2E-SES-05 — Auto-refresh suspends when document.hidden is true', async ({
  page,
}) => {
  let sessionListFetchCount = 0;

  // Count only /api/sessions list fetches (not detail).
  page.on('request', (req) => {
    const url = req.url();
    if (
      url.includes('/api/sessions')
      && !url.match(/\/api\/sessions\/[^/]+\/[^/]+/)
    ) {
      sessionListFetchCount++;
    }
  });

  await loadLiveSessionsTab(page);
  // loadLiveSessionsTab waits for aria-busy="false" so the initial fetch has
  // completed. Record baseline count.
  const fetchesAfterInit = sessionListFetchCount;

  // Simulate tab backgrounding: override document.hidden = true and dispatch
  // visibilitychange.
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', {
      value: true,
      configurable: true,
      writable: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));
  });

  // Wait one full auto-refresh interval (10 s) + 1 s margin.
  // sessions.js: setInterval(() => { if (!document.hidden) fetchSessions(); }, 10000)
  await page.waitForTimeout(11_000);
  const fetchesWhileHidden = sessionListFetchCount - fetchesAfterInit;

  // Must be 0. Tolerance of 1 in case a tick fired before the event propagated.
  expect(fetchesWhileHidden).toBeLessThanOrEqual(1);

  // Restore visibility and verify auto-refresh resumes.
  const fetchesBeforeResume = sessionListFetchCount;
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', {
      value: false,
      configurable: true,
      writable: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));
  });

  // sessions.js on visibilitychange: if (!document.hidden) fetchSessions().
  // Wait up to 11 s for at least one resumed fetch.
  let resumedFetches = 0;
  const deadline = Date.now() + 11_000;
  while (Date.now() < deadline) {
    await page.waitForTimeout(500);
    resumedFetches = sessionListFetchCount - fetchesBeforeResume;
    if (resumedFetches >= 1) { break; }
  }
  expect(resumedFetches).toBeGreaterThanOrEqual(1);
});
