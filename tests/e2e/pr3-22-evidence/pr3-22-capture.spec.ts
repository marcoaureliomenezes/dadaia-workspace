/**
 * PR3-22 evidence capture: missing screenshot + axe-core scans.
 *
 * NOT part of the permanent test suite. Run once for evidence capture.
 * Results written to the QA reports directory.
 */

import { test, expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';
import * as fs from 'fs';
import * as path from 'path';

const TOKEN_PATH = path.join(process.env.HOME || '', '.dadaia', 'state', 'panel.token');
const PANEL_TOKEN = fs.existsSync(TOKEN_PATH) ? fs.readFileSync(TOKEN_PATH, 'utf-8').trim() : '';
const BASE_URL = 'http://127.0.0.1:4999';

const REPORT_DIR = '/home/marco/workspace/dadaia/.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T201500Z';
const SCREENSHOTS_DIR = path.join(REPORT_DIR, 'screenshots');

// Shared axe-results accumulator (per-process, workers=1)
const axeResults: Record<string, {
  critical: number; serious: number; totalViolations: number;
  violations: Array<{ id: string; impact: string | null; help: string; nodes: number }>;
  passes: number;
}> = {};

async function gotoPanel(page: any, extraPath = '/') {
  await page.goto(`${BASE_URL}${extraPath}?token=${encodeURIComponent(PANEL_TOKEN)}`, {
    waitUntil: 'domcontentloaded',
  });
}

async function activateTab(page: any, sectionId: string) {
  await page.click(`#tab-${sectionId}`);
  await page.waitForSelector(`#section-${sectionId}.active`, { timeout: 8000 });
}

async function applyTheme(page: any, theme: 'mint' | 'sage' | 'warm') {
  await page.evaluate((t: string) => {
    document.documentElement.setAttribute('data-theme', t);
  }, theme);
  await page.waitForTimeout(300);
}

function writeResults() {
  fs.writeFileSync(path.join(REPORT_DIR, 'axe-results.json'), JSON.stringify(axeResults, null, 2));
}

// -------------------------------------------------------------------------
// Screenshot: agent-card-collapsed-qa-engineer.png
// -------------------------------------------------------------------------
test('PR3-22-SS — capture agent-card-collapsed-qa-engineer.png', async ({ page }) => {
  await gotoPanel(page);
  await activateTab(page, 'agents');
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 15000 });

  const qaCard = page.locator('.agent-card', { hasText: 'qa-engineer' }).first();
  await qaCard.waitFor({ state: 'visible', timeout: 8000 });
  await qaCard.screenshot({
    path: path.join(SCREENSHOTS_DIR, 'agent-card-collapsed-qa-engineer.png'),
  });
  expect(fs.existsSync(path.join(SCREENSHOTS_DIR, 'agent-card-collapsed-qa-engineer.png'))).toBe(true);
});

// -------------------------------------------------------------------------
// axe-core: Mint × Agents
// -------------------------------------------------------------------------
test('PR3-22-AXE-01 — axe: Mint × Agents', async ({ page }) => {
  await gotoPanel(page);
  await applyTheme(page, 'mint');
  await activateTab(page, 'agents');
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 15000 });

  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();

  const critical = result.violations.filter(v => v.impact === 'critical');
  const serious  = result.violations.filter(v => v.impact === 'serious');
  axeResults['mint-agents'] = {
    critical: critical.length, serious: serious.length,
    totalViolations: result.violations.length,
    violations: result.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length })),
    passes: result.passes.length,
  };
  writeResults();

  if (critical.length + serious.length > 0) {
    const msgs = [...critical, ...serious].map(v => `[${v.impact}] ${v.id}: ${v.help}`).join('\n');
    throw new Error(`STOP — axe violations on Mint×Agents:\n${msgs}`);
  }
  expect(critical.length, 'critical violations Mint×Agents').toBe(0);
  expect(serious.length,  'serious violations Mint×Agents').toBe(0);
});

// -------------------------------------------------------------------------
// axe-core: Mint × Workflows
// -------------------------------------------------------------------------
test('PR3-22-AXE-02 — axe: Mint × Workflows', async ({ page }) => {
  await gotoPanel(page);
  await applyTheme(page, 'mint');
  await activateTab(page, 'workflows');
  await page.waitForTimeout(2500);

  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();

  const critical = result.violations.filter(v => v.impact === 'critical');
  const serious  = result.violations.filter(v => v.impact === 'serious');
  axeResults['mint-workflows'] = {
    critical: critical.length, serious: serious.length,
    totalViolations: result.violations.length,
    violations: result.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length })),
    passes: result.passes.length,
  };
  writeResults();

  if (critical.length + serious.length > 0) {
    const msgs = [...critical, ...serious].map(v => `[${v.impact}] ${v.id}: ${v.help}`).join('\n');
    throw new Error(`STOP — axe violations on Mint×Workflows:\n${msgs}`);
  }
  expect(critical.length, 'critical violations Mint×Workflows').toBe(0);
  expect(serious.length,  'serious violations Mint×Workflows').toBe(0);
});

// -------------------------------------------------------------------------
// axe-core: Sage × Agents
// -------------------------------------------------------------------------
test('PR3-22-AXE-03 — axe: Sage × Agents', async ({ page }) => {
  await gotoPanel(page);
  await applyTheme(page, 'sage');
  await activateTab(page, 'agents');
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 15000 });

  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();

  const critical = result.violations.filter(v => v.impact === 'critical');
  const serious  = result.violations.filter(v => v.impact === 'serious');
  axeResults['sage-agents'] = {
    critical: critical.length, serious: serious.length,
    totalViolations: result.violations.length,
    violations: result.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length })),
    passes: result.passes.length,
  };
  writeResults();

  if (critical.length + serious.length > 0) {
    const msgs = [...critical, ...serious].map(v => `[${v.impact}] ${v.id}: ${v.help}`).join('\n');
    throw new Error(`STOP — axe violations on Sage×Agents:\n${msgs}`);
  }
  expect(critical.length, 'critical violations Sage×Agents').toBe(0);
  expect(serious.length,  'serious violations Sage×Agents').toBe(0);
});

// -------------------------------------------------------------------------
// axe-core: Sage × Workflows
// -------------------------------------------------------------------------
test('PR3-22-AXE-04 — axe: Sage × Workflows', async ({ page }) => {
  await gotoPanel(page);
  await applyTheme(page, 'sage');
  await activateTab(page, 'workflows');
  await page.waitForTimeout(2500);

  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();

  const critical = result.violations.filter(v => v.impact === 'critical');
  const serious  = result.violations.filter(v => v.impact === 'serious');
  axeResults['sage-workflows'] = {
    critical: critical.length, serious: serious.length,
    totalViolations: result.violations.length,
    violations: result.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length })),
    passes: result.passes.length,
  };
  writeResults();

  if (critical.length + serious.length > 0) {
    const msgs = [...critical, ...serious].map(v => `[${v.impact}] ${v.id}: ${v.help}`).join('\n');
    throw new Error(`STOP — axe violations on Sage×Workflows:\n${msgs}`);
  }
  expect(critical.length, 'critical violations Sage×Workflows').toBe(0);
  expect(serious.length,  'serious violations Sage×Workflows').toBe(0);
});

// -------------------------------------------------------------------------
// axe-core: Warm × Agents
// -------------------------------------------------------------------------
test('PR3-22-AXE-05 — axe: Warm × Agents', async ({ page }) => {
  await gotoPanel(page);
  await applyTheme(page, 'warm');
  await activateTab(page, 'agents');
  await page.waitForSelector('#agents-grid[aria-busy="false"]', { timeout: 15000 });

  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();

  const critical = result.violations.filter(v => v.impact === 'critical');
  const serious  = result.violations.filter(v => v.impact === 'serious');
  axeResults['warm-agents'] = {
    critical: critical.length, serious: serious.length,
    totalViolations: result.violations.length,
    violations: result.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length })),
    passes: result.passes.length,
  };
  writeResults();

  if (critical.length + serious.length > 0) {
    const msgs = [...critical, ...serious].map(v => `[${v.impact}] ${v.id}: ${v.help}`).join('\n');
    throw new Error(`STOP — axe violations on Warm×Agents:\n${msgs}`);
  }
  expect(critical.length, 'critical violations Warm×Agents').toBe(0);
  expect(serious.length,  'serious violations Warm×Agents').toBe(0);
});

// -------------------------------------------------------------------------
// axe-core: Warm × Workflows
// -------------------------------------------------------------------------
test('PR3-22-AXE-06 — axe: Warm × Workflows', async ({ page }) => {
  await gotoPanel(page);
  await applyTheme(page, 'warm');
  await activateTab(page, 'workflows');
  await page.waitForTimeout(2500);

  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();

  const critical = result.violations.filter(v => v.impact === 'critical');
  const serious  = result.violations.filter(v => v.impact === 'serious');
  axeResults['warm-workflows'] = {
    critical: critical.length, serious: serious.length,
    totalViolations: result.violations.length,
    violations: result.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length })),
    passes: result.passes.length,
  };
  writeResults();

  if (critical.length + serious.length > 0) {
    const msgs = [...critical, ...serious].map(v => `[${v.impact}] ${v.id}: ${v.help}`).join('\n');
    throw new Error(`STOP — axe violations on Warm×Workflows:\n${msgs}`);
  }
  expect(critical.length, 'critical violations Warm×Workflows').toBe(0);
  expect(serious.length,  'serious violations Warm×Workflows').toBe(0);
});
