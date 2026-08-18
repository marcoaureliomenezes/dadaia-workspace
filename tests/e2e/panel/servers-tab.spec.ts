/**
 * servers-tab.spec.ts — E2E-SRV-01
 *
 * Tests: 1
 * Surface: Servers tab smoke test.
 *
 * Priority: P2 (smoke only; servers tab is low priority in R3)
 *
 * Intent: CONTRACT — v0.4.3 A18.2 (E2E-SRV-01 servers tab smoke)
 * Owner: software-engineer
 */

import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab } from './helpers';

// ---------------------------------------------------------------------------
// E2E-SRV-01 — Servers tab smoke: activates without error
// ---------------------------------------------------------------------------
test('E2E-SRV-01 — Servers tab activates without console errors or 5xx responses', async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  const serverErrors: Array<{ url: string; status: number }> = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('response', (response) => {
    if (response.status() >= 500) {
      serverErrors.push({ url: response.url(), status: response.status() });
    }
  });

  await gotoPanel(page);
  await activateTab(page, 'servers');

  // Section must be visible
  const sectionVisible = await page.$eval('#section-servers', (el) =>
    el.classList.contains('active')
  );
  expect(sectionVisible).toBe(true);

  // No 5xx errors
  expect(serverErrors).toHaveLength(0);

  // No JS errors (excluding favicon 404s which are expected)
  const nonFaviconErrors = consoleErrors.filter((e) => !e.includes('favicon'));
  expect(nonFaviconErrors).toHaveLength(0);
});
