"""CSS design tokens for the Dadaia Workspace Panel.

Phase 1 (SE): contains the :root block of custom properties extracted from
_assets.py PANEL_CSS.
Phase 2 (FE / PR3-03): adds three theme palettes via [data-theme="mint"|"sage"|"warm"]
selectors. Mint is the default — its values match :root for zero visual regression.

Brand hex values (immutable, per brand-identity-v1):
  #9cddc8  mint
  #bfd8ad  sage
  #ddd9ab  warm olive
  #f7af63  amber
  #633d2e  brown
"""

TOKENS_CSS: str = """
:root {
  --color-bg:            #fafafa;
  --color-surface:       #ffffff;
  --color-text:          #222222;
  --color-heading:       #111111;
  --color-muted:         #666666;
  --color-border:        #dddddd;
  --color-border-strong: #333333;
  --color-accent:        #9cddc8; /* was #7ec8e3 — brand-identity-v1 */
  --color-accent-dark:   #2d7d9a;
  --color-code-bg:       #f0f0f0;
  --color-th-bg:         #eeeeee;
  --color-primary-ring:  #9cddc8; /* was #7ec8e3 — brand-identity-v1 */
  --color-primary-bg:    #f0fbf7; /* was #f0faff — brand-identity-v1 */
  --color-accent-secondary: #bfd8ad; /* brand-identity-v1 */
  --color-warning-bg:    #ddd9ab; /* brand-identity-v1 */
  --color-alert:         #f7af63; /* brand-identity-v1 */
  --color-cost:          #633d2e; /* brand-identity-v1 */
  --color-active-dot:    #3aaa6e;
  --color-stale-dot:     #cc7700;
  --color-row-hover:     #f5f5f5;
  --color-placeholder-bg: #f7f7f7;
  --color-card-hover:    #f8feff;

  --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --font-mono:  ui-monospace, "SFMono-Regular", Consolas, monospace;

  --radius:      4px;
  --radius-card: 6px;
  --space-xs:    0.3rem;
  --space-sm:    0.6rem;
  --space-md:    1rem;
  --space-lg:    1.5rem;
  --space-xl:    2rem;
  --topbar-h:    52px;
  --nav-h:       44px;
}

/* ── Theme: Mint (default) ───────────────────────────────────────────────────
   Applied when data-theme="mint" is set explicitly, or when no data-theme
   attribute is present (html:not([data-theme])). Values are identical to :root
   so switching to Mint is a no-op — zero visual regression.
   ─────────────────────────────────────────────────────────────────────────── */
html[data-theme="mint"],
html:not([data-theme]) {
  --color-accent:           #9cddc8; /* mint — tab active underline, card left-border, chips */
  --color-accent-dark:      #2d7d9a; /* teal-blue — links, CTA text (WCAG AA on light bg) */
  --color-primary-ring:     #9cddc8;
  --color-primary-bg:       #f0fbf7;
  --color-accent-secondary: #bfd8ad; /* sage — chip hover */
  --color-warning-bg:       #ddd9ab; /* warm olive — banners */
  --color-alert:            #f7af63; /* amber — badges */
  --color-cost:             #633d2e; /* brown — headings, wordmark (WCAG AAA ~7.5:1 on white) */
  --color-active-dot:       #3aaa6e;
  --color-card-hover:       #f8feff;
}

/* ── Theme: Sage (sage-forward) ──────────────────────────────────────────────
   Accent is sage-green. Softer, more muted. Accent-dark shifts to a deeper
   green-grey. Good for long sessions where mint reads slightly electric.
   WCAG: accent-dark on white meets AA (>=4.5:1). Accent is decorative only.
   ─────────────────────────────────────────────────────────────────────────── */
html[data-theme="sage"] {
  --color-accent:           #bfd8ad; /* sage — primary accent */
  --color-accent-dark:      #4a7c59; /* deep sage-green — links (WCAG AA on white) */
  --color-primary-ring:     #bfd8ad;
  --color-primary-bg:       #f5fbf0;
  --color-accent-secondary: #9cddc8; /* mint — chip hover (inverted from default) */
  --color-warning-bg:       #ddd9ab; /* warm olive — unchanged */
  --color-alert:            #f7af63; /* amber — unchanged */
  --color-cost:             #633d2e; /* brown — unchanged (WCAG AAA on white) */
  --color-active-dot:       #4a7c59; /* matches accent-dark */
  --color-card-hover:       #f6faf3;
}

/* ── Theme: Warm (amber-forward) ─────────────────────────────────────────────
   Accent is amber. Cost becomes a deeper brown for stronger heading contrast.
   Works well at the end of long days when cool tones read cold.
   WCAG NOTE: amber alone fails the 3:1 UI-component contrast threshold on white,
   so focus-visible rules for this theme use a double outline (accent-dark first,
   which meets 4.5:1). See structure.py for the override rule (E2E-THM-07).
   ─────────────────────────────────────────────────────────────────────────── */
html[data-theme="warm"] {
  --color-accent:           #f7af63; /* amber — tabs, borders, chips */
  --color-accent-dark:      #633d2e; /* brown — links and CTA text (WCAG AA ~7.5:1 on white) */
  --color-primary-ring:     #f7af63;
  --color-primary-bg:       #fffbf4;
  --color-accent-secondary: #ddd9ab; /* warm olive — chip hover */
  --color-warning-bg:       #bfd8ad; /* sage — banners get a cool counterpoint */
  --color-alert:            #633d2e; /* brown — alert badges */
  --color-cost:             #4a3020; /* deeper brown — headings (WCAG AA ~10:1 on white) */
  --color-active-dot:       #b36a00; /* darkened amber — status dots (WCAG AA ~4.8:1 on white) */
  --color-card-hover:       #fffaf2;
}
"""
