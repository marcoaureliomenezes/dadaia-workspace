---
slug: brand-identity
title: brand-identity
category: product
tldr: The panel's canonical five-colour palette and its CSS token mapping, sourced only from `views/assets/css/tokens.py`.
summary: The canonical five-colour palette and CSS tokens of the panel, homed in `features/panel/views/assets/css/tokens.py` and extended per theme by `[data-theme]` selectors.
tags:
- brand
- design
- css
- tokens
---

## Tokens

`dadaia_workspace/features/panel/views/assets/css/tokens.py` is the one home for spacing, radius,
shadows, z-index, motion, dimensions and colours. The three themes
(`[data-theme="mint|sage|warm"]`) extend those base tokens; no second token module exists
([[panel]]).

| Name | Hex | CSS token | Role |
|---|---|---|---|
| accent | `#9cddc8` | `--color-accent`, `--color-primary-ring` | active tab, highlight border, decorative badges with dark text — never a text colour (~2.1:1 on white fails WCAG AA) |
| — | `#f0fbf7` | `--color-primary-bg` | derived from accent |
| accent_secondary | `#bfd8ad` | `--color-accent-secondary` | positive-state badge background, expanded-row background |
| warning_bg | `#ddd9ab` | `--color-warning-bg` | stale-price warning banner; overlaid text `#3d3600` |
| alert | `#f7af63` | `--color-alert` | inline alert icon/border — never a text colour |
| cost | `#633d2e` | `--color-cost` | monetary values and the topbar wordmark (~8:1 on white, WCAG AAA) |
