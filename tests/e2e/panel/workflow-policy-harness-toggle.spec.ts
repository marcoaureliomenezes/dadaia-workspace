/**
 * E2E: panel harness toggle persists a real harness change (v0.1.45 redesign).
 *
 * The per-step model governance now lives INSIDE each workflow diagram card's expand: an
 * inline `.wf-step-picker` per model-driven step. These assertions are JS-driven and
 * CANNOT be covered by a server-side pytest (qa H1):
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
import {
  gotoPanel,
  activateTab,
  expandWorkflowCard,
  authHeaders,
  clickAndAwaitPut,
  BASE_URL,
} from './helpers';

const EMPTY_OVERLAY = {
  schema_version: 'workflow-model-policy-v1',
  policy_id: 'default',
  contexts: { default: { workflows: {} } },
};

// The implement step's inline picker mount inside the implementation card's expand.
// implement is a producing step that supports both harnesses, so a pi toggle is always
// valid (release_definition steps may be single-harness).
const IMPLEMENT_PICKER =
  'details.dadaia-wf-card[data-workflow="implementation_reviews"] .wf-step-picker[data-wfp-step="implement"]';

async function restoreEmptyOverlay(request: any): Promise<void> {
  const res = await request.put(`${BASE_URL}/api/workflow-model-policy?context=default`, {
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    data: EMPTY_OVERLAY,
  });
  // FR11(b): a silent restore failure would leak state into the next test.
  expect(res.status()).toBe(200);
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
  // Start from a known-clean overlay so the test does not depend on live workspace state.
  await restoreEmptyOverlay(request);
});

test.afterEach(async ({ request }) => {
  await restoreEmptyOverlay(request);
});

test('Harness toggle to pi filters the dropdown and flags the harness diff', async ({ page }) => {
  await openImplementPicker(page);

  const picker = page.locator(`${IMPLEMENT_PICKER} .wfp-picker`);
  // implement defaults to codex — no harness override flag yet.
  await expect(picker).not.toHaveClass(/wfp-picker--overridden/);
  await expect(page.locator(`${IMPLEMENT_PICKER} [data-testid="wfp-diff-harness"]`)).toHaveCount(0);

  // Flip the segmented control to pi.
  await page.locator(`${IMPLEMENT_PICKER} .wfp-seg-btn[data-wfp-harness="pi"]`).click();

  // The picker is now overridden and the dropdown lists only pi profiles.
  // Assert on option VALUE (harness-prefixed profile id), not the label: v0.1.45's
  // labelled kimi profile keeps its `pi-` id but its display text no longer contains "pi".
  await expect(page.locator(`${IMPLEMENT_PICKER} .wfp-picker`)).toHaveClass(
    /wfp-picker--overridden/
  );
  const piValues = await page
    .locator(`${IMPLEMENT_PICKER} .wfp-profile-select option`)
    .evaluateAll((opts) => opts.map((o) => (o as HTMLOptionElement).value));
  expect(piValues.length).toBeGreaterThan(0);
  expect(piValues.every((v) => v.startsWith('pi-'))).toBe(true);

  // The default-vs-effective diff shows the harness change codex → pi.
  const harnessDiff = page.locator(`${IMPLEMENT_PICKER} [data-testid="wfp-diff-harness"]`);
  await expect(harnessDiff).toContainText('codex');
  await expect(harnessDiff).toContainText('pi');
});

test('Harness toggle persists through PUT and the catalog diff reflects it', async ({
  page,
  request,
}) => {
  await openImplementPicker(page);

  // Flip implement to pi, then validate + save.
  await page.locator(`${IMPLEMENT_PICKER} .wfp-seg-btn[data-wfp-harness="pi"]`).click();
  await page.locator('#wfp-validate-btn').click();
  await expect(page.locator('#wfp-banner')).toHaveClass(/wfp-banner--ok/, { timeout: 10000 });
  // FR11(a): the banner class is shared between validate and save outcomes, so the
  // stale validate banner is NOT a save signal. Arm the PUT wait before clicking
  // save and await the 200 response itself — only then is the GET race-free.
  await clickAndAwaitPut(page, '#wfp-save-btn', '/api/workflow-model-policy');

  // The overlay persisted the implement harness (round-trip through GET).
  const polRes = await request.get(`${BASE_URL}/api/workflow-model-policy?context=default`, {
    headers: authHeaders(),
  });
  expect(polRes.status()).toBe(200);
  const polBody = await polRes.json();
  expect(polBody.exists).toBe(true);
  // FR11(c): an empty overlay serializes WITHOUT the `workflows` key — guard the
  // deep access so a shape regression fails with a readable assertion, not a
  // TypeError inside the property chain.
  const workflows = polBody.policy?.contexts?.default?.workflows ?? {};
  const impl = workflows.implementation_reviews;
  expect(impl, 'persisted overlay must carry contexts.default.workflows.implementation_reviews').toBeTruthy();
  expect(impl.harnesses.implement).toBe('pi');

  // The catalog default-vs-effective diff reflects the persisted harness change.
  const catRes = await request.get(`${BASE_URL}/api/workflow-catalog?context=default`, {
    headers: authHeaders(),
  });
  expect(catRes.status()).toBe(200);
  const catBody = await catRes.json();
  const implWf = catBody.workflows.find((wf: any) => wf.workflow_id === 'implementation_reviews');
  const implStep = implWf.steps.find((s: any) => s.step === 'implement');
  expect(implStep.harness).toBe('pi');
  expect(implStep.default_harness).toBe('codex');
  expect(implStep.harness_overridden).toBe(true);
  expect(/^pi-/.test(implStep.effective_profile)).toBe(true);
});
