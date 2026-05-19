/**
 * workflows-tab.spec.ts — E2E-WF-01 through E2E-WF-14
 *
 * Tests: 14
 * Surface: Workflows tab — card grid, detail view, DAG SVG, back navigation,
 *          Mermaid guard, API shape, auth enforcement, axe-core audit.
 *
 * Priority: P0 (E2E-WF-01–09) / P1 (E2E-WF-10–14)
 *
 * Canonical workflows from .dadaia/agentic/workflows/ (12 files):
 *   architecture-review, bug-fix-fastlane, cross-cutting-feature,
 *   deploy-validation-only, game-bugfix, game-dev-cycle,
 *   game-spec-definition, hotfix-release, onboarding-new-repo,
 *   security-patch, spec-refinement, tdd-cycle
 *
 * tdd-cycle has 5 stages; cross-cutting-feature has 7 stages;
 * spec-refinement has 7 stages with the widest parallel group.
 */

import { test, expect } from '@playwright/test';
import { gotoPanel, activateTab, authHeaders, BASE_URL } from './helpers';
import * as path from 'path';

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');

const KNOWN_SKILL_SLUGS = [
  'dadaia-task-manager',
  'dadaia-handoff-emitter',
  'dadaia-workspace-spec-navigator',
  'dadaia-grill-me',
  'dadaia-worklog',
];

async function openWorkflowsTab(page: any) {
  await gotoPanel(page);
  await activateTab(page, 'workflows');
  // Wait for cards to appear (not skeleton)
  await page.waitForSelector(
    '#workflows-grid .workflow-card:not(.workflow-card--skeleton), #workflows-empty:not([hidden])',
    { timeout: 15000 }
  );
}

// ---------------------------------------------------------------------------
// E2E-WF-01 — Workflows tab shows exactly 12 canonical workflow cards
// ---------------------------------------------------------------------------
test('E2E-WF-01 — Workflows tab shows exactly 12 canonical workflow cards', async ({ page }) => {
  await openWorkflowsTab(page);

  const cardCount = await page.$$eval(
    '#workflows-grid .workflow-card:not(.workflow-card--skeleton)',
    (cards) => cards.length
  );
  expect(cardCount).toBe(12);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'workflows-grid.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-WF-02 — Workflow cards show real workflow names, not skill names
// ---------------------------------------------------------------------------
test('E2E-WF-02 — Workflow cards show real workflow names, not skill slugs', async ({ page }) => {
  await openWorkflowsTab(page);

  const cardNames = await page.$$eval(
    '#workflows-grid .workflow-card:not(.workflow-card--skeleton) .workflow-card__name',
    (els) => els.map((e) => e.textContent?.trim() ?? '')
  );
  expect(cardNames.length).toBe(12);

  // Must include known workflow names
  const lowerNames = cardNames.map((n) => n.toLowerCase());
  expect(lowerNames.some((n) => n.includes('tdd-cycle') || n.includes('tdd cycle'))).toBe(true);
  expect(
    lowerNames.some((n) => n.includes('cross-cutting') || n.includes('cross cutting'))
  ).toBe(true);
  expect(
    lowerNames.some((n) => n.includes('architecture-review') || n.includes('architecture review'))
  ).toBe(true);

  // Must NOT contain skill slugs
  for (const skillSlug of KNOWN_SKILL_SLUGS) {
    const hasSkill = lowerNames.some((n) => n.includes(skillSlug));
    expect(hasSkill).toBe(false);
  }
});

// ---------------------------------------------------------------------------
// E2E-WF-03 — tdd-cycle and cross-cutting-feature cards show correct metadata
// ---------------------------------------------------------------------------
test('E2E-WF-03 — Workflow cards show name, description, agent chips, stats footer', async ({
  page,
}) => {
  await openWorkflowsTab(page);

  const cards = await page.$$('#workflows-grid .workflow-card:not(.workflow-card--skeleton)');
  expect(cards.length).toBe(12);

  for (const card of cards) {
    // Name must be non-empty
    const name = await card.$eval('.workflow-card__name', (el) => el.textContent?.trim() ?? '');
    expect(name.length).toBeGreaterThan(0);

    // Description must exist (even if empty message)
    const descEl = await card.$('.workflow-card__description');
    expect(descEl).not.toBeNull();

    // At least one agent chip
    const chips = await card.$$('.workflow-agent-chip:not(.skeleton-pulse)');
    expect(chips.length).toBeGreaterThan(0);

    // Stage count badge in header must match /\d+ stage/i
    const stageBadge = await card.$('.workflow-stage-badge');
    expect(stageBadge).not.toBeNull();
    const stageBadgeText = await stageBadge!.textContent();
    expect(stageBadgeText).toMatch(/\d+\s*stage/i);

    // Stats footer (CTA button) must exist
    const footer = await card.$('.workflow-card__footer');
    expect(footer).not.toBeNull();
  }

  // Screenshot tdd-cycle card
  const tddCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
    hasText: 'tdd-cycle',
  }).first();
  if (await tddCard.isVisible()) {
    await tddCard.screenshot({ path: path.join(SCREENSHOTS_DIR, 'workflow-card-tdd-cycle.png') });
  }

  // Screenshot cross-cutting-feature card
  const ccfCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
    hasText: 'cross-cutting',
  }).first();
  if (await ccfCard.isVisible()) {
    await ccfCard.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'workflow-card-cross-cutting-feature.png'),
    });
  }
});

// ---------------------------------------------------------------------------
// E2E-WF-04 — Click "View DAG" on tdd-cycle opens detail view
// ---------------------------------------------------------------------------
test('E2E-WF-04 — Click "View DAG" on tdd-cycle opens detail view', async ({ page }) => {
  await openWorkflowsTab(page);

  // Find the tdd-cycle card's CTA button
  const tddCta = await page.locator('.workflow-dag-cta[aria-label*="tdd-cycle"]').first();
  if (!await tddCta.isVisible()) {
    // Fallback: find by card name text, then find the CTA within it
    const tddCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
      hasText: 'tdd-cycle',
    }).first();
    await tddCard.locator('.workflow-dag-cta').click();
  } else {
    await tddCta.click();
  }

  // Detail view must appear
  await page.waitForSelector('#workflow-detail-view', { timeout: 10000 });

  const detailVisible = await page.$eval(
    '#workflow-detail-view',
    (el) => el.offsetParent !== null || getComputedStyle(el).display !== 'none'
  );
  expect(detailVisible).toBe(true);

  // Detail view must contain the workflow name
  const detailText = await page.$eval('#workflow-detail-view', (el) => el.textContent ?? '');
  expect(detailText.toLowerCase()).toContain('tdd-cycle');

  // URL hash must contain tdd-cycle
  const currentUrl = page.url();
  expect(currentUrl.toLowerCase()).toContain('tdd-cycle');

  // Agent chips must be present in the detail view
  const agentChips = await page.$$('#workflow-detail-view .workflow-detail-chip');
  expect(agentChips.length).toBeGreaterThan(0);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'workflow-detail-tdd-cycle-full.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-WF-05 — tdd-cycle DAG SVG has 5 nodes and is valid XML
// ---------------------------------------------------------------------------
test('E2E-WF-05 — tdd-cycle DAG SVG contains exactly 5 nodes and is valid XML', async ({
  page,
}) => {
  await openWorkflowsTab(page);

  // Navigate to tdd-cycle detail
  const tddCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
    hasText: 'tdd-cycle',
  }).first();
  await tddCard.locator('.workflow-dag-cta').click();
  await page.waitForSelector('#workflow-detail-view', { timeout: 10000 });

  // Wait for SVG to load
  await page.waitForSelector('#workflow-detail-view svg', { timeout: 10000 });

  // SVG must be non-empty
  const svgExists = await page.$('#workflow-detail-view svg');
  expect(svgExists).not.toBeNull();

  // Count rectangular node elements (rect elements represent workflow stages)
  const rectCount = await page.$eval('#workflow-detail-view svg', (svg) => {
    return svg.querySelectorAll('rect').length;
  });
  expect(rectCount).toBe(5);

  // SVG must be valid XML (parseable by DOMParser)
  const svgValid = await page.evaluate(() => {
    const svgEl = document.querySelector('#workflow-detail-view svg');
    if (!svgEl) return false;
    const svgStr = svgEl.outerHTML;
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgStr, 'image/svg+xml');
    const parseError = doc.querySelector('parsererror');
    return parseError === null;
  });
  expect(svgValid).toBe(true);

  await page.locator('#workflow-detail-view svg').screenshot({
    path: path.join(SCREENSHOTS_DIR, 'workflow-dag-tdd-cycle.png'),
  });
});

// ---------------------------------------------------------------------------
// E2E-WF-06 — cross-cutting-feature DAG has 7 nodes, edges, gate markers, parallel groups
// ---------------------------------------------------------------------------
test('E2E-WF-06 — cross-cutting-feature DAG has 7 nodes, edges, and valid XML', async ({
  page,
}) => {
  await openWorkflowsTab(page);

  const ccfCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
    hasText: 'cross-cutting',
  }).first();
  await ccfCard.locator('.workflow-dag-cta').click();
  await page.waitForSelector('#workflow-detail-view svg', { timeout: 10000 });

  // 7 rectangular nodes (dag-band background rects are excluded)
  const rectCount = await page.$eval('#workflow-detail-view svg', (svg) => {
    return svg.querySelectorAll('rect:not(.dag-band)').length;
  });
  expect(rectCount).toBe(7);

  // Edge elements (path or line elements for DAG edges)
  const edgeCount = await page.$eval('#workflow-detail-view svg', (svg) => {
    return svg.querySelectorAll('path, line').length;
  });
  expect(edgeCount).toBeGreaterThan(0);

  // Valid XML
  const svgValid = await page.evaluate(() => {
    const svgEl = document.querySelector('#workflow-detail-view svg');
    if (!svgEl) return false;
    const svgStr = svgEl.outerHTML;
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgStr, 'image/svg+xml');
    return doc.querySelector('parsererror') === null;
  });
  expect(svgValid).toBe(true);

  await page.locator('#workflow-detail-view svg').screenshot({
    path: path.join(SCREENSHOTS_DIR, 'workflow-dag-cross-cutting-feature.png'),
  });
});

// ---------------------------------------------------------------------------
// E2E-WF-07 — spec-refinement DAG has 7 nodes with no overlapping bounding boxes
// ---------------------------------------------------------------------------
test('E2E-WF-07 — spec-refinement DAG has 7 nodes with non-overlapping bounding boxes', async ({
  page,
}) => {
  await openWorkflowsTab(page);

  const srCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
    hasText: 'spec-refinement',
  }).first();
  await srCard.locator('.workflow-dag-cta').click();
  await page.waitForSelector('#workflow-detail-view svg', { timeout: 10000 });

  // 7 nodes (dag-band background rects are excluded)
  const rectCount = await page.$eval('#workflow-detail-view svg', (svg) => {
    return svg.querySelectorAll('rect:not(.dag-band)').length;
  });
  expect(rectCount).toBe(7);

  // No overlapping bounding boxes — use getBBox() to resolve parent <g transform="translate(...)">
  const noOverlap = await page.evaluate(() => {
    const svgEl = document.querySelector('#workflow-detail-view svg') as SVGSVGElement | null;
    if (!svgEl) return false;
    const rects = Array.from(svgEl.querySelectorAll('rect:not(.dag-band)')) as SVGRectElement[];
    if (rects.length < 2) return true;
    const boxes = rects.map((r) => {
      // getBBox() returns coordinates in the element's local coordinate space after transforms
      const bb = r.getBBox();
      // Walk up to accumulate translate transforms from parent <g> elements
      let tx = 0;
      let ty = 0;
      let el: Element | null = r.parentElement;
      while (el && el !== svgEl) {
        const transform = el.getAttribute('transform');
        if (transform) {
          const m = transform.match(/translate\(\s*([^,)]+),\s*([^)]+)\)/);
          if (m) {
            tx += parseFloat(m[1]);
            ty += parseFloat(m[2]);
          }
        }
        el = el.parentElement;
      }
      return { x: tx + bb.x, y: ty + bb.y, x2: tx + bb.x + bb.width, y2: ty + bb.y + bb.height, w: bb.width, h: bb.height };
    });
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i];
        const b = boxes[j];
        // Skip zero-size rects (background decorators)
        if (a.w === 0 || a.h === 0 || b.w === 0 || b.h === 0) continue;
        const overlaps =
          a.x < b.x2 - 2 && a.x2 > b.x + 2 && a.y < b.y2 - 2 && a.y2 > b.y + 2;
        if (overlaps) return false;
      }
    }
    return true;
  });
  expect(noOverlap).toBe(true);

  await page.locator('#workflow-detail-view svg').screenshot({
    path: path.join(SCREENSHOTS_DIR, 'workflow-dag-spec-refinement.png'),
  });
});

// ---------------------------------------------------------------------------
// E2E-WF-08 — DAG is server-rendered (response contains diagram_svg or dag_svg)
// ---------------------------------------------------------------------------
test('E2E-WF-08 — DAG SVG comes from server response (server-rendered, not client-computed)', async ({
  page,
}) => {
  await openWorkflowsTab(page);

  // Intercept the workflow detail API response
  let capturedSvg: string | null = null;

  page.on('response', async (response) => {
    const url = response.url();
    if (
      (url.includes('/api/workflows/tdd-cycle') || url.includes('/api/workflows?') || url.endsWith('/api/workflows'))
    ) {
      try {
        const body = await response.json();
        // Check both field names per divergence D1 in the test plan
        if (typeof body.diagram_svg === 'string' && body.diagram_svg.includes('<svg')) {
          capturedSvg = body.diagram_svg;
        } else if (typeof body.dag_svg === 'string' && body.dag_svg.includes('<svg')) {
          capturedSvg = body.dag_svg;
        } else if (Array.isArray(body.workflows)) {
          // List endpoint: check each workflow
          for (const wf of body.workflows) {
            if (wf.name === 'tdd-cycle') {
              if (typeof wf.diagram_svg === 'string' && wf.diagram_svg.includes('<svg')) {
                capturedSvg = wf.diagram_svg;
              } else if (typeof wf.dag_svg === 'string' && wf.dag_svg.includes('<svg')) {
                capturedSvg = wf.dag_svg;
              }
            }
          }
        }
      } catch {
        // Not JSON
      }
    }
  });

  const tddCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
    hasText: 'tdd-cycle',
  }).first();
  await tddCard.locator('.workflow-dag-cta').click();
  await page.waitForSelector('#workflow-detail-view svg', { timeout: 10000 });

  // The SVG rendered in the DOM must come from the server
  expect(capturedSvg).not.toBeNull();
  expect(capturedSvg).toContain('<svg');
});

// ---------------------------------------------------------------------------
// E2E-WF-09 — No Mermaid library loaded
// ---------------------------------------------------------------------------
test('E2E-WF-09 — No Mermaid library is loaded', async ({ page }) => {
  const mermaidRequests: string[] = [];

  page.on('request', (req) => {
    if (req.url().toLowerCase().includes('mermaid')) {
      mermaidRequests.push(req.url());
    }
  });

  await openWorkflowsTab(page);

  // Navigate to a workflow detail
  const firstCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').first();
  await firstCard.locator('.workflow-dag-cta').click();
  await page.waitForSelector('#workflow-detail-view', { timeout: 10000 });

  // No mermaid network requests
  expect(mermaidRequests).toHaveLength(0);

  // No mermaid script tags
  const mermaidScripts = await page.$$eval(
    'script[src]',
    (scripts) =>
      scripts
        .map((s) => s.getAttribute('src') || '')
        .filter((src) => src.toLowerCase().includes('mermaid'))
  );
  expect(mermaidScripts).toHaveLength(0);

  // window.mermaid must not be defined
  const hasMermaid = await page.evaluate(
    () => typeof (window as any).mermaid !== 'undefined'
  );
  expect(hasMermaid).toBe(false);
});

// ---------------------------------------------------------------------------
// E2E-WF-10 — "Back to Workflows" navigation restores the grid
// ---------------------------------------------------------------------------
test('E2E-WF-10 — "Back to Workflows" button restores the workflow grid', async ({ page }) => {
  await openWorkflowsTab(page);

  // Open tdd-cycle detail
  const tddCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
    hasText: 'tdd-cycle',
  }).first();
  await tddCard.locator('.workflow-dag-cta').click();
  await page.waitForSelector('#workflow-detail-view', { timeout: 10000 });

  // Click back button
  const backBtn = await page.$('#detail-back-btn');
  expect(backBtn).not.toBeNull();
  await backBtn!.click();

  // Grid must be restored
  await page.waitForSelector(
    '#workflows-grid .workflow-card:not(.workflow-card--skeleton)',
    { timeout: 8000 }
  );

  const cardCount = await page.$$eval(
    '#workflows-grid .workflow-card:not(.workflow-card--skeleton)',
    (cards) => cards.length
  );
  expect(cardCount).toBe(12);

  // Detail view must be gone or hidden
  const detailGone =
    (await page.$('#workflow-detail-view')) === null ||
    !(await page.$eval('#workflow-detail-view', (el) =>
      el.offsetParent !== null
    ));
  expect(detailGone).toBe(true);

  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'workflows-grid-after-back.png'),
    fullPage: false,
  });
});

// ---------------------------------------------------------------------------
// E2E-WF-11 — Workflows API response shape validation
// ---------------------------------------------------------------------------
test('E2E-WF-11 — GET /api/workflows returns 200 with 12 workflows and tdd-cycle has 5 stages', async ({
  request,
}) => {
  const response = await request.get(`${BASE_URL}/api/workflows`, {
    headers: authHeaders(),
  });
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(body).toHaveProperty('workflows');
  expect(Array.isArray(body.workflows)).toBe(true);
  expect(body.workflows).toHaveLength(12);

  const tddCycle = body.workflows.find((w: any) => w.name === 'tdd-cycle');
  expect(tddCycle).toBeTruthy();

  // Each workflow must have a stages array with id, agent, needs
  for (const wf of body.workflows) {
    expect(wf).toHaveProperty('name');
    // stage_count or stages array must be present
    const hasStageCount = typeof wf.stage_count === 'number';
    const hasStagesArray = Array.isArray(wf.stages);
    expect(hasStageCount || hasStagesArray).toBe(true);
  }

  // If stages are included in list response, validate tdd-cycle stages
  if (Array.isArray(tddCycle.stages)) {
    expect(tddCycle.stages).toHaveLength(5);
    const firstStage = tddCycle.stages[0];
    expect(firstStage).toHaveProperty('id');
    expect(firstStage).toHaveProperty('agent');
    expect(firstStage).toHaveProperty('needs');
    expect(Array.isArray(firstStage.needs)).toBe(true);
    expect(firstStage.needs).toHaveLength(0); // first stage has no needs
  } else {
    // Validate via detail endpoint
    const detailResponse = await request.get(`${BASE_URL}/api/workflows/tdd-cycle`, {
      headers: authHeaders(),
    });
    expect(detailResponse.status()).toBe(200);
    const detailBody = await detailResponse.json();
    expect(Array.isArray(detailBody.stages)).toBe(true);
    expect(detailBody.stages).toHaveLength(5);
    const firstStage = detailBody.stages[0];
    expect(firstStage).toHaveProperty('id');
    expect(firstStage).toHaveProperty('agent');
    expect(firstStage).toHaveProperty('needs');
    expect(firstStage.needs).toHaveLength(0);
  }
});

// ---------------------------------------------------------------------------
// E2E-WF-12 — Workflows API requires Bearer auth
// ---------------------------------------------------------------------------
test('E2E-WF-12 — GET /api/workflows without Bearer token returns 401', async ({ request }) => {
  const response = await request.get(`${BASE_URL}/api/workflows`, {
    headers: {},
  });
  expect(response.status()).toBe(401);
});

// ---------------------------------------------------------------------------
// E2E-WF-13 — Accessibility audit on Workflows tab
// ---------------------------------------------------------------------------
test('E2E-WF-13 — axe-core: zero critical/serious violations on Workflows tab', async ({
  page,
}) => {
  await openWorkflowsTab(page);

  const { AxeBuilder } = await import('@axe-core/playwright');
  // color-contrast is excluded: palette is a design-system decision tracked separately.
  // This test targets structural/semantic accessibility (focus, labels, ARIA, keyboard).
  const results = await new AxeBuilder({ page })
    .include('#section-workflows')
    .withTags(['wcag2a', 'wcag2aa'])
    .disableRules(['color-contrast'])
    .analyze();

  const criticalOrSerious = results.violations.filter(
    (v) => v.impact === 'critical' || v.impact === 'serious',
  );
  expect(criticalOrSerious).toHaveLength(0);
});

// ---------------------------------------------------------------------------
// E2E-WF-14 — DAG SVG has accessibility attributes (role="img" and <title>)
// ---------------------------------------------------------------------------
test('E2E-WF-14 — DAG SVG has role="img" and non-empty <title> element', async ({ page }) => {
  await openWorkflowsTab(page);

  const tddCard = await page.locator('.workflow-card:not(.workflow-card--skeleton)').filter({
    hasText: 'tdd-cycle',
  }).first();
  await tddCard.locator('.workflow-dag-cta').click();
  await page.waitForSelector('#workflow-detail-view svg', { timeout: 10000 });

  // role="img" on the SVG element
  const svgRole = await page.$eval('#workflow-detail-view svg', (el) =>
    el.getAttribute('role')
  );
  expect(svgRole).toBe('img');

  // <title> element inside SVG with non-empty text
  const titleText = await page.$eval('#workflow-detail-view svg title', (el) =>
    el.textContent?.trim() ?? ''
  );
  expect(titleText.length).toBeGreaterThan(0);
});
