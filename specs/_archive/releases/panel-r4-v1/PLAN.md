# PLAN — Release `panel-r4-v1`

**Status:** Aprovado
**Release ID:** panel-r4-v1
**Owner:** product-engineer
**Created:** 2026-05-19
**Phase:** PLAN

---

## 1. Sumário

Este plano implementa o bug fix do reader Claude que deixa `sessions.agent_name` como
NULL para todos os 50 sessions existentes (causa raiz comprovada do "Sessions/Cost/Last
seen zerados" no painel), introduz um campo `tier` por agente derivado de frontmatter
para que o `/api/agents` exponha a topologia de orquestração, e reformula visualmente
os cards (`.agent-card`) com borda 2px + acento lateral 4px tonalizado por tier. O
trabalho é dividido em 6 fases ordenadas (P1..P6), com P1 e P2 explicitamente paralelas
(write sets disjuntos), P3 dependendo do `tier` field de P2 e da spec de design, e P6
fechando o release com memory + archive.

## 2. Arquitetura — superfícies afetadas

| Camada | Arquivo / módulo | Mudança |
|--------|------------------|---------|
| Telemetry reader | `dadaia_workspace/features/telemetry/reader/claude.py` | Extrai `agent_name` do evento jsonl e persiste em sessions |
| Telemetry store DAO | `dadaia_workspace/features/telemetry/store/dao.py` | Confirmar que aceita `agent_name`; se reader passar `None` hoje, bug é só no reader |
| Telemetry aggregator | `dadaia_workspace/features/telemetry/aggregator/queries.py` | Sem mudança — `list_agents()` já agrupa por `agent_name`; funciona após backfill |
| Panel API handler | `dadaia_workspace/features/panel/views/api.py` (linhas ~163-321) | Inclui `tier` por agente no payload `/api/agents` |
| Agent service / model | `dadaia_workspace/infrastructure/markdown_agent_store.py` (ou módulo equivalente) | Parsing do `tier:` frontmatter; surface no modelo |
| Agent frontmatter | `dadaia_workspace/public/agents/*.md` (16 arquivos) | Adiciona `tier: 1\|2\|3` em cada agente |
| Panel CSS | `dadaia_workspace/features/panel/views/assets/css/agents.py` (linhas ~39-72) | Border 2px default; selectors `data-tier`; tokens `--color-tier-1/2/3` × 3 palettes |
| Panel JS | `dadaia_workspace/features/panel/views/assets/js/agents.js` (~linhas 111-113) | Define `data-tier="${agent.tier}"` em cada card |
| Tests | `tests/unit/features/telemetry/reader/test_claude_reader.py`, `tests/unit/features/agents/test_reader.py`, `tests/unit/features/panel/test_api_agents.py`, `tests/integration/features/telemetry/...` | Unit + integration tests para FR1/FR2/FR3 |
| Memory atoms (CLOSURE) | `specs/memory/product/panel.html`, `specs/memory/architecture.html` | Documentação atomic do estado pós-release |

## 3. Fases (P0..P6)

**P0 — Foundation** *product-engineer.*
Deliverables: branch `release/panel-r4-v1` cut from `main`; SPEC.md + PLAN.md + TASKS.md
em `**Status:** Aprovado`; ACTIVE.md sincronizado em `release: panel-r4-v1, phase:
TASKS` ao fim de P0.
Acceptance: artefatos lidos por outra sessão sem ambiguidade; PR4-01..04 marcados `[x]`.
Deps: nenhuma.

**P1 — Reader fix (FR1)** *software-engineer.*
Deliverables: (a) script de descoberta `scripts/inspect_jsonl_agent_field.py` que
imprime o field path da persona despachada em um jsonl real; (b) patch em
`reader/claude.py` extraindo `agent_name`; (c) CLI/script de backfill idempotente que
re-popula as 50 linhas NULL; (d) execução do backfill contra
`~/.dadaia/state/telemetry/telemetry.sqlite`; (e) unit test com fixture jsonl sintética;
(f) integration test mostrando `/api/agents` com `session_count > 0` para ≥ 1 agente.
Acceptance: C1, C2, C3 todos verdes.
Deps: nenhuma — pode rodar em paralelo com P2.

**P2 — Tier field (FR2)** *software-engineer.*
Deliverables: (a) `tier:` frontmatter adicionado aos 16 markdowns em
`dadaia_workspace/public/agents/`; (b) parsing do `tier` no agent reader; (c) inclusão
de `tier` no payload `/api/agents`; (d) unit tests para reader e API.
Acceptance: C4, C5 verdes.
Deps: nenhuma — paralelo com P1.

**P3 — Card border (FR3)** *design-specialist → frontend-engineer.*
Deliverables: (a) screenshot baseline capturado por qa-engineer (Playwright via `dadaia
panel`); (b) design report de design-specialist com tokens Mint/Sage/Warm × tiers 1/2/3
(9 hex values), contraste WCAG AA verificado, ASCII sketches; (c) implementação por
frontend-engineer: borda 2px default + selectors `[data-tier]` + 3 tokens × 3 palettes
em `agents.py` CSS; wiring de `data-tier` em `agents.js`; (d) unit test verificando
`data-tier` no JS renderizado.
Acceptance: C6, C7, C8 verdes.
Deps: **P2 (tier field)** — sem `tier` no payload `/api/agents` o JS não consegue
emitir `data-tier`. Note: design-specialist → frontend-engineer é handoff explícito
mediado por design report; frontend-engineer NÃO implementa sem o design report mais
recente.

**P4 — Doctor checkpoint** *devops-engineer.*
Deliverables: `dadaia public stage && dadaia public install --target all && dadaia
public doctor` executado; output capturado; todos os entries `[ok]` exceto known
`[unsupported]`/`[partial]`/`[not-applicable]` documentados.
Acceptance: doctor output anexado ao report devops; sem `[drift]` ou `[fail]`.
Deps: P1, P2, P3 concluídos.

**P5 — Live panel smoke** *qa-engineer.*
Deliverables: `dadaia panel` iniciado; navegação ao Agents tab; screenshot evidenciando
(a) stats não-zero; (b) Last seen mostrando "Xm ago"; (c) borders 2px + acentos
tier-coded visíveis; report HTML com screenshot embedded.
Acceptance: C8 verde via screenshot evidência.
Deps: P4 concluído.

**P6 — CLOSURE** *product-engineer.*
Deliverables: (a) ACTIVE.md → `phase: CLOSURE`; (b) CLOSURE.md com Summary, Tasks
completed (lista com SHA por task), Validations (triplas C1..C10), Drifts, Memory
updates, Backlog returns, Archive: MOVE; (c) update de `specs/memory/product/panel.html`
e `specs/memory/architecture.html` (ou equivalentes markdown se HTML migration não
ainda); (d) `dadaia specs doctor` 0/0; (e) `git mv specs/releases/panel-r4-v1
specs/_archive/releases/panel-r4-v1`; (f) ACTIVE.md → `release: none, phase: none`.
Acceptance: C9, C10 verdes; todas tasks PR4-22..27 `[x]`.
Deps: P5 concluído.

## 4. Janelas paralelas

- **P1 e P2 são paralelas seguras.** Write sets disjuntos:
  - P1 escreve `dadaia_workspace/features/telemetry/reader/claude.py`, scripts de
    backfill, e tests em `tests/unit/features/telemetry/reader/`.
  - P2 escreve `dadaia_workspace/public/agents/*.md`, agent reader, `panel/views/api.py`,
    e tests em `tests/unit/features/agents/` e `tests/unit/features/panel/`.
  - Não há overlap; podem ocupar dois `[-]` simultâneos se a regra de paralelismo for
    declarada explicitamente em TASKS.md.
- **P3 depende de P2.** O JS de P3 emite `data-tier="${agent.tier}"`; sem o `tier`
  no payload do `/api/agents` o atributo seria `undefined`. P3 deve aguardar P2
  concluído (ou o tier estável pelo menos no payload).
- **P4, P5, P6 são estritamente sequenciais** após P1/P2/P3.

## 5. Tests — arquivos criados ou editados

- `tests/unit/features/telemetry/reader/test_claude_reader.py` — novo caso
  `test_agent_name_extracted_from_dispatched_subagent` com fixture sintética
  (possivelmente em `tests/unit/features/telemetry/reader/fixtures/`).
- `tests/integration/features/telemetry/test_api_agents_with_telemetry.py` (ou similar)
  — integration test plantando eventos jsonl seeded e verificando `session_count > 0`
  em `/api/agents`.
- `tests/unit/features/agents/test_reader.py` — extender para assertar `tier` parseado
  para todos os 16 agentes.
- `tests/unit/features/panel/test_api_agents.py` — extender para assertar `tier ∈
  {1, 2, 3}` em todo agente do payload; novo caso (ou novo arquivo
  `test_agents_render.py`) para verificar `data-tier` no JS renderizado.

## 6. Riscos

- **R1 — Brittleness do reader regex.** A extração de `agent_name` depende do schema
  jsonl do Claude Code. Se Claude mudar o nome do campo, o reader silenciosamente
  volta a popular NULL. **Mitigação:** PR4-05 começa com discovery script que pinpoint
  o field path; PR4-07 fixa o contrato em fixture de teste; CLOSURE documenta a versão
  observada do schema jsonl.
- **R2 — Round-trip de design-specialist → frontend-engineer.** Dois hops de agente vs.
  uma edição direta de CSS. **Mitigação:** escopo da spec é narrow (3 tokens × 3
  palettes + 1 mudança de border-weight), reduzindo a latência do hop.
- **R3 — Backfill atomicity.** Se a operação re-criar linhas em vez de atualizar,
  contagem dobra. **Mitigação:** PR4-08 mandata UPDATE-WHERE-session_id idempotente;
  PR4-09 verifica row count = 50 antes e após segundo run.

## 7. Architect ADR — decisão de NÃO comissionar

**Decisão:** este release NÃO requer ADR do `software-architect`.

**Justificativa:** o trabalho é trêmulo em superfície mas pequeno em essência — um bug
fix de extração de campo (reader), uma adição de campo em payload já estruturado
(`/api/agents`), e uma reescrita visual de uma regra CSS existente. Nenhuma decisão
arquitetural (camadas, dependências, contratos novos entre módulos) está em jogo:

- O reader já é o "source of truth" canônico para `agent_name`; estamos consertando-o,
  não escolhendo entre alternativas.
- O frontmatter `tier:` extende um padrão já estabelecido (agent markdowns são lidos
  por um agent reader pré-existente).
- A reescrita do `.agent-card` opera dentro do mesmo módulo CSS já presente.

Esta decisão é registrada explicitamente para satisfazer o contrato com `software-architect`
e evitar dispatch desnecessário. Se durante implementação um drift arquitetural
inesperado emergir (e.g., o reader precisar de uma nova abstração de "agent name
resolver"), o software-engineer pausa e escala via `project-manager` para abrir ADR
emergencial.
