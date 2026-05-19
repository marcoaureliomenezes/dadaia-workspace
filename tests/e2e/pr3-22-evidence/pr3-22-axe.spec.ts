/**
 * PR3-22 — one-shot axe-core scans: Mint/Sage/Warm × Agents/Workflows.
 * Run from repo root:
 *   PANEL_TEST_PORT=4999 npx playwright test /tmp/pr3-22-axe.spec.ts --reporter=line
 * Outputs JSON summary to /tmp/pr3-22-axe-results.json.
 */
import { test, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import * as fs from 'fs';
import * as path from 'path';

const PANEL_TOKEN = fs.readFileSync(
  path.join(process.env.HOME || '', '.dadaia', 'state', 'panel.token'),
  'utf-8',
).trim();
const BASE_URL = `http://127.0.0.1:${process.env.PANEL_TEST_PORT || 4999}`;

const themes = ['mint', 'sage', 'warm'] as const;
const surfaces = ['agents', 'workflows'] as const;
const results: Array<{
  theme: string;
  surface: string;
  critical: number;
  serious: number;
  moderate: number;
  minor: number;
}> = [];

async function gotoWithToken(page: Page) {
  await page.goto(`${BASE_URL}/?token=${encodeURIComponent(PANEL_TOKEN)}`, {
    waitUntil: 'domcontentloaded',
  });
}

for (const theme of themes) {
  for (const surface of surfaces) {
    test(`axe ${theme} × ${surface}`, async ({ page }) => {
      await gotoWithToken(page);
      // Switch theme
      await page.click('#theme-btn');
      await page.waitForSelector('#theme-menu:not([hidden])', { timeout: 3000 });
      await page.click(`[data-theme-value="${theme}"]`);
      // Activate surface tab
      await page.click(`#tab-${surface}`);
      await page.waitForSelector(`#section-${surface}.active`, { timeout: 5000 });
      const cardSel =
        surface === 'agents'
          ? '#agents-grid .agent-card:not(.agent-card--skeleton)'
          : '#workflows-grid .workflow-card:not(.workflow-card--skeleton)';
      await page.waitForSelector(cardSel, { timeout: 15000 });

      const scan = await new AxeBuilder({ page }).analyze();
      const by = {
        critical: scan.violations.filter((v) => v.impact === 'critical').length,
        serious: scan.violations.filter((v) => v.impact === 'serious').length,
        moderate: scan.violations.filter((v) => v.impact === 'moderate').length,
        minor: scan.violations.filter((v) => v.impact === 'minor').length,
      };
      results.push({ theme, surface, ...by });
      expect(by.critical, `critical: ${theme}/${surface}`).toBe(0);
      expect(by.serious, `serious: ${theme}/${surface}`).toBe(0);
    });
  }
}

test.afterAll(async () => {
  fs.writeFileSync('/tmp/pr3-22-axe-results.json', JSON.stringify(results, null, 2));
});
