/**
 * spec-context-operation-journey.spec.ts — E2E-SCP-OP-01 (v0.1.51 FR4 / AC-4)
 *
 * The first panel OPERATION journey: a real state mutation in the store the panel
 * reads (`.dadaia/states/spec_contexts.json`), observed as a DOM content change on
 * the Spec Context Projects tab — beyond rendering and API 200s.
 *
 * Verification-first result (recorded): the tab is per-request fresh by
 * construction — `render_index._view` calls `PanelService.list_active_contexts()`
 * on every GET, which reads the spec-context store (`list_all()`) per call; no
 * startup cache. This spec proves it live across a reload.
 *
 * Surface note: `list_active_contexts()` filters `state == alive` BY DESIGN — a
 * DEAD context does not render a card at all. The pinned DOM delta is therefore
 * card PRESENCE → ABSENCE (with an unrelated card as the liveness control), the
 * strongest content assertion this surface exposes.
 *
 * Safety: the registry is mutated ONLY when it lives inside the checkout — the
 * shape the CI job bootstraps (`init --workspace $PWD` + seeded registry). In a
 * local run the panel resolves the operator's LIVE workspace (the repo root is
 * never a workspace — hygiene law), so this spec deterministically skips rather
 * than ever touching live state. AC-4's evidence is the `e2e-panel` CI run.
 */

import { test, expect } from '@playwright/test';
import { gotoPanel } from './helpers';
import * as fs from 'fs';
import * as path from 'path';

const REPO_ROOT = path.resolve(__dirname, '../../..');
// PANEL_TEST_REGISTRY: local sandbox override (point the spec at a throwaway
// workspace's registry alongside a PANEL_WEB_SERVER_COMMAND cd-ing there). The
// default is the CI-bootstrapped checkout registry.
const REGISTRY =
  process.env.PANEL_TEST_REGISTRY ||
  path.join(REPO_ROOT, '.dadaia', 'states', 'spec_contexts.json');

const JOURNEY_SLUG = 'journey-op-x';

test.describe('E2E-SCP-OP-01 — context operation journey (store mutation → DOM delta)', () => {
  test.skip(
    !fs.existsSync(REGISTRY),
    'CI-seeded checkout workspace not present — a local run resolves the live ' +
      'workspace, which is never mutated by tests'
  );

  let original: string;

  test.beforeAll(() => {
    original = fs.readFileSync(REGISTRY, 'utf-8');
  });

  test.afterAll(() => {
    if (original !== undefined) fs.writeFileSync(REGISTRY, original);
  });

  test('an ALIVE context renders a card; flipping it DEAD in the store removes it on reload', async ({
    page,
  }) => {
    // 1) Operation: register a new ALIVE context directly in the store the CLI writes.
    const data = JSON.parse(original);
    data.contexts.push({
      name: JOURNEY_SLUG,
      state: 'alive',
      repo_slug: JOURNEY_SLUG,
      repo_url: `https://example.com/${JOURNEY_SLUG}.git`,
      created_at: '2026-01-01T00:00:00+00:00',
      alive_since: '2026-01-01T00:00:00+00:00',
      dead_since: null,
      current_branch: 'main',
    });
    fs.writeFileSync(REGISTRY, JSON.stringify(data, null, 2));

    await gotoPanel(page);
    await page.waitForSelector('#section-memories.active');

    // DOM content assertion: the journey card rendered from the mutated store.
    const journeyCard = page.locator(`.card-zone-c[data-slug="${JOURNEY_SLUG}"]`);
    await expect(journeyCard).toHaveCount(1);
    await expect(
      page.locator('.context-card', { hasText: JOURNEY_SLUG }).locator('.card-name')
    ).toHaveText(JOURNEY_SLUG);

    // 2) Operation: flip the context to DEAD — the exact transition `context dead`
    //    persists (state + dead_since).
    const ctx = data.contexts.find((c: { name: string }) => c.name === JOURNEY_SLUG);
    ctx.state = 'dead';
    ctx.dead_since = '2026-01-02T00:00:00+00:00';
    fs.writeFileSync(REGISTRY, JSON.stringify(data, null, 2));

    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('#section-memories.active');

    // Pinned DOM delta: the DEAD context's card is gone (alive-only surface)…
    await expect(page.locator(`.card-zone-c[data-slug="${JOURNEY_SLUG}"]`)).toHaveCount(0);

    // …while the seeded context still renders — the page is live-fresh, not empty:
    // the disappearance is the mutation's effect, not a blank/error render.
    const remaining = data.contexts.filter((c: { state: string }) => c.state === 'alive');
    expect(remaining.length).toBeGreaterThan(0);
    await expect(
      page.locator(`.card-zone-c[data-slug="${remaining[0].repo_slug}"]`)
    ).toHaveCount(1);
  });
});
