/**
 * E2E: panel harness toggle persists a real harness change (v0.1.29 / T-29-C-05, AC-6).
 *
 * These assertions are JS-driven and CANNOT be covered by a server-side pytest (qa H1):
 *   - flipping the codex/pi segmented control to pi filters the dropdown to pi profiles
 *     AND auto-selects the harness's default profile (mirrors the resolver, D-1);
 *   - the default-vs-effective diff renders a harness-overridden flag (codex → pi);
 *   - validate-before-save passes and save PUTs the harness into the overlay;
 *   - GET /api/workflow-model-policy round-trips the step harness;
 *   - GET /api/workflow-catalog reflects the persisted harness change (effective harness
 *     pi + harness_overridden flag + the PI default profile as effective_profile).
 *
 * The panel is loopback with no credential; the Host-guard is satisfied by the webServer
 * fixture (playwright.config.ts boots `dadaia panel`). The test targets the `implementation`
 * workflow's `implement` step (both harnesses supported) and restores the empty overlay
 * before and after so it never depends on, or leaks, live workspace state.
 */
import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, authHeaders, BASE_URL } from './helpers';

const EMPTY_OVERLAY = {
  schema_version: 'workflow-model-policy-v1',
  policy_id: 'default',
  contexts: { default: { workflows: {} } },
};

// The implementation.implement worker step: a producing step that supports both harnesses,
// so a pi toggle is always valid (release_definition steps may be single-harness).
const IMPLEMENT_ROW = '[data-wfp-workflow-card="implementation"] [data-wfp-step-row="implement"]';

async function restoreEmptyOverlay(request: any): Promise<void> {
  await request.put(`${BASE_URL}/api/workflow-model-policy?context=default`, {
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    data: EMPTY_OVERLAY,
  });
}

async function openWorkflowsTab(page: any): Promise<void> {
  await gotoPanel(page);
  await activateTab(page, 'workflows');
  await page.waitForSelector(IMPLEMENT_ROW, { timeout: 15000 });
}

test.beforeEach(async ({ request }) => {
  // Start from a known-clean overlay so the test does not depend on live workspace state.
  await restoreEmptyOverlay(request);
});

test.afterEach(async ({ request }) => {
  await restoreEmptyOverlay(request);
});

test('Harness toggle to pi filters the dropdown and flags the harness diff', async ({ page }) => {
  await openWorkflowsTab(page);

  const row = page.locator(IMPLEMENT_ROW);
  // implement defaults to codex — no harness override flag yet.
  await expect(row).not.toHaveClass(/wfp-step-row--overridden/);
  await expect(row.locator('[data-testid="wfp-diff-harness"]')).toHaveCount(0);

  // Flip the segmented control to pi.
  await row.locator('.wfp-seg-btn[data-wfp-harness="pi"]').click();

  // The row is now overridden and the dropdown lists only pi profiles.
  await expect(page.locator(IMPLEMENT_ROW)).toHaveClass(/wfp-step-row--overridden/);
  const piOptions = await page.locator(`${IMPLEMENT_ROW} .wfp-profile-select option`).allTextContents();
  expect(piOptions.length).toBeGreaterThan(0);
  expect(piOptions.every((o) => /pi/i.test(o))).toBe(true);

  // The default-vs-effective diff shows the harness change codex → pi.
  const harnessDiff = page.locator(`${IMPLEMENT_ROW} [data-testid="wfp-diff-harness"]`);
  await expect(harnessDiff).toContainText('codex');
  await expect(harnessDiff).toContainText('pi');
});

test('Harness toggle persists through PUT and the catalog diff reflects it', async ({
  page,
  request,
}) => {
  await openWorkflowsTab(page);

  // Flip implement to pi, then validate + save.
  await page.locator(`${IMPLEMENT_ROW} .wfp-seg-btn[data-wfp-harness="pi"]`).click();
  await page.locator('#wfp-validate-btn').click();
  await expect(page.locator('#wfp-banner')).toHaveClass(/wfp-banner--ok/, { timeout: 10000 });
  await page.locator('#wfp-save-btn').click();
  await expect(page.locator('#wfp-banner')).toHaveClass(/wfp-banner--ok/, { timeout: 10000 });

  // The overlay persisted the implement harness (round-trip through GET).
  const polRes = await request.get(`${BASE_URL}/api/workflow-model-policy?context=default`, {
    headers: authHeaders(),
  });
  expect(polRes.status()).toBe(200);
  const polBody = await polRes.json();
  expect(polBody.exists).toBe(true);
  const impl = polBody.policy.contexts.default.workflows.implementation;
  expect(impl.harnesses.implement).toBe('pi');

  // The catalog default-vs-effective diff reflects the persisted harness change.
  const catRes = await request.get(`${BASE_URL}/api/workflow-catalog?context=default`, {
    headers: authHeaders(),
  });
  expect(catRes.status()).toBe(200);
  const catBody = await catRes.json();
  const implWf = catBody.workflows.find((wf: any) => wf.workflow_id === 'implementation');
  const implStep = implWf.steps.find((s: any) => s.step === 'implement');
  expect(implStep.harness).toBe('pi');
  expect(implStep.default_harness).toBe('codex');
  expect(implStep.harness_overridden).toBe(true);
  expect(/^pi-/.test(implStep.effective_profile)).toBe(true);
});
