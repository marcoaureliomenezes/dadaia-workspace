# Spec: Release — dadaia-workspace-brand-identity-v1

> **Status:** Aprovado
> **Approved:** 2026-05-17
> **Approved-by:** operator
> **Release ID:** dadaia-workspace-brand-identity-v1
> **Phase:** SPEC
> **Owner:** product-engineer (curator) / frontend-engineer (co-author on Aprovado)
> **Created:** 2026-05-17
> **Source candidate:** `specs/backlog/candidates.md` § Histórico (promovido a partir de entrada não-estruturada em `backlog/backlog-future.md`)
> **Discovery inputs:**
> - PE Discovery (parallel project): `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-17T052532Z-agent-monitoring-discovery.html`
> - Frontend design report (consumer-side): `.dadaia/reports/dadaia-workspace/frontend-engineer/2026-05-17T053015Z-agent-monitoring-design.html` § 6 (token mapping) + § 7 (logo specs)
> - PE Reconciliation: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-17T053947Z-agent-monitoring-reconciliation.html`
> **Parallel release:** `agent-monitoring-v1` (consumer of brand tokens; ships independently with fallback to current values)

---

## Visão

Identidade visual nova do dadaia-workspace, materializada em três artefatos
desacoplados e atômicos:

1. **Paleta canônica** — 5 cores em hex, com mapeamento explícito de tokens CSS para uso semântico.
2. **Tokens CSS no panel** — `--color-accent`, `--color-cost`, `--color-warning-bg`, `--color-alert`, `--color-accent-secondary`, atualizados em `dadaia_workspace/features/panel/views/_assets.py` (PANEL_CSS).
3. **Logo rinoceronte** — SVG inline monocromático, 24×24 (e variante 16×16), `currentColor`, usado no topbar e como decoração de cards de agente/workflow.

A release é puramente de identidade visual: não toca em lógica de produto, não cria novos endpoints, não consome dados. Tudo que ela produz é consumido pela `agent-monitoring-v1` (que tem fallback para tokens atuais se essa release ainda não pousou) e pelo panel existente.

---

## Escopo

### In-scope

- Paleta canônica `#9cddc8 #bfd8ad #ddd9ab #f7af63 #633d2e`.
- Mapeamento explícito de cada cor para tokens CSS, com uso semântico documentado.
- Atualização de PANEL_CSS em `dadaia_workspace/features/panel/views/_assets.py` com os 5 tokens (3 novos + 2 atualizados).
- SVG `dadaia_workspace/features/panel/views/assets/logo-rhino-24.svg` (e variante 16).
- Wordmark "dadaia" no topbar — atualização tipográfica leve (cor + spacing) sem mudar a fonte.
- Tests de contraste WCAG AA para combinações texto-sobre-token usadas no panel.

### Out of scope

- Dark mode (apenas light theme nesta release).
- Favicon (`/favicon.ico`).
- Animações ou transições novas.
- Atualizações de logos em outras superfícies (CLI, docs externos, README).
- Mudanças tipográficas além do wordmark (mesma font stack atual).
- Paletas alternativas para acessibilidade (high-contrast mode) — fica para release sucessora.
- Componentes UI novos (botões, formulários custom, etc.) — release não introduz primitives.

---

## Paleta canônica

| Hex | Swatch | Uso semântico (no panel) |
|-----|--------|--------------------------|
| `#9cddc8` | accent (mint) | Aba ativa, border de destaque, badges decorativos com texto escuro. **Nunca como cor de texto** (ratio ~2.1:1 sobre branco falha AA). |
| `#bfd8ad` | accent-secondary (sage) | Fundo de badges de estado positivo ("ativo hoje"), fundo de linhas expandidas. |
| `#ddd9ab` | warning-bg (sand) | Fundo do banner de aviso de preço desatualizado. Texto sobreposto: `#3d3600`. |
| `#f7af63` | alert (amber) | Ícone/border de alerta inline. **Nunca como cor de texto** — ratio insuficiente sobre branco. |
| `#633d2e` | cost (rich brown) | Valores monetários (`$1.84`), ratio ~8:1 sobre branco (AAA). |

---

## Mapeamento de tokens CSS (do frontend report § 6, reconciliado)

| Token CSS | Valor atual | Novo valor | Uso |
|-----------|-------------|------------|-----|
| `--color-accent` | `#7ec8e3` | `#9cddc8` | Underline de aba ativa, borders, badges decorativos |
| `--color-accent-secondary` | (não existe) | `#bfd8ad` | Fundo verde claro de badges de estado |
| `--color-warning-bg` | (não existe) | `#ddd9ab` | Banner de aviso de preço defasado |
| `--color-alert` | (não existe) | `#f7af63` | Ícone/border de alerta inline |
| `--color-cost` | (não existe) | `#633d2e` | Valores monetários USD |
| `--color-primary-ring` | `#7ec8e3` | `#9cddc8` | Border-left do card primary (acompanha `--color-accent`) |
| `--color-primary-bg` | `#f0faff` | `#f0fbf7` | Fundo do card primary (derivado de `#9cddc8` com 95% lum.) |

**Tokens mantidos sem alteração** (auditados como compatíveis): `--color-bg`, `--color-surface`, `--color-text`, `--color-heading`, `--color-muted`, `--color-border`, `--color-border-strong`, `--color-code-bg`, `--color-th-bg`, `--color-active-dot`, `--color-stale-dot`, `--color-row-hover`, `--color-card-hover`, `--color-placeholder-bg`, `--color-accent-dark`.

---

## Logo rinoceronte (do frontend report § 7)

| Atributo | Especificação |
|----------|---------------|
| Dimensões intrínsecas | 24×24 px. Variante secundária 16×16 (mesma silhueta, paths simplificados). |
| viewBox | `0 0 24 24` (e `0 0 16 16` na variante). |
| Modo de cor | Monocromático puro. `fill="currentColor"` e `stroke="currentColor"` em todos os elementos. Zero hex hardcoded no SVG. |
| Estilo | Minimalista. Silhueta plana de cabeça de rinoceronte de perfil, olhando para a direita. Chifre único proeminente. Sem sombreamento, sem gradientes, sem texturas. |
| Elementos | 1 ou 2 paths. Path principal: contorno preenchido (`fill="currentColor"`). Path opcional: olho como círculo (negativo via `fill="transparent"` ou cor de bg via variável). Total ≤ 3 elementos. |
| Uso no topbar | Inserido antes de `.topbar-wordmark`. Classe `topbar-logo`. 24×24 fixo. `aria-hidden="true"` (decorativo — wordmark adjacente é o label textual). |
| Uso em cards | Mesmo SVG ou variante 16×16. Como ícone funcional: `role="img"` + `aria-label="dadaia workspace"` + `<title>` interno. |

**Arquivos físicos:**
- `dadaia_workspace/features/panel/views/assets/logo-rhino-24.svg`
- `dadaia_workspace/features/panel/views/assets/logo-rhino-16.svg`

Servidos como string inline em PANEL_HTML (não via `<img src>`) para evitar segundo roundtrip HTTP.

---

## Critério de aceite

1. **Paleta canônica** declarada como constante única em `_assets.py` (não duplicada).
2. **5 tokens CSS** (3 novos + 2 atualizados) presentes em PANEL_CSS com comentários referenciando esta SPEC.
3. **WCAG AA validado** em todas as combinações texto-sobre-cor usadas no panel:
   - texto `#222` sobre `#9cddc8` (badges com fundo accent) → ratio ≥ 4.5:1.
   - texto `#3d3600` sobre `#ddd9ab` (banner warning) → ratio ≥ 4.5:1.
   - texto `#633d2e` (cost) sobre `#ffffff` → ratio ≥ 7:1 (AAA target).
   - texto `#222` sobre `#bfd8ad` → ratio ≥ 4.5:1.
   - `#9cddc8` e `#f7af63` **não** usados como cor de texto sobre branco em nenhum lugar.
4. **Logo SVG 24×24** presente em `views/assets/`, com `currentColor` puro e ≤ 3 elementos.
5. **Variante 16×16** presente.
6. **Topbar** renderiza logo + wordmark com cor `--color-cost` para o wordmark (alto contraste).
7. **Suite de testes** assertando: paleta canônica é única, contrastes mínimos, SVG não tem hex hardcoded.
8. `dadaia doctor` passa.
9. Operador transiciona `Status: Em revisão → Aprovado`.

---

## Como `agent-monitoring-v1` consome esta release

- Os tokens CSS são lidos diretamente do PANEL_CSS atualizado.
- Se esta release **ainda não foi Aprovada** no momento da implementação de `agent-monitoring-v1`:
  - `agent-monitoring-v1` ship com fallback aos valores **atuais** (e.g. `--color-accent: #7ec8e3`).
  - Quando esta release pousar, agent-monitoring herda automaticamente os novos valores (todos os tokens são referência semântica, não hex direto nos componentes).
  - Não há quebra contratual em qualquer ordem de aprovação.

---

## Threat model / risco

- **Acessibilidade:** uso indevido de `#9cddc8` ou `#f7af63` como cor de texto sobre branco viola AA. Mitigação: lint via teste automatizado (`#9cddc8` proibido em qualquer `color:` rule dentro de PANEL_CSS, exceto badge backgrounds).
- **SVG inline com path malformado** pode causar parse error no navegador. Mitigação: validar SVG via parser stdlib (`xml.etree.ElementTree`) no teste antes de incluir em PANEL_HTML.
- **Drift de paleta com brand assets externos** (presentations, docs) fora deste repo: documentar a paleta em `specs/memory/product.html` (atomic memory edit) como fonte de verdade.
