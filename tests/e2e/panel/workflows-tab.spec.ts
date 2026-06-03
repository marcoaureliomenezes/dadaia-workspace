import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, authHeaders, BASE_URL } from './helpers';

async function openWorkflowsTab(page: any) {
  await gotoPanel(page);
  await activateTab(page, 'workflows');
  await page.waitForSelector(
    '#workflows-grid .workflow-card:not(.workflow-card--skeleton), #workflows-empty:not([hidden])',
    { timeout: 15000 }
  );
}

test('Workflows tab renders current workflow cards', async ({ page }) => {
  await openWorkflowsTab(page);

  const cards = page.locator('#workflows-grid .workflow-card:not(.workflow-card--skeleton)');
  const count = await cards.count();
  expect(count).toBeGreaterThan(0);

  const first = cards.first();
  await expect(first.locator('.workflow-card__name')).toHaveText(/\S+/);
  await expect(first.locator('.workflow-card__description')).toBeVisible();
  await expect(first.locator('.workflow-agent-chip:not(.skeleton-pulse)').first()).toBeVisible();
  await expect(first.locator('.workflow-stage-badge')).toHaveText(/\d+\s*stage/i);
  await expect(first.locator('.workflow-dag-cta')).toBeVisible();
});

test('Workflow detail journey opens DAG and returns to the grid', async ({ page }) => {
  await openWorkflowsTab(page);

  await page.locator('#workflows-grid .workflow-dag-cta[data-workflow-name]').first().click();
  const detail = page.locator('#workflow-detail-view');
  await expect(detail).toBeVisible({ timeout: 10000 });
  await expect(detail.locator('svg')).toBeVisible({ timeout: 10000 });

  const svgValid = await page.evaluate(() => {
    const svgEl = document.querySelector('#workflow-detail-view svg');
    if (!svgEl) return false;
    const doc = new DOMParser().parseFromString(svgEl.outerHTML, 'image/svg+xml');
    return doc.querySelector('parsererror') === null;
  });
  expect(svgValid).toBe(true);

  await page.locator('#detail-back-btn').click();
  await expect(page.locator('#workflows-grid .workflow-card:not(.workflow-card--skeleton)').first())
    .toBeVisible({ timeout: 8000 });
});

test('Workflows API returns the current workflow envelope', async ({ request }) => {
  const response = await request.get(`${BASE_URL}/api/workflows`, { headers: authHeaders() });
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(Array.isArray(body.workflows)).toBe(true);
  expect(body.workflows.length).toBeGreaterThan(0);

  for (const workflow of body.workflows) {
    expect(typeof workflow.name).toBe('string');
    expect(workflow.name.length).toBeGreaterThan(0);
    expect(typeof workflow.stage_count).toBe('number');
    expect(workflow.stage_count).toBeGreaterThan(0);
    expect(Array.isArray(workflow.agent_ids)).toBe(true);
  }
});

test('Workflow detail API returns SVG for a listed workflow', async ({ request }) => {
  const list = await request.get(`${BASE_URL}/api/workflows`, { headers: authHeaders() });
  const body = await list.json();
  const workflow = body.workflows[0];

  const detail = await request.get(`${BASE_URL}/api/workflows/${workflow.name}`, {
    headers: authHeaders(),
  });
  expect(detail.status()).toBe(200);
  const detailBody = await detail.json();
  expect(Array.isArray(detailBody.stages)).toBe(true);
  expect(detailBody.stages.length).toBeGreaterThan(0);
  expect(detailBody.diagram_svg ?? detailBody.dag_svg).toContain('<svg');
});

test('Workflows tab does not load Mermaid', async ({ page }) => {
  const mermaidRequests: string[] = [];
  page.on('request', (req) => {
    if (req.url().toLowerCase().includes('mermaid')) {
      mermaidRequests.push(req.url());
    }
  });

  await openWorkflowsTab(page);
  await page.locator('#workflows-grid .workflow-dag-cta[data-workflow-name]').first().click();
  await expect(page.locator('#workflow-detail-view')).toBeVisible({ timeout: 10000 });

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
