/**
 * E2E: Sub-agents tab — L1 agent model governance (v0.1.65 FR8 / AC-6).
 *
 * Journeys (JS-driven, cannot be covered by a server-side pytest):
 *   1. Tab activation renders the 9-core-agent roster with model + effort pickers,
 *      the template selector (3 built-ins, `balanced` default) and the Apply toolbar.
 *   2. Template apply flow: select `subscription-saver` → Apply → PUT resolves →
 *      post-apply pop-up shows the G-2 per-harness pickup instructions → GET
 *      reflects the applied template in the resolved roster.
 *   3. Per-agent override flow: change software-engineer's model → Apply → the
 *      override persists (PUT/GET round-trip) and the AC-3 per-field merge holds
 *      (model from override, effort from template) → pop-up shown.
 *   4. Validation rejection: Fable-on-security-reviewer (G-1/D-7) is rejected at
 *      the validate step with a readable error banner and NO write happens.
 *
 * Determinism: every Apply click goes through `clickAndAwaitPut` (FR11 pattern —
 * the PUT response itself is the only save signal; banners are shared between
 * validate and save outcomes). The rejection test arms a `waitForResponse` on the
 * 400 validate POST before clicking.
 *
 * State hygiene: the overlay is restored to a clean `balanced` baseline (no
 * overrides) before AND after every test, with asserted 200s, so the suite never
 * depends on — or leaks — live workspace policy state.
 */
import { test, expect, Page, APIRequestContext } from '@playwright/test';
import { gotoPanel, authHeaders, clickAndAwaitPut, BASE_URL } from './helpers';

const CLEAN_OVERLAY = {
  schema_version: 'agent-model-policy-v1',
  applied_template: 'balanced',
};

const CORE_AGENTS = [
  'project-manager',
  'software-architect',
  'product-engineer',
  'project-auditor',
  'security-reviewer',
  'code-reviewer',
  'ai-engineer',
  'software-engineer',
  'qa-engineer',
];

async function restoreCleanOverlay(request: APIRequestContext): Promise<void> {
  const res = await request.put(`${BASE_URL}/api/agent-model-policy`, {
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    data: CLEAN_OVERLAY,
  });
  // A silent restore failure would leak policy state into the next test.
  expect(res.status()).toBe(200);
}

async function openSubagentsTab(page: Page): Promise<void> {
  await gotoPanel(page);
  await page.click('#tab-subagents');
  await page.waitForSelector('#section-subagents.active', { timeout: 8000 });
  // agent_policy.js hydrates lazily on tab click — wait for the roster table.
  await page.waitForSelector('#ap-roster table.ap-roster-table tbody tr', {
    timeout: 15000,
  });
}

async function getPolicy(request: APIRequestContext): Promise<any> {
  const res = await request.get(`${BASE_URL}/api/agent-model-policy`, {
    headers: authHeaders(),
  });
  expect(res.status()).toBe(200);
  return res.json();
}

test.beforeEach(async ({ request }) => {
  await restoreCleanOverlay(request);
});

test.afterEach(async ({ request }) => {
  await restoreCleanOverlay(request);
});

test('Sub-agents tab renders the 9-core-agent roster with pickers and templates', async ({
  page,
}) => {
  await openSubagentsTab(page);

  // Every core agent has a row with a model picker and an effort picker.
  for (const agent of CORE_AGENTS) {
    await expect(
      page.locator(`#ap-roster .ap-model-select[data-ap-agent="${agent}"]`)
    ).toHaveCount(1);
    await expect(
      page.locator(`#ap-roster .ap-effort-select[data-ap-agent="${agent}"]`)
    ).toHaveCount(1);
  }
  // At least the 9 core rows (installed plugin agents append after).
  const rowCount = await page.locator('#ap-roster tbody tr').count();
  expect(rowCount).toBeGreaterThanOrEqual(9);

  // Template selector carries the 3 built-ins; `balanced` is selected (clean overlay).
  const templateValues = await page
    .locator('#ap-template-select option')
    .evaluateAll((opts) => opts.map((o) => (o as HTMLOptionElement).value));
  expect(templateValues).toEqual(
    expect.arrayContaining(['balanced', 'subscription-saver', 'max-quality'])
  );
  expect(templateValues.length).toBe(3);
  await expect(page.locator('#ap-template-select')).toHaveValue('balanced');

  // The effort vocabulary is the D-3 five-value set.
  const effortValues = await page
    .locator('#ap-roster .ap-effort-select[data-ap-agent="qa-engineer"] option')
    .evaluateAll((opts) => opts.map((o) => (o as HTMLOptionElement).value));
  expect(effortValues).toEqual(['low', 'medium', 'high', 'xhigh', 'max']);

  // The Apply toolbar and (hidden) post-apply dialog are present.
  await expect(page.locator('#ap-apply-btn')).toBeVisible();
  await expect(page.locator('#ap-popup')).toBeHidden();
});

test('Template select + Apply round-trips PUT/GET and shows the post-apply pop-up', async ({
  page,
  request,
}) => {
  await openSubagentsTab(page);

  await page.selectOption('#ap-template-select', 'subscription-saver');
  // FR11 pattern: the PUT response is the save signal — arm before clicking Apply.
  await clickAndAwaitPut(page, '#ap-apply-btn', '/api/agent-model-policy');

  // Post-apply pop-up: G-2 per-harness pickup instructions + re-render summary.
  const popup = page.locator('#ap-popup');
  await expect(popup).toBeVisible();
  const popupBody = page.locator('#ap-popup-body');
  await expect(popupBody).toContainText('claude');
  await expect(popupBody).toContainText('codex');
  await expect(popup.locator('[data-testid="ap-rerendered"]')).toHaveCount(1);
  await popup.locator('#ap-popup-close').click();
  await expect(popup).toBeHidden();

  // GET reflects the applied template in policy AND resolved roster.
  const body = await getPolicy(request);
  expect(body.exists).toBe(true);
  expect(body.policy.applied_template).toBe('subscription-saver');
  // product-engineer distinguishes subscription-saver (sonnet-5/xhigh) from
  // balanced (opus-4-8/high) — a copy of the old roster would fail here.
  expect(body.resolved['product-engineer']).toEqual({
    model: 'claude-sonnet-5',
    effort: 'xhigh',
    source: 'template',
  });
  // G-1: security-reviewer is never Fable in any template.
  expect(body.resolved['security-reviewer'].model).not.toBe('claude-fable-5');
});

test('Per-agent override round-trips through Apply with the AC-3 per-field merge', async ({
  page,
  request,
}) => {
  await openSubagentsTab(page);

  // subscription-saver baseline + a model-only override on software-engineer.
  await page.selectOption('#ap-template-select', 'subscription-saver');
  await page.selectOption(
    '#ap-roster .ap-model-select[data-ap-agent="software-engineer"]',
    'claude-opus-4-8'
  );
  // The edit is flagged as a pending override in the source badge.
  await expect(
    page
      .locator('#ap-roster tr', { hasText: 'software-engineer' })
      .locator('.ap-source-badge')
  ).toContainText('override');

  await clickAndAwaitPut(page, '#ap-apply-btn', '/api/agent-model-policy');
  await expect(page.locator('#ap-popup')).toBeVisible();
  await page.locator('#ap-popup-close').click();

  // Persisted: the overlay carries the model-only override…
  const body = await getPolicy(request);
  expect(body.policy.applied_template).toBe('subscription-saver');
  expect(body.policy.overrides['software-engineer']).toEqual({
    model: 'claude-opus-4-8',
  });
  // …and the resolved roster applies the AC-3 per-field merge: model from the
  // override, effort from the subscription-saver template (xhigh).
  expect(body.resolved['software-engineer']).toEqual({
    model: 'claude-opus-4-8',
    effort: 'xhigh',
    source: 'override',
  });

  // The UI reflects the persisted override after its own reload (GET round-trip).
  await expect(
    page.locator('#ap-roster .ap-model-select[data-ap-agent="software-engineer"]')
  ).toHaveValue('claude-opus-4-8');
});

test('Fable on security-reviewer is rejected at validate with no write (G-1/D-7)', async ({
  page,
  request,
}) => {
  await openSubagentsTab(page);

  await page.selectOption(
    '#ap-roster .ap-model-select[data-ap-agent="security-reviewer"]',
    'claude-fable-5'
  );

  // Arm the deterministic signal: the validate POST must come back 400.
  const validateRejected = page.waitForResponse(
    (res) =>
      res.url().includes('/api/agent-model-policy/validate') &&
      res.request().method() === 'POST' &&
      res.status() === 400,
    { timeout: 10000 }
  );
  await page.locator('#ap-apply-btn').click();
  await validateRejected;

  // Readable error banner naming the rejected combination; no pop-up.
  const banner = page.locator('#ap-banner');
  await expect(banner).toBeVisible();
  await expect(banner).toHaveClass(/ap-banner--error/);
  await expect(banner).toContainText('security-reviewer');
  await expect(page.locator('#ap-popup')).toBeHidden();

  // No write happened: the persisted policy still resolves the clean baseline.
  const body = await getPolicy(request);
  expect(body.policy.applied_template).toBe('balanced');
  expect(body.policy.overrides ?? {}).toEqual({});
  expect(body.resolved['security-reviewer'].model).not.toBe('claude-fable-5');
});
