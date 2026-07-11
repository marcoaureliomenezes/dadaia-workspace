/**
 * button-smoke.spec.ts — FR7 restyled-control smoke (release v0.1.59 · W6 · AC-8)
 *
 * The operator's standing complaint on the pre-overhaul panel was "ugly, unstyled
 * buttons … looks like a 2005 website". FR2 restyled every interactive control
 * uniformly from `TOKENS_CSS` (padding rhythm, radius, hover/active/focus-visible).
 * This is the honest, falsifiable smoke that the shipped controls are actually
 * STYLED and not browser-default: it reads the computed `border-radius` / `padding`
 * of the three restyled button families and asserts token-driven values that a bare
 * UA-stylesheet <button> (padding ~1px 6px, border-radius 0px) does NOT carry.
 *
 * Restyled control → shipped token values (structure.py / tokens.py, root 16px):
 *   .theme-btn     padding var(--control-pad-y/-x) = 6.4px 12px · radius var(--radius-pill)  = 9999px (pill)
 *   .runtime-btn   padding var(--control-pad-y/-x) = 6.4px 12px · radius var(--control-radius) = 6px
 *   .nav-tab       padding var(--space-sm/-md)     = 9.6px 16px · (bottom-border tab, no radius)
 *
 * Falsifiable (AC-9 mutation-sanity): stripping a restyled control's padding/radius
 * back to the browser default re-reds this spec (captured on the T-59-60 task line).
 * A browser-default button has paddingTop≈1px, paddingLeft≈6px, borderRadius 0px —
 * every threshold below sits strictly above that default.
 */

import { test, expect, Page } from '@playwright/test';
import { gotoPanel, activateSessionsSubsection } from './helpers';

type BoxStyle = {
  paddingTop: number;
  paddingLeft: number;
  borderRadius: number;
};

const px = (v: string): number => parseFloat(v) || 0;

async function readControlStyle(page: Page, selector: string): Promise<BoxStyle> {
  const el = page.locator(selector).first();
  await el.waitFor({ state: 'attached', timeout: 8000 });
  return el.evaluate((node) => {
    const cs = getComputedStyle(node as Element);
    const num = (s: string): number => parseFloat(s) || 0;
    return {
      paddingTop: num(cs.paddingTop),
      paddingLeft: num(cs.paddingLeft),
      borderRadius: num(cs.borderTopLeftRadius),
    };
  });
}

// A browser-default <button> in Chromium is ~1px/6px padding, 0px radius. Every
// restyled control clears these thresholds by construction; an UNstyled control
// would fall back under them and fail.
const MIN_PAD_Y = 4; // token rhythm ≥ 6.4px; UA default ≈ 1px
const MIN_PAD_X = 8; // token rhythm ≥ 12px; UA default ≈ 6px
const MIN_RADIUS = 4; // pill 9999px / control-radius 6px; UA default 0px

test('FR7 — restyled controls carry token-driven padding rhythm (not browser-default)', async ({
  page,
}) => {
  await gotoPanel(page);
  await page.waitForSelector('#theme-btn');

  // .nav-tab and .theme-btn live in the always-visible topbar / nav.
  const navTab = await readControlStyle(page, '.nav-tab');
  const themeBtn = await readControlStyle(page, '.theme-btn');

  // .runtime-btn lives in the Sessions sub-section header, now nested inside the
  // 1º Agentic Layer tabpanel — activate it so the control is laid out exactly as
  // the operator sees it (v0.1.79 relocation).
  await activateSessionsSubsection(page);
  const runtimeBtn = await readControlStyle(page, '.runtime-btn');

  for (const [name, s] of [
    ['.nav-tab', navTab],
    ['.theme-btn', themeBtn],
    ['.runtime-btn', runtimeBtn],
  ] as const) {
    const diag = `${name} :: padTop=${s.paddingTop} padLeft=${s.paddingLeft} radius=${s.borderRadius}`;
    expect(s.paddingTop, `${name} has browser-default vertical padding — control is unstyled (${diag})`).toBeGreaterThan(
      MIN_PAD_Y,
    );
    expect(s.paddingLeft, `${name} has browser-default horizontal padding — control is unstyled (${diag})`).toBeGreaterThan(
      MIN_PAD_X,
    );
  }
});

test('FR7 — pill/segmented controls carry a token-driven border-radius (not square UA default)', async ({
  page,
}) => {
  await gotoPanel(page);
  await page.waitForSelector('#theme-btn');

  // .theme-btn is a pill (var(--radius-pill) = 9999px); getComputedStyle resolves it
  // to a large px band value.
  const themeBtn = await readControlStyle(page, '.theme-btn');
  expect(
    themeBtn.borderRadius,
    `.theme-btn has no border-radius — pill styling missing (radius=${themeBtn.borderRadius})`,
  ).toBeGreaterThan(MIN_RADIUS);

  // .runtime-btn is a soft-cornered segment (var(--control-radius) = 6px).
  await activateSessionsSubsection(page);
  const runtimeBtn = await readControlStyle(page, '.runtime-btn');
  expect(
    runtimeBtn.borderRadius,
    `.runtime-btn has no border-radius — segment styling missing (radius=${runtimeBtn.borderRadius})`,
  ).toBeGreaterThan(MIN_RADIUS);
});
