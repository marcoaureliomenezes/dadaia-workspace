/**
 * response-guard.spec.ts — E2E-GUARD-01 and E2E-GUARD-02
 *
 * Tests: 2
 * Surface: Global guard — any status >= 400 or console error during a full
 *          tab tour (all 6 tabs) plus clicking the first memory chip and
 *          waiting for networkidle.
 *
 * Priority: P0 — these guards must run before any other panel tests.
 * If these fail, other tests are unreliable.
 *
 * E2E-GUARD-01: Register a response listener BEFORE navigation. Fail on ANY
 *   response status >= 400 during a full tab tour (workflows, sessions, reports,
 *   academy, servers, memories) PLUS clicking the first memory chip and
 *   waiting for networkidle. Include the failing URL+status list in the
 *   assertion message.
 *
 * E2E-GUARD-02: Fail on ANY console error across the same tour (all tabs plus
 *   memory chip click). CSP-policy-string console errors are excluded because
 *   they are browser-internal metadata logs, not JS errors from the panel.
 *
 * v0.1.45 redesign: the Agentic (ops) tab, agents grid, personas UI, and Kanban
 *   view were removed. The tour now covers the surviving nav set.
 */

import { test, expect } from '@playwright/test';
import { gotoPanel, PANEL_TOKEN, BASE_URL } from './helpers';

// ---------------------------------------------------------------------------
// Tab tour definition — 6 tabs in display order (v0.1.45 nav set)
// ---------------------------------------------------------------------------
const ALL_TABS = [
  { tabId: '#tab-workflows', sectionId: 'workflows', label: 'Workflows' },
  { tabId: '#tab-sessions', sectionId: 'sessions', label: 'Sessions' },
  { tabId: '#tab-reports', sectionId: 'reports', label: 'Reports' },
  { tabId: '#tab-academy', sectionId: 'academy', label: 'Academy' },
  { tabId: '#tab-servers', sectionId: 'servers', label: 'Servers' },
  { tabId: '#tab-memories', sectionId: 'memories', label: 'Spec Context Projects' },
] as const;

// ---------------------------------------------------------------------------
// E2E-GUARD-01 — No 4xx/5xx responses during full tab tour + memory chip
// ---------------------------------------------------------------------------
test('E2E-GUARD-01 — No status >= 400 during full tab tour and memory chip click', async ({
  page,
}) => {
  const failedResponses: Array<{ url: string; status: number }> = [];

  // Register listener BEFORE navigation
  page.on('response', (response) => {
    const status = response.status();
    if (status >= 400) {
      failedResponses.push({ url: response.url(), status });
    }
  });

  // Navigate to panel
  await gotoPanel(page);
  await page.waitForSelector('[role="tab"]');

  // Tour every tab
  for (const { tabId, sectionId } of ALL_TABS) {
    await page.click(tabId);
    await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });
    // Allow any lazy data loads to settle
    await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {
      // networkidle may timeout on tabs with persistent connections — that is
      // acceptable; we only care that no 4xx/5xx fired.
    });
  }

  // Go back to memories tab and click the first memory chip (if any card exists)
  await page.click('#tab-memories');
  await page.waitForSelector('#section-memories.active', { timeout: 8000 });

  const firstChip = await page.$('.memory-chip');
  if (firstChip) {
    // Open chip in the panel (it navigates to /memory-view/...)
    await firstChip.click();
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {
      // networkidle may timeout if the memory frame loads slowly
    });
  }

  // Build a human-readable failure message listing every failing request
  const message = failedResponses
    .map((r) => `  ${r.status} ${r.url}`)
    .join('\n');

  expect(failedResponses, `HTTP responses >= 400 detected:\n${message}`).toHaveLength(0);
});

// ---------------------------------------------------------------------------
// E2E-GUARD-02 — No console errors during full tab tour + memory chip
// ---------------------------------------------------------------------------
test('E2E-GUARD-02 — No console errors during full tab tour and memory chip click', async ({
  page,
}) => {
  const consoleErrors: string[] = [];

  // Register listener BEFORE navigation
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Exclude browser-internal CSP metadata logs (not panel JS errors)
      if (text.includes('Content-Security-Policy') && text.includes('meta')) {
        return;
      }
      consoleErrors.push(text);
    }
  });

  // Navigate to panel
  await gotoPanel(page);
  await page.waitForSelector('[role="tab"]');

  // Tour every tab
  for (const { tabId, sectionId } of ALL_TABS) {
    await page.click(tabId);
    await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });
    await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  }

  // Go back to memories tab and click the first memory chip (if any card exists)
  await page.click('#tab-memories');
  await page.waitForSelector('#section-memories.active', { timeout: 8000 });

  const firstChip = await page.$('.memory-chip');
  if (firstChip) {
    await firstChip.click();
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
  }

  // Filter known benign browser console entries
  const hardErrors = consoleErrors.filter((e) => {
    // favicon 404s from test environment are not panel bugs
    if (e.includes('favicon')) return false;
    return true;
  });

  const message = hardErrors.join('\n  ');
  expect(hardErrors, `Console errors detected:\n  ${message}`).toHaveLength(0);
});
