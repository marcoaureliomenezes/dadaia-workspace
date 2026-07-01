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
  // 'agents' merged into 'ops' (T-016-P09). 'workflows' is a first-class tab again
  // (T-28-C-03 / D-5) hosting the model-governance editor.
  sectionId: 'memories' | 'servers' | 'ops' | 'sessions' | 'reports' | 'academy' | 'workflows'
): Promise<void> {
  const tabId = `#tab-${sectionId}`;
  await page.click(tabId);
  await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });
}

/**
 * Expand the Workflows tab's "Model policy" disclosure.
 *
 * v0.1.45 (T-45-08 refinement #1) demoted the per-step model-governance matrix
 * into a collapsed `<details class="wfp-policy">` below the diagram cards. The
 * cards LEAD the tab; the policy matrix is secondary/opt-in. `#wfp-root` is
 * populated on load regardless of the disclosure state, but its controls are
 * `hidden` (display:none) until the `<details>` is open — so any test that
 * interacts with a step row / toolbar must expand it first.
 */
export async function openModelPolicy(page: Page): Promise<void> {
  const details = page.locator('details.wfp-policy');
  await details.waitFor({ state: 'attached', timeout: 8000 });
  const isOpen = await details.evaluate((el) => (el as HTMLDetailsElement).open);
  if (!isOpen) {
    await page.locator('summary.wfp-policy-summary').click();
  }
  await page.waitForFunction(
    () => {
      const d = document.querySelector('details.wfp-policy') as HTMLDetailsElement | null;
      return !!d && d.open;
    },
    { timeout: 8000 }
  );
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
