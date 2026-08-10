/**
 * sessions-dashboard.spec.ts — E2E-SES-DASH-01..04 (panel-plumbing v0.1.52 FR2 / AC-2, AC-7a)
 *
 * The Sessions tab is dashboard-only: a 4-card cost aggregate + a cost-unknown
 * banner rendered by sessions.js from the /api/sessions aggregate envelope. The
 * list table, sort/filter, detail drawer, skeleton rows, and 10s auto-refresh
 * were removed (v0.1.52). These journeys drive the REAL panel + REAL sessions.js
 * with /api/sessions mocked per FR1 cost-known matrix case, asserting the four
 * cards' DOM content, the runtime-driven banner, and (E2E-GUARD-02 posture) that
 * the tab visit is console-error-free.
 *
 * Runtime selection is seeded via localStorage before navigation (runtime.js reads
 * `dadaia-panel-runtime`); sessions.js then fetches ?runtime=<runtime>, which the
 * mock scopes its aggregate to. The empty sandbox store is irrelevant because the
 * aggregate endpoint is intercepted.
 *
 * v0.1.79 amendment: the standalone Sessions tab was removed — the dashboard is now
 * a sub-section rendered inside the "Agents" (`#section-subagents`)
 * tabpanel. `activateSessionsSubsection()` opens that tab and waits for the
 * relocated `#section-sessions` mount; `sessions.js` and the `/api/sessions`
 * contract are otherwise unchanged.
 */

import { test, expect, type Page, type Route } from '@playwright/test';
import { gotoPanel, activateSessionsSubsection } from './helpers';

// ---------------------------------------------------------------------------
// Aggregate envelope shape (SPEC §FR1). `top_agent` is {name, session_count} | null.
// ---------------------------------------------------------------------------
interface TopAgent {
  name: string;
  session_count: number;
}
interface SessionAggregate {
  runtime: string;
  total_sessions: number;
  active_sessions: number;
  total_cost_usd: number | null;
  cost_known: boolean;
  total_messages: number;
  top_agent: TopAgent | null;
  generated_at: string;
}

// ---------------------------------------------------------------------------
// Matrix-case fixtures.
// ---------------------------------------------------------------------------
const CLAUDE_WITH_COST: SessionAggregate = {
  runtime: 'claude',
  total_sessions: 3,
  active_sessions: 1,
  total_cost_usd: 1.73,
  cost_known: true,
  total_messages: 67,
  top_agent: { name: 'qa-engineer', session_count: 2 },
  generated_at: '2026-07-02T18:00:00+00:00',
};

const CLAUDE_NULL_COST: SessionAggregate = {
  runtime: 'claude',
  total_sessions: 2,
  active_sessions: 0,
  total_cost_usd: null,
  cost_known: false,
  total_messages: 8,
  top_agent: null,
  generated_at: '2026-07-02T18:00:00+00:00',
};

const CODEX_AGG: SessionAggregate = {
  runtime: 'codex',
  total_sessions: 5,
  active_sessions: 2,
  total_cost_usd: null,
  cost_known: false,
  total_messages: 40,
  top_agent: { name: 'operator', session_count: 5 },
  generated_at: '2026-07-02T18:00:00+00:00',
};

const PI_AGG: SessionAggregate = {
  runtime: 'pi',
  total_sessions: 1,
  active_sessions: 0,
  total_cost_usd: null,
  cost_known: false,
  total_messages: 4,
  top_agent: null,
  generated_at: '2026-07-02T18:00:00+00:00',
};

// ---------------------------------------------------------------------------
// Helpers.
// ---------------------------------------------------------------------------

/** Intercept every /api/sessions request and serve the given aggregate. */
async function mockAggregate(page: Page, aggregate: SessionAggregate): Promise<void> {
  await page.route('**/api/sessions**', (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify(aggregate),
    });
  });
}

/** Seed the persisted runtime so sessions.js fetches ?runtime=<runtime>. */
async function seedRuntime(page: Page, runtime: string): Promise<void> {
  await page.addInitScript((rt) => {
    try {
      localStorage.setItem('dadaia-panel-runtime', rt as string);
    } catch (_) {
      /* localStorage unavailable — runtime defaults to claude */
    }
  }, runtime);
}

/** Locate the value span of the stat card whose label matches. */
function statValue(page: Page, label: string) {
  return page
    .locator('.sessions-stat-card')
    .filter({ has: page.locator('.sessions-stat-label', { hasText: label }) })
    .locator('.sessions-stat-value');
}

/** Locate the sub-label span of the stat card whose label matches. */
function statSub(page: Page, label: string) {
  return page
    .locator('.sessions-stat-card')
    .filter({ has: page.locator('.sessions-stat-label', { hasText: label }) })
    .locator('.sessions-stat-sub');
}

/**
 * Register a console-error collector BEFORE navigation, filtering the known
 * browser-internal CSP-metadata noise + favicon 404s (mirrors response-guard.spec.ts).
 */
function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    if (text.includes('Content-Security-Policy') && text.includes('meta')) return;
    if (text.includes('favicon')) return;
    errors.push(text);
  });
  return errors;
}

async function assertNoConsoleErrors(page: Page, errors: string[]): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  expect(errors, `Console errors detected:\n  ${errors.join('\n  ')}`).toHaveLength(0);
}

// ---------------------------------------------------------------------------
// E2E-SES-DASH-01 — claude with cost → '$X.XX', "N active", top agent + count
// ---------------------------------------------------------------------------
test('E2E-SES-DASH-01 — claude with cost renders $X.XX, N-active, and top agent', async ({
  page,
}) => {
  const errors = collectConsoleErrors(page);
  await seedRuntime(page, 'claude');
  await mockAggregate(page, CLAUDE_WITH_COST);

  await gotoPanel(page);
  await activateSessionsSubsection(page);

  await expect(statValue(page, 'Total Cost')).toHaveText('$1.73');
  await expect(statValue(page, 'Total Sessions')).toHaveText('3');
  await expect(statSub(page, 'Total Sessions')).toHaveText('1 active');
  await expect(statValue(page, 'AI Turns')).toHaveText('67');
  await expect(statValue(page, 'Top Agent')).toHaveText('qa-engineer');
  await expect(statSub(page, 'Top Agent')).toHaveText('2 sessions');

  // Banner stays hidden for the cost-known claude runtime.
  await expect(page.locator('#sessions-banner')).toBeHidden();

  await assertNoConsoleErrors(page, errors);
});

// ---------------------------------------------------------------------------
// E2E-SES-DASH-02 — claude, null cost → '—' (NOT 'N/A'), null top agent → '—'
// ---------------------------------------------------------------------------
test('E2E-SES-DASH-02 — claude with null cost renders the em-dash, not N/A', async ({
  page,
}) => {
  const errors = collectConsoleErrors(page);
  await seedRuntime(page, 'claude');
  await mockAggregate(page, CLAUDE_NULL_COST);

  await gotoPanel(page);
  await activateSessionsSubsection(page);

  await expect(statValue(page, 'Total Cost')).toHaveText('—');
  await expect(statValue(page, 'Total Sessions')).toHaveText('2');
  await expect(statSub(page, 'Total Sessions')).toHaveText('none active');
  await expect(statValue(page, 'Top Agent')).toHaveText('—');

  await expect(page.locator('#sessions-banner')).toBeHidden();

  await assertNoConsoleErrors(page, errors);
});

// ---------------------------------------------------------------------------
// E2E-SES-DASH-03 — codex → 'N/A' cost + banner visible
// ---------------------------------------------------------------------------
test('E2E-SES-DASH-03 — codex renders N/A cost and the cost-unknown banner', async ({
  page,
}) => {
  const errors = collectConsoleErrors(page);
  await seedRuntime(page, 'codex');
  await mockAggregate(page, CODEX_AGG);

  await gotoPanel(page);
  await activateSessionsSubsection(page);

  await expect(statValue(page, 'Total Cost')).toHaveText('N/A');
  await expect(statValue(page, 'Total Sessions')).toHaveText('5');
  await expect(statSub(page, 'Total Sessions')).toHaveText('2 active');

  const banner = page.locator('#sessions-banner');
  await expect(banner).toBeVisible();
  await expect(banner).toHaveText('Cost not tracked for Codex');

  await assertNoConsoleErrors(page, errors);
});

// ---------------------------------------------------------------------------
// E2E-SES-DASH-04 — pi → 'N/A' cost + PI banner visible
// ---------------------------------------------------------------------------
test('E2E-SES-DASH-04 — pi renders N/A cost and the PI cost-unknown banner', async ({
  page,
}) => {
  const errors = collectConsoleErrors(page);
  await seedRuntime(page, 'pi');
  await mockAggregate(page, PI_AGG);

  await gotoPanel(page);
  await activateSessionsSubsection(page);

  await expect(statValue(page, 'Total Cost')).toHaveText('N/A');

  const banner = page.locator('#sessions-banner');
  await expect(banner).toBeVisible();
  await expect(banner).toHaveText('Cost not tracked for PI');

  await assertNoConsoleErrors(page, errors);
});
