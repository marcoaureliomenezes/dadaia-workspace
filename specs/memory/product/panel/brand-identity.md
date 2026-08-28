---
slug: brand-identity
title: brand-identity
category: product
tldr: The panel's canonical five-colour palette and its CSS token mapping, sourced only from `views/assets/css/tokens.py`.
summary: The panel's canonical palette and CSS tokens, homed in one module and extended per theme.
tags: [brand, design, css, tokens]
---

## Tokens

- `features/panel/views/assets/css/tokens.py` is the one home for spacing, radius, shadow, z-index, motion, dimension and colour tokens ([[panel]]).
- The three themes `[data-theme="mint|sage|warm"]` extend those base tokens; `--color-primary-bg` (`#f0fbf7`) derives from accent.

| Name | Hex | CSS token | Role |
|---|---|---|---|
| accent | `#9cddc8` | `--color-accent`, `--color-primary-ring` | active tab, border, dark-text badge — never text |
| accent_secondary | `#bfd8ad` | `--color-accent-secondary` | positive-state badge, expanded row |
| warning_bg | `#ddd9ab` | `--color-warning-bg` | warning banner; overlaid text `#3d3600` |
| alert | `#f7af63` | `--color-alert` | alert icon/border — never text |
| cost | `#633d2e` | `--color-cost` | monetary values and the topbar wordmark |
