/**
 * Shared helpers for the panel E2E test suite.
 *
 * Design principles:
 *   - All helpers are pure functions; they take a `page` or `request` and return
 *     a result — they never access global state beyond the fixtures below.
 *   - The panel Bearer token is read once from disk by this helper.
 *     module and re-exported here for convenience.
 *   - Zero mocks; tests exercise the real running panel.
 */

import * as fs from 'fs';
import * as path from 'path';
import { Page, APIRequestContext } from '@playwright/test';

// ---------------------------------------------------------------------------
// Token resolution
// ---------------------------------------------------------------------------

function resolvePanelToken(): string {
  const tokenPath = path.join(
    process.env.HOME || process.env.USERPROFILE || '',
    '.dadaia', 'state', 'panel.token'
  );
  try {
    return fs.readFileSync(tokenPath, 'utf-8').trim();
  } catch {
    return '';
  }
}

export const PANEL_TOKEN: string = resolvePanelToken();
// 4999 is the conventional operator-local live panel port — the e2e webServer
// must never collide with it (T-65-14 CI-fix amendment; kept in lockstep
// with playwright.config.ts's own PANEL_PORT fallback).
export const PANEL_PORT: number = parseInt(process.env.PANEL_TEST_PORT || '5065', 10);
export const BASE_URL: string = `http://127.0.0.1:${PANEL_PORT}`;

// ---------------------------------------------------------------------------
// Navigation helpers
// ---------------------------------------------------------------------------

/**
 * Navigate to the panel root and inject the Bearer token into the session cookie
 * so subsequent /api/* requests from the page are authorised.
 *
 * The panel's auth model: the first load URL carries ?token=<value>; the client JS
 * stores it in sessionStorage and attaches it as `Authorization: Bearer <token>`
 * on every authedFetch() call.  We replicate that by navigating to the token URL.
 */
export async function gotoPanel(page: Page, options?: { path?: string }): Promise<void> {
  const targetPath = options?.path ?? '/';
  const url = `${BASE_URL}${targetPath}?token=${encodeURIComponent(PANEL_TOKEN)}`;
  await page.goto(url, { waitUntil: 'domcontentloaded' });
}

/**
 * Activate a tab by clicking it and wait for the section to have class "active".
 *
 * v0.1.45 panel redesign: the Agentic (`ops`) tab was deleted along with the
 * agents grid, personas UI, and the Kanban view.
 * v0.1.79 panel agentic-layers reorg: the standalone Sessions tab was REMOVED
 * — its cost/telemetry dashboard is now a sub-section rendered inside the
 * `subagents` ("Agents") tabpanel. There is no `#tab-sessions` /
 * `#section-sessions.active` to wait on any more; use
 * `activateTab(page, 'subagents')` and locate `#section-sessions` within the
 * opened tabpanel (see `activateSessionsSubsection` below). The surviving
 * primary nav is exactly: Projects (`memories`), Agents (`subagents`),
 * Agentic Entities (`entities`), Reports, Academy, Servers (v0.3.0: the
 * 2º Agentic Layer `workflows` tab died with the workflow engine; `entities`
 * renders the abstract-entity registry server-side).
 */
export async function activateTab(
  page: Page,
  sectionId: 'memories' | 'servers' | 'reports' | 'academy' | 'subagents' | 'entities'
): Promise<void> {
  const tabId = `#tab-${sectionId}`;
  await page.click(tabId);
  await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });
}

/**
 * Activate the "Agents" (subagents) tab and wait for the relocated
 * Sessions cost/telemetry dashboard sub-section to be present in the DOM
 * (v0.1.79 — the Sessions tab merged into this tabpanel).
 */
export async function activateSessionsSubsection(page: Page): Promise<void> {
  await activateTab(page, 'subagents');
  await page.waitForSelector('#section-subagents #section-sessions', { timeout: 8000 });
}


/**
 * Deterministic save wait (FR11, v0.1.65): arm a `waitForResponse` for the
 * matching PUT BEFORE clicking the trigger, then await the 200 response.
 *
 * Rationale: the policy banner reuses the same ok-banner class
 * for validate and save outcomes, so a post-save banner assertion can pass
 * instantly against the STALE validate banner while the save PUT is still in
 * flight — any follow-up GET then races the write (the CI flake in
 * `e2e-panel-harness-toggle-ci-flake`). Awaiting the PUT response itself is the
 * only deterministic save signal.
 */
export async function clickAndAwaitPut(
  page: Page,
  triggerSelector: string,
  apiPathFragment: string,
  timeout = 10_000
): Promise<void> {
  const putResponse = page.waitForResponse(
    (res) =>
      res.url().includes(apiPathFragment) &&
      res.request().method() === 'PUT' &&
      res.status() === 200,
    { timeout }
  );
  await page.locator(triggerSelector).click();
  await putResponse;
}

// ---------------------------------------------------------------------------
// API helpers (direct HTTP, no browser rendering)
// ---------------------------------------------------------------------------

export function authHeaders(): Record<string, string> {
  return { Authorization: `Bearer ${PANEL_TOKEN}` };
}

export async function apiGet(
  request: APIRequestContext,
  endpoint: string,
  withAuth = true
) {
  const headers = withAuth ? authHeaders() : {};
  return request.get(`${BASE_URL}${endpoint}`, { headers });
}
