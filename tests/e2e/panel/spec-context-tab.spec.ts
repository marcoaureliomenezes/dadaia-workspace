/**
 * spec-context-tab.spec.ts — E2E-SCP-01 through E2E-SCP-02
 *
 * Tests: 2
 * Surface: Spec Context Projects tab (formerly "Memories").
 *
 * Priority: P2 (E2E-SCP-01 functional, E2E-SCP-02 back-compat)
 */

import { test, expect } from '@playwright/test';
import { gotoPanel } from './helpers';
import * as path from 'path';

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');

// ---------------------------------------------------------------------------
// E2E-SCP-01 — Spec Context Projects tab renders context cards
// ---------------------------------------------------------------------------
test('E2E-SCP-01 — Spec Context Projects tab renders context cards with three links', async ({
  page,
}) => {
  await gotoPanel(page);
  await page.waitForSelector('#section-memories.active');

  // At least one context card must be visible
  const contextCards = await page.$$('.context-card');
  expect(contextCards.length).toBeGreaterThan(0);

  // Each visible card must have the three required memory links
  for (const card of contextCards) {
    const links = await card.$$('.memory-link');
    const linkLabels = await Promise.all(
      links.map((l) => l.$eval('.memory-link-label', (el) => el.textContent?.trim() ?? ''))
    );
    expect(linkLabels).toContain('Architecture');
    expect(linkLabels).toContain('Tech Stack');
    expect(linkLabels).toContain('Product');
  }

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'spec-context-tab.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-SCP-02 — Internal section ID back-compat
// ---------------------------------------------------------------------------
test('E2E-SCP-02 — Internal DOM IDs section-memories and tab-memories are preserved', async ({
  page,
}) => {
  await gotoPanel(page);
  await page.waitForSelector('#section-memories');

  // Back-compat: id="section-memories" must exist
  const sectionExists = await page.$('#section-memories');
  expect(sectionExists).not.toBeNull();

  // Back-compat: id="tab-memories" must exist
  const tabExists = await page.$('#tab-memories');
  expect(tabExists).not.toBeNull();

  // Visible label is "Spec Context Projects", not "Memories"
  const tabLabel = await page.$eval('#tab-memories', (el) => el.textContent?.trim() ?? '');
  expect(tabLabel).toBe('Spec Context Projects');
});
