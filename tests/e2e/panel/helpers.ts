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
export const PANEL_PORT: number = parseInt(process.env.PANEL_TEST_PORT || '4999', 10);
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
 */
export async function activateTab(
  page: Page,
  sectionId: 'memories' | 'agents' | 'workflows' | 'servers'
): Promise<void> {
  const tabId = `#tab-${sectionId}`;
  await page.click(tabId);
  await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });
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
