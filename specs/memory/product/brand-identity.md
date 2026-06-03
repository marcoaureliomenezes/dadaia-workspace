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
token_estimate: 338
last_updated: '2026-06-01'
release_origin: memory-markdown-source-v1
---

## Propósito

Define a paleta canônica e os tokens CSS do dadaia-workspace panel, garantindo consistência visual entre tabs e modos. Declarada como constante `PALETTE` em `dadaia_workspace/features/panel/views/_assets.py` e consumida via tokens CSS em `PANEL_CSS`.

## Brand identity

Paleta canônica e tokens CSS do dadaia-workspace, definidos na release [dadaia-workspace-brand-identity-v1 SPEC](../../releases/dadaia-workspace-brand-identity-v1/SPEC.md). A paleta é declarada como constante `PALETTE` em `dadaia_workspace/features/panel/views/_assets.py` e consumida via tokens CSS em `PANEL_CSS`. 

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
