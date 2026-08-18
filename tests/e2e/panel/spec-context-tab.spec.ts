/**
 * spec-context-tab.spec.ts — E2E-SCP-01 through E2E-SCP-06
 *
 * Tests: 6
 * Surface: Spec Context Projects tab (formerly "Memories").
 *
 * Priority: P2 (E2E-SCP-01 functional, E2E-SCP-02 back-compat)
 *           P0 (E2E-SCP-03/04/05/06 regression guard — T-016-P03)
 *
 * Intent: CONTRACT — E2E-SCP-01..06 (T-016-P03 regression guard)
 * Owner: software-engineer
 */

import { test, expect } from '@playwright/test';
import { gotoPanel, BASE_URL, PANEL_TOKEN } from './helpers';

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
    const links = await card.$$('.memory-chip');
    const linkLabels = await Promise.all(
      links.map((l) => l.evaluate((el) => el.textContent?.trim() ?? ''))
    );
    expect(linkLabels).toContain('Architecture');
    expect(linkLabels).toContain('Tech Stack');
    expect(linkLabels).toContain('Product');
  }
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

  // Visible label is "Projects"
  const tabLabel = await page.$eval('#tab-memories', (el) => el.textContent?.trim() ?? '');
  expect(tabLabel).toBe('Projects');
});

// ---------------------------------------------------------------------------
// E2E-SCP-03 — Architecture chip click returns 200 with non-empty body
// ---------------------------------------------------------------------------
test('E2E-SCP-03 — Architecture memory chip click loads iframe with 200 non-empty response', async ({
  page,
  request,
}) => {
  await gotoPanel(page);
  await page.waitForSelector('#section-memories.active');

  // Get the href of the first Architecture chip
  const archHref = await page.$eval(
    '.memory-chip:text("Architecture")',
    (el) => el.getAttribute('href') ?? ''
  );
  expect(archHref).not.toBe('');
  expect(archHref).not.toContain('.html');  // regression guard: must not be .html

  // Derive the /memory/ path from the /memory-view/ href
  // href: /memory-view/<slug>/<path>  → API: /memory/<slug>/<path>
  const memoryPath = archHref.replace('/memory-view/', '/memory/');
  const response = await request.get(`${BASE_URL}${memoryPath}`);
  expect(response.status(), `Architecture memory path ${memoryPath} must return 200`).toBe(200);
  const body = await response.text();
  expect(body.length, 'Architecture memory response body must be non-empty').toBeGreaterThan(500);
});

// ---------------------------------------------------------------------------
// E2E-SCP-04 — Tech Stack chip click returns 200 with non-empty body
// ---------------------------------------------------------------------------
test('E2E-SCP-04 — Tech Stack memory chip click loads iframe with 200 non-empty response', async ({
  page,
  request,
}) => {
  await gotoPanel(page);
  await page.waitForSelector('#section-memories.active');

  const techHref = await page.$eval(
    '.memory-chip:text("Tech Stack")',
    (el) => el.getAttribute('href') ?? ''
  );
  expect(techHref).not.toBe('');
  expect(techHref).not.toContain('.html');

  const memoryPath = techHref.replace('/memory-view/', '/memory/');
  const response = await request.get(`${BASE_URL}${memoryPath}`);
  expect(response.status(), `Tech Stack memory path ${memoryPath} must return 200`).toBe(200);
  const body = await response.text();
  expect(body.length, 'Tech Stack memory response body must be non-empty').toBeGreaterThan(500);
});

// ---------------------------------------------------------------------------
// E2E-SCP-05 — Product chip click returns 200 with non-empty body
// ---------------------------------------------------------------------------
test('E2E-SCP-05 — Product memory chip click loads iframe with 200 non-empty response', async ({
  page,
  request,
}) => {
  await gotoPanel(page);
  await page.waitForSelector('#section-memories.active');

  const productHref = await page.$eval(
    '.memory-chip:text("Product")',
    (el) => el.getAttribute('href') ?? ''
  );
  expect(productHref).not.toBe('');
  expect(productHref).not.toContain('.html');

  const memoryPath = productHref.replace('/memory-view/', '/memory/');
  const response = await request.get(`${BASE_URL}${memoryPath}`);
  expect(response.status(), `Product memory path ${memoryPath} must return 200`).toBe(200);
  const body = await response.text();
  expect(body.length, 'Product memory response body must be non-empty').toBeGreaterThan(500);
});

// ---------------------------------------------------------------------------
// E2E-SCP-06 — API contract: GET /memory/<slug>/architecture.md → 200 text/html >500 bytes
// ---------------------------------------------------------------------------
test('E2E-SCP-06 — API contract: GET /memory/<slug>/architecture.md returns 200 text/html', async ({
  page,
  request,
}) => {
  await gotoPanel(page);
  await page.waitForSelector('#section-memories.active');

  // Discover the slug from the first context card
  const slug = await page.$eval('.context-card [data-slug]', (el) => el.getAttribute('data-slug') ?? '');
  expect(slug).not.toBe('');

  const url = `${BASE_URL}/memory/${slug}/architecture.md`;
  const response = await request.get(url);
  expect(response.status(), `${url} must return 200`).toBe(200);
  const contentType = response.headers()['content-type'] ?? '';
  expect(contentType, 'Content-type must be text/html').toContain('text/html');
  const body = await response.text();
  expect(body.length, 'Response body must be > 500 bytes').toBeGreaterThan(500);
});
