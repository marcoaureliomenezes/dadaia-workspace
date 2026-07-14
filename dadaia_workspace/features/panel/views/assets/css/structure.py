"""Structural CSS for the Dadaia Workspace Panel.

Phase 1 (SE): reset, body, links, code, topbar, nav-tabs, main content area,
section visibility, section-header, servers section, memory cards grid, and
shared utility classes.
Phase 2 (FE / PR3-03): adds the Warm theme focus-visible override (E2E-THM-07).
"""

STRUCTURE_CSS: str = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-stack);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.55;
  min-height: 100vh;
}

a { color: var(--color-accent-dark); text-decoration: none; }
a:hover, a:focus { text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--color-accent, #9cddc8); outline-offset: 2px; border-radius: 2px; }

code {
  font-family: var(--font-mono);
  background: var(--color-code-bg);
  padding: 0.1em 0.3em;
  border-radius: var(--radius);
  font-size: 0.88em;
}

/* ── Top bar ─────────────────────────────────────── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--topbar-h);
  background: var(--color-surface);
  border-bottom: 2px solid var(--color-border-strong);
  display: flex;
  align-items: center;
  padding: 0 var(--space-lg);
  gap: var(--space-md);
}

.topbar-logo { color: var(--color-cost, #633d2e); display: inline-flex; align-items: center; margin-right: 0.5rem; }
.topbar-logo svg { width: 36px; height: 36px; display: block; }

.topbar-wordmark {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e); /* brand-identity-v1 T-BR-07: high-contrast brown (AAA on white) */
  letter-spacing: -0.01em;
}
.topbar-wordmark span { color: var(--color-accent-dark); }
.topbar-divider { width: 1px; height: 24px; background: var(--color-border); }
.topbar-subtitle { color: var(--color-muted); font-size: 0.9rem; }

/* ── Topbar right cluster + theme-switcher anchor (de-inlined v0.1.59 / FR3) ──
   Replaces the former inline `style=` attributes on .topbar-right and
   .theme-switcher in views/index.py (CSP-clean, token-anchored — no ad-hoc
   literals). .topbar-right right-aligns the control cluster inside the flex
   .topbar; .theme-switcher establishes the positioning context for the
   absolutely-positioned #theme-menu popover. */
.topbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}
.theme-switcher {
  position: relative;
}
/* ── Navigation tabs ─────────────────────────────── */
.nav-tabs {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  max-width: 100%;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  padding: 0 var(--space-lg);
  gap: 0;
}

/* ── Controls · one button language (v0.1.59 / FR2) ──────────────────────────
   Nav tabs, the theme button, and the runtime switcher share the token-anchored
   control vocabulary from tokens.py (--control-*, --focus-ring-*, --text-*,
   --font-weight-*). No ad-hoc hex / px / rem-font-size / px-radius literals in
   these rules — grep-enforced by test_control_tokens.py. Brand tokens that need a
   defensive fallback (test_panel_css_contrast) use a nested var() fallback rather
   than a hex, so the rule is both fallback-safe AND literal-free. */
.nav-tab {
  display: inline-block;
  padding: var(--space-sm) var(--space-md);
  font-size: var(--text-lg);
  font-weight: var(--font-weight-medium);
  color: var(--color-muted);
  border-bottom: var(--border-width-accent) solid transparent;
  cursor: pointer;
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
  font-family: inherit;
  transition: color var(--duration-fast) var(--easing-standard),
              border-color var(--duration-fast) var(--easing-standard);
  white-space: nowrap;
}
.nav-tab:hover { color: var(--color-text); }
.nav-tab:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: -2px;
}
.nav-tab.active {
  color: var(--color-heading);
  font-weight: var(--font-weight-semibold);
  border-bottom-color: var(--color-accent, var(--color-accent-dark));
}

/* ── Main content ───────────────────────────────── */
.main {
  max-width: 1024px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
}

.section { display: none; }
.section.active { display: block; }

.section-header {
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}
.section-header h2 {
  font-size: 1.15rem;
  color: var(--color-heading);
  line-height: var(--line-height-tight);
  letter-spacing: -0.01em;
}
.section-header p {
  font-size: var(--text-base);
  color: var(--color-muted);
  margin-top: var(--space-2xs);
  line-height: var(--line-height-snug);
}

/* ── Title + trailing-meta header row (v0.1.59 / FR4) ────────────────────────
   A section header that pairs its <h2> title with a single trailing meta pill
   (the Projects tab's .projects-count-badge) lays out on ONE aligned row — title
   left, count right — instead of the pre-pass block flow that dropped the count
   badge onto a second line below the title. This is the same single-row pattern
   the W3/FR3 pass gave the Sessions .runtime-switcher header, applied here for a
   consistent header hierarchy across the six tabs. The badge is pushed to the
   trailing edge (margin-left:auto, in projects.py); a long title ellipsises
   before the badge shrinks. Token-anchored; no colour/type/radius literals.
   Scoped via :has(.projects-count-badge) so the plain title/description headers
   (Servers, Reports, Academy) keep their stacked title+description flow. */
.section-header:has(.projects-count-badge) {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: var(--space-md);
  min-width: 0;
}
.section-header:has(.projects-count-badge) > h2 {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Single-line header/control row (v0.1.59 / FR3) ──────────────────────────
   A header that pairs a title with a trailing control (the Sessions tab's
   <h2> + .runtime-switcher) lays out on ONE line by default. Before this pass the
   shared .section-header was display:block, so the switcher stacked onto a second
   line at every width — the operator's "rows breaking onto two or more lines"
   complaint. Scoped via :has(.runtime-switcher) so the plain title/description
   headers (Servers, Projects) are left untouched. min-width:0 + ellipsis let a
   long title shrink and truncate instead of forcing a wrap; the control never
   shrinks (flex-shrink:0). Responsive at 1024px (the --main cap) and 1440px.
   Token-anchored; no colour/type/radius literals. */
.section-header:has(.runtime-switcher) {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: var(--space-md);
  min-width: 0;
}
.section-header:has(.runtime-switcher) > h2 {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Servers section ─────────────────────────────── */
.refresh-notice {
  font-size: 0.8rem;
  color: var(--color-muted);
  text-align: right;
  margin-bottom: var(--space-sm);
}

#refresh-status {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-active-dot);
  margin-right: 4px;
  vertical-align: middle;
  transition: opacity 0.3s;
}
#refresh-status.updating { opacity: 0.3; }

.group-label {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-muted);
  margin: var(--space-lg) 0 var(--space-xs) 0;
}
.group-label:first-of-type { margin-top: 0; }

table.servers-table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  overflow: hidden;
  font-size: 0.92rem;
}
table.servers-table th,
table.servers-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: middle;
}
table.servers-table th {
  background: var(--color-th-bg);
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
}
table.servers-table tr:last-child td { border-bottom: none; }
table.servers-table tbody tr:hover { background: var(--color-row-hover); }

.status-active { color: var(--color-active-dot); font-weight: 600; }
.status-stale  { color: var(--color-stale-dot); }

.port-badge {
  font-family: var(--font-mono);
  font-size: 0.88em;
  background: var(--color-code-bg);
  padding: 0.15em 0.4em;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
}

.empty-state {
  padding: var(--space-xl);
  text-align: center;
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-muted);
}
.empty-state code { display: inline-block; margin-top: var(--space-sm); font-size: 0.85em; }

/* ── Memory cards grid ───────────────────────────── */
/* (.context-count purged v0.1.59 / FR6 Cat-A — the live projects count uses
   .projects-count-badge, W4; grep-proven zero live refs in views/JS/tests.) */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-md);
}

.context-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  overflow: hidden;
  transition: box-shadow 0.15s;
}
.context-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
/* (.context-card.primary purged v0.1.59 / FR6 Cat-A — index.py renders only
   class="context-card" (index.py:226); the .primary modifier is never emitted.
   .context-card + :hover STAY live.) */

/* (.card-header + .card-primary-badge purged v0.1.59 / FR6 Cat-A — the OLD card
   anatomy; grep-proven zero live refs (the only card-header token in served HTML is
   the distinct .dadaia-wf-card-header in workflows.py; card-primary-badge appears only
   in a test_views_index `not in` absence guard). .card-name STAYS live — asserted by
   test_index_dom_contract + rendered by _render_context_card. */
.card-name { font-size: 0.97rem; font-weight: 700; color: var(--color-heading); flex: 1; }
.card-meta {
  padding: 0 var(--space-md) var(--space-sm);
  font-size: 0.83rem;
  color: var(--color-muted);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

/* (.card-links + .memory-link* purged v0.1.59 / FR6 Cat-A — the OLD memory-link card
   anatomy; grep-proven zero live refs in views/JS/tests. The live card memory pills use
   .memory-chip (projects.py). The now-dangling .memory-link:focus-visible selector was
   also dropped from the Warm-theme focus-visible override below. */

/* ── panel-section base ──────────────────────────── */
.panel-section { display: none; }
.panel-section.active { display: block; }

/* ── Responsive tab labels (<768px) ─────────────────────────────────────────
   On narrow viewports the "Spec Context Projects" label is abbreviated to
   "Spec Contexts" via CSS ::after replacement. The visible text is hidden with
   font-size:0 and the short label is injected via ::after content so that the
   aria-label on the button keeps the full string "Spec Context Projects" for
   screen readers (PR3-06).
   ─────────────────────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .topbar { padding-inline: var(--space-sm); gap: var(--space-xs); }
  .topbar-divider, .topbar-subtitle, .theme-btn-label, .theme-btn-caret { display: none; }
  .theme-btn { width: var(--control-height); justify-content: center; padding: 0; }
  .tab-memories-btn {
    font-size: 0;
  }
}

/* ── Theme switcher — swatch popover (T-016-P08 visual redesign) ─────────────
   Operator design: compact icon-button in topbar (top-right) that opens a clean
   popover showing 3 themes as labelled colour-dot rows. Active theme is
   highlighted. Polished spacing, subtle shadow, hover/active states.
   IDs and data-theme-value attributes are unchanged (e2e selectors preserved).
   ─────────────────────────────────────────────────────────────────────────── */

/* Button — compact icon-pill in topbar (token-anchored, one button language) */
.theme-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--control-gap);
  padding: var(--control-pad-y) var(--control-pad-x);
  background: transparent;
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-pill);   /* pill shape — compact and tidy */
  color: var(--color-muted);
  font-family: var(--font-stack);
  font-size: var(--text-md);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background var(--duration-fast) var(--easing-standard),
              border-color var(--duration-fast) var(--easing-standard),
              color var(--duration-fast) var(--easing-standard);
  white-space: nowrap;
  line-height: var(--line-height-snug);
}
.theme-btn:hover {
  background: var(--color-primary-bg, var(--color-surface));
  border-color: var(--color-accent, var(--color-accent-dark));
  color: var(--color-text);
}
.theme-btn:active {
  background: var(--color-accent, var(--color-accent-dark));
  border-color: var(--color-accent, var(--color-accent-dark));
  color: var(--color-heading);
}
.theme-btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-accent-dark);
  outline-offset: var(--focus-ring-offset);
}

/* Half-circle icon (◑) + caret */
.theme-btn-icon {
  font-size: 1em;
  line-height: 1;
  color: var(--color-accent-dark, #2d7d9a);
}
.theme-btn-label {
  font-size: var(--text-md);
  color: inherit;
}
.theme-btn-caret {
  font-size: 0.6em;
  line-height: 1;
  opacity: 0.7;
  transition: transform 0.15s var(--easing-standard, cubic-bezier(0.4,0,0.2,1));
}
/* Rotate caret when open */
.theme-btn[aria-expanded="true"] .theme-btn-caret {
  transform: rotate(180deg);
}

/* Popover panel — token-anchored spacing / radius / elevation (v0.1.59 / FR5 polish).
   The former ad-hoc literals (6px offset, 0.3rem padding, 1px border, --radius-card,
   a hardcoded two-layer box-shadow) are replaced by the design tokens so the popover
   shares the card-elevation language (softer --radius-lg + the lifted --shadow-card-hover
   the W4 cards use). min-width stays a bare layout constraint (no width token exists).
   The [role="menuitemradio"] rows are NOT in the test_control_tokens allowlist, so this
   polish is free to tokenize them without perturbing the FR2 grep gate. */
#theme-menu {
  position: absolute;
  top: calc(100% + var(--space-2xs));
  right: 0;
  z-index: 200;
  list-style: none;
  margin: 0;
  padding: var(--space-2xs) 0;
  background: var(--color-surface, #ffffff);
  border: var(--border-width) solid var(--color-border, #dddddd);
  border-radius: var(--radius-lg, 10px);
  box-shadow: var(--shadow-card-hover);
  min-width: 130px;
  animation: theme-popover-in var(--duration-fast, 120ms) var(--easing-decelerate, cubic-bezier(0,0,0.2,1));
}
@keyframes theme-popover-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  #theme-menu { animation: none; }
}
/* The [hidden] attribute hides the menu; JS toggles it. */
#theme-menu[hidden] { display: none; }

/* Row: colour dot + label — tokenized spacing rhythm + comfortable click target */
#theme-menu [role="menuitemradio"] {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  font-size: var(--text-base);
  color: var(--color-text, #222222);
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--easing-standard);
  border-radius: 0;
}
#theme-menu [role="menuitemradio"]:first-child { border-radius: var(--radius-card, 6px) var(--radius-card, 6px) 0 0; }
#theme-menu [role="menuitemradio"]:last-child  { border-radius: 0 0 var(--radius-card, 6px) var(--radius-card, 6px); }
#theme-menu [role="menuitemradio"]:only-child  { border-radius: var(--radius-card, 6px); }
#theme-menu [role="menuitemradio"]:hover {
  background: var(--color-primary-bg, #f0fbf7);
}
#theme-menu [role="menuitemradio"]:focus-visible {
  outline: 2px solid var(--color-accent-dark, #2d7d9a);
  outline-offset: -2px;
  border-radius: var(--radius, 4px);
}

/* Active row: subtle highlight — tokenized weight, brand-bg fallback preserved */
#theme-menu [role="menuitemradio"][aria-checked="true"] {
  background: var(--color-primary-bg, #f0fbf7);
  font-weight: var(--font-weight-semibold);
  color: var(--color-heading, #111111);
}

/* Colour dot swatch — filled circle in the theme's accent colour */
.theme-swatch-dot {
  flex-shrink: 0;
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1.5px solid rgba(0,0,0,.15);
}
.theme-swatch-dot--mint { background: #9cddc8; }
.theme-swatch-dot--sage { background: #bfd8ad; }
.theme-swatch-dot--warm { background: #f7af63; }

/* Theme label — wraps just the text so textContent returns the theme name cleanly */
.theme-label {
  flex: 1;
  min-width: 0;
}

/* Check mark: CSS ::after on the active row — no DOM node needed */
#theme-menu [role="menuitemradio"]::after {
  content: "";
  display: inline-block;
  width: 0.9em;
  flex-shrink: 0;
}
#theme-menu [role="menuitemradio"][aria-checked="true"]::after {
  content: "✓";
  color: var(--color-accent-dark, #2d7d9a);
  font-size: 0.82em;
  line-height: 1;
}

/* ── Runtime switcher — segmented control (PR5-D4; relocated from tokens.py in
   v0.1.59 / FR2 so the component rules live in a served control-surface stylesheet,
   not the token-definition file). The --color-runtime-* tokens and per-theme
   [data-runtime] overrides remain defined in tokens.py. Token-anchored to the one
   button language (--control-*, --focus-ring-*, --text-*) — no ad-hoc literals. */
.runtime-switcher {
  display: flex;
  align-items: center;
  gap: var(--space-2xs);
  background: var(--color-surface);
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--space-2xs);
  /* De-inlined from views/sessions.py (v0.1.59 / FR3): the switcher is pushed to
     the trailing edge of its flex .section-header and never shrinks, so the title
     ellipsises before the control does. */
  margin-left: auto;
  flex-shrink: 0;
}

.runtime-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--control-gap);
  padding: var(--control-pad-y) var(--control-pad-x);
  border: var(--border-width) solid transparent;
  border-radius: var(--control-radius);
  background: transparent;
  color: var(--color-muted);
  font-family: var(--font-stack);
  font-size: var(--text-md);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background var(--duration-fast) var(--easing-standard),
              color var(--duration-fast) var(--easing-standard),
              border-color var(--duration-fast) var(--easing-standard);
  white-space: nowrap;
}

.runtime-btn[aria-checked="true"] {
  background: var(--color-runtime-active);
  color: var(--color-surface);
  border-color: transparent;
}

.runtime-btn[aria-checked="false"]:hover {
  background: var(--color-row-hover);
  color: var(--color-text);
}

.runtime-btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--color-runtime-active);
  outline-offset: var(--focus-ring-offset);
}

.runtime-btn-icon {
  font-size: 0.75em;
  line-height: 1;
}

/* ── Ops consolidated tab — stacked sub-sections ─────────────────────────────
   T-016-P09: Agents + Workflows merged into one "Ops" nav tab.
   Each sub-section is stacked vertically inside #section-ops with a labelled
   header and compact cards.
   ─────────────────────────────────────────────────────────────────────────── */
.ops-subsection {
  margin-bottom: var(--space-xl, 2rem);
  padding-bottom: var(--space-lg, 1.25rem);
  border-bottom: 1px solid var(--color-border, #dddddd);
}
.ops-subsection:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.ops-subsection-header {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: var(--space-md, 1rem);
  padding-bottom: var(--space-xs, 0.35rem);
  border-bottom: 1px solid var(--color-border, #dddddd);
}
.ops-subsection-title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-heading, #111111);
  margin: 0;
  white-space: nowrap;
}

/* (.agents-grid--compact + .workflows-grid--compact purged v0.1.59 / FR6 Cat-A —
   the compact ops grids for the removed Agentic/Ops agents+workflows grids;
   grep-proven zero live refs in views/JS/tests. The surviving .ops-subsection*
   header rules above STAY live — rendered by workflows.py:202-204. */

/* ── Warm theme focus-visible override (E2E-THM-07) ─────────────────────────
   Amber alone fails the WCAG 3:1 UI-component contrast threshold on white.
   In the Warm theme the focus ring uses --color-accent-dark (brown) as the
   primary outline so the focus indicator meets WCAG AA. A secondary amber
   outline is added as a visual accent that does not carry the contrast burden.
   See tokens.py for the amber hex value definition.
   ─────────────────────────────────────────────────────────────────────────── */
html[data-theme="warm"] a:focus-visible,
html[data-theme="warm"] .nav-tab:focus-visible,
html[data-theme="warm"] button:focus-visible,
html[data-theme="warm"] [role="button"]:focus-visible,
html[data-theme="warm"] [role="menuitem"]:focus-visible,
html[data-theme="warm"] [role="menuitemradio"]:focus-visible {
  outline: 2px solid var(--color-accent-dark, #633d2e),
           1px solid var(--color-accent, #f7af63);
  outline-offset: 2px;
}

/* ── Overflow safety (v0.1.45 / T-45-07) ─────────────────────────────────
   The content column is capped at 1024px and centred, so at 1440px the panel
   never scrolls horizontally. These defensive rules ensure that at 1024px a
   long unbroken token inside a flex/grid child ellipsises (min-width:0 lets a
   child shrink below its content) instead of forcing a horizontal scrollbar —
   the "rows wrap / bad layout" the operator flagged. Token-anchored; no colour,
   type, or radius literals. */
.main { overflow-x: hidden; }
.section,
.panel-section,
.ops-subsection { min-width: 0; }
"""
