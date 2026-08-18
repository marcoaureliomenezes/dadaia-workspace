/**
 * header-row-width.spec.ts — FR3 single-line header/control-row width guard
 * (release v0.1.59 · Q2/PM Binding Ruling 2 · Option A — authored in W3
 * co-located with the fix, captured RED against the pre-fix wrapping tree BEFORE
 * the de-inline + single-line CSS lands, then GREEN after).
 *
 * Surface: the shared `.section-header` + `.runtime-switcher` control-row pattern
 *          in the Sessions tab — the operator's "header/control rows that wrap
 *          onto two or more lines" complaint.
 *
 * Falsifiable invariant (AC-4): the Sessions section-header lays its <h2> title
 * and the `.runtime-switcher` control out on ONE line. The control must share the
 * heading's vertical band — its top edge sits ABOVE the heading's bottom edge. A
 * WRAPPED control (the pre-fix block-layout bug, where `.section-header` is
 * display:block so the switcher stacks onto a second line) is pushed below the
 * heading, so its top would be at/below the heading's bottom and the header's
 * rendered height would roughly double.
 *
 * RED anchor (empirically pinned — recorded on the T-59-30 task line): the wrap is
 * STRUCTURAL, not width-responsive — the pre-fix `.section-header` is display:block,
 * so the switcher stacks below the title at EVERY viewport width. This spec runs at
 * BOTH 1024px (the `--main` content cap) and 1440px, on all 3 themes; every one of
 * the 6 combinations is genuinely RED against the pre-fix tree and GREEN after the
 * fix. (AC-9(d) sabotage: restoring the inline `margin-left:auto` wrapping row
 * re-reds this spec at the pinned width.)
 *
 * v0.1.79 amendment: the Sessions dashboard relocated from its own standalone tab
 * into a sub-section inside the "Agents" (`#section-subagents`) tabpanel;
 * `#section-sessions` and its `.section-header` survive unchanged as the nested
 * mount, so this guard still applies at its original selector, now scoped under
 * `#section-subagents`.
 *
 * Intent: CONTRACT — v0.1.59 FR3 / AC-4 (single-line header/control-row width guard)
 * Owner: software-engineer
 */

import { test, expect, Page } from '@playwright/test';
import { gotoPanel, activateSessionsSubsection } from './helpers';

const THEMES = ['mint', 'sage', 'warm'] as const;
const WIDTHS = [1024, 1440] as const;

type RowBoxes = {
  headerBox: { x: number; y: number; width: number; height: number };
  h2Box: { x: number; y: number; width: number; height: number };
  rsBox: { x: number; y: number; width: number; height: number };
};

async function measureSessionsHeaderRow(page: Page): Promise<RowBoxes> {
  const header = page.locator('#section-subagents #section-sessions .section-header');
  const h2 = header.locator('h2');
  const rs = header.locator('.runtime-switcher');
  await header.waitFor({ state: 'visible', timeout: 8000 });
  await rs.waitFor({ state: 'visible', timeout: 8000 });
  const headerBox = await header.boundingBox();
  const h2Box = await h2.boundingBox();
  const rsBox = await rs.boundingBox();
  if (!headerBox || !h2Box || !rsBox) {
    throw new Error('Sessions header / h2 / runtime-switcher not measurable');
  }
  return { headerBox, h2Box, rsBox };
}

for (const theme of THEMES) {
  for (const width of WIDTHS) {
    test(`FR3 — Sessions header/control row is single-line (no wrap) — theme=${theme} @${width}px`, async ({
      page,
    }) => {
      // Apply the theme via the pre-paint head script (localStorage), matching
      // E2E-THM-06 — no dependency on the theme-switcher click flow.
      await page.addInitScript((t) => {
        try {
          localStorage.setItem('dadaia-panel-theme', t as string);
        } catch {
          /* storage may be unavailable in some contexts; the default theme still renders */
        }
      }, theme);
      await page.setViewportSize({ width, height: 900 });
      await gotoPanel(page);

      const applied = await page.evaluate(() => document.documentElement.dataset.theme);
      expect(applied, `theme was not applied by the pre-paint script`).toBe(theme);

      await activateSessionsSubsection(page);
      const { headerBox, h2Box, rsBox } = await measureSessionsHeaderRow(page);

      const h2Bottom = h2Box.y + h2Box.height;
      const diag =
        `theme=${theme} @${width}px :: ` +
        `h2 y=${h2Box.y.toFixed(1)} h=${h2Box.height.toFixed(1)} bottom=${h2Bottom.toFixed(1)}; ` +
        `runtime-switcher y=${rsBox.y.toFixed(1)} h=${rsBox.height.toFixed(1)}; ` +
        `header h=${headerBox.height.toFixed(1)}`;

      // (1) Primary: the control shares the heading's row — its top is above the
      //     heading's bottom. A wrapped control is on a second line (top >= bottom).
      expect(
        rsBox.y,
        `runtime-switcher WRAPS below the heading (${diag})`
      ).toBeLessThan(h2Bottom);

      // (2) Height: the header is a single row. A single row's height is bounded by
      //     the taller child + padding/border; a wrapped header stacks both children
      //     and roughly doubles. The generous allowance keeps this robust across
      //     font metrics/themes while still separating single-row from wrapped.
      const singleRowCeiling = Math.max(h2Box.height, rsBox.height) + 24;
      expect(
        headerBox.height,
        `Sessions header is taller than a single control row — it wrapped (${diag})`
      ).toBeLessThan(singleRowCeiling);
    });
  }
}
