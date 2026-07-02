---
slug: brand-identity
title: brand-identity
category: product
tldr: paleta canônica de 5 cores e tokens CSS do panel (release dadaia-workspace-brand-identity-v1).
summary: paleta canônica de 5 cores e tokens CSS do panel (release dadaia-workspace-brand-identity-v1).
tags:
- brand
- design
- css
- tokens
agent_tier: self-pull
token_estimate: 350
last_updated: '2026-07-01'
release_origin: v0.1.47
---

## Propósito

Define a paleta canônica e os tokens CSS do dadaia-workspace panel, garantindo consistência visual entre tabs e temas. O home dos tokens é `dadaia_workspace/features/panel/views/assets/css/tokens.py` (spacing, radius, shadows, z-index, motion, dimensions e colors), consumido pelos seletores `[data-theme="mint|sage|warm"]`. (`views/_assets.py` retém apenas constantes de path legadas — as antigas `PALETTE`/`PANEL_CSS` foram removidas.)

## Brand identity

Paleta canônica e tokens CSS do dadaia-workspace. Os valores vivem em `tokens.py` (home acima); as três paletas do panel ([[panel]]) estendem os tokens base via `[data-theme]`.

### Paleta canônica (5 cores)

Nome | Hex | Papel semântico
---|---|---
accent | `#9cddc8` | Aba ativa, border de destaque, badges decorativos com texto escuro. Nunca como cor de texto (ratio ~2.1:1 sobre branco falha WCAG AA).
accent_secondary | `#bfd8ad` | Fundo de badges de estado positivo ("ativo hoje"), fundo de linhas expandidas.
warning_bg | `#ddd9ab` | Fundo do banner de aviso de preço desatualizado. Texto sobreposto: `#3d3600`.
alert | `#f7af63` | Ícone/border de alerta inline. Nunca como cor de texto (ratio insuficiente sobre branco).
cost | `#633d2e` | Valores monetários (ex: `$1.84`), wordmark do topbar. Ratio ~8:1 sobre branco (WCAG AAA).

### Mapeamento token CSS → PALETTE

Token CSS | PALETTE key | Hex | Valor anterior
---|---|---|---
`--color-accent` | accent | `#9cddc8` | `#7ec8e3` (atualizado)
`--color-primary-ring` | accent | `#9cddc8` | `#7ec8e3` (atualizado)
`--color-primary-bg` | — | `#f0fbf7` | `#f0faff` (atualizado, derivado de accent)
`--color-accent-secondary` | accent_secondary | `#bfd8ad` | (novo)
`--color-warning-bg` | warning_bg | `#ddd9ab` | (novo)
`--color-alert` | alert | `#f7af63` | (novo)
`--color-cost` | cost | `#633d2e` | (novo)
`--color-cost` (wordmark) | cost | `#633d2e` | `--color-heading` (atualizado via T-BR-07)
