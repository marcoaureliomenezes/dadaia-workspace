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
 *
 * v0.1.45 panel redesign: the Agentic (`ops`) tab was deleted along with the
 * agents grid, personas UI, legacy workflow-DAG cards, and the Kanban view.
 * The surviving nav is exactly: Projects (`memories`), Workflows, Sessions,
 * Reports, Academy, Servers.
 */
export async function activateTab(
  page: Page,
  sectionId: 'memories' | 'servers' | 'sessions' | 'reports' | 'academy' | 'workflows'
): Promise<void> {
  const tabId = `#tab-${sectionId}`;
  await page.click(tabId);
  await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });
}

/**
 * Expand a Workflows-tab diagram card and wait for its inline per-step model
 * pickers to hydrate.
 *
 * v0.1.45 redesign: the Workflows tab LEADS with `.dadaia-wf-catalog` diagram
 * cards, each a native `<details class="dadaia-wf-card" data-workflow="<id>">`.
 * Expanding a card (clicking its `<summary>`) reveals the flow strip
 * (`.dadaia-wf-flux`) and one `.dadaia-wf-step` card per step. The per-step
 * model governance moved INTO the expand: every model-driven step carries a
 * `.wf-step-picker` mount that `workflow-policy.js` hydrates with a `.wfp-picker`
 * (harness segment + `.wfp-profile-select` + diff + reset). There is no longer a
 * separate collapsed "Model policy" matrix.
 *
 * The picker mounts exist in the DOM even while the card is collapsed, but they
 * are only interactable once the `<details>` is open — so any test that clicks a
 * picker must expand its card first.
 */
export async function expandWorkflowCard(page: Page, workflowId: string): Promise<void> {
  const card = page.locator(`details.dadaia-wf-card[data-workflow="${workflowId}"]`);
  await card.waitFor({ state: 'attached', timeout: 8000 });
  const isOpen = await card.evaluate((el) => (el as HTMLDetailsElement).open);
  if (!isOpen) {
    await card.locator('summary.dadaia-wf-card-summary').click();
  }
  await page.waitForFunction(
    (wf) => {
      const d = document.querySelector(
        `details.dadaia-wf-card[data-workflow="${wf}"]`
      ) as HTMLDetailsElement | null;
      if (!d || !d.open) {
        return false;
      }
      // The inline picker is hydrated by workflow-policy.js after the catalog loads.
      return !!d.querySelector('.wf-step-picker .wfp-picker');
    },
    workflowId,
    { timeout: 15000 }
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
