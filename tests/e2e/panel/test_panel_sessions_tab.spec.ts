/**
 * Browser journeys for the Sessions tab and runtime switcher.
 *
 * Surface:
 *   E2E-SES-01..05: Sessions tab — table population, drawer detail,
 *     sort by Cost, "Last updated" badge ticking, auto-refresh suspension.
 *   E2E-RT-01..04: Three-tab x two-runtime matrix — toggling the
 *     runtime switcher reloads Agents, Workflows, AND Sessions with ?runtime=codex;
 *     localStorage persistence verified across page.reload().
 *
 * Live FE mode:
 *   Each test isolates the browser journey from dev-server asset timing:
 *     1. Navigates to the REAL panel origin (http://127.0.0.1:4999) so
 *        page.route() intercepts have a concrete origin for relative URL resolution.
 *     2. Uses page.route() to intercept the panel root ("/") and serve a crafted
 *        HTML page that embeds the REAL sessions section HTML (generated from
 *        render_sessions_section() via a helper constant) and loads the REAL
 *        sessions.js via a <script> tag that is intercepted from the filesystem.
 *     3. Mocks /api/sessions* with deterministic fixture payloads.
 *
 *   Multi-tab mode:
 *     Same origin-interception strategy, but the crafted page includes all three
 *     tab sections (Agents, Workflows, Sessions) + the runtime switcher markup,
 *     loads runtime.js + agents.js + workflows.js + sessions.js from the filesystem,
 *     and mocks /api/agents*, /api/workflows*, /api/sessions* for both runtimes.
 *
 *   This drives the REAL views/*.py DOM contracts and REAL assets/js/*.js logic —
 *   the only synthetic element is the surrounding minimal HTML scaffold.
 *
 * Coverage: sessions list/detail, runtime filter propagation, refresh timing,
 * localStorage persistence, and the Codex cost-unknown presentation.
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

// ============================================================================
// Runtime switcher: three-tab x two-runtime matrix + localStorage persistence
// ============================================================================
//
// These tests verify that toggling the runtime switcher causes each of the
// three data tabs (Agents, Workflows, Sessions) to refetch with the new
// ?runtime=<value> query param, and that localStorage['dadaia-panel-runtime']
// survives a page.reload().
//
// Scaffold design:
//   - Full panel page with all three sections + runtime-switcher markup.
//   - runtime.js + agents.js + workflows.js + sessions.js served from filesystem.
//   - /api/agents*, /api/workflows*, /api/sessions* mocked for both runtimes.
//   - core.js served live from the panel (handles authedFetch + tab activation
//     hooks for Agents / Workflows on tab click).
// ============================================================================

// ---------------------------------------------------------------------------
// Static HTML scaffolds for Agents and Workflows sections
// (mirror render_agents_section() / render_workflows_section() output)
// ---------------------------------------------------------------------------

// Agents and Workflows are now .ops-subsection divs inside #section-ops (T-016-P09).
// They are NOT standalone .section elements — only #section-ops carries that class.
const REAL_AGENTS_SECTION_HTML = `<div id="ops-subsection-agents" class="ops-subsection">
  <header class="section-header">
    <h2>Agents</h2>
    <p class="section-meta" id="agents-meta" aria-live="polite"></p>
  </header>
  <div id="agents-staleness-banner" class="warning-banner" hidden role="status"></div>
  <div id="agents-grid" class="card-grid agents-grid" aria-busy="false"></div>
  <p id="agents-empty" class="empty-state" hidden>Nenhum agente observado ainda.</p>
</div>`;

const REAL_WORKFLOWS_SECTION_HTML = `<div id="ops-subsection-workflows" class="ops-subsection">
  <header class="section-header">
    <h2>Workflows</h2>
    <p class="section-meta" id="workflows-meta" aria-live="polite"></p>
  </header>
  <p id="workflows-empty" class="empty-state" hidden>Nenhum workflow descoberto.</p>
  <div id="workflows-grid" class="workflows-card-grid" aria-busy="false"></div>
  <nav class="workflows-list" aria-label="Workflow list" id="workflows-list" hidden></nav>
  <div class="workflows-detail" id="workflows-detail" role="region" aria-label="Workflow detail" aria-live="polite" hidden></div>
</div>`;

// ---------------------------------------------------------------------------
// Full multi-tab panel page HTML
//
// Includes:
//   - Runtime switcher (matches views/index.py topbar markup)
//   - Nav: single #tab-ops (Agents+Workflows+Kanban merged) + #tab-sessions
//     (T-016-P09 consolidation — Agents/Workflows are subsections of #section-ops)
//   - Sections: #section-ops wraps agentsSection + workflowsSection;
//     sessionsSection is standalone as before.
//   - runtime.js loaded first (synchronous), then core.js, agents.js,
//     workflows.js, sessions.js (same order as views/index.py)
// ---------------------------------------------------------------------------
function buildMultiTabPageHtml(
  agentsSection: string,
  workflowsSection: string,
  sessionsSection: string
): string {
  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>dadaia panel — Multi-tab runtime e2e scaffold</title>
  <script>(function(){var r=localStorage.getItem('dadaia-panel-runtime');if(r&&(r==='claude'||r==='codex')){document.documentElement.dataset.runtime=r;}})();</script>
  <style>
    /* Minimal structural styles */
    body { font-family: sans-serif; margin: 0; }
    .section { display: none; }
    .section.active { display: block; }
    .session-drawer { display: none; }
    .session-drawer:not([hidden]).open { display: block; }
  </style>
</head>
<body>
  <header class="topbar" role="banner">
    <div class="runtime-switcher" role="radiogroup" aria-label="Active runtime">
      <button type="button"
        class="runtime-btn runtime-btn--claude"
        id="runtime-btn-claude"
        role="radio"
        aria-checked="true"
        data-runtime-value="claude"
        aria-label="Claude runtime">
        <span class="runtime-btn-label">Claude</span>
      </button>
      <button type="button"
        class="runtime-btn runtime-btn--codex"
        id="runtime-btn-codex"
        role="radio"
        aria-checked="false"
        data-runtime-value="codex"
        aria-label="Codex runtime">
        <span class="runtime-btn-label">Codex</span>
      </button>
    </div>
  </header>
  <nav class="nav-tabs" aria-label="Panel sections" role="tablist">
    <button class="nav-tab" data-section="ops" aria-selected="false" role="tab" id="tab-ops">Ops</button>
    <button class="nav-tab active" data-section="sessions" aria-selected="true" role="tab" id="tab-sessions">Sessions</button>
  </nav>
  <main class="main" role="main">
    <section id="section-ops" class="section" role="tabpanel" tabindex="0" aria-labelledby="tab-ops">
      ${agentsSection}
      ${workflowsSection}
    </section>
    ${sessionsSection}
  </main>
  <!-- runtime.js: must load before agents.js, workflows.js, sessions.js -->
  <script src="/static/runtime.js"></script>
  <!-- core.js: provides window.authedFetch + tab-activation hooks -->
  <script src="/static/core.js"></script>
  <!-- tab modules: served from filesystem via page.route -->
  <script src="/static/agents.js"></script>
  <script src="/static/workflows.js"></script>
  <script src="/static/sessions.js" defer></script>
</body>
</html>`;
}

// ---------------------------------------------------------------------------
// Mock fixture data — Codex variants
// (Claude variants reuse MOCK_SESSIONS_LIST / MOCK_AGENTS_LIST / MOCK_WORKFLOWS_LIST)
// ---------------------------------------------------------------------------

const MOCK_AGENTS_CLAUDE = {
  agents: [
    {
      agent_id: 'qa-engineer',
      display_name: 'QA Engineer',
      description: 'E2E tests and deploy validation.',
      status: 'active',
      skills: ['playwright', 'cypress'],
      tools: [],
      model: 'claude-sonnet-4-6',
      tier: 3,
      telemetry: {
        session_count: 5,
        total_cost_usd: 1.23,
        cost_known: true,
        last_activity_at: '2026-05-19T17:00:00+00:00',
        context_breakdown: [],
      },
    },
  ],
  status_window_days: 30,
  pricing_age_days: 10,
  runtime: 'claude',
};

const MOCK_AGENTS_CODEX = {
  agents: [
    {
      agent_id: 'software-engineer',
      display_name: 'Software Engineer',
      description: 'TDD implementation (Codex runtime).',
      status: 'active',
      skills: ['python', 'tdd'],
      tools: [],
      model: 'codex-latest',
      tier: 3,
      telemetry: {
        session_count: 3,
        total_cost_usd: null,
        cost_known: false,
        last_activity_at: '2026-05-19T16:00:00+00:00',
        context_breakdown: [],
      },
    },
  ],
  status_window_days: 30,
  pricing_age_days: 10,
  runtime: 'codex',
};

const MOCK_WORKFLOWS_CLAUDE = {
  source_hint: 'dadaia-workspace',
  workflows: [
    {
      name: 'spec-to-impl',
      display_name: 'Spec → Impl (Claude)',
      description: 'Claude-backed SDD release pipeline.',
      agent_ids: ['product-engineer', 'software-engineer', 'qa-engineer'],
      stage_count: 5,
      version: 'v1.0',
      schema_version: '1',
      has_parallel: true,
      has_gates: true,
      source_path: 'specs/workflows/spec-to-impl.yaml',
    },
  ],
  runtime: 'claude',
};

const MOCK_WORKFLOWS_CODEX = {
  source_hint: 'dadaia-workspace',
  workflows: [
    {
      name: 'codex-impl',
      display_name: 'Codex Impl Pipeline',
      description: 'Codex-backed implementation workflow.',
      agent_ids: ['software-engineer'],
      stage_count: 3,
      version: 'v1.0',
      schema_version: '1',
      has_parallel: false,
      has_gates: false,
      source_path: 'specs/workflows/codex-impl.yaml',
    },
  ],
  runtime: 'codex',
};

const MOCK_SESSIONS_CODEX = {
  generated_at: '2026-05-19T18:30:00+00:00',
  runtime: 'codex',
  project: null,
  limit: 50,
  total_count: 2,
  sessions: [
    {
      session_id: 'codex-session-zzz000yyy111xxx2',
      runtime: 'codex',
      project: 'dadaia-workspace',
      cwd: '/home/user/workspace/dadaia/repos/dadaia-workspace',
      model: 'codex-latest',
      started_at: '2026-05-19T14:00:00+00:00',
      last_activity_at: '2026-05-19T17:30:00+00:00',
      message_count: 12,
      context_size_tokens: 8000,
      cumulative_cost_usd: null,
      cost_known: false,
      status: 'active',
      agent_name: 'software-engineer',
      ai_title: 'Codex implementation session',
    },
    {
      session_id: 'codex-session-aaa999bbb888ccc7',
      runtime: 'codex',
      project: 'dadaia-workspace',
      cwd: '/home/user/workspace/dadaia',
      model: 'codex-latest',
      started_at: '2026-05-19T10:00:00+00:00',
      last_activity_at: '2026-05-19T13:00:00+00:00',
      message_count: 6,
      context_size_tokens: 3000,
      cumulative_cost_usd: null,
      cost_known: false,
      status: 'idle',
      agent_name: 'backend-engineer',
      ai_title: null,
    },
  ],
};

// ---------------------------------------------------------------------------
// Multi-tab route installer
//
// Intercepts:
//   "/" — serves the crafted multi-tab page HTML.
//   "/static/runtime.js", "/static/agents.js", "/static/workflows.js",
//   "/static/sessions.js" — served from filesystem.
//   "/api/agents*" — returns MOCK_AGENTS_CLAUDE or MOCK_AGENTS_CODEX based on
//     the ?runtime= query param.
//   "/api/workflows*" — same pattern.
//   "/api/sessions*" — returns MOCK_SESSIONS_LIST (claude) or MOCK_SESSIONS_CODEX.
// ---------------------------------------------------------------------------

async function installMultiTabRoutes(page: Page): Promise<void> {
  const runtimeJsContent = fs.readFileSync(
    path.join(JS_ASSETS_DIR, 'runtime.js'), 'utf-8'
  );
  const agentsJsContent = fs.readFileSync(
    path.join(JS_ASSETS_DIR, 'agents.js'), 'utf-8'
  );
  const workflowsJsContent = fs.readFileSync(
    path.join(JS_ASSETS_DIR, 'workflows.js'), 'utf-8'
  );
  const sessionsJsContent = fs.readFileSync(
    path.join(JS_ASSETS_DIR, 'sessions.js'), 'utf-8'
  );

  const multiTabPageHtml = buildMultiTabPageHtml(
    REAL_AGENTS_SECTION_HTML,
    REAL_WORKFLOWS_SECTION_HTML,
    REAL_SESSIONS_SECTION_HTML
  );

  // 1. Panel root — serve the crafted multi-tab page.
  await page.route(
    (url) => {
      const pathname = new URL(url).pathname;
      return pathname === '/' || pathname === '';
    },
    (route: Route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/html; charset=utf-8',
        body: multiTabPageHtml,
      });
    }
  );

  // 2. JS assets — served from filesystem.
  await page.route('**/static/runtime.js', (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: runtimeJsContent,
    });
  });
  await page.route('**/static/agents.js', (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: agentsJsContent,
    });
  });
  await page.route('**/static/workflows.js', (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: workflowsJsContent,
    });
  });
  await page.route('**/static/sessions.js', (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: sessionsJsContent,
    });
  });

  // 3. /api/agents — runtime-aware mock.
  await page.route(/\/api\/agents(?!.*\/prompt)/, (route: Route, request) => {
    const url = new URL(request.url());
    const pathParts = url.pathname.split('/').filter(Boolean);
    // Skip /api/agents/<id>/prompt — not needed for these tests.
    if (pathParts.length >= 3) {
      route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
      return;
    }
    const runtime = url.searchParams.get('runtime') || 'claude';
    const payload = runtime === 'codex' ? MOCK_AGENTS_CODEX : MOCK_AGENTS_CLAUDE;
    route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify(payload),
    });
  });

  // 4. /api/workflows — runtime-aware mock.
  await page.route(/\/api\/workflows(?!\/)/, (route: Route, request) => {
    const url = new URL(request.url());
    const runtime = url.searchParams.get('runtime') || 'claude';
    const payload = runtime === 'codex' ? MOCK_WORKFLOWS_CODEX : MOCK_WORKFLOWS_CLAUDE;
    route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify(payload),
    });
  });

  // 5. /api/sessions* — runtime-aware mock (list only; detail not needed here).
  await page.route(/\/api\/sessions/, (route: Route, request) => {
    const url = new URL(request.url());
    const pathParts = url.pathname.split('/').filter(Boolean);
    // /api/sessions/<runtime>/<id> detail — return 404 (not tested in RT suite).
    if (pathParts.length >= 4) {
      route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
      return;
    }
    const runtime = url.searchParams.get('runtime') || 'claude';
    const payload = runtime === 'codex' ? MOCK_SESSIONS_CODEX : MOCK_SESSIONS_LIST;
    route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify(payload),
    });
  });
}

// ---------------------------------------------------------------------------
// Multi-tab bootstrap: install routes, seed token, navigate, wait for Sessions
// (the default active tab in the scaffold) to complete its initial load.
// ---------------------------------------------------------------------------

async function loadMultiTabPanel(page: Page): Promise<void> {
  await installMultiTabRoutes(page);

  await page.goto(`${BASE_URL}/?token=${encodeURIComponent(PANEL_TOKEN)}`, {
    waitUntil: 'domcontentloaded',
  });

  // Wait for the sessions section initial fetch to complete (aria-busy flips).
  await page.waitForSelector('#sessions-table-container[aria-busy="false"]', {
    timeout: 15_000,
  });
}

// ---------------------------------------------------------------------------
// E2E-RT-01 — Runtime switcher reloads Agents tab with ?runtime=codex
//
// Scenario:
//   Given the multi-tab panel is loaded and the Agents tab is activated.
//   When Runtime.set('codex') is called (simulating the switcher click).
//   Then agents.js refetches /api/agents?runtime=codex and renders the
//        Codex-scoped agent cards.
//
// Verifies: agents.js `dadaia:runtime-change` subscription and the
//           ?runtime= fetch param.
// ---------------------------------------------------------------------------
test('E2E-RT-01 — Runtime switcher reloads Agents tab with ?runtime=codex', async ({
  page,
}) => {
  const agentFetchUrls: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/agents') && !req.url().includes('/prompt')) {
      agentFetchUrls.push(req.url());
    }
  });

  await loadMultiTabPanel(page);

  // Activate the Ops tab — triggers Agents.load() via core.js tab hook.
  // (Agents is now a subsection of #section-ops, not a standalone tab — T-016-P09.)
  await page.click('#tab-ops');
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 10_000 });

  // Initial fetch must have used ?runtime=claude (the default).
  const claudeAgentFetches = agentFetchUrls.filter((u) => u.includes('runtime=claude'));
  expect(claudeAgentFetches.length).toBeGreaterThan(0);

  const fetchCountBeforeSwitch = agentFetchUrls.length;

  // Toggle runtime to Codex via Runtime.set() — this fires dadaia:runtime-change.
  // agents.js handles this by clearing promptCache, resetting loaded flag,
  // and calling load() if section-ops is active.
  await page.evaluate(() => {
    (window as any).Runtime.set('codex');
  });

  // Wait for the refetch to complete (aria-busy flips back to false).
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 10_000 });
  await page.waitForTimeout(500); // allow any in-flight requests to settle

  // At least one new fetch must have occurred with ?runtime=codex.
  const codexAgentFetches = agentFetchUrls.filter((u) => u.includes('runtime=codex'));
  expect(codexAgentFetches.length).toBeGreaterThan(0);
  expect(agentFetchUrls.length).toBeGreaterThan(fetchCountBeforeSwitch);

  // The rendered grid must reflect Codex data (agent from MOCK_AGENTS_CODEX).
  const gridText = await page.textContent('#agents-grid');
  expect(gridText).toBeTruthy();
  expect(gridText).toContain('Software Engineer');

  // Reset runtime back to claude for test isolation.
  await page.evaluate(() => { (window as any).Runtime.set('claude'); });

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'runtime-agents-codex.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-RT-02 — Runtime switcher reloads Workflows tab with ?runtime=codex
//
// Scenario:
//   Given the multi-tab panel is loaded and the Workflows tab is activated.
//   When Runtime.set('codex') is called.
//   Then workflows.js refetches /api/workflows?runtime=codex and renders the
//        Codex-scoped workflow cards.
//
// Verifies: workflows.js `dadaia:runtime-change` subscription.
// ---------------------------------------------------------------------------
test('E2E-RT-02 — Runtime switcher reloads Workflows tab with ?runtime=codex', async ({
  page,
}) => {
  const workflowFetchUrls: string[] = [];
  page.on('request', (req) => {
    // Capture list fetches only (no /api/workflows/<name> detail).
    if (req.url().match(/\/api\/workflows(\?|$)/)) {
      workflowFetchUrls.push(req.url());
    }
  });

  await loadMultiTabPanel(page);

  // Activate the Ops tab — triggers Workflows.handleHashOnActivation() via core.js.
  // (Workflows is now a subsection of #section-ops, not a standalone tab — T-016-P09.)
  await page.click('#tab-ops');
  await page.waitForSelector('#workflows-grid[aria-busy="false"]', { timeout: 10_000 });

  // Initial fetch must have used ?runtime=claude.
  const claudeWorkflowFetches = workflowFetchUrls.filter((u) => u.includes('runtime=claude'));
  expect(claudeWorkflowFetches.length).toBeGreaterThan(0);

  const fetchCountBeforeSwitch = workflowFetchUrls.length;

  // Toggle runtime to Codex.
  await page.evaluate(() => {
    (window as any).Runtime.set('codex');
  });

  // Wait for the refetch to complete.
  await page.waitForSelector('#workflows-grid[aria-busy="false"]', { timeout: 10_000 });
  await page.waitForTimeout(500);

  // At least one new fetch must have occurred with ?runtime=codex.
  const codexWorkflowFetches = workflowFetchUrls.filter((u) => u.includes('runtime=codex'));
  expect(codexWorkflowFetches.length).toBeGreaterThan(0);
  expect(workflowFetchUrls.length).toBeGreaterThan(fetchCountBeforeSwitch);

  // The rendered grid must reflect Codex data.
  const gridText = await page.textContent('#workflows-grid');
  expect(gridText).toBeTruthy();
  expect(gridText).toContain('Codex Impl Pipeline');

  // Reset runtime.
  await page.evaluate(() => { (window as any).Runtime.set('claude'); });

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'runtime-workflows-codex.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-RT-03 — Runtime switcher reloads Sessions tab with ?runtime=codex
//
// Scenario:
//   Given the multi-tab panel is loaded (Sessions is the active tab).
//   When Runtime.set('codex') is called.
//   Then sessions.js refetches /api/sessions?runtime=codex and renders the
//        Codex sessions.
//
// Verifies: sessions.js `dadaia:runtime-change` subscription.
// ---------------------------------------------------------------------------
test('E2E-RT-03 — Runtime switcher reloads Sessions tab with ?runtime=codex', async ({
  page,
}) => {
  const sessionFetchUrls: string[] = [];
  page.on('request', (req) => {
    // Capture list fetches only (exclude detail /api/sessions/<r>/<id>).
    if (
      req.url().includes('/api/sessions')
      && !req.url().match(/\/api\/sessions\/[^/]+\/[^/]+/)
    ) {
      sessionFetchUrls.push(req.url());
    }
  });

  await loadMultiTabPanel(page);

  // Sessions tab is already active in the scaffold. The initial fetch with
  // runtime=claude should have completed (aria-busy="false" was awaited in
  // loadMultiTabPanel).
  const claudeSessionFetches = sessionFetchUrls.filter((u) => u.includes('runtime=claude'));
  expect(claudeSessionFetches.length).toBeGreaterThan(0);

  const fetchCountBeforeSwitch = sessionFetchUrls.length;

  // Toggle runtime to Codex.
  await page.evaluate(() => {
    (window as any).Runtime.set('codex');
  });

  // Wait for sessions-table-container to finish its refetch (aria-busy flips).
  await page.waitForSelector('#sessions-table-container[aria-busy="false"]', {
    timeout: 10_000,
  });
  await page.waitForTimeout(300);

  // At least one new fetch with ?runtime=codex.
  const codexSessionFetches = sessionFetchUrls.filter((u) => u.includes('runtime=codex'));
  expect(codexSessionFetches.length).toBeGreaterThan(0);
  expect(sessionFetchUrls.length).toBeGreaterThan(fetchCountBeforeSwitch);

  // Rendered table must reflect Codex sessions (2 rows from MOCK_SESSIONS_CODEX).
  const rowCount = await page.$$eval(
    '.sessions-table tbody tr.session-row',
    (rows) => rows.length
  );
  expect(rowCount).toBe(2);

  // The Codex session-id slug must be present.
  const tableText = await page.textContent('.sessions-table');
  expect(tableText).toBeTruthy();
  expect(tableText).toContain('codex-se'); // first 8 chars of 'codex-session-zzz...'

  // Reset runtime.
  await page.evaluate(() => { (window as any).Runtime.set('claude'); });

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'runtime-sessions-codex.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-RT-04 — localStorage persistence: runtime survives page.reload()
//
// Scenario:
//   Given the multi-tab panel is loaded.
//   When Runtime.set('codex') is called and then page.reload() is executed.
//   Then localStorage.getItem('dadaia-panel-runtime') === 'codex'
//        AND document.documentElement.dataset.runtime === 'codex'
//        (the inline <script> in the page <head> restores data-runtime on reload).
//
// Verifies: runtime localStorage persistence.
// ---------------------------------------------------------------------------
test('E2E-RT-04 — localStorage persistence: runtime=codex survives page.reload()', async ({
  page,
}) => {
  await loadMultiTabPanel(page);

  // Set runtime to 'codex' before reload.
  await page.evaluate(() => {
    (window as any).Runtime.set('codex');
  });

  // Confirm the value is persisted in localStorage immediately.
  const storedBeforeReload = await page.evaluate(() =>
    localStorage.getItem('dadaia-panel-runtime')
  );
  expect(storedBeforeReload).toBe('codex');

  // Confirm data-runtime attribute is set on <html>.
  const dataRuntimeBeforeReload = await page.evaluate(() =>
    document.documentElement.getAttribute('data-runtime')
  );
  expect(dataRuntimeBeforeReload).toBe('codex');

  // Reload the page — the route interceptors are still active for this page
  // context, so the crafted HTML is served again. The inline <script> in the
  // <head> reads localStorage and sets data-runtime before any module loads.
  await page.reload({ waitUntil: 'domcontentloaded' });

  // Wait for sessions initial load to complete after reload.
  await page.waitForSelector('#sessions-table-container[aria-busy="false"]', {
    timeout: 15_000,
  });

  // localStorage must still carry 'codex'.
  const storedAfterReload = await page.evaluate(() =>
    localStorage.getItem('dadaia-panel-runtime')
  );
  expect(storedAfterReload).toBe('codex');

  // The inline <head> script must have restored data-runtime='codex' on <html>.
  const dataRuntimeAfterReload = await page.evaluate(() =>
    document.documentElement.getAttribute('data-runtime')
  );
  expect(dataRuntimeAfterReload).toBe('codex');

  // window.Runtime.get() must also return 'codex' (runtime.js reads localStorage on init).
  const runtimeGetAfterReload = await page.evaluate(() =>
    (window as any).Runtime ? (window as any).Runtime.get() : null
  );
  expect(runtimeGetAfterReload).toBe('codex');

  // Clean up: reset to 'claude' so other tests in subsequent runs start clean.
  await page.evaluate(() => {
    (window as any).Runtime.set('claude');
  });

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'runtime-localstorage-persist.png'),
    fullPage: false,
  });
});

// ============================================================================
// Codex banner + Cost column "—" override
// ============================================================================
//
// E2E-COD-01: When the runtime switcher is set to 'codex':
//   - #sessions-banner is visible with text matching /Cost not tracked/i.
//   - Every Cost cell in the sessions table contains "—" (not a dollar value).
// When toggled back to 'claude':
//   - #sessions-banner has the [hidden] attribute (not visible).
//   - Cost cells contain "$" (dollar prefix from the formatter).
//
// Uses the multi-tab scaffold + runtime-aware mocks from installMultiTabRoutes()
// so sessions.js receives MOCK_SESSIONS_CODEX on runtime=codex fetches and
// MOCK_SESSIONS_LIST (Claude) on runtime=claude fetches.
//
// Verifies the Codex cost presentation contract:
//   - Banner element #sessions-banner visible with "Cost not tracked" text.
//   - Cost column renders "—" for all Codex rows (cumulative_cost_usd=null).
//   - Banner disappears and Cost cells show "$" when runtime reverts to claude.
// ============================================================================

test('E2E-COD-01 — Codex banner appears with "Cost not tracked" and Cost cells show "—"; reverts on claude toggle', async ({
  page,
}) => {
  await loadMultiTabPanel(page);

  // ── Part 1: Switch to Codex ──────────────────────────────────────────────

  await page.evaluate(() => {
    (window as any).Runtime.set('codex');
  });

  // Wait for sessions to refetch with runtime=codex (aria-busy flips back to false).
  await page.waitForSelector('#sessions-table-container[aria-busy="false"]', {
    timeout: 10_000,
  });

  // sessions.js calls updateBanner() immediately on dadaia:runtime-change, before the
  // fetch completes. The banner must be visible as soon as the event fires.
  // Wait for #sessions-banner to not have the [hidden] attribute.
  await page.waitForFunction(
    () => {
      const banner = document.getElementById('sessions-banner');
      return banner !== null && !banner.hasAttribute('hidden');
    },
    {},
    { timeout: 8_000 }
  );

  // Banner must be visible and contain "Cost not tracked" text.
  const bannerVisible = await page.isVisible('#sessions-banner');
  expect(bannerVisible).toBe(true);

  const bannerText = await page.textContent('#sessions-banner');
  expect(bannerText).toBeTruthy();
  expect(bannerText?.toLowerCase()).toContain('cost not tracked');

  // All Cost cells in the Codex sessions table must render "—" (em dash or hyphen),
  // not a dollar value.  MOCK_SESSIONS_CODEX has cumulative_cost_usd=null for all rows.
  // sessions.js: cost = (runtime === 'codex') ? '—' : fmtCost(...)
  const costTextsCodex = await page.$$eval(
    '.sessions-table tbody tr.session-row .cell-cost',
    (cells) => cells.map((el) => el.textContent?.trim() ?? '')
  );
  expect(costTextsCodex.length).toBeGreaterThan(0);
  for (const costText of costTextsCodex) {
    // Must not contain a dollar sign when runtime is codex.
    expect(costText).not.toMatch(/\$/);
    // Must be the em dash or hyphen placeholder.
    expect(costText).toMatch(/^[—\-]$/);
  }

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'codex-banner-visible.png'),
    fullPage: false,
  });

  // ── Part 2: Switch back to Claude ───────────────────────────────────────

  await page.evaluate(() => {
    (window as any).Runtime.set('claude');
  });

  // Wait for sessions to refetch with runtime=claude.
  await page.waitForSelector('#sessions-table-container[aria-busy="false"]', {
    timeout: 10_000,
  });

  // Wait for banner to be hidden again.
  await page.waitForFunction(
    () => {
      const banner = document.getElementById('sessions-banner');
      return banner !== null && banner.hasAttribute('hidden');
    },
    {},
    { timeout: 8_000 }
  );

  // Banner must now be hidden.
  const bannerHidden = await page.getAttribute('#sessions-banner', 'hidden');
  expect(bannerHidden).not.toBeNull(); // [hidden] attribute is present

  // Cost cells must now contain "$" (Claude sessions have cost_known=true).
  // MOCK_SESSIONS_LIST has cumulative_cost_usd: 0.45, 1.20, 0.08.
  // sessions.js: fmtCost() renders "$0.45", "$1.20", "$0.08".
  const costTextsClaude = await page.$$eval(
    '.sessions-table tbody tr.session-row .cell-cost',
    (cells) => cells.map((el) => el.textContent?.trim() ?? '')
  );
  expect(costTextsClaude.length).toBeGreaterThan(0);
  const hasAtLeastOneDollarCell = costTextsClaude.some((t) => t.includes('$'));
  expect(hasAtLeastOneDollarCell).toBe(true);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'claude-banner-hidden-costs-restored.png'),
    fullPage: false,
  });
});
