/**
 * test_panel_sessions_tab.spec.ts — E2E-SES-01 through E2E-SES-05
 *
 * Tests: 5 (panel-r5-v1 PR5-C6)
 * Surface: Sessions tab — table population, drawer detail, sort by Cost,
 *          "Last updated" badge ticking, auto-refresh suspension on hidden tab.
 *
 * Dry-run mode (Phase C, no live FE yet):
 *   Each test loads a minimal HTML scaffold via page.setContent() that
 *   faithfully represents the DOM contract the FE (PR5-C7) must produce.
 *   All /api/sessions* calls are intercepted via page.route() and return a
 *   deterministic fixture payload matching the SessionRow / SessionDetail
 *   shape from tests/integration/test_panel_sessions_endpoint.py.
 *
 *   When the FE lands, this spec is re-run against the live panel (replace
 *   loadSessionsTabScaffold() with openLiveSessionsTab() and remove the
 *   setContent scaffolding).  The DOM contract encoded here is the acceptance
 *   gate — the FE must produce elements with the selectors used below.
 *
 * Done criterion (TASKS.md PR5-C6):
 *   (a) Sessions tab populates from /api/sessions?runtime=claude
 *   (b) row click opens drawer with SessionDetail content
 *   (c) sort by Cost (desc) reorders rows
 *   (d) "Last updated" badge ticks at ≤11 s
 *   (e) auto-refresh suspends when document.hidden
 *
 * FR coverage: FR3 (API contract shape), FR4 (table + drawer), NFR4 (auto-refresh).
 *
 * Priority: P0 (E2E-SES-01, E2E-SES-02) / P1 (E2E-SES-03, E2E-SES-04) /
 *           P2 (E2E-SES-05)
 */

import { test, expect, type Page, type Route } from '@playwright/test';
import * as path from 'path';
import { BASE_URL, PANEL_TOKEN } from './helpers';

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');

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
      cwd: '/home/marco/workspace/dadaia/repos/dadaia-workspace',
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
      project: 'tauan-games',
      cwd: '/home/marco/workspace/dadaia/repos/tauan-games',
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
      cwd: '/home/marco/workspace/dadaia',
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
  cwd: '/home/marco/workspace/dadaia/repos/dadaia-workspace',
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
// Route interceptors (always installed before any navigation).
// Must be installed BEFORE page.goto() / page.setContent().
// ---------------------------------------------------------------------------

async function installSessionsMocks(page: Page): Promise<void> {
  // All /api/sessions* requests are dispatched through a single handler that
  // discriminates between the detail path and the list path.
  // Pattern: matches any URL whose path contains /api/sessions (including
  // query strings and sub-paths).
  await page.route(
    /\/api\/sessions/,
    (route: Route, request) => {
      const url = new URL(request.url());
      const pathParts = url.pathname.split('/').filter(Boolean);
      // After filter(Boolean), /api/sessions/<runtime>/<session_id> yields:
      //   ['api', 'sessions', '<runtime>', '<session_id>'] (indices 0-3)
      if (pathParts.length >= 4 && pathParts[0] === 'api' && pathParts[1] === 'sessions') {
        const runtime = pathParts[2];
        const sessionId = pathParts[3];
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
      // /api/sessions (list) — respond with mock session list.
      route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: JSON.stringify(MOCK_SESSIONS_LIST),
      });
    }
  );
}

// ---------------------------------------------------------------------------
// Minimal HTML scaffold — represents the DOM contract for the Sessions tab.
//
// The FE (PR5-C1..C5) must produce this structure.  The spec validates
// behavior against it.  When the real FE lands, this scaffold is replaced
// by the actual panel page.
//
// DOM contract (must match what sessions.py / sessions.js will produce):
//   #section-sessions.active  — the sessions tab section
//   .sessions-table           — the sortable table
//   tbody .session-row        — one row per session (data-session-id attr)
//   .cell-cost                — cost cell inside each row
//   [data-status]             — status dot with data-status="active|idle|ended"
//   .session-drawer           — detail drawer (hidden by default)
//   #sessions-last-updated    — "last updated" badge
//   th[data-sort="cost"]      — sortable Cost column header
// ---------------------------------------------------------------------------

const SESSIONS_SCAFFOLD_HTML = /* html */ `
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>dadaia panel — Sessions (test scaffold)</title>
  <style>
    .session-drawer { display: none; }
    .session-drawer.open { display: block; }
    body { font-family: sans-serif; }
  </style>
</head>
<body>
  <!-- Nav tabs -->
  <div role="tablist">
    <button role="tab" id="tab-sessions" aria-selected="true"
            aria-controls="section-sessions">Sessions</button>
  </div>

  <!-- Sessions section -->
  <section id="section-sessions" class="active"
           aria-labelledby="tab-sessions">

    <!-- Last-updated badge — updated by JS after each auto-refresh -->
    <span id="sessions-last-updated" data-testid="sessions-last-updated">
      Never
    </span>

    <!-- Sessions table container — aria-busy="true" until first fetch completes -->
    <div id="sessions-table-container" aria-busy="true">
      <table class="sessions-table">
        <thead>
          <tr>
            <th>Session</th>
            <th>Project</th>
            <th>Model</th>
            <th data-sort="cost" data-sort-dir="none">Cost</th>
            <th>Status</th>
            <th>Last activity</th>
          </tr>
        </thead>
        <tbody id="sessions-tbody">
          <!-- Rows injected by JS -->
        </tbody>
      </table>
    </div>

    <!-- Detail drawer — opens when a row is clicked -->
    <aside class="session-drawer" id="session-drawer" aria-hidden="true">
      <div class="session-drawer__content">
        <!-- Populated by JS after /api/sessions/<runtime>/<id> fetch -->
      </div>
      <button id="drawer-close">Close</button>
    </aside>
  </section>

  <script>
    // ---------------------------------------------------------------------------
    // Minimal Sessions module — implements the behavioral contract that the real
    // sessions.js (PR5-C3) must honour.  This scaffold code drives the test cases.
    // ---------------------------------------------------------------------------

    (function () {
      'use strict';

      // Token is injected as window.__PANEL_TOKEN by addInitScript before page load.
      const TOKEN = (window.__PANEL_TOKEN) || new URLSearchParams(location.search).get('token') || '';
      const DEFAULT_RUNTIME = 'claude';
      const AUTO_REFRESH_INTERVAL_MS = 10_000;

      let _refreshTimer = null;
      let _fetchController = null;

      // -----------------------------------------------------------------------
      // Authenticated fetch helper (mirrors authedFetch pattern in real panel)
      // -----------------------------------------------------------------------
      function authedFetch(url) {
        _fetchController = new AbortController();
        return fetch(url, {
          headers: { 'Authorization': 'Bearer ' + TOKEN },
          signal: _fetchController.signal,
        });
      }

      // -----------------------------------------------------------------------
      // Render helpers
      // -----------------------------------------------------------------------
      function renderRows(sessions) {
        const tbody = document.getElementById('sessions-tbody');
        tbody.innerHTML = '';
        // Sort order is client-side state; initial render is insertion order.
        sessions.forEach(function (s) {
          const tr = document.createElement('tr');
          tr.className = 'session-row';
          tr.setAttribute('data-session-id', s.session_id);
          tr.innerHTML =
            '<td class="cell-session">' + s.session_id.substring(0, 8) + '</td>' +
            '<td class="cell-project">' + (s.project || '—') + '</td>' +
            '<td class="cell-model">' + (s.model || '—') + '</td>' +
            '<td class="cell-cost">' + (s.cost_known ? '$' + (s.cumulative_cost_usd || 0).toFixed(2) : '—') + '</td>' +
            '<td class="cell-status"><span class="status-dot" data-status="' + s.status + '">' + s.status + '</span></td>' +
            '<td class="cell-last-activity">' + (s.last_activity_at || '—') + '</td>';
          tr.addEventListener('click', function () { openDrawer(s.session_id); });
          tbody.appendChild(tr);
        });
      }

      function updateBadge() {
        const badge = document.getElementById('sessions-last-updated');
        if (badge) {
          badge.textContent = 'Updated: ' + new Date().toLocaleTimeString();
        }
      }

      // -----------------------------------------------------------------------
      // Detail drawer
      // -----------------------------------------------------------------------
      function openDrawer(sessionId) {
        const drawer = document.getElementById('session-drawer');
        drawer.classList.add('open');
        drawer.setAttribute('aria-hidden', 'false');

        authedFetch('/api/sessions/' + DEFAULT_RUNTIME + '/' + sessionId)
          .then(function (r) { return r.json(); })
          .then(function (detail) {
            const content = drawer.querySelector('.session-drawer__content');
            content.innerHTML =
              '<p class="drawer-session-id">' + detail.session_id.substring(0, 8) + '</p>' +
              '<p class="drawer-model">' + (detail.model || '—') + '</p>' +
              '<p class="drawer-agent">' + (detail.agent_name || '—') + '</p>' +
              '<p class="drawer-status">' + (detail.status || '—') + '</p>' +
              '<p class="drawer-cost">' + (detail.cost_known ? '$' + (detail.cumulative_cost_usd || 0).toFixed(2) : '—') + '</p>' +
              '<ul class="drawer-events">' +
                (detail.event_timestamps || []).map(function (ts) {
                  return '<li>' + ts + '</li>';
                }).join('') +
              '</ul>';
          });
      }

      document.getElementById('drawer-close').addEventListener('click', function () {
        const drawer = document.getElementById('session-drawer');
        drawer.classList.remove('open');
        drawer.setAttribute('aria-hidden', 'true');
      });

      // -----------------------------------------------------------------------
      // Sort
      // -----------------------------------------------------------------------
      document.querySelector('th[data-sort="cost"]').addEventListener('click', function () {
        const th = this;
        const dir = th.getAttribute('data-sort-dir');
        const newDir = dir === 'desc' ? 'asc' : 'desc';
        th.setAttribute('data-sort-dir', newDir);

        const tbody = document.getElementById('sessions-tbody');
        const rows = Array.from(tbody.querySelectorAll('tr.session-row'));
        rows.sort(function (a, b) {
          const aText = a.querySelector('.cell-cost').textContent.replace(/[^0-9.]/g, '') || '0';
          const bText = b.querySelector('.cell-cost').textContent.replace(/[^0-9.]/g, '') || '0';
          const aVal = parseFloat(aText);
          const bVal = parseFloat(bText);
          return newDir === 'desc' ? bVal - aVal : aVal - bVal;
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      });

      // -----------------------------------------------------------------------
      // Auto-refresh with document.hidden guard (NFR4)
      // -----------------------------------------------------------------------
      function fetchSessions() {
        if (document.hidden) { return; }
        authedFetch('/api/sessions?runtime=' + DEFAULT_RUNTIME)
          .then(function (r) { return r.json(); })
          .then(function (data) {
            renderRows(data.sessions || []);
            updateBadge();
            // Set aria-busy false once loaded
            document.getElementById('sessions-table-container')
              .setAttribute('aria-busy', 'false');
          })
          .catch(function () {});
      }

      function scheduleRefresh() {
        if (_refreshTimer !== null) { clearInterval(_refreshTimer); }
        _refreshTimer = setInterval(function () {
          if (!document.hidden) { fetchSessions(); }
        }, AUTO_REFRESH_INTERVAL_MS);
      }

      document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
          fetchSessions();
        }
        // When hidden: existing interval still ticks but fetchSessions() is a no-op
        // because of the document.hidden guard inside it.
      });

      // -----------------------------------------------------------------------
      // Initial load
      // -----------------------------------------------------------------------
      fetchSessions();
      scheduleRefresh();
    }());
  </script>
</body>
</html>
`;

// ---------------------------------------------------------------------------
// Setup: load the scaffold, install mocks, then run assertions.
// ---------------------------------------------------------------------------

async function loadSessionsTabScaffold(page: Page): Promise<void> {
  await installSessionsMocks(page);

  // Inject the token as a window global before any page scripts run.
  // This lets the scaffold access it without relying on location.search
  // (which is unavailable after page.setContent).
  await page.addInitScript((token: string) => {
    (window as any).__PANEL_TOKEN = token;
  }, PANEL_TOKEN);

  // Navigate to the live panel root first so page.route() intercepts have a
  // concrete origin (http://127.0.0.1:4999) for relative URL resolution.
  await page.goto(`${BASE_URL}/?token=${encodeURIComponent(PANEL_TOKEN)}`, {
    waitUntil: 'domcontentloaded',
  });

  // Replace the page content with the scaffold.
  await page.setContent(SESSIONS_SCAFFOLD_HTML, { waitUntil: 'domcontentloaded' });

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

  await loadSessionsTabScaffold(page);

  // Verify that /api/sessions was requested with runtime=claude.
  const claudeRequests = sessionFetchUrls.filter(
    (url) => url.includes('/api/sessions') && url.includes('runtime=claude')
  );
  expect(claudeRequests.length).toBeGreaterThan(0);

  // The sessions table must render exactly 3 rows (one per mock session).
  const rowCount = await page.$$eval(
    '.sessions-table tbody tr.session-row',
    (rows) => rows.length
  );
  expect(rowCount).toBe(3);

  // The first mock session's session_id slug must appear in the table.
  const tableText = await page.textContent('.sessions-table');
  expect(tableText).toBeTruthy();
  expect(tableText).toContain(MOCK_SESSION_ID_1.substring(0, 8));

  // Status dot for the active session must carry data-status="active".
  const activeStatusDots = await page.$$eval(
    '.status-dot[data-status="active"]',
    (els) => els.length
  );
  expect(activeStatusDots).toBeGreaterThanOrEqual(1);

  // Status dot for the idle session must carry data-status="idle".
  const idleStatusDots = await page.$$eval(
    '.status-dot[data-status="idle"]',
    (els) => els.length
  );
  expect(idleStatusDots).toBeGreaterThanOrEqual(1);

  // Status dot for the ended session must carry data-status="ended".
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
  await loadSessionsTabScaffold(page);

  const detailRequests: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes(`/api/sessions/claude/${MOCK_SESSION_ID_1}`)) {
      detailRequests.push(req.url());
    }
  });

  // Click the first session row (data-session-id attribute is the contract).
  const firstRow = page.locator(`[data-session-id="${MOCK_SESSION_ID_1}"]`).first();
  await expect(firstRow).toBeVisible({ timeout: 8_000 });
  await firstRow.click();

  // The drawer must open (class "open" and aria-hidden="false").
  await page.waitForSelector('.session-drawer.open[aria-hidden="false"]', {
    timeout: 10_000,
  });

  // Wait for the detail request to be intercepted (route handler fires synchronously).
  // Then wait for the drawer content to be rendered with the session-id slug.
  // The scaffold renders .drawer-session-id after the fetch resolves — poll up to 8 s.
  await page.waitForFunction(
    (expectedSlug: string) => {
      const content = document.querySelector('.session-drawer .session-drawer__content');
      return content !== null && content.textContent?.includes(expectedSlug) === true;
    },
    MOCK_SESSION_ID_1.substring(0, 8),
    { timeout: 8_000 }
  );

  // Verify a detail API request was indeed fired.
  expect(detailRequests.length).toBeGreaterThan(0);

  // Drawer content must include the session_id slug (first 8 chars).
  const drawerContent = await page.textContent('.session-drawer .session-drawer__content');
  expect(drawerContent).toBeTruthy();
  expect(drawerContent).toContain(MOCK_SESSION_ID_1.substring(0, 8));

  // Drawer must show the model name.
  expect(drawerContent).toContain('claude-sonnet-4-6');

  // Drawer must show the agent_name.
  expect(drawerContent).toContain('qa-engineer');

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'sessions-drawer-open.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-SES-03 (c) — Sort by Cost (desc) reorders rows
// ---------------------------------------------------------------------------
test('E2E-SES-03 — Sorting by Cost (desc) reorders session rows correctly', async ({
  page,
}) => {
  await loadSessionsTabScaffold(page);

  // Mock data costs in insertion order: 0.45, 1.20, 0.08
  // Expected cost-desc order:          1.20, 0.45, 0.08

  // Click the Cost column header.  The scaffold starts with data-sort-dir="none"
  // so the first click sets "asc" and the second sets "desc".
  const costHeader = page.locator('th[data-sort="cost"]');
  await costHeader.click();
  await page.waitForTimeout(200);

  // Read current sort direction.
  const dirAfterFirstClick = await costHeader.getAttribute('data-sort-dir');
  if (dirAfterFirstClick !== 'desc') {
    await costHeader.click();
    await page.waitForTimeout(200);
  }

  // Verify the header now says "desc".
  const finalDir = await costHeader.getAttribute('data-sort-dir');
  expect(finalDir).toBe('desc');

  // Read cost cell values from all rows.
  const costTexts = await page.$$eval(
    '.sessions-table tbody tr.session-row .cell-cost',
    (cells) => cells.map((el) => el.textContent?.trim() ?? '')
  );
  expect(costTexts.length).toBe(3);

  // Parse cost values (FE renders as "$1.20", "$0.45", "$0.08").
  const parseCost = (s: string): number => parseFloat(s.replace(/[^0-9.]/g, '')) || 0;
  const costs = costTexts.map(parseCost);

  // Assert descending order.
  expect(costs[0]).toBeGreaterThanOrEqual(costs[1]);
  expect(costs[1]).toBeGreaterThanOrEqual(costs[2]);

  // Verify the highest-cost session (1.20) is first.
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
  // Use the shared bootstrap so addInitScript, page.route, and page.setContent
  // are applied in the correct order (fixes the token-source inconsistency from
  // the prior dispatch).
  await loadSessionsTabScaffold(page);

  // Wait for the badge to appear.
  await page.waitForSelector('#sessions-last-updated', { timeout: 12_000 });

  // The badge updates after the first fetchSessions() completes on load.
  // Wait until the badge text is no longer "Never" (initial placeholder).
  await page.waitForFunction(
    () => {
      const el = document.getElementById('sessions-last-updated');
      return el !== null && el.textContent?.trim() !== 'Never' && el.textContent?.trim() !== '';
    },
    {},
    { timeout: 11_000 }
  );

  const badgeText = await page.textContent('#sessions-last-updated');
  expect(badgeText).toBeTruthy();
  // The badge must contain a timestamp-like string (e.g. "Updated: 18:05:42").
  expect(badgeText?.toLowerCase()).toContain('updated');

  // Now verify the badge updates again within 11 s (the 10 s auto-refresh tick).
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
    if (url.includes('/api/sessions') && !url.match(/\/api\/sessions\/[^/]+\/[^/]+/)) {
      sessionListFetchCount++;
    }
  });

  // Use the shared bootstrap so addInitScript, page.route, and page.setContent
  // are applied in the correct order (fixes the token-source inconsistency from
  // the prior dispatch).  loadSessionsTabScaffold already waits for aria-busy="false"
  // so the first fetch has completed before we record the baseline count.
  await loadSessionsTabScaffold(page);
  const fetchesAfterInit = sessionListFetchCount;

  // Simulate tab backgrounding: override document.hidden = true and dispatch
  // visibilitychange (exact technique from TASKS.md PR5-C6 done criterion).
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', {
      value: true,
      configurable: true,
      writable: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));
  });

  // Wait one full auto-refresh interval (10 s) + 1 s margin.
  await page.waitForTimeout(11_000);
  const fetchesWhileHidden = sessionListFetchCount - fetchesAfterInit;

  // Must be 0.  Tolerance of 1 in case a tick fired before the event propagated.
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
