/**
 * E2E: first-class Workflows nav — model-governance editor (T-28-C-04, qa H1).
 *
 * These assertions are JS-driven and CANNOT be covered by a server-side pytest:
 *   - the profile dropdown is filtered by the segmented codex/pi harness control;
 *   - switching harness / picking a profile flips the default-vs-effective diff DOM;
 *   - reset-to-default clears the override;
 *   - validate runs before save and surfaces a banner;
 *   - save persists the overlay (PUT) and the editor reloads it as effective.
 *
 * The panel is loopback with no credential; the Host-guard is satisfied by the
 * webServer fixture (playwright.config.ts boots `dadaia panel`).
 */
import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, authHeaders, BASE_URL } from './helpers';

async function openWorkflowsTab(page: any): Promise<void> {
  await gotoPanel(page);
  await activateTab(page, 'workflows');
  // The editor renders one step matrix per governed workflow.
  await page.waitForSelector('#wfp-root .wfp-matrix', { timeout: 15000 });
}

test('Workflows is a first-class top-level tab', async ({ page }) => {
  await gotoPanel(page);
  await expect(page.locator('#tab-workflows')).toBeVisible();
  await activateTab(page, 'workflows');
  await expect(page.locator('#section-workflows.active')).toBeVisible();
  // Agents + Kanban remain available in the Agentic tab during the transition (D-5).
  await expect(page.locator('#tab-ops')).toBeVisible();
});

test('Profile dropdown is filtered by the selected harness', async ({ page }) => {
  await openWorkflowsTab(page);

  const firstRow = page.locator('#wfp-root .wfp-step-row').first();
  const select = firstRow.locator('.wfp-profile-select');

  // Default harness is codex — every option in the dropdown is a codex profile.
  const codexOptions = await select.locator('option').allTextContents();
  expect(codexOptions.length).toBeGreaterThan(0);
  expect(codexOptions.every((o) => /codex/i.test(o))).toBe(true);

  // Switch the segmented control to pi — the dropdown now lists pi profiles only.
  await firstRow.locator('.wfp-seg-btn[data-wfp-harness="pi"]').click();
  const piOptions = await firstRow.locator('.wfp-profile-select option').allTextContents();
  expect(piOptions.length).toBeGreaterThan(0);
  expect(piOptions.every((o) => /pi/i.test(o))).toBe(true);
});

test('Editing a profile flips the default-vs-effective diff, reset clears it', async ({ page }) => {
  await openWorkflowsTab(page);

  const firstRow = page.locator('#wfp-root .wfp-step-row').first();
  // Initially not overridden.
  await expect(firstRow).not.toHaveClass(/wfp-step-row--overridden/);

  // Choose a different codex profile (review-deep) to create an override.
  await firstRow.locator('.wfp-profile-select').selectOption('codex-review-deep');
  const overriddenRow = page.locator('#wfp-root .wfp-step-row').first();
  await expect(overriddenRow).toHaveClass(/wfp-step-row--overridden/);
  await expect(overriddenRow.locator('[data-testid="wfp-diff"]')).toContainText('→');

  // Reset clears the override (diff returns to "default").
  await overriddenRow.locator('[data-wfp-reset]').click();
  await expect(page.locator('#wfp-root .wfp-step-row').first()).not.toHaveClass(
    /wfp-step-row--overridden/
  );
});

test('Validate-before-save shows a banner, save persists the overlay', async ({ page, request }) => {
  await openWorkflowsTab(page);

  const firstRow = page.locator('#wfp-root .wfp-step-row').first();
  const stepName = (await firstRow.locator('.wfp-c-step').textContent())?.trim();
  await firstRow.locator('.wfp-profile-select').selectOption('codex-review-deep');

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
  expect(stepName && stepName.length).toBeTruthy();
});

test('Run-snapshot evidence view reads the persisted snapshot', async ({ page }) => {
  await openWorkflowsTab(page);
  // Opening the run-snapshot panel must not error even with no runs recorded.
  await page.locator('.wfp-runs-btn').first().click();
  const panel = page.locator('[data-wfp-runs-panel]').first();
  await expect(panel).toBeVisible();
  // Either snapshots render, or the empty-state message appears — never an error.
  await expect(panel.locator('.wfp-error')).toHaveCount(0);
});
