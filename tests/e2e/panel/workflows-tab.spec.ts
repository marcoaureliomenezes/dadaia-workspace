/**
 * workflows-tab.spec.ts — Workflows tab (v0.1.45 redesign).
 *
 * The Workflows tab LEADS with a catalog of big diagram cards (`.dadaia-wf-catalog`),
 * one native `<details class="dadaia-wf-card">` per dadaia-workflow. The collapsed face
 * is the card the operator scans; expanding it (via the `.dadaia-wf-expand-hint`
 * summary) reveals a FLOW strip (`.dadaia-wf-flux` with a server-rendered SVG fluxogram)
 * plus one `.dadaia-wf-step` card per step, each model-driven step carrying an inline
 * `.wf-step-picker` model dropdown. There is no old DAG modal / detail-view any more.
 *
 * `/api/workflow-catalog` is the sole catalog API and carries the effective model policy.
 */

import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, expandWorkflowCard, authHeaders, BASE_URL } from './helpers';

async function openWorkflowsTab(page: any): Promise<void> {
  await gotoPanel(page);
  await activateTab(page, 'workflows');
  await page.waitForSelector('.dadaia-wf-catalog .dadaia-wf-card', { timeout: 15000 });
}

test('Workflows is a first-class top-level tab leading with diagram cards', async ({ page }) => {
  await gotoPanel(page);
  await expect(page.locator('#tab-workflows')).toBeVisible();
  await activateTab(page, 'workflows');
  await expect(page.locator('#section-workflows.active')).toBeVisible();

  // The catalog of diagram cards leads the tab.
  const cards = page.locator('.dadaia-wf-catalog .dadaia-wf-card');
  expect(await cards.count()).toBeGreaterThan(0);

  // The Agentic (ops) tab and its legacy DAG grid are gone.
  expect(await page.$('#tab-ops')).toBeNull();
  expect(await page.$('#workflows-grid')).toBeNull();
});

test('Each workflow diagram card shows a title, availability badge, and step count', async ({
  page,
}) => {
  await openWorkflowsTab(page);

  const first = page.locator('.dadaia-wf-catalog .dadaia-wf-card').first();
  await expect(first.locator('.dadaia-wf-card-title')).toHaveText(/\S+/);
  await expect(first.locator('.dadaia-wf-badge')).toHaveText(/\S+/);
  await expect(first.locator('.dadaia-wf-step-count')).toHaveText(/\d+\s*steps/i);
  // The card is a native <details> disclosure — collapsed by default.
  const open = await first.evaluate((el) => (el as HTMLDetailsElement).open);
  expect(open).toBe(false);
});

test('Expanding a card reveals the flow strip (SVG fluxogram) and per-step cards', async ({
  page,
}) => {
  await openWorkflowsTab(page);

  // The `implementation` workflow has model-driven steps → its expand hydrates pickers.
  await expandWorkflowCard(page, 'implementation_reviews');
  const card = page.locator('details.dadaia-wf-card[data-workflow="implementation_reviews"]');

  // The flow strip carries a server-rendered SVG fluxogram (no client Mermaid).
  const flux = card.locator('.dadaia-wf-flux');
  await expect(flux).toBeVisible();
  const svg = flux.locator('.dadaia-wf-diagram-svg svg');
  await expect(svg).toBeVisible();
  const svgValid = await card.evaluate((el) => {
    const svgEl = el.querySelector('.dadaia-wf-flux .dadaia-wf-diagram-svg svg');
    if (!svgEl) return false;
    const doc = new DOMParser().parseFromString(svgEl.outerHTML, 'image/svg+xml');
    return doc.querySelector('parsererror') === null;
  });
  expect(svgValid).toBe(true);

  // One formatted step card per step, with a readable header + purpose.
  const steps = card.locator('.dadaia-wf-steps .dadaia-wf-step');
  expect(await steps.count()).toBeGreaterThan(0);
  await expect(steps.first().locator('.dadaia-wf-step-label')).toHaveText(/\S+/);

  // Model-driven steps carry an inline picker; it hydrates on expand.
  await expect(card.locator('.wf-step-picker .wfp-picker').first()).toBeVisible();
});

test('Workflow catalog API returns all governed workflows', async ({ request }) => {
  const response = await request.get(`${BASE_URL}/api/workflow-catalog`, { headers: authHeaders() });
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(Array.isArray(body.workflows)).toBe(true);
  expect(body.workflows.length).toBeGreaterThan(0);

  for (const workflow of body.workflows) {
    expect(typeof workflow.workflow_id).toBe('string');
    expect(workflow.workflow_id.length).toBeGreaterThan(0);
    expect(Array.isArray(workflow.steps)).toBe(true);
    expect(workflow.steps.length).toBeGreaterThan(0);
  }
});

test('Workflow catalog detail returns effective step policy', async ({ request }) => {
  const list = await request.get(`${BASE_URL}/api/workflow-catalog`, { headers: authHeaders() });
  const body = await list.json();
  const workflow = body.workflows[0];

  const detail = await request.get(`${BASE_URL}/api/workflow-catalog/${workflow.workflow_id}`, {
    headers: authHeaders(),
  });
  expect(detail.status()).toBe(200);
  const detailBody = await detail.json();
  expect(Array.isArray(detailBody.steps)).toBe(true);
  expect(detailBody.steps.length).toBeGreaterThan(0);
  expect(typeof detailBody.steps[0].effective_profile).toBe('string');
});

test('Workflows tab does not load Mermaid', async ({ page }) => {
  const mermaidRequests: string[] = [];
  page.on('request', (req) => {
    if (req.url().toLowerCase().includes('mermaid')) {
      mermaidRequests.push(req.url());
    }
  });

  await openWorkflowsTab(page);
  await expandWorkflowCard(page, 'implementation_reviews');

  expect(mermaidRequests).toHaveLength(0);
  expect(await page.evaluate(() => typeof (window as any).mermaid !== 'undefined')).toBe(false);
});

test('Workflows tab has no critical or serious axe violations', async ({ page }) => {
  await openWorkflowsTab(page);

  const { AxeBuilder } = await import('@axe-core/playwright');
  const results = await new AxeBuilder({ page })
    .include('#section-workflows')
    .withTags(['wcag2a', 'wcag2aa'])
    .disableRules(['color-contrast'])
    .analyze();

  const violations = results.violations.filter((v: any) =>
    ['critical', 'serious'].includes(v.impact)
  );
  expect(violations).toHaveLength(0);
});
