/**
 * ops-tab.spec.ts — E2E tests for the consolidated Ops tab (T-016-P09)
 *
 * The Ops tab merges Agents + Workflows + Kanban into a single scrollable panel.
 * Each appears as a labelled sub-section stacked vertically.
 *
 * Tests:
 *   OPS-01: Ops tab exists in the nav bar, Agents/Workflows/Kanban tabs are gone.
 *   OPS-02: Clicking Ops reveals all three sub-sections in the DOM.
 *   OPS-03: Agents sub-section loads real agent cards (content contract preserved).
 *   OPS-04: Workflows sub-section loads real workflow cards.
 *   OPS-05: Kanban sub-section renders the board (may be empty — that is fine).
 *   OPS-06: Full guard tour (mirrors GUARD-01/02 intent for the merged tab).
 */

import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, authHeaders, BASE_URL } from './helpers';

// ---------------------------------------------------------------------------
// OPS-01 — Ops tab present; individual Agents/Workflows/Kanban tabs absent
// ---------------------------------------------------------------------------
test('OPS-01 — Agentic + first-class Workflows tabs present; Agents/Kanban tabs are absent', async ({ page }) => {
  await gotoPanel(page);
  await page.waitForSelector('[role="tab"]');

  const tabTexts = await page.$$eval('[role="tab"]', (els) =>
    els.map((el) => el.textContent?.trim() ?? '')
  );

  expect(tabTexts).toContain('Agentic');
  // v0.1.28 (D-5) promoted Workflows back to a first-class top-level tab — the model-
  // governance control plane. Agents and Kanban remain consolidated under Agentic.
  expect(tabTexts).toContain('Workflows');
  expect(tabTexts).not.toContain('Agents');
  expect(tabTexts).not.toContain('Kanban');

  // The per-feature Agents/Kanban tabs stay consolidated under Agentic; Workflows is
  // now its own first-class tab.
  expect(await page.$('#tab-agents')).toBeNull();
  expect(await page.$('#tab-kanban')).toBeNull();
  expect(await page.$('#tab-workflows')).not.toBeNull();
});

// ---------------------------------------------------------------------------
// OPS-02 — Clicking Ops activates section-ops; sub-sections are visible
// ---------------------------------------------------------------------------
test('OPS-02 — Clicking Agentic activates section-ops with Agents, Personas, Workflows, and Kanban sub-sections', async ({ page }) => {
  await gotoPanel(page);
  await activateTab(page, 'ops');

  // The section must be active
  const sectionActive = await page.$eval('#section-ops', (el) =>
    el.classList.contains('active')
  );
  expect(sectionActive).toBe(true);

  // The Agentic sub-sections must exist inside section-ops. v0.1.28 (D-5) moved the
  // dadaia-workflows control plane OUT of Agentic into the first-class Workflows tab
  // (section-workflows), so it is no longer a section-ops sub-section. v0.1.45 (T-45-05)
  // reworked Agentic into two role-keyed rosters: Claude sub-agents + Layer-2 personas.
  await expect(page.locator('#section-ops #ops-subsection-agents')).toBeAttached();
  await expect(page.locator('#section-ops #ops-subsection-personas')).toBeAttached();
  await expect(page.locator('#section-ops #ops-subsection-workflows')).toBeAttached();
  await expect(page.locator('#section-ops #ops-subsection-kanban')).toBeAttached();
  // dadaia-workflows now lives under the first-class Workflows tab, not Agentic.
  await expect(page.locator('#section-ops #ops-subsection-dadaia-workflows')).toHaveCount(0);
  await expect(page.locator('#section-workflows #ops-subsection-dadaia-workflows')).toBeAttached();

  // Agents grid must be in the DOM
  await expect(page.locator('#agents-grid')).toBeAttached();
  // Workflows grid must be in the DOM
  await expect(page.locator('#workflows-grid')).toBeAttached();
  // Kanban board must be in the DOM
  await expect(page.locator('#kanban-board')).toBeAttached();

  // Subsection order under Agentic: Agents (top) → Personas → Workflows → Kanban (bottom).
  const subsectionIds = await page.$$eval(
    '#section-ops .ops-subsection',
    (els) => els.map((el) => el.id)
  );
  expect(subsectionIds[0]).toBe('ops-subsection-agents');
  expect(subsectionIds[1]).toBe('ops-subsection-personas');
  expect(subsectionIds[2]).toBe('ops-subsection-workflows');
  expect(subsectionIds[3]).toBe('ops-subsection-kanban');
});

// ---------------------------------------------------------------------------
// OPS-03 — Agents sub-section loads real cards
// ---------------------------------------------------------------------------
test('OPS-03 — Agents sub-section loads real agent cards inside the Ops tab', async ({ page }) => {
  await gotoPanel(page);
  await activateTab(page, 'ops');
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 15000 });

  const cards = page.locator('#agents-grid .agent-card:not(.agent-card--skeleton)');
  const count = await cards.count();
  expect(count).toBeGreaterThan(0);

  const first = cards.first();
  // Minimalist card redesign (ab859c7): status badge removed from the collapsed
  // card; the Model fact (real id or explicit "inherited default") is the
  // non-empty content contract now.
  await expect(first.locator('.agent-card__name')).toHaveText(/\S+/);
  await expect(
    first.locator('.agent-card__model-id, .agent-card__model-inherited')
  ).toHaveText(/\S+/);
});

// ---------------------------------------------------------------------------
// OPS-04 — Workflows sub-section loads real workflow cards
// ---------------------------------------------------------------------------
test('OPS-04 — Workflows sub-section loads real workflow cards inside the Ops tab', async ({ page }) => {
  await gotoPanel(page);
  await activateTab(page, 'ops');
  await page.waitForSelector(
    '#workflows-grid .workflow-card:not(.workflow-card--skeleton), #workflows-empty:not([hidden])',
    { timeout: 15000 }
  );

  const cards = page.locator('#workflows-grid .workflow-card:not(.workflow-card--skeleton)');
  const count = await cards.count();
  expect(count).toBeGreaterThan(0);

  const first = cards.first();
  await expect(first.locator('.workflow-card__name')).toHaveText(/\S+/);
  await expect(first.locator('.workflow-stage-badge')).toHaveText(/\d+\s*stage/i);
});

// ---------------------------------------------------------------------------
// OPS-05 — Kanban sub-section renders board (may be empty — that is fine)
// ---------------------------------------------------------------------------
test('OPS-05 — Kanban sub-section renders (board or empty message) inside the Ops tab', async ({ page }) => {
  await gotoPanel(page);
  await activateTab(page, 'ops');

  // Kanban board initialises on DOMContentLoaded — wait for either a lane or
  // the empty-board message to appear.
  await page.waitForSelector(
    '#kanban-board .kanban-lane, #kanban-board .kanban-board-empty, #kanban-board .kanban-error',
    { timeout: 15000 }
  );

  // #kanban-board must be visible (not hidden by CSS)
  await expect(page.locator('#kanban-board')).toBeVisible();
});

// ---------------------------------------------------------------------------
// OPS-06 — No 4xx/5xx or console errors when touring the Ops tab (GUARD)
// ---------------------------------------------------------------------------
test('OPS-06 — No HTTP errors or console errors when clicking the Ops tab', async ({ page }) => {
  const failedResponses: Array<{ url: string; status: number }> = [];
  const consoleErrors: string[] = [];

  page.on('response', (response) => {
    const status = response.status();
    if (status >= 400) {
      failedResponses.push({ url: response.url(), status });
    }
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (text.includes('Content-Security-Policy') && text.includes('meta')) { return; }
      if (text.includes('favicon')) { return; }
      consoleErrors.push(text);
    }
  });

  await gotoPanel(page);
  await activateTab(page, 'ops');

  // Wait for agents and workflows to settle
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 15000 });
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});

  const httpMsg = failedResponses.map((r) => `  ${r.status} ${r.url}`).join('\n');
  expect(failedResponses, `HTTP errors during Ops tab activation:\n${httpMsg}`).toHaveLength(0);

  const consoleMsg = consoleErrors.join('\n  ');
  expect(consoleErrors, `Console errors during Ops tab activation:\n  ${consoleMsg}`).toHaveLength(0);
});
