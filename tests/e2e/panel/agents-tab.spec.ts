import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, authHeaders, BASE_URL } from './helpers';

// Agents are now inside the Ops tab (T-016-P09 consolidation).
async function openAgentsTab(page: any) {
  await gotoPanel(page);
  await activateTab(page, 'ops');
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 15000 });
}

test('Agents tab renders the current agent catalog as usable cards', async ({ page }) => {
  await openAgentsTab(page);

  const cards = page.locator('#agents-grid .agent-card:not(.agent-card--skeleton)');
  const count = await cards.count();
  expect(count).toBeGreaterThan(0);

  const first = cards.first();
  await expect(first.locator('.agent-card__name')).toHaveText(/\S+/);
  await expect(first.locator('.agent-status-badge')).toHaveText(/ACTIVE|INACTIVE/i);
  await expect(first.locator('.agent-card__description')).toHaveText(/\S+/);
  await expect(first.locator('.skill-chip:not(.skeleton-pulse)').first()).toBeVisible();
  await expect(first).toHaveAttribute('aria-haspopup', 'dialog');
});

test('Agent card opens the shared detail modal and lazy-loads a prompt', async ({ page }) => {
  await openAgentsTab(page);

  const promptRequests: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/agents/') && req.url().includes('/prompt')) {
      promptRequests.push(req.url());
    }
  });

  await page.locator('#agents-grid .agent-card:not(.agent-card--skeleton)').first().click();

  const modal = page.locator('#agent-modal');
  await expect(modal).toBeVisible({ timeout: 10000 });
  await expect(modal.locator('.agent-prompt code')).toHaveText(/\S{20,}/, { timeout: 10000 });
  expect(promptRequests.length).toBeGreaterThan(0);

  await page.locator('#agent-modal-close').click();
  await expect(modal).not.toBeVisible();
});

test('Agent detail modal is keyboard reachable from a card', async ({ page }) => {
  await openAgentsTab(page);

  const card = page.locator('#agents-grid .agent-card:not(.agent-card--skeleton)').first();
  await card.focus();
  await page.keyboard.press('Enter');

  await expect(page.locator('#agent-modal')).toBeVisible({ timeout: 10000 });
  await page.keyboard.press('Escape');
  await expect(page.locator('#agent-modal')).not.toBeVisible();
});

test('Agents API returns the current catalog envelope', async ({ request }) => {
  const response = await request.get(`${BASE_URL}/api/agents`, { headers: authHeaders() });
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(Array.isArray(body.agents)).toBe(true);
  expect(body.agents.length).toBeGreaterThan(0);

  for (const agent of body.agents) {
    expect(typeof agent.agent_id).toBe('string');
    expect(agent.agent_id.length).toBeGreaterThan(0);
    expect(typeof agent.display_name).toBe('string');
    expect(typeof agent.description).toBe('string');
    expect(['active', 'inactive']).toContain(agent.status);
    expect(Array.isArray(agent.skills)).toBe(true);
    expect(typeof agent.telemetry).toBe('object');
  }
});

test('Agents tab has no critical or serious axe violations', async ({ page }) => {
  await openAgentsTab(page);

  const { AxeBuilder } = await import('@axe-core/playwright');
  const results = await new AxeBuilder({ page })
    // Agents are now a subsection of #section-ops (T-016-P09 consolidation).
    .include('#ops-subsection-agents')
    .withTags(['wcag2a', 'wcag2aa'])
    .disableRules(['color-contrast'])
    .analyze();

  const violations = results.violations.filter((v: any) =>
    ['critical', 'serious'].includes(v.impact)
  );
  expect(violations).toHaveLength(0);
});
