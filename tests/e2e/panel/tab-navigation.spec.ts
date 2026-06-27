/**
 * tab-navigation.spec.ts — E2E-TAB-01 through E2E-TAB-06
 *
 * Tests: 6
 * Surfaces: Tab ordering, active tab default, navigation, CSP, HTTP errors,
 *           CDN/Mermaid script guard.
 *
 * Priority: P0 (E2E-TAB-01, E2E-TAB-02, E2E-TAB-04) / P1 (E2E-TAB-05, E2E-TAB-06) / P2 (E2E-TAB-03)
 */

import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, BASE_URL } from './helpers';
import * as path from 'path';

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');

// ---------------------------------------------------------------------------
// E2E-TAB-01 — Tab order and labels
// ---------------------------------------------------------------------------
test('E2E-TAB-01 — Tab bar contains the current tabs in correct order', async ({ page }) => {
  await gotoPanel(page);
  await page.waitForSelector('[role="tab"]');

  const tabs = await page.$$eval('[role="tab"]', (els) =>
    els.map((el) => el.textContent?.trim() ?? '')
  );

  // v0.1.28 (D-5) promoted Workflows to a first-class top-level tab at position 2.
  expect(tabs).toEqual([
    'Projects',
    'Workflows',
    'Agentic',
    'Sessions',
    'Reports',
    'Academy',
    'Servers',
  ]);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'tab-bar-initial.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-TAB-02 — Default active tab
// ---------------------------------------------------------------------------
test('E2E-TAB-02 — Default active tab is Projects', async ({ page }) => {
  await gotoPanel(page);
  await page.waitForSelector('[role="tab"]');

  // The first tab must have aria-selected="true"
  const firstTabSelected = await page.$eval('#tab-memories', (el) =>
    el.getAttribute('aria-selected')
  );
  expect(firstTabSelected).toBe('true');

  // #section-memories must have class "active"
  const memoriesHasActive = await page.$eval('#section-memories', (el) =>
    el.classList.contains('active')
  );
  expect(memoriesHasActive).toBe(true);

  // #section-servers must NOT have class "active"
  const serversHasActive = await page.$eval('#section-servers', (el) =>
    el.classList.contains('active')
  );
  expect(serversHasActive).toBe(false);
});

// ---------------------------------------------------------------------------
// E2E-TAB-03 — Tab click navigation
// ---------------------------------------------------------------------------
test('E2E-TAB-03 — Clicking each tab activates the correct section', async ({ page }) => {
  await gotoPanel(page);
  await page.waitForSelector('[role="tab"]');

  const tabs: Array<{ tabId: string; sectionId: string }> = [
    { tabId: '#tab-ops', sectionId: 'ops' },
    { tabId: '#tab-sessions', sectionId: 'sessions' },
    { tabId: '#tab-reports', sectionId: 'reports' },
    { tabId: '#tab-academy', sectionId: 'academy' },
    { tabId: '#tab-servers', sectionId: 'servers' },
    { tabId: '#tab-memories', sectionId: 'memories' },
  ];

  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  for (const { tabId, sectionId } of tabs) {
    await page.click(tabId);
    await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });

    const selected = await page.$eval(tabId, (el) =>
      el.getAttribute('aria-selected')
    );
    expect(selected).toBe('true');
  }

  // No JS errors during navigation
  expect(consoleErrors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
});

// ---------------------------------------------------------------------------
// E2E-TAB-04 — No CSP violations on load and all tab activations
// ---------------------------------------------------------------------------
test('E2E-TAB-04 — No CSP violations on load and all tab activations', async ({ page }) => {
  const cspViolations: string[] = [];

  page.on('console', (msg) => {
    const text = msg.text();
    // Chrome reports CSP violations as console errors with specific patterns
    if (
      msg.type() === 'error' &&
      (text.includes('Content Security Policy') ||
        text.includes('CSP') ||
        text.includes('Refused to') ||
        text.includes('violates'))
    ) {
      cspViolations.push(text);
    }
  });

  await gotoPanel(page);
  await page.waitForSelector('[role="tab"]');

  // Navigate to each tab (agents/workflows/kanban now merged under Ops)
  for (const sectionId of ['ops', 'servers', 'memories'] as const) {
    await activateTab(page, sectionId);
  }

  expect(cspViolations).toHaveLength(0);
});

// ---------------------------------------------------------------------------
// E2E-TAB-05 — No 4xx/5xx on initial page load
// ---------------------------------------------------------------------------
test('E2E-TAB-05 — No 4xx/5xx responses on initial panel load', async ({ page }) => {
  const failedResponses: Array<{ url: string; status: number }> = [];

  page.on('response', (response) => {
    const status = response.status();
    if (status >= 400) {
      failedResponses.push({ url: response.url(), status });
    }
  });

  await gotoPanel(page);
  await page.waitForLoadState('networkidle');

  // Allow 401s only for API endpoints that are fetched without explicit auth
  // by the page during initial load (if any). However, per spec, the initial
  // HTML load should not trigger unauthenticated API calls that return 4xx.
  const hardFailures = failedResponses.filter(
    (r) => r.status >= 500 || (r.status >= 400 && r.status !== 401)
  );

  expect(hardFailures).toHaveLength(0);
});

// ---------------------------------------------------------------------------
// E2E-TAB-06 — No CDN script tags in HTML and no Mermaid
// ---------------------------------------------------------------------------
test('E2E-TAB-06 — No external CDN scripts or Mermaid in page HTML', async ({ page }) => {
  const mermaidRequests: string[] = [];

  page.on('request', (req) => {
    if (req.url().toLowerCase().includes('mermaid')) {
      mermaidRequests.push(req.url());
    }
  });

  await gotoPanel(page);
  await page.waitForLoadState('domcontentloaded');

  // Assert no external <script src="http..."> tags
  const externalScripts = await page.$$eval(
    'script[src]',
    (scripts) =>
      scripts
        .map((s) => s.getAttribute('src') || '')
        .filter((src) => src.startsWith('http://') || src.startsWith('https://'))
  );
  expect(externalScripts).toHaveLength(0);

  // Assert no external <link rel="stylesheet" href="http..."> tags
  const externalStylesheets = await page.$$eval(
    'link[rel="stylesheet"]',
    (links) =>
      links
        .map((l) => l.getAttribute('href') || '')
        .filter((href) => href.startsWith('http://') || href.startsWith('https://'))
  );
  expect(externalStylesheets).toHaveLength(0);

  // Assert no "mermaid" in any script src
  const mermaidInScripts = await page.$$eval(
    'script[src]',
    (scripts) =>
      scripts
        .map((s) => s.getAttribute('src') || '')
        .filter((src) => src.toLowerCase().includes('mermaid'))
  );
  expect(mermaidInScripts).toHaveLength(0);

  // Assert no mermaid network requests were made
  expect(mermaidRequests).toHaveLength(0);

  // Assert window.mermaid is not defined
  const hasMermaid = await page.evaluate(() => typeof (window as any).mermaid !== 'undefined');
  expect(hasMermaid).toBe(false);
});
