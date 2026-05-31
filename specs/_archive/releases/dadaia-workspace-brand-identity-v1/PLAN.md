# Plan: Release — dadaia-workspace-brand-identity-v1

> **Status:** Aprovado
> **Approved:** 2026-05-17
> **Approved-by:** operator
> **Release ID:** dadaia-workspace-brand-identity-v1
> **Phase:** PLAN
> **Owner:** product-engineer (curator) / frontend-engineer (executor on Aprovado)
> **Created:** 2026-05-17
> **Plan version:** 1
> **SPEC:** `specs/releases/dadaia-workspace-brand-identity-v1/SPEC.md` (Status: Aprovado)

---

## Resumo

- **O que:** três artefatos atômicos — paleta canônica, tokens CSS no PANEL_CSS, logo SVG rinoceronte (24×24 + 16×16).
- **Onde:** todo o código vive em `dadaia_workspace/features/panel/views/` (PANEL_CSS em `_assets.py` + novo subdir `assets/` para SVG).
- **Não toca:** lógica de produto, endpoints, schema, services, telemetry, infra, CI.
- **Zero deps novas.** SVG é XML puro; CSS é string Python como hoje.
- **Tamanho:** ~80 LoC modificadas em `_assets.py`, ~30 LoC de SVG (string inline), ~120 LoC de testes (paleta, contraste, SVG validation).

---

## Fases

```
┌──────────────────────────────────────────────────────────────────┐
│  Phase 1 — Paleta canônica + tokens CSS                          │
│    _assets.py: PALETTE = {...} constante; PANEL_CSS atualizado   │
│  Phase 2 — Logo SVG (24 + 16)                                    │
│    views/assets/logo-rhino-24.svg + logo-rhino-16.svg            │
│    PANEL_HTML inline insertion no topbar                         │
│  Phase 3 — Wordmark + tests                                      │
│    .topbar-wordmark color = --color-cost                         │
│    test_palette_contrast.py + test_svg_validity.py               │
└──────────────────────────────────────────────────────────────────┘
```

### Phase 1 — Paleta e tokens (gating)

**Files touched:**
- `dadaia_workspace/features/panel/views/_assets.py` (PANEL_CSS): adiciona 3 tokens novos (`--color-cost`, `--color-warning-bg`, `--color-alert`, `--color-accent-secondary`), atualiza 3 tokens (`--color-accent`, `--color-primary-ring`, `--color-primary-bg`).
- Nova constante module-level `PALETTE: dict[str, str]` — fonte única de verdade da paleta canônica.

**Por que primeiro:** sem tokens definidos, nada mais consome valores. Mudança é puramente aditiva nos 3 novos; nos 3 atualizados, valor antigo segue em comentário ao lado da nova entrada (rastro de migração).

### Phase 2 — Logo SVG

**Files touched:**
- Novo dir: `dadaia_workspace/features/panel/views/assets/`.
- Novos: `logo-rhino-24.svg`, `logo-rhino-16.svg`.
- `_assets.py`: novas constantes `LOGO_RHINO_24` e `LOGO_RHINO_16` carregadas via `pathlib.Path.read_text()` em module init (uma vez por processo).
- `views/index.py`: inserir `LOGO_RHINO_24` antes do `.topbar-wordmark` no topbar HTML.

**Por que paralelo a Phase 1:** SVG é arquivo isolado; pode ser desenhado/aprovado pelo operador antes mesmo de Phase 1 começar. Mas o **load** no PANEL_HTML depende do PANEL_CSS já ter `--color-cost` definido (para o wordmark contrastar). Marcado aqui como após Phase 1.

### Phase 3 — Wordmark + tests + consumer audit

**Files touched:**
- `_assets.py` PANEL_CSS: `.topbar-wordmark { color: var(--color-cost); ... }`.
- `tests/unit/features/panel/test_palette.py` (novo): asserta que `PALETTE` é a única fonte; nenhum hex de paleta hardcoded em outras strings; relacionamentos token↔valor estão corretos.
- `tests/unit/features/panel/test_contrast.py` (novo): para cada par "texto / fundo" listado no SPEC § Critério de aceite #3, calcular ratio WCAG e asserta ≥ 4.5:1 (texto normal) ou ≥ 3:1 (texto grande / non-text).
- `tests/unit/features/panel/test_svg_validity.py` (novo): parse de `LOGO_RHINO_24` e `LOGO_RHINO_16` via `xml.etree.ElementTree`; asserta zero atributos `fill` ou `stroke` com hex (todos `currentColor`).

---

## Consumer compatibility com `agent-monitoring-v1`

| Cenário | Comportamento |
|---------|---------------|
| Esta release Aprovada **antes** de `agent-monitoring-v1` | `agent-monitoring-v1` consome tokens novos diretamente; T-AM-19 vira no-op |
| `agent-monitoring-v1` Aprovada **antes** desta | `agent-monitoring-v1` ship com fallback aos valores atuais; quando esta release pousar, tokens migram silenciosamente (componentes referenciam `var(--color-*)`, não hex direto) |
| Releases pousam no mesmo dia | Sem conflito de merge — esta toca `_assets.py` PANEL_CSS e `views/index.py` topbar; `agent-monitoring-v1` toca PANEL_CSS em zona separada (estilos das novas abas) e `views/index.py` nas tabs (não no topbar) |

**Coordenação de merge:** se ambas estiverem em flight, ordem recomendada é **esta primeiro** (menor blast radius, sem deps), depois `agent-monitoring-v1`.

---

## Plano de testes

| Tipo | Cobertura | Onde |
|------|-----------|------|
| Unit | PALETTE é única; nenhum hex duplicado em PANEL_CSS | `test_palette.py` |
| Unit | WCAG AA em pares texto/fundo listados | `test_contrast.py` |
| Unit | SVG parses; zero hex; `currentColor` em todos os fill/stroke | `test_svg_validity.py` |
| Smoke | PANEL_HTML rendered contém o SVG inline e o wordmark | `test_views_index.py` (atualizar) |
| Manual | Visual review pelo operador antes de Aprovado | screenshot do panel local |

Cobertura ≥ 80% nos arquivos novos (constitution).

---

## Riscos

| # | Risco | Mitigação |
|---|-------|-----------|
| RB1 | `#9cddc8` (accent) usado como cor de texto em algum lugar futuro | `test_contrast.py` falha CI ao detectar |
| RB2 | SVG malformado quebra parse no browser | `test_svg_validity.py` valida XML antes do load |
| RB3 | Atualização de `--color-primary-bg` para `#f0fbf7` muda aparência de Memories sem revisão | Snapshot test do Memories card (visual diff manual via panel local) antes do merge |
| RB4 | Drift entre paleta no repo e assets externos (slides, docs) | Documentar paleta canônica em `specs/memory/product.html` como fonte de verdade |

---

## Rollback

- Cada phase = 1 commit. Reverter qualquer phase é seguro:
  - Phase 1: tokens voltam aos valores anteriores; consumidores continuam funcionando.
  - Phase 2: remove SVG do topbar; panel volta a mostrar só o wordmark.
  - Phase 3: testes saem; comportamento de runtime inalterado.

---

## Definition of Done

- 3 phases concluídas.
- Todos os testes passam.
- `dadaia doctor` passa.
- Operador validou visualmente o panel local com o novo branding.
- `SPEC.md` transição `Em revisão → Aprovado` pelo operador.
