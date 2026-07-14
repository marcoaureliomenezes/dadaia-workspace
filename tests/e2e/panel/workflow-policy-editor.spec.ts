/**
 * E2E: Workflows tab — inline per-step model picker (v0.1.45 redesign).
 *
 * The per-step model governance moved INTO each workflow diagram card's expand: every
 * model-driven step card carries a `.wf-step-picker` mount that `workflow-policy.js`
 * hydrates with a real editor (segmented codex/pi harness control + profile `<select>` +
 * default-vs-effective diff + reset). A single Validate / Save toolbar at the top of the
 * Workflows tab commits the pending overrides. There is no longer a separate collapsed
 * "Model policy" matrix and no old DAG modal.
 *
 * These assertions are JS-driven and CANNOT be covered by a server-side pytest:
 *   - the profile dropdown is filtered by the segmented codex/pi harness control
 *     (and the pi list includes the labelled OpenRouter kimi option, id `pi-openrouter-kimi-high`);
 *   - picking a profile flips the default-vs-effective diff DOM;
 *   - reset-to-default clears the override;
 *   - validate runs before save and surfaces a banner;
 *   - save persists the overlay (PUT) and the picker reloads it as effective.
 *
 * The panel is loopback with no credential; the Host-guard is satisfied by the webServer
 * fixture (playwright.config.ts boots `dadaia panel`). The picker targets the
 * `implementation` workflow's `implement` step (both harnesses supported) and restores the
 * empty overlay before/after so it never depends on, or leaks, live workspace state.
 */
import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, expandWorkflowCard, authHeaders, BASE_URL } from './helpers';

const EMPTY_OVERLAY = {
  schema_version: 'workflow-model-policy-v1',
  policy_id: 'default',
  contexts: { default: { workflows: {} } },
};

// The implement step's inline picker mount inside the implementation card's expand.
const IMPLEMENT_PICKER =
  'details.dadaia-wf-card[data-workflow="implementation_reviews"] .wf-step-picker[data-wfp-step="implement"]';

async function restoreEmptyOverlay(request: any): Promise<void> {
  await request.put(`${BASE_URL}/api/workflow-model-policy?context=default`, {
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    data: EMPTY_OVERLAY,
  });
}

async function openImplementPicker(page: any): Promise<void> {
  await gotoPanel(page);
  await activateTab(page, 'workflows');
  await expandWorkflowCard(page, 'implementation_reviews');
  await page.waitForSelector(`${IMPLEMENT_PICKER} .wfp-picker`, {
    state: 'visible',
    timeout: 15000,
  });
}

test.beforeEach(async ({ request }) => {
  await restoreEmptyOverlay(request);
});

test.afterEach(async ({ request }) => {
  await restoreEmptyOverlay(request);
});

test('Workflows is a first-class top-level tab', async ({ page }) => {
  await gotoPanel(page);
  await expect(page.locator('#tab-workflows')).toBeVisible();
  await activateTab(page, 'workflows');
  await expect(page.locator('#section-workflows.active')).toBeVisible();
  // The Agentic (ops) tab was removed in v0.1.45.
  expect(await page.$('#tab-ops')).toBeNull();
});

test('Profile dropdown is filtered by the selected harness', async ({ page }) => {
  await openImplementPicker(page);

  const picker = page.locator(IMPLEMENT_PICKER);
  const select = picker.locator('.wfp-profile-select');

  // Default harness is codex — every profile in the dropdown is a codex profile.
  // Assert on the option VALUE (profile id, harness-prefixed) rather than the label:
  // v0.1.45's labelled OpenRouter kimi profile ("OpenRouter — kimi …") keeps its `pi-`
  // id but its display text no longer contains its harness name.
  const codexValues = await select
    .locator('option')
    .evaluateAll((opts) => opts.map((o) => (o as HTMLOptionElement).value));
  expect(codexValues.length).toBeGreaterThan(0);
  expect(codexValues.every((v) => v.startsWith('codex-'))).toBe(true);

  // Switch the segmented control to pi — the dropdown now lists pi profiles only,
  // including the labelled OpenRouter kimi profile.
  await picker.locator('.wfp-seg-btn[data-wfp-harness="pi"]').click();
  const piValues = await page
    .locator(`${IMPLEMENT_PICKER} .wfp-profile-select option`)
    .evaluateAll((opts) => opts.map((o) => (o as HTMLOptionElement).value));
  expect(piValues.length).toBeGreaterThan(0);
  expect(piValues.every((v) => v.startsWith('pi-'))).toBe(true);
  expect(piValues).toContain('pi-openrouter-kimi-high');
});

test('Editing a profile flips the default-vs-effective diff, reset clears it', async ({ page }) => {
  await openImplementPicker(page);

  // Initially not overridden.
  await expect(page.locator(`${IMPLEMENT_PICKER} .wfp-picker`)).not.toHaveClass(
    /wfp-picker--overridden/
  );

  // Choose a different codex profile (review-deep) to create an override.
  await page.locator(`${IMPLEMENT_PICKER} .wfp-profile-select`).selectOption('codex-review-deep');
  await expect(page.locator(`${IMPLEMENT_PICKER} .wfp-picker`)).toHaveClass(
    /wfp-picker--overridden/
  );
  await expect(page.locator(`${IMPLEMENT_PICKER} [data-testid="wfp-diff"]`)).toContainText('→');

  // Reset clears the override (diff returns to "default").
  await page.locator(`${IMPLEMENT_PICKER} [data-wfp-reset]`).click();
  await expect(page.locator(`${IMPLEMENT_PICKER} .wfp-picker`)).not.toHaveClass(
    /wfp-picker--overridden/
  );
});

test('Validate-before-save shows a banner, save persists the overlay', async ({
  page,
  request,
}) => {
  await openImplementPicker(page);

  await page.locator(`${IMPLEMENT_PICKER} .wfp-profile-select`).selectOption('codex-review-deep');

  // Validate → green banner.
  await page.locator('#wfp-validate-btn').click();
  await expect(page.locator('#wfp-banner')).toBeVisible();
  await expect(page.locator('#wfp-banner')).toHaveClass(/wfp-banner--ok/, { timeout: 10000 });

  // Save → persisted; the banner reports success.
  await page.locator('#wfp-save-btn').click();
  await expect(page.locator('#wfp-banner')).toHaveClass(/wfp-banner--ok/, { timeout: 10000 });

  // The overlay was persisted: GET /api/workflow-model-policy reflects it.
  const res = await request.get(`${BASE_URL}/api/workflow-model-policy?context=default`, {
    headers: authHeaders(),
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.exists).toBe(true);
  const workflows = body.policy.contexts.default.workflows;
  const anyStep = Object.values(workflows).some((wf: any) =>
    Object.values(wf.steps).includes('codex-review-deep')
  );
  expect(anyStep).toBe(true);
});
