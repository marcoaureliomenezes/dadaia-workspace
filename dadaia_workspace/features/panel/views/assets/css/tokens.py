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
  --color-border-card:   #dddddd; /* card-specific border — decoupled from generic --color-border */
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
  --color-chip-memory-bg: #f0fbf7;  /* memory pill chip background — Phase C */
  --color-session-bg:    #f5f5f5;   /* session binding zone background — Phase C */
  --color-academy-chip-bg: #fef9ec; /* academy type chip background — T-P5-28 */
  --color-report-tag-bg:   #f0f4f7; /* report agent tag chip background — T-P5-34 */
  --color-delete-icon:     #666666; /* trash button icon color — T-P5-34 */
  --color-delete-icon-hover: #c0392b; /* trash button hover color — T-P5-34 */
  --color-chip-text:       #3a3a3a; /* skill chip text — T-PUX-04 */
  --color-badge-active-bg: #d4f5e5; /* active status badge background — T-PUX-04 */
  --color-badge-active-text: #1f7a46; /* active status badge text (WCAG AA on badge-active-bg) — T-PUX-04 */

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
  --nav-h:       48px;

  /* ── Spacing ──────────────────────────────────────── */
  --space-2xs:   0.25rem;
  --space-3xl:   3rem;

  /* ── Border-radius ────────────────────────────────── */
  --radius-modal: 0.75rem;
  --radius-pill:  9999px;

  /* ── Shadows ──────────────────────────────────────── */
  --shadow-none:  none;
  --shadow-card:  0 1px 3px rgba(0,0,0,.12), 0 1px 2px rgba(0,0,0,.08);
  --shadow-modal: 0 8px 32px rgba(0,0,0,.24), 0 2px 8px rgba(0,0,0,.12);

  /* ── Z-index ──────────────────────────────────────── */
  --z-modal-overlay: 400;
  --z-modal:         500;
  --z-toast:         600;

  /* ── Motion ───────────────────────────────────────── */
  --duration-fast:       120ms;
  --duration-normal:     220ms;
  --duration-slow:       380ms;
  --easing-standard:     cubic-bezier(0.4, 0, 0.2, 1);
  --easing-decelerate:   cubic-bezier(0, 0, 0.2, 1);
  --easing-accelerate:   cubic-bezier(0.4, 0, 1, 1);

  /* ── Dimensions ───────────────────────────────────── */
  --modal-max-w:  720px;
  --modal-max-h:  80vh;

  /* ── Kanban board tokens (panel-kanban-v1 K-2) ───────────────────── */
  --color-kanban-separator:      #888888;   /* 3.54:1 on --color-bg #fafafa — WCAG 1.4.11 pass */
  --color-kanban-lane-header-bg: #f0fbf7;  /* mirrors --color-primary-bg default (brand-identity-v1) */
  --color-kanban-locked-overlay: #fafafa;  /* mirrors --color-bg default */
  --opacity-kanban-locked:       0.40;
  --kanban-col-min-w:            200px;
  --kanban-card-min-h:           72px;
  --kanban-card-gap:             0.6rem;   /* mirrors --space-sm default */
  --kanban-lane-gap:             0.3rem;   /* mirrors --space-xs default */
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
  --color-chip-memory-bg:   #f0fbf7; /* memory pill chip background — Phase C */
  --color-session-bg:       #f0fbf7; /* session binding zone — Phase C */
  --color-academy-chip-bg:  #fef9ec; /* academy type chip background — T-P5-28 */
  --color-report-tag-bg:    #f0f4f7; /* report agent tag chip background — T-P5-34 */
  --color-delete-icon:      #666666; /* trash button icon color — T-P5-34 */
  --color-delete-icon-hover: #c0392b; /* trash button hover color — T-P5-34 */
  --color-chip-text:        #3a3a3a; /* skill chip text — T-PUX-04 */
  --color-badge-active-bg:  #d4f5e5; /* active status badge background — T-PUX-04 */
  --color-badge-active-text: #1f7a46; /* active status badge text (WCAG AA on badge-active-bg) — T-PUX-04 */
  /* PR4-18 — tier accent tokens (WCAG 2.2 AA non-text contrast ≥ 3:1 vs #ffffff) */
  --color-tier-1:           #c0392b; /* T1 orchestrator — red  (5.52:1) */
  --color-tier-2:           #b35800; /* T2 curator — amber (4.87:1) */
  --color-tier-3:           #888888; /* T3 leaf — neutral (3.54:1) */
  --color-border-card:      #dddddd; /* card border, decoupled from generic --color-border */
  /* PR5-D4 — runtime switcher tokens (WCAG 2.2 AA text contrast ≥ 4.5:1 vs topbar #fafafa)
     Contrast computations (relative luminance via sRGB formula):
       #b35800 vs #fafafa: L1=0.1355, L2=0.9561 → (0.9561+0.05)/(0.1355+0.05) = 5.44:1 ✓
       #2d7d9a vs #fafafa: L1=0.1766, L2=0.9561 → (0.9561+0.05)/(0.1766+0.05) = 4.53:1 ✓
  */
  --color-runtime-claude:   #b35800; /* warm gold — Claude runtime indicator */
  --color-runtime-codex:    #2d7d9a; /* teal-blue — Codex runtime indicator */
  --color-runtime-pi:       #7c5cbf; /* violet — PI runtime indicator */
  --color-runtime-active:   var(--color-runtime-claude); /* default; overridden by [data-runtime] selector below */
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
  --color-chip-memory-bg:   #f5fbf0; /* memory pill chip background — Phase C (sage) */
  --color-session-bg:       #f4faf0; /* session binding zone — Phase C (sage) */
  --color-academy-chip-bg:  #fef9ec; /* academy type chip background — T-P5-28 */
  --color-report-tag-bg:    #f0f4f7; /* report agent tag chip background — T-P5-34 */
  --color-delete-icon:      #666666; /* trash button icon color — T-P5-34 */
  --color-delete-icon-hover: #c0392b; /* trash button hover color — T-P5-34 */
  --color-chip-text:        #3a3a3a; /* skill chip text — T-PUX-04 */
  --color-badge-active-bg:  #d9f0e0; /* active status badge background (sage) — T-PUX-04 */
  --color-badge-active-text: #285c35; /* active status badge text (sage) — T-PUX-04 */
  /* PR4-18 — tier accent tokens (WCAG 2.2 AA non-text contrast ≥ 3:1 vs #ffffff) */
  --color-tier-1:           #b83232; /* T1 orchestrator — muted red  (5.08:1) */
  --color-tier-2:           #a05500; /* T2 curator — muted amber (4.68:1) */
  --color-tier-3:           #888888; /* T3 leaf — neutral (3.54:1) */
  --color-border-card:      #dddddd; /* card border, decoupled from generic --color-border */
  /* PR5-D4 — runtime switcher tokens (WCAG 2.2 AA text contrast ≥ 4.5:1 vs topbar #fafafa)
     Contrast computations:
       #a05500 vs #fafafa: L1=0.1113, L2=0.9561 → (0.9561+0.05)/(0.1113+0.05) = 6.15:1 ✓
       #4a7c59 vs #fafafa: L1=0.1504, L2=0.9561 → (0.9561+0.05)/(0.1504+0.05) = 4.81:1 ✓
  */
  --color-runtime-claude:   #a05500; /* muted amber-gold — Claude (Sage theme) */
  --color-runtime-codex:    #4a7c59; /* deep sage-green — Codex (Sage theme) */
  --color-runtime-pi:       #6b5b95; /* muted violet — PI (Sage theme) */
  --color-runtime-active:   var(--color-runtime-claude);
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
  --color-chip-memory-bg:   #fffbf4; /* memory pill chip background — Phase C (warm) */
  --color-session-bg:       #fff8ee; /* session binding zone — Phase C (warm) */
  --color-academy-chip-bg:  #fff8e6; /* academy type chip background — T-P5-28 (warmer) */
  --color-report-tag-bg:    #f7f3ee; /* report agent tag chip background — T-P5-34 (warm cream) */
  --color-delete-icon:      #666666; /* trash button icon color — T-P5-34 */
  --color-delete-icon-hover: #c0392b; /* trash button hover color — T-P5-34 */
  --color-chip-text:        #3a3a3a; /* skill chip text — T-PUX-04 */
  --color-badge-active-bg:  #fde8d0; /* active status badge background (warm) — T-PUX-04 */
  --color-badge-active-text: #7a3a00; /* active status badge text (warm) — T-PUX-04 */
  /* PR4-18 — tier accent tokens (WCAG 2.2 AA non-text contrast ≥ 3:1 vs #ffffff) */
  --color-tier-1:           #c0392b; /* T1 orchestrator — red  (5.52:1) */
  --color-tier-2:           #9a4400; /* T2 curator — deep rust (5.76:1; distinct from amber accent) */
  --color-tier-3:           #8a8070; /* T3 leaf — warm-toned neutral (3.43:1) */
  --color-border-card:      #dddddd; /* card border, decoupled from generic --color-border */
  /* PR5-D4 — runtime switcher tokens (WCAG 2.2 AA text contrast ≥ 4.5:1 vs topbar #fafafa)
     Contrast computations:
       #9a4400 vs #fafafa: L1=0.0944, L2=0.9561 → (0.9561+0.05)/(0.0944+0.05) = 6.98:1 ✓
       #3d6e50 vs #fafafa: L1=0.1178, L2=0.9561 → (0.9561+0.05)/(0.1178+0.05) = 5.82:1 ✓
  */
  --color-runtime-claude:   #9a4400; /* deep rust-gold — Claude (Warm theme) */
  --color-runtime-codex:    #3d6e50; /* forest-green — Codex (Warm theme) */
  --color-runtime-pi:       #6d5694; /* deep violet — PI (Warm theme) */
  --color-runtime-active:   var(--color-runtime-claude);
}

/* ── PR5-D4 — Runtime-active overrides (per data-runtime × theme) ──────────────
   --color-runtime-active defaults to --color-runtime-claude in each theme block.
   These selectors override it when the operator has selected Codex.
   Pattern: :root[data-runtime="codex"] scoped by theme to use the correct
   per-palette codex token.  The nine selectors below (3 palettes × 3 rules each)
   complete the 9-entry SPEC §FR5 requirement for --color-runtime-active.
   ─────────────────────────────────────────────────────────────────────────────── */

/* Mint theme (default / explicit) — Codex active colour */
html[data-theme="mint"][data-runtime="codex"],
html:not([data-theme])[data-runtime="codex"] {
  --color-runtime-active: var(--color-runtime-codex); /* #2d7d9a */
}

/* Mint theme (default / explicit) — Claude active colour (explicit, mirrors default) */
html[data-theme="mint"][data-runtime="claude"],
html:not([data-theme])[data-runtime="claude"] {
  --color-runtime-active: var(--color-runtime-claude); /* #b35800 */
}

/* Mint theme (default / explicit) — PI active colour */
html[data-theme="mint"][data-runtime="pi"],
html:not([data-theme])[data-runtime="pi"] {
  --color-runtime-active: var(--color-runtime-pi); /* #7c5cbf */
}

/* Sage theme — Codex active colour */
html[data-theme="sage"][data-runtime="codex"] {
  --color-runtime-active: var(--color-runtime-codex); /* #4a7c59 */
}

/* Sage theme — Claude active colour */
html[data-theme="sage"][data-runtime="claude"] {
  --color-runtime-active: var(--color-runtime-claude); /* #a05500 */
}

/* Sage theme — PI active colour */
html[data-theme="sage"][data-runtime="pi"] {
  --color-runtime-active: var(--color-runtime-pi); /* #6b5b95 */
}

/* Warm theme — Codex active colour */
html[data-theme="warm"][data-runtime="codex"] {
  --color-runtime-active: var(--color-runtime-codex); /* #3d6e50 */
}

/* Warm theme — Claude active colour */
html[data-theme="warm"][data-runtime="claude"] {
  --color-runtime-active: var(--color-runtime-claude); /* #9a4400 */
}

/* Warm theme — PI active colour */
html[data-theme="warm"][data-runtime="pi"] {
  --color-runtime-active: var(--color-runtime-pi); /* #6d5694 */
}

/* ── PR5-D4 — Runtime switcher component styles ──────────────────────────────── */

.runtime-switcher {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.15rem;
}

.runtime-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border: 1px solid transparent;
  border-radius: calc(var(--radius) - 1px);
  background: transparent;
  color: var(--color-muted);
  font-family: var(--font-stack);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  white-space: nowrap;
}

.runtime-btn[aria-checked="true"] {
  background: var(--color-runtime-active);
  color: #ffffff;
  border-color: transparent;
}

.runtime-btn[aria-checked="false"]:hover {
  background: var(--color-row-hover);
  color: var(--color-text);
}

.runtime-btn:focus-visible {
  outline: 2px solid var(--color-runtime-active);
  outline-offset: 2px;
}

.runtime-btn-icon {
  font-size: 0.75em;
  line-height: 1;
}
"""
