---
slug: brand-identity
title: brand-identity
category: product
tldr: canonical 5-color palette and CSS tokens of the panel (release dadaia-workspace-brand-identity-v1).
summary: canonical 5-color palette and CSS tokens of the panel (release dadaia-workspace-brand-identity-v1).
tags:
- brand
- design
- css
- tokens
token_estimate: 375
last_updated: '2026-07-07'
release_origin: v0.1.61
---

## Purpose

Defines the canonical palette and CSS tokens of the dadaia-workspace panel, guaranteeing visual consistency across tabs and themes. The tokens' home is `dadaia_workspace/features/panel/views/assets/css/tokens.py` (spacing, radius, shadows, z-index, motion, dimensions and colors), consumed by the `[data-theme="mint|sage|warm"]` selectors. (The old `views/_assets.py` module was removed entirely, together with its `PALETTE`/`PANEL_CSS` constants — `tokens.py` is the sole token home.)

## Brand identity

Canonical palette and CSS tokens of dadaia-workspace. The values live in `tokens.py` (home above); the panel's three palettes ([[panel]]) extend the base tokens via `[data-theme]`.

### Canonical palette (5 colors)

Name | Hex | Semantic role
---|---|---
accent | `#9cddc8` | Active tab, highlight border, decorative badges with dark text. Never as a text color (~2.1:1 ratio over white fails WCAG AA).
accent_secondary | `#bfd8ad` | Background of positive-state badges ("ativo hoje"), background of expanded rows.
warning_bg | `#ddd9ab` | Background of the stale-price warning banner. Overlaid text: `#3d3600`.
alert | `#f7af63` | Inline alert icon/border. Never as a text color (insufficient ratio over white).
cost | `#633d2e` | Monetary values (e.g. `$1.84`), topbar wordmark. ~8:1 ratio over white (WCAG AAA).

### CSS token → palette mapping

CSS token | Palette name | Hex
---|---|---
`--color-accent` | accent | `#9cddc8`
`--color-primary-ring` | accent | `#9cddc8`
`--color-primary-bg` | — (derived from accent) | `#f0fbf7`
`--color-accent-secondary` | accent_secondary | `#bfd8ad`
`--color-warning-bg` | warning_bg | `#ddd9ab`
`--color-alert` | alert | `#f7af63`
`--color-cost` (incl. topbar wordmark) | cost | `#633d2e`
