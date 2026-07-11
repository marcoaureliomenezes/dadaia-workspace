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
 * agents grid, personas UI, legacy workflow-DAG cards, and the Kanban view.
 * v0.1.79 panel agentic-layers reorg: the standalone Sessions tab was REMOVED
 * — its cost/telemetry dashboard is now a sub-section rendered inside the
 * `subagents` ("1º Agentic Layer") tabpanel. There is no `#tab-sessions` /
 * `#section-sessions.active` to wait on any more; use
 * `activateTab(page, 'subagents')` and locate `#section-sessions` within the
 * opened tabpanel (see `activateSessionsSubsection` below). The surviving
 * primary nav is exactly: Projects (`memories`), 2º Agentic Layer
 * (`workflows`), 1º Agentic Layer (`subagents`), Reports, Academy, Servers.
 */
export async function activateTab(
  page: Page,
  sectionId: 'memories' | 'servers' | 'reports' | 'academy' | 'workflows' | 'subagents'
): Promise<void> {
  const tabId = `#tab-${sectionId}`;
  await page.click(tabId);
  await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });
}

/**
 * Activate the "1º Agentic Layer" (subagents) tab and wait for the relocated
 * Sessions cost/telemetry dashboard sub-section to be present in the DOM
 * (v0.1.79 — the Sessions tab merged into this tabpanel).
 */
export async function activateSessionsSubsection(page: Page): Promise<void> {
  await activateTab(page, 'subagents');
  await page.waitForSelector('#section-subagents #section-sessions', { timeout: 8000 });
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

/**
 * Deterministic save wait (FR11, v0.1.65): arm a `waitForResponse` for the
 * matching PUT BEFORE clicking the trigger, then await the 200 response.
 *
 * Rationale: the workflow-policy banner reuses the same `wfp-banner--ok` class
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
