# Game Agents Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the monolithic `game-developer` agent into three specialists — `game-developer` (logic), `game-designer` (design/assets), `game-tester` (UE5 automation) — each with deep Unreal Engine 5 expertise, WebSearch with trusted source whitelists, and new game-exclusive workflows.

**Architecture:** All artifacts live in `dadaia_workspace/public/` and are projected to `.claude/`, `.agents/`, `.codex/`, `.opencode/` via `dadaia public install --target all`. The SDD gate requires each task in `specs/TASKS.md` to be marked `[-]` IN PROGRESS before editing any file, and `[x]` DONE after committing. Never two `[-]` simultaneously.

**Tech Stack:** Markdown + YAML frontmatter, dadaia CLI (`dadaia public stage`, `dadaia public install --target all`, `dadaia public doctor`)

---

## Pre-flight

Before starting any task, verify the active context:

```bash
dadaia context show --json
# Expected: name = "dadaia-workspace"
```

Verify no task is already IN PROGRESS:

```bash
grep "\[-\]" /home/marco/workspace/dadaia/repos/dadaia-workspace/specs/TASKS.md
# Expected: empty output
```

---

## Task 1: SDD Artifacts — SPEC.md

**Files:**
- Create: `specs/features/game-agents-split/SPEC.md`
- Modify: `specs/TASKS.md` (T146 → [x])

- [ ] **Step 1: Mark T146 IN PROGRESS**

```bash
# Edit specs/TASKS.md: change T146 from [ ] to [-]
# Then:
git add specs/TASKS.md
git commit -m "chore(tasks): start T146 — game-agents-split SPEC.md"
```

- [ ] **Step 2: Create the SPEC.md**

Create `specs/features/game-agents-split/SPEC.md` with this exact content:

```markdown
# SPEC: Game Agents Split

**Status:** Aprovado
**Version:** 1.0
**Context:** dadaia-workspace

## Problem

The monolithic `game-developer` agent covers game logic, map design, visual assets,
audio, and testing simultaneously. With `redacted-slug-v2` targeting Unreal Engine 5
(JSBSim + Cesium + Nanite + Lumen + photogrammetric pipeline), the agent is too shallow
in each domain to produce high-quality output.

## Solution

Split into three purpose-built agents, each a deep UE5 specialist with WebSearch
and trusted-source whitelists, integrated into game-exclusive workflows.

## Agents

| Agent | Model | Domain |
|---|---|---|
| `game-developer` | claude-sonnet-4-6 | Game logic: AI, physics, ballistics, mechanics, JSBSim |
| `game-designer` | claude-opus-4-7 | Design: maps, materials, audio, art direction, geospatial pipeline |
| `game-tester` | claude-opus-4-7 | Quality: UE5 Automation, Gauntlet, PIE screenshots, reports |

## New Skills (7)

| Skill | Agent |
|---|---|
| `game-unreal-developer` | game-developer |
| `game-flight-dynamics` | game-developer |
| `game-unreal-designer` | game-designer |
| `game-visual-design` | game-designer |
| `game-geospatial-pipeline` | game-designer |
| `game-audio-design` | game-designer |
| `game-testing-ue5` | game-tester |

Migrated: `game-map-architect` moves from game-developer → game-designer.

## New Workflows (3)

| Workflow | Trigger |
|---|---|
| `game-spec-definition` | New game or major evolution; replaces spec-refinement for game contexts |
| `game-dev-cycle` | Approved spec + open task in TASKS.md |
| `game-bugfix` | User-reported bug not caught by game-tester |

Updated: `tdd-cycle` removes `game-developer` from implementer list.

## New Rule (1)

`game-agents-coordination.md` — Decision Authority Matrix + anti-deadlock protocol
with `dadaia-grill-me` as tie-breaker.

## Acceptance Criteria

- [ ] `dadaia public doctor` shows `[ok]` for all 13 new entries and 3 modified entries
- [ ] `game-designer` and `game-tester` agents load correctly in Claude Code
- [ ] `game-developer-scope.md` names all 3 game agents with their sub-domains
- [ ] `game-agents-coordination.md` rule is always active in game contexts
- [ ] `game-spec-definition` workflow validates cleanly via `dadaia public stage`
- [ ] `game-dev-cycle` workflow validates cleanly via `dadaia public stage`
- [ ] `game-bugfix` workflow validates cleanly via `dadaia public stage`
- [ ] `tdd-cycle` implementer list no longer includes `game-developer`
```

- [ ] **Step 3: Mark T146 DONE and commit**

```bash
# Edit specs/TASKS.md: change T146 from [-] to [x]
git add specs/features/game-agents-split/SPEC.md specs/TASKS.md
git commit -m "feat(game-agents-split): create SPEC.md Aprovado (T146)"
```

---

## Task 2: SDD Artifacts — PLAN.md and TASKS.md

**Files:**
- Create: `specs/features/game-agents-split/PLAN.md`
- Create: `specs/features/game-agents-split/TASKS.md`
- Modify: `specs/TASKS.md` (T147, T148)

- [ ] **Step 1: Mark T147 IN PROGRESS**

```bash
# Edit specs/TASKS.md: [ ] T147 → [-]
git add specs/TASKS.md && git commit -m "chore(tasks): start T147"
```

- [ ] **Step 2: Create PLAN.md**

Create `specs/features/game-agents-split/PLAN.md`:

```markdown
# PLAN: Game Agents Split

**Status:** Aprovado
**Reference:** `docs/superpowers/plans/2026-05-16-game-agents-split.md`

## Approach

Content-creation plan. All artifacts are Markdown + YAML files in
`dadaia_workspace/public/`. Propagated to all runtimes via dadaia CLI after
all files are written.

## Execution Order

1. Rules: game-agents-coordination, game-developer-scope (update)
2. Agents: game-developer (update), game-designer (new), game-tester (new)
3. Skills: 7 new files (game-unreal-developer through game-testing-ue5)
4. Workflows: 3 new + tdd-cycle update
5. Propagation: dadaia public stage && install && doctor
```

- [ ] **Step 3: Mark T147 DONE, mark T148 IN PROGRESS, create TASKS.md**

```bash
# Edit specs/TASKS.md: [-] T147 → [x], [ ] T148 → [-]
git add specs/features/game-agents-split/PLAN.md specs/TASKS.md
git commit -m "feat(game-agents-split): create PLAN.md Aprovado (T147)"
```

Create `specs/features/game-agents-split/TASKS.md`:

```markdown
# TASKS: game-agents-split

| Marker | State |
|---|---|
| `[ ]` | OPEN |
| `[-]` | IN PROGRESS |
| `[x]` | DONE |

## Rules and Agents

- [ ] TA01 — Criar game-agents-coordination.md rule
- [ ] TA02 — Atualizar game-developer-scope.md (3 agents)
- [ ] TA03 — Atualizar game-developer.md (narrow scope, add WebSearch, workspace table)
- [ ] TA04 — Criar game-designer.md agent
- [ ] TA05 — Criar game-tester.md agent

## Skills

- [ ] TA06 — Criar game-unreal-developer/SKILL.md
- [ ] TA07 — Criar game-flight-dynamics/SKILL.md
- [ ] TA08 — Criar game-unreal-designer/SKILL.md
- [ ] TA09 — Criar game-visual-design/SKILL.md
- [ ] TA10 — Criar game-geospatial-pipeline/SKILL.md
- [ ] TA11 — Criar game-audio-design/SKILL.md
- [ ] TA12 — Criar game-testing-ue5/SKILL.md

## Workflows

- [ ] TA13 — Criar game-spec-definition.workflow.md
- [ ] TA14 — Criar game-dev-cycle.workflow.md
- [ ] TA15 — Criar game-bugfix.workflow.md
- [ ] TA16 — Atualizar tdd-cycle.workflow.md

## Propagation

- [ ] TA17 — dadaia public stage && install --target all
- [ ] TA18 — dadaia public doctor (all [ok])
```

- [ ] **Step 4: Commit**

```bash
# Edit specs/TASKS.md: [-] T148 → [x]
git add specs/features/game-agents-split/TASKS.md specs/TASKS.md
git commit -m "feat(game-agents-split): create TASKS.md (T148)"
```

---

## Task 3: Rule — `game-agents-coordination.md`

**Files:**
- Create: `dadaia_workspace/public/rules/game-agents-coordination.md`
- Modify: `specs/features/game-agents-split/TASKS.md` (TA01), `specs/TASKS.md` (T166)

- [ ] **Step 1: Mark T166/TA01 IN PROGRESS**

```bash
# specs/TASKS.md: [ ] T166 → [-]
# specs/features/game-agents-split/TASKS.md: [ ] TA01 → [-]
git add specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "chore(tasks): start T166/TA01 — game-agents-coordination rule"
```

- [ ] **Step 2: Create the rule file**

Create `dadaia_workspace/public/rules/game-agents-coordination.md`:

````markdown
# game-agents-coordination

Esta rule é sempre ativa em contextos de jogo neste workspace.

## Agentes de Jogo

Três agentes têm autoridade exclusiva sobre `repos/redacted-slug/`, cada um com
sub-domínio distinto:

| Agente | Sub-domínio | Escreve |
|---|---|---|
| `game-developer` | Lógica | C++, Blueprints (gameplay), fixtures de teste |
| `game-designer` | Design | Scripts Python/CLI, configs, specs de assets, HDA |
| `game-tester` | Testes | Scripts de teste, reports HTML com evidências |

## Decision Authority Matrix

| Domínio | Autoridade Primária | Podem Objetar (com evidência) | Tie-breaker |
|---|---|---|---|
| Mecânicas, física, IA, balística | **game-developer** | game-designer, game-tester | product-engineer |
| Design visual, mapas, áudio, arte | **game-designer** | game-developer, game-tester | product-engineer |
| Critérios de qualidade, test strategy | **game-tester** | game-developer, game-designer | product-engineer |
| Arquitetura geral, code patterns | **software-architect** | game-developer (idiomas UE5) | game-developer vence em decisões UE5-específicas |
| CI/CD, build, deploy | **devops-engineer** | game-developer, game-designer | devops-engineer |
| Escopo, prioridades, SPEC | **product-engineer** | todos | product-engineer (palavra final) |

## Protocolo Anti-Deadlock

Quando dois agentes divergem:

1. Cada agente documenta sua posição e trade-offs no próprio report
2. `product-engineer` sintetiza e propõe resolução no synthesis report
3. Se ainda sem consenso → **invocar `dadaia-grill-me` com o operador** (decisão humana estruturada)

**Regra absoluta:** nenhum agente bloqueia o domínio do outro.
Uma objeção sem evidência é automaticamente ignorada.

## Protocolo de Pesquisa

Cada agente usa `WebSearch` apenas dentro de sua whitelist de fontes confiáveis.
A whitelist está embedded na skill especializada de cada agente.
Nunca usar fontes fora da whitelist sem aprovação explícita do operador.

## Conflito de Sub-domínio

Quando um bug ou feature span dois sub-domínios (ex: performance de mapa afeta física
de voo), o `game-tester` classifica e emite dois sub-reports direcionados
independentemente para `game-designer` e `game-developer`.
````

- [ ] **Step 3: Mark DONE and commit**

```bash
# specs/TASKS.md: [-] T166 → [x]
# specs/features/game-agents-split/TASKS.md: [-] TA01 → [x]
git add dadaia_workspace/public/rules/game-agents-coordination.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-agents-coordination rule (T166/TA01)"
```

---

## Task 4: Rule — Update `game-developer-scope.md`

**Files:**
- Modify: `dadaia_workspace/public/rules/game-developer-scope.md`
- Modify: task markers (T162/TA02)

- [ ] **Step 1: Mark T162/TA02 IN PROGRESS and commit**

- [ ] **Step 2: Replace content of `dadaia_workspace/public/rules/game-developer-scope.md`**

```markdown
# game-developer-scope

Esta rule é sempre ativa neste workspace.

## Domínio Exclusivo de Jogos

Três agentes especializados têm autoridade exclusiva sobre todo o código de jogo.
Código de jogo inclui qualquer arquivo dentro de `repos/redacted-slug/`.

| Agente | Sub-domínio | O que escreve |
|---|---|---|
| `game-developer` | Lógica | C++, Blueprints (gameplay), IA, física, balística, mecânicas |
| `game-designer` | Design | Assets estáticos, materiais, mapas, áudio, scripts de pipeline |
| `game-tester` | Testes | Scripts de automação UE5, reports HTML com evidências |

## Proibido para Outros Agentes

Nenhum dos agentes abaixo deve modificar arquivos em `repos/redacted-slug/`:
`product-engineer`, `software-architect`, `software-engineer`, `frontend-engineer`,
`backend-engineer`, `qa-engineer`, `devops-engineer`.

Estes agentes podem **LER** arquivos de jogo para contexto, mas nunca escrever.

Se receber uma tarefa que envolva código de jogo, responda:

```
[SCOPE ERROR] Código de jogo é domínio exclusivo dos agentes game-developer,
game-designer e game-tester. Use o agente correto para esta tarefa.
```

## Fronteira de Escopo

O critério é simples: se o arquivo vive em `repos/redacted-slug/`, é domínio dos
agentes de jogo. Se vive fora, não é.

## Jogos Ativos no Workspace

| Jogo | Engine | Agentes responsáveis |
|---|---|---|
| `redacted-slug-trex` | Phaser.js 3.60 | game-developer, game-designer, game-tester |
| `redacted-slug` | Three.js r165 | game-developer, game-designer, game-tester |
| `redacted-slug-v2` | Unreal Engine 5 | game-developer, game-designer, game-tester |

## O Que Cada Agente NÃO Toca

**game-developer:** assets visuais, áudio, terreno, materiais, mapas, testes

**game-designer:** lógica de jogo, IA de inimigos, física de voo, balística, testes

**game-tester:** código de produção e assets — apenas scripts de teste e reports
```

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/rules/game-developer-scope.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): update game-developer-scope rule (T162/TA02)"
```

---

## Task 5: Agent — Update `game-developer.md`

**Files:**
- Modify: `dadaia_workspace/public/agents/game-developer.md`
- Modify: task markers (T151/TA03)

- [ ] **Step 1: Mark T151/TA03 IN PROGRESS and commit**

- [ ] **Step 2: Update `dadaia_workspace/public/agents/game-developer.md`**

Update the following sections (keep existing input_contract structure):

**Frontmatter:** add `WebSearch` to tools list; update skills list:
```yaml
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebFetch
  - WebSearch
skills:
  - dadaia-workspace-spec-navigator
  - dadaia-task-manager
  - game-physics-engine
  - game-platform-browser
  - game-platform-godot
  - game-platform-unity
  - game-platform-unreal
  - game-packaging-distribution
  - game-unreal-developer
  - game-flight-dynamics
```

**Description:** change from "Agente ÚNICO autorizado" to:
```
Especialista em lógica de jogo — um dos 3 agentes de jogo do workspace. Implementa
mecânicas, IA de inimigos, física de voo (JSBSim), balística e sistemas de gameplay
em Phaser.js, Three.js, Godot, Unity e Unreal Engine 5. NÃO toca em design visual,
áudio, mapas ou testes.
```

**Workspace table:** add redacted-slug-v2:
```markdown
| `redacted-slug-v2` | Unreal Engine 5 | C++ + Blueprints, JSBSim, Nanite, Lumen |
```

**Skills table:** add new skills:
```markdown
| Lógica UE5 + pesquisa em forums | `game-unreal-developer` |
| JSBSim, aerodinâmica, FDM | `game-flight-dynamics` |
```

**Scope section:** update to reflect the 3-agent model.

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/agents/game-developer.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): narrow game-developer scope (T151/TA03)"
```

---

## Task 6: Agent — Create `game-designer.md`

**Files:**
- Create: `dadaia_workspace/public/agents/game-designer.md`
- Modify: task markers (T149/TA04)

- [ ] **Step 1: Mark T149/TA04 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/agents/game-designer.md`**

```markdown
---
name: game-designer
description: >
  Especialista em design de jogos — um dos 3 agentes de jogo do workspace. Implementa
  assets estáticos, direção de arte, mapas, iluminação, áudio e pipeline geoespacial
  (QGIS → GDAL → Cesium → UE5). Pesquisa ativamente referências e dados públicos em
  fontes confiáveis. NÃO toca em lógica de jogo, IA de inimigos ou testes.
model: claude-opus-4-7
color: purple
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebFetch
  - WebSearch
skills:
  - dadaia-workspace-spec-navigator
  - dadaia-task-manager
  - game-map-architect
  - game-unreal-designer
  - game-visual-design
  - game-geospatial-pipeline
  - game-audio-design
maxTurns: 60
input_contract:
  requires_inputs:
    - name: context
      kind: string
      source: workflow_input
      description: "Active Spec Context Project name (must be a redacted-slug project)"
      stop_if_missing: true
    - name: game_spec
      kind: report
      source: report_path
      description: "Approved game-feature SPEC.md path under repos/redacted-slug/.../specs/"
      stop_if_missing: true
  produces_outputs:
    - name: game_design_report
      kind: report
      path: .dadaia/reports/{context}/game-designer/{ts}-design.html
      schema_ref: handoff-schema-v1
  stop_if_missing: true
---

# Game Designer

> Reports são arquivos HTML. O template e seções obrigatórias estão em `.dadaia/reports/AGENTS.md`.

Você é o especialista de design de jogo neste workspace. Um dos 3 agentes de jogo.
Responsável por tudo que é visto, ouvido e espacialmente navegado no jogo.

---

## Escopo

**Você toca em:**
- Assets estáticos: heightfields, material instances, Houdini HDAs, configs Cesium
- Level design: terrain, posicionamento de objetivos, zonas de combate
- Iluminação: Lumen setup, sky atmosphere, time-of-day, volumetric fog
- Áudio: MetaSounds config, spatial audio, sound design specs
- Pipeline geoespacial: QGIS → GDAL/PDAL → RealityScan → Cesium ion → UE5
- Art direction: design bible, paleta, estética, moodboard, post-process
- Pesquisa ativa de referências e dados em fontes confiáveis

**Você NÃO toca em:**
- Lógica de jogo, IA, física de voo, balística, mecânicas
- Testes automatizados, reports de qualidade

Se solicitado fora do escopo:
```
[SCOPE ERROR] Sou o game-designer — cuido de design visual, áudio e mapas.
Para lógica: use game-developer. Para testes: use game-tester.
```

---

## Workspace: redacted-slug

| Jogo | Engine | Stack |
|---|---|---|
| `redacted-slug-trex` | Phaser.js 3.60 | HTML + JS puro, assets procedurais |
| `redacted-slug` | Three.js r165 | HTML + JS puro, estética N64 |
| `redacted-slug-v2` | Unreal Engine 5 | Nanite, Lumen, Cesium, Megascans |

---

## Skills disponíveis

| Tarefa | Skill |
|---|---|
| Mapa, câmera, parallax, HUD | `game-map-architect` |
| Level design UE5, Nanite, Lumen, pesquisa de mapas | `game-unreal-designer` |
| Art direction, moodboard, post-process | `game-visual-design` |
| QGIS, GDAL, Cesium, fotogrametria | `game-geospatial-pipeline` |
| MetaSounds, spatial audio, sound design | `game-audio-design` |

---

## Protocolo de Pesquisa

Use `WebSearch` apenas dentro da whitelist de fontes confiáveis da sua skill.
Sempre verificar licença antes de usar qualquer dado externo.
Nunca usar Google Maps, Google Earth ou Street View para reconstrução 3D.

---

## Como trabalha

### Fluxo obrigatório

```
1. Ler specs/features/<jogo>/SPEC.md
2. Identificar a task no TASKS.md
3. Marcar a task como [-] in_progress
4. Carregar a skill correspondente à tarefa de design
5. Implementar assets estáticos / pipeline / art direction
6. Documentar em design report HTML
7. Marcar a task como [x] done
```

### Princípios inegociáveis

- **Licenças sempre verificadas** — qualquer dado externo precisa de licença clara antes de usar
- **Pipeline documentado** — todo asset geoespacial tem o pipeline de origem registrado
- **Commits atômicos** — uma feature de design por commit

---

## Permissões de escrita

| Path | Permissão |
|---|---|
| `repos/redacted-slug/**` | ✅ Write — assets, configs, scripts de pipeline |
| `.dadaia/reports/<context-name>/game-designer/` | ✅ Write — design reports |
| Qualquer outro path | ❌ Proibido |

## Proibições absolutas

- Lógica de jogo, IA, física — use `game-developer`
- Testes automatizados, reports de bug — use `game-tester`
- Infraestrutura, Docker, CI/CD — use `devops-engineer`
- Specs e planos — use `product-engineer`

---

## Gate SDD

Nunca implemente sem `**Status:** Aprovado` na spec da feature.

### Path de reports

```
.dadaia/reports/<context-name>/game-designer/<YYYY-MM-DDTHHMMSSZ>-<jogo>-<feature>.html
```
```

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/agents/game-designer.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): create game-designer agent (T149/TA04)"
```

---

## Task 7: Agent — Create `game-tester.md`

**Files:**
- Create: `dadaia_workspace/public/agents/game-tester.md`
- Modify: task markers (T150/TA05)

- [ ] **Step 1: Mark T150/TA05 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/agents/game-tester.md`**

```markdown
---
name: game-tester
description: >
  Especialista em testes de jogo — um dos 3 agentes de jogo do workspace. Define
  acceptance criteria antes da implementação, executa UE5 Automation Framework e
  Gauntlet, captura PIE screenshots como evidência e emite quality reports HTML.
  Pesquisa ativamente bugs conhecidos e padrões de teste em UE5. NÃO escreve
  código de produção ou assets.
model: claude-opus-4-7
color: yellow
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebFetch
  - WebSearch
skills:
  - dadaia-workspace-spec-navigator
  - dadaia-task-manager
  - game-testing-ue5
maxTurns: 40
input_contract:
  requires_inputs:
    - name: context
      kind: string
      source: workflow_input
      description: "Active Spec Context Project name (must be a redacted-slug project)"
      stop_if_missing: true
    - name: game_spec
      kind: report
      source: report_path
      description: "Approved game-feature SPEC.md path under repos/redacted-slug/.../specs/"
      stop_if_missing: true
  produces_outputs:
    - name: game_quality_report
      kind: report
      path: .dadaia/reports/{context}/game-tester/{ts}-quality.html
      schema_ref: handoff-schema-v1
  stop_if_missing: true
---

# Game Tester

> Reports são arquivos HTML. O template e seções obrigatórias estão em `.dadaia/reports/AGENTS.md`.

Você é o especialista de qualidade de jogo neste workspace. Um dos 3 agentes de jogo.
Sua autoridade é máxima em critérios de qualidade, test strategy e evidências.

---

## Escopo

**Você toca em:**
- Acceptance criteria: define ANTES de qualquer implementação começar
- Test scenarios: condições, inputs, resultados esperados
- UE5 Automation: FunctionalTest actors, RunTests CLI
- Gauntlet: performance e stress tests
- PIE screenshots: evidências visuais automatizadas
- Quality reports: HTML com screenshots, severity matrix, reproduction steps
- Bug reports: classifica e direciona para game-developer (lógica) ou game-designer (design)

**Você NÃO toca em:**
- Código de produção (C++, Blueprints, scripts Python)
- Assets visuais ou de áudio
- Specs ou planos de implementação

Se solicitado fora do escopo:
```
[SCOPE ERROR] Sou o game-tester — defino critérios e valido qualidade.
Para código de jogo: use game-developer ou game-designer.
```

---

## Severity Matrix

| Nível | Definição | Exemplo |
|---|---|---|
| Critical | Crash, dados perdidos, jogo inicia mas não fecha | NullPointerException no GameMode |
| High | Feature core quebrada, sem workaround | Avião não responde a input de voo |
| Medium | Feature degradada, workaround possível | Áudio do motor com delay inconsistente |
| Low | Cosmético, não afeta gameplay | Z-fighting em textura de mapa distante |

---

## Skills disponíveis

| Tarefa | Skill |
|---|---|
| UE5 Automation, Gauntlet, PIE, reports | `game-testing-ue5` |

---

## Como trabalha

### Na fase de spec (antes de implementação)

```
1. Ler SPEC.md aprovada
2. Escrever test scenarios (condições, inputs, outputs esperados)
3. Documentar acceptance criteria no quality report inicial
4. Pesquisar bugs conhecidos do UE5 relevantes ao escopo
```

### Na fase de validação (depois de implementação)

```
1. Rodar UE5 Automation suite
2. Capturar PIE screenshots como evidências
3. Classificar falhas por severity e sub-domínio (lógica vs design)
4. Emitir quality report HTML com todas as evidências
5. Direcionar bug reports aos agentes corretos
```

### Protocolo de Pesquisa

Use `WebSearch` apenas dentro da whitelist da skill `game-testing-ue5`.
Pesquise bugs conhecidos da versão UE5 alvo ANTES de cada sessão de teste.

---

## Permissões de escrita

| Path | Permissão |
|---|---|
| `repos/redacted-slug/**/tests/` | ✅ Write — test scripts UE5 |
| `.dadaia/reports/<context-name>/game-tester/` | ✅ Write — quality reports |
| Qualquer outro path | ❌ Proibido |

## Proibições absolutas

- Código de produção (C++, Blueprints, assets) — use game-developer ou game-designer
- Specs e planos — use product-engineer
- Infraestrutura — use devops-engineer

---

## Gate SDD

Nunca valide sem `**Status:** Aprovado` na spec da feature.
Nunca marque uma task como [x] DONE se o quality report tiver itens Critical ou High abertos.

### Path de reports

```
.dadaia/reports/<context-name>/game-tester/<YYYY-MM-DDTHHMMSSZ>-<jogo>-<feature>-quality.html
```
```

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/agents/game-tester.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): create game-tester agent (T150/TA05)"
```

---

## Task 8: Skill — `game-unreal-developer`

**Files:**
- Create: `dadaia_workspace/public/skills/game-unreal-developer/SKILL.md`
- Modify: task markers (T152/TA06)

- [ ] **Step 1: Mark T152/TA06 IN PROGRESS and commit**

- [ ] **Step 2: Create the skill file**

Create `dadaia_workspace/public/skills/game-unreal-developer/SKILL.md`:

````markdown
---
name: game-unreal-developer
description: >
  UE5 profundo para lógica de jogo: C++ Actor/Component/GameMode/GameState/PlayerController/Pawn,
  Behavior Trees, EQS, Chaos Physics, delegates, collision channels. Inclui protocolo de
  pesquisa com whitelist de fontes confiáveis para forums, exemplos e bugs conhecidos.
applyTo: "repos/redacted-slug/redacted-slug-v2/**"
trusted_sources:
  - dev.epicgames.com
  - forums.unrealengine.com
  - github.com
  - stackoverflow.com
  - reddit.com/r/unrealengine
  - reddit.com/r/gamedev
  - jsbsim-team.github.io
---

# game-unreal-developer

Referência técnica de UE5 para o game-developer. Carregue ao implementar qualquer
mecânica de gameplay em redacted-slug-v2.

---

## 1. Arquitetura de Classes UE5

### Hierarquia obrigatória

```
UGameInstance          → persiste entre levels, estado global de sessão
  UGameMode            → regras do jogo (server-only), spawns, condições de vitória
  UGameState           → estado replicável visível a todos os players
    APlayerController  → input, câmera, HUD (não tem mesh)
      APawn/ACharacter → mesh, movimentação física no mundo
        UActorComponent → lógica modular (weapon, health, flight)
```

### Onde colocar cada sistema

| Sistema | Classe correta |
|---|---|
| Regras de round, score, spawn de inimigos | `AGameMode` |
| Vidas, pontuação sincronizada | `AGameState` |
| Input de voo, câmera | `APlayerController` |
| Mesh da aeronave, colisões | `APawn` |
| Sistema de armas, health, afterburner | `UActorComponent` |
| IA de inimigo | `AAIController` + `UBehaviorTree` |

---

## 2. C++ Patterns Obrigatórios

### UFUNCTION e UPROPERTY

```cpp
UCLASS()
class AEROFIGHTERS_API APlayerAircraft : public APawn
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight")
    float MaxThrust = 50000.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weapons")
    int32 MissileCount = 6;

    UFUNCTION(BlueprintCallable, Category = "Flight")
    void FireMissile();

    UFUNCTION(BlueprintImplementableEvent, Category = "VFX")
    void OnMissileFired();

private:
    UPROPERTY()
    TObjectPtr<UFlightComponent> FlightComp;
};
```

### Delegate para eventos desacoplados

```cpp
// No header do GameMode:
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnEnemyDestroyed, int32, Points);

UPROPERTY(BlueprintAssignable)
FOnEnemyDestroyed OnEnemyDestroyed;

// No enemy actor ao morrer:
if (AMyGameMode* GM = GetWorld()->GetAuthGameMode<AMyGameMode>())
{
    GM->OnEnemyDestroyed.Broadcast(PointValue);
}
```

---

## 3. Behavior Tree para IA de Inimigo

### Setup mínimo

```
UBehaviorTree (asset)
  └── Root
        └── Selector
              ├── Sequence [atacar se jogador visível]
              │     ├── BTTask_CheckLineOfSight
              │     └── BTTask_FireWeapon
              └── Sequence [patrulhar]
                    └── BTTask_MoveToPatrolPoint
```

```cpp
// No AIController:
UPROPERTY(EditDefaultsOnly, Category = "AI")
TObjectPtr<UBehaviorTree> EnemyBehaviorTree;

void AEnemyAIController::BeginPlay()
{
    Super::BeginPlay();
    if (EnemyBehaviorTree)
    {
        RunBehaviorTree(EnemyBehaviorTree);
    }
}
```

---

## 4. Collision Channels

```cpp
// Setup de canal customizado no ProjectSettings → Collision:
// Canal: "Projectile" (ECC_GameTraceChannel1)
// Canal: "Aircraft"   (ECC_GameTraceChannel2)

// No construtor do projétil:
CollisionComponent->SetCollisionProfileName("Projectile");

// Query de linha (hitbox):
FHitResult Hit;
FCollisionQueryParams Params;
Params.AddIgnoredActor(this);

bool bHit = GetWorld()->LineTraceSingleByChannel(
    Hit,
    StartLocation,
    EndLocation,
    ECC_GameTraceChannel1,  // Projectile channel
    Params
);
```

---

## 5. Protocolo de Pesquisa

Antes de implementar qualquer sistema novo:

```
1. WebSearch em dev.epicgames.com — documentação oficial da feature
2. WebSearch em forums.unrealengine.com — threads com a versão UE5 alvo
3. WebSearch em github.com — exemplos de código para o pattern
4. Registrar qualquer bug conhecido da versão antes de iniciar
```

Fontes permitidas: dev.epicgames.com, forums.unrealengine.com, github.com,
stackoverflow.com, reddit.com/r/unrealengine, reddit.com/r/gamedev, jsbsim-team.github.io

**Nunca pesquisar fora desta whitelist sem aprovação explícita do operador.**
````

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/skills/game-unreal-developer/SKILL.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-unreal-developer skill (T152/TA06)"
```

---

## Task 9: Skill — `game-flight-dynamics`

**Files:**
- Create: `dadaia_workspace/public/skills/game-flight-dynamics/SKILL.md`
- Modify: task markers (T153/TA07)

- [ ] **Step 1: Mark T153/TA07 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/skills/game-flight-dynamics/SKILL.md`**

````markdown
---
name: game-flight-dynamics
description: >
  JSBSim FDM integrado com UE5: coeficientes aerodinâmicos, propulsão, trem de pouso,
  FCS, loop de simulação passo fixo, ground effect, stall, integração com Chaos Physics.
applyTo: "repos/redacted-slug/redacted-slug-v2/**"
---

# game-flight-dynamics

Referência para integração do JSBSim Flight Dynamics Model com Unreal Engine 5.

---

## 1. Conceitos Fundamentais

| Variável | Símbolo | Descrição |
|---|---|---|
| Thrust | T | Força propulsiva (N) |
| Drag | D | Resistência aerodinâmica |
| Lift | L | Sustentação |
| Angle of Attack | α (alpha) | Ângulo entre vetor velocidade e corda da asa |
| Sideslip | β (beta) | Ângulo lateral |
| Mach | M | Velocidade relativa ao som |

**Stall:** ocorre quando α excede o ângulo crítico (~15-18°). Lift cai abruptamente.

**Ground effect:** Lift aumenta ~10-20% quando aeronave está a menos de 1 envergadura do solo.

---

## 2. Arquitetura de Integração UE5 + JSBSim

```
UE5 Tick (variável)
  ↓
UFlightComponent::TickComponent()
  ↓
JSBSimInterface::Step(dt_fixed)  ← passo fixo (dt = 1/120s)
  ↓ acumula dt_remaining
JSBSimInterface::GetState()      ← posição, velocidade, atitude
  ↓
APawn::SetActorLocation/Rotation ← interpolado para UE5
```

### Por que passo fixo?

JSBSim é um integrador numérico. Frame rate variável do UE5 causa instabilidade
na simulação física. Usar passo fixo de 1/120s (8.33ms) com acúmulo de delta time.

```cpp
// UFlightComponent.cpp
void UFlightComponent::TickComponent(float DeltaTime, ...)
{
    AccumulatedDt += DeltaTime;
    const float FixedStep = 1.0f / 120.0f;

    while (AccumulatedDt >= FixedStep)
    {
        JSBSimInterface->Step(FixedStep);
        AccumulatedDt -= FixedStep;
    }

    // Interpolar posição entre passos
    const float Alpha = AccumulatedDt / FixedStep;
    UpdateActorTransform(Alpha);
}
```

---

## 3. Inputs de Controle

```cpp
// Normalizado [-1, 1] → JSBSim espera range específico por eixo
JSBSimInterface->SetControl("fcs/aileron-cmd-norm",  AileronInput);   // roll
JSBSimInterface->SetControl("fcs/elevator-cmd-norm", ElevatorInput);  // pitch
JSBSimInterface->SetControl("fcs/rudder-cmd-norm",   RudderInput);    // yaw
JSBSimInterface->SetControl("fcs/throttle-cmd-norm", ThrottleInput);  // 0..1
```

---

## 4. Trem de Pouso e Ground Effect

```cpp
// Detectar contato com solo via Chaos Physics, não via JSBSim collision
void UFlightComponent::CheckGroundContact()
{
    FHitResult Hit;
    const FVector Start = GetOwner()->GetActorLocation();
    const FVector End = Start - FVector(0, 0, 200.0f);

    if (GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_WorldStatic))
    {
        const float HeightAGL = Hit.Distance; // Height Above Ground Level
        JSBSimInterface->SetGroundHeight(Hit.ImpactPoint.Z);
        JSBSimInterface->SetProperty("position/h-agl-ft", HeightAGL * 0.0328084f); // cm→ft
    }
}
```

---

## 5. Referências Oficiais

- JSBSim Introduction: https://jsbsim-team.github.io/jsbsim/
- Aircraft FDM files: https://github.com/JSBSim-Team/jsbsim/tree/master/aircraft
````

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/skills/game-flight-dynamics/SKILL.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-flight-dynamics skill (T153/TA07)"
```

---

## Task 10: Skill — `game-unreal-designer`

**Files:**
- Create: `dadaia_workspace/public/skills/game-unreal-designer/SKILL.md`
- Modify: task markers (T154/TA08)

- [ ] **Step 1: Mark T154/TA08 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/skills/game-unreal-designer/SKILL.md`**

````markdown
---
name: game-unreal-designer
description: >
  UE5 profundo para design: World Partition, Landscape, PCG, Nanite, Lumen, Megascans/Fab.
  Protocolo de pesquisa e curadoria de mapas e assets de fontes públicas seguras
  (OSM, USGS, NASA EarthData, OpenTopography, Sketchfab CC, ArtStation).
applyTo: "repos/redacted-slug/redacted-slug-v2/**"
trusted_sources:
  - dev.epicgames.com
  - forums.unrealengine.com
  - openstreetmap.org
  - earthexplorer.usgs.gov
  - earthdata.nasa.gov
  - opentopography.org
  - sketchfab.com
  - fab.com
  - artstation.com
  - freesound.org
  - cesium.com/learn
  - sidefx.com/docs
  - gdal.org
  - qgis.org
---

# game-unreal-designer

Referência técnica de UE5 para o game-designer. Carregue ao implementar level design,
pipeline geoespacial ou configuração de iluminação em redacted-slug-v2.

---

## 1. World Partition + Sublevels

```
World Partition = streaming automático de cells do mundo
  └── Cada cell: 128m x 128m (padrão, ajustável)
        └── Ativa/desativa baseado em posição do player

Sublevels = agrupamento manual de actors em layers temáticos
  ├── SL_Terrain    → landscape + terrain meshes
  ├── SL_Buildings  → estruturas urbanas
  ├── SL_VFX        → effects, weather
  └── SL_Gameplay   → triggers, spawn points (gerenciado pelo game-developer)
```

**Regra:** game-designer gerencia SL_Terrain, SL_Buildings, SL_VFX.
SL_Gameplay é exclusivo do game-developer.

---

## 2. Nanite para Meshes Fotogramétricos

```python
# Python no UE5 Editor para configurar Nanite em batch:
import unreal

assets = unreal.EditorAssetLibrary.list_assets("/Game/Photogrammetry/", recursive=True)
for asset_path in assets:
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if isinstance(asset, unreal.StaticMesh):
        asset.set_editor_property("nanite_settings",
            unreal.MeshNaniteSettings(enabled=True, position_precision=1.0))
        unreal.EditorAssetLibrary.save_asset(asset_path)
```

---

## 3. Lumen — Configuração Recomendada

```ini
# DefaultEngine.ini
[/Script/Engine.RendererSettings]
r.Lumen.Reflections.Allow=1
r.Lumen.DiffuseIndirect.Allow=1
r.Lumen.HardwareRayTracing=1          # GPU RTX: melhor qualidade
r.Lumen.HardwareRayTracing=0          # Sem RTX: software fallback
r.Lumen.Scene.SurfaceCacheResolution=1.0
r.Shadow.Virtual.Enable=1             # Virtual Shadow Maps (obrigatório com Lumen)
```

**Sky Light:** sempre usar HDRI para base de iluminação realista. Avoid baked lightmaps.

---

## 4. PCG Framework — Vegetação e Scatter

```cpp
// PCGGraph para distribuição de árvores em terreno:
// 1. Surface Sampler → pontos no Landscape
// 2. Attribute Filter → slope < 30° (sem árvores em encostas íngremes)
// 3. Density Filter → baseado em altitude (altura = menos vegetação)
// 4. Static Mesh Spawner → sorteia de pool de N meshes de árvores
```

---

## 5. Protocolo de Pesquisa de Mapas

### Fontes permitidas e licenças

| Fonte | Dados | Licença | Atribuição |
|---|---|---|---|
| openstreetmap.org | Vias, edificações, infraestrutura | ODbL | Obrigatória |
| earthexplorer.usgs.gov | DEM, terrain, imagery | Domínio público (EUA) | Recomendada |
| earthdata.nasa.gov | Satellite imagery, SRTM | Domínio público | Recomendada |
| opentopography.org | LiDAR, point cloud | CC-BY / Open | Por dataset |
| sketchfab.com | 3D assets | CC (verificar por item) | Por item |
| fab.com | Megascans | Fab EULA | Incluída |

### Regra de segurança

**NUNCA usar Google Maps, Google Earth ou Street View para:**
- Reconstrução 3D
- Extração de dados geoespaciais
- Base de heightmap

Violação dessas diretrizes é proibida pela Google Geo Guidelines.

### Workflow de curadoria

```
1. Identificar área geográfica de interesse
2. WebSearch no USGS EarthExplorer → baixar DEM (GeoTIFF, WGS84)
3. WebSearch no OSM → exportar área como .osm ou via Overpass API
4. QGIS → reprojetar para CRS do projeto (UTM ou projeção local)
5. GDAL → gerar mosaico, recortar por AOI, exportar .tif
6. UE5 → importar heightmap via Landscape Import
7. Registrar fonte e licença no design report
```
````

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/skills/game-unreal-designer/SKILL.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-unreal-designer skill (T154/TA08)"
```

---

## Task 11: Skill — `game-visual-design`

**Files:**
- Create: `dadaia_workspace/public/skills/game-visual-design/SKILL.md`
- Modify: task markers (T155/TA09)

- [ ] **Step 1: Mark T155/TA09 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/skills/game-visual-design/SKILL.md`**

````markdown
---
name: game-visual-design
description: >
  Art direction para jogos UE5: design bible, identidade visual, paleta, moodboard,
  post-process volume (bloom, DoF, tone mapping), sky atmosphere, fog volumétrico,
  time-of-day system e camera rigs cinematográficas.
applyTo: "repos/redacted-slug/**"
---

# game-visual-design

Referência de art direction e visual design. Carregue ao definir estética do jogo
ou configurar sistemas visuais em UE5.

---

## 1. Design Bible — Formato

```markdown
# Design Bible: <nome do jogo>

## Conceito Visual
<1 parágrafo: o que o jogador deve sentir ao ver o jogo>

## Referências Visuais
- Ref 1: [URL no ArtStation ou artstation.com] — por quê
- Ref 2: [URL] — por quê

## Paleta de Cores
| Papel | Hex | Uso |
|---|---|---|
| Sky primary | #1a2b4c | Céu noturno de combate |
| Enemy accent | #ff3a1a | Aviões inimigos, alertas |
| Friendly | #3af0ff | Aeronave do player, HUD |
| Terrain | #4a5a3a | Terreno / vegetação |

## Estética
<Low-poly / fotorrealista / estilizado / híbrido + justificativa>

## Proibições
<O que NÃO deve aparecer no jogo — mantém consistência>
```

---

## 2. Post-Process Volume — Config de Combate Aéreo

```ini
# Configurações recomendadas para redacted-slug-v2:

Bloom:
  Intensity: 0.4          # Sutil, não ofusca o HUD
  Threshold: 1.0

Depth of Field:
  Method: CircleDOF
  FocalDistance: 5000.0   # Foco no range de combate
  FstopAperture: 32.0     # DOF suave, não distrator

Tone Mapping:
  ACES: enabled           # Cor cinematográfica, padrão UE5
  Gamma: 2.2

Chromatic Aberration:
  Intensity: 0.3          # Apenas ao tomar dano (via Material Parameter Collection)

Vignette:
  Intensity: 0.3          # Borda escura, foco central
```

---

## 3. Sky Atmosphere + Time-of-Day

```cpp
// Configurar ciclo dia/noite via timeline:
// Altitude do sol em graus: 90° = meio-dia, 0° = nascer/pôr, -90° = meia-noite

UPROPERTY(EditAnywhere, BlueprintReadWrite)
float TimeOfDay = 14.0f; // 14h = luz de tarde, boa para combate

void ATimeOfDayManager::UpdateSunPosition()
{
    const float SunAngle = (TimeOfDay / 24.0f) * 360.0f - 90.0f;
    SunLight->SetRelativeRotation(FRotator(SunAngle, 0.0f, 0.0f));
    // SkyAtmosphere atualiza automaticamente via DirectionalLight
}
```

---

## 4. Fog Volumétrico para Altitude

```ini
# Exponential Height Fog — simula camada de neblina em baixa altitude:
FogDensity: 0.02
FogHeightFalloff: 0.2    # Fog diminui rapidamente com altitude
FogStartDistance: 5000   # Começa a 5km de distância
Volumetric: enabled
VolumetricScatteringIntensity: 1.0
```
````

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/skills/game-visual-design/SKILL.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-visual-design skill (T155/TA09)"
```

---

## Task 12: Skill — `game-geospatial-pipeline`

**Files:**
- Create: `dadaia_workspace/public/skills/game-geospatial-pipeline/SKILL.md`
- Modify: task markers (T156/TA10)

- [ ] **Step 1: Mark T156/TA10 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/skills/game-geospatial-pipeline/SKILL.md`**

````markdown
---
name: game-geospatial-pipeline
description: >
  Pipeline completo de dados geoespaciais para UE5: QGIS → GDAL/PDAL →
  RealityScan/Metashape → Cesium ion → Cesium for Unreal → UE5 Landscape.
  Estratégia de fidelidade em 3 escalas: regional, urbana e landmark.
applyTo: "repos/redacted-slug/redacted-slug-v2/**"
---

# game-geospatial-pipeline

Pipeline de ponta a ponta para mapas realistas baseados em dados geoespaciais.

---

## 1. Estratégia de Fidelidade em 3 Escalas

| Escala | Método | Ferramenta | Fidelidade |
|---|---|---|---|
| Regional (>10km) | DEM heightfield + ortofoto | USGS/NASA → GDAL → UE5 Landscape | Macro relevo, vales, rios |
| Urbana (500m–10km) | 3D Tiles streamados | RealityScan → Cesium ion → Cesium for Unreal | Edificações, infraestrutura |
| Landmark (<500m) | Mesh local Nanite | RealityScan/Metashape → Nanite | Aeroporto, torre, base |

---

## 2. QGIS — Preparação e Validação

```bash
# Reprojetar DEM para UTM (necessário para importar no UE5):
# No QGIS Processing → Reproject Layer
# Source CRS: EPSG:4326 (WGS84)
# Target CRS: EPSG:32723 (UTM Zone 23S para Brasil)

# Inspecionar raster antes de exportar:
# Layer → Layer Properties → Information
# Verificar: CRS correto, nodata = -9999, unidade em metros
```

---

## 3. GDAL — Comandos Essenciais

```bash
# Reprojetar + recortar por bounding box:
gdalwarp -t_srs EPSG:32723 \
         -te xmin ymin xmax ymax \
         -r bilinear \
         input_dem.tif output_dem_utm.tif

# Normalizar para heightmap 16-bit PNG (UE5 usa R16):
gdal_translate -ot UInt16 -scale \
               output_dem_utm.tif heightmap_r16.png

# Verificar estatísticas:
gdalinfo -stats heightmap_r16.png
```

---

## 4. Cesium for Unreal — Setup

```
1. Instalar plugin Cesium for Unreal via Epic Games Marketplace
2. Criar conta Cesium ion (cesium.com/ion)
3. No UE5: Cesium panel → Sign In → conectar token
4. Add Cesium World Terrain (tile global de terreno)
5. Add Bing Maps Aerial imagery (ortofoto global)
6. Georeference Origin: definir lat/lon/alt do ponto central do mapa
```

```cpp
// Georreferenciamento no UE5:
ACesiumGeoreference* GeoRef = ACesiumGeoreference::GetDefaultGeoreference(GetWorld());
GeoRef->SetOriginLongitude(-46.6333);  // São Paulo como exemplo
GeoRef->SetOriginLatitude(-23.5505);
GeoRef->SetOriginHeight(800.0);        // Altitude em metros
```

---

## 5. Importar Heightmap no UE5 Landscape

```
1. Landscape tool → Import from File
2. Format: R16 (16-bit unsigned)
3. Scale Z: (max_altitude - min_altitude) * 100 / 512 cm
   Ex: (3000m - 0m) * 100 / 512 = 585.9 → usar 600
4. Após import: Landscape → Material → atribuir LandscapeMaterial com layers
```

---

## 6. Legal e Licenças

| Fonte | Licença | Obrigação |
|---|---|---|
| USGS EarthExplorer | Domínio público (dados federais EUA) | Atribuição recomendada |
| NASA EarthData / SRTM | Domínio público | Citar como "NASA SRTM data" |
| OpenStreetMap | ODbL | Atribuição obrigatória: "© OpenStreetMap contributors" |
| OpenTopography | CC-BY 4.0 (maioria) | Atribuição obrigatória por dataset |

**Proibições absolutas:**
- Não usar Google Maps, Google Earth ou Street View
- Não redistribuir dados com licença restritiva sem permissão
- Sempre registrar fonte e licença no design report
````

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/skills/game-geospatial-pipeline/SKILL.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-geospatial-pipeline skill (T156/TA10)"
```

---

## Task 13: Skill — `game-audio-design`

**Files:**
- Create: `dadaia_workspace/public/skills/game-audio-design/SKILL.md`
- Modify: task markers (T157/TA11)

- [ ] **Step 1: Mark T157/TA11 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/skills/game-audio-design/SKILL.md`**

````markdown
---
name: game-audio-design
description: >
  MetaSounds UE5, Attenuation Shapes, Reverb Submix. Sound design para combate aéreo:
  turbinas, afterburner, Doppler shift, explosões, cockpit. Fontes públicas seguras:
  Freesound.org (CC0/CC-BY), ZapSplat free tier.
applyTo: "repos/redacted-slug/**"
---

# game-audio-design

Referência de áudio para jogos. Carregue ao implementar sistema sonoro.

---

## 1. MetaSounds — Estrutura Básica

```
MetaSound Source Asset
  ├── Inputs: Throttle (float 0..1), IsAfterburner (bool), Velocity (float)
  ├── Nodes:
  │     ├── Wave Player: turbine_idle.wav (loop)
  │     ├── Pitch Shift: +Throttle * 12 semitones
  │     ├── Volume Envelope: Throttle * 0.8
  │     └── [If IsAfterburner] Additive Layer: afterburner_roar.wav
  └── Output: Mono/Stereo mix
```

---

## 2. Attenuation — Aeronave em Combate

```ini
# Sound Attenuation Asset para aeronaves:
AttenuationShape: Sphere
AttenuationShapeExtents: 5000.0    # Raio de 50m em UE units (1 UU = 1 cm)
FalloffDistance: 15000.0           # Fade out até 200m
SpatializationAlgorithm: HRTF     # Áudio 3D com Head-Related Transfer Function
OcclusionEnabled: true
DopplerIntensity: 0.8              # Efeito Doppler moderado (não exagerado)
```

---

## 3. Specs de Som para redacted-slug-v2

| Som | Técnica | Característica |
|---|---|---|
| Turbina idle | Loop + pitch shift por throttle | Frequência: 800–2400 Hz |
| Afterburner | Layer aditiva + reverb hall | Burst de 150–300 Hz + harmônicos |
| Vento relativo | Noise filtrado por velocidade | Aumenta quadraticamente com speed |
| Explosão | ADSR: attack 2ms, decay 800ms | Layered: bass boom + crackle + debris |
| Cockpit ambience | Loop de baixa amplitude | Frequências < 200 Hz |
| Lock-on warning | Beep repetido + reverb cabin | 1200 Hz, 200ms on/off |

---

## 4. Fontes de Áudio Públicas

| Fonte | Licença | Como usar |
|---|---|---|
| freesound.org | CC0 / CC-BY (por arquivo) | Verificar licença individual antes de baixar |
| zapsplat.com (free tier) | ZapSplat License | Crédito em documentação interna |
| BBC Sound Effects Library | BBC RemArc License | Verificar se uso em jogo é permitido por categoria |

**Workflow:**
```
1. WebSearch freesound.org "jet engine turbine loop"
2. Filtrar: License = CC0 (sem atribuição)
3. Baixar → processar no Audacity (normalizar, loop seamless)
4. Importar no UE5 como Sound Wave asset
5. Registrar fonte e licença no design report
```
````

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/skills/game-audio-design/SKILL.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-audio-design skill (T157/TA11)"
```

---

## Task 14: Skill — `game-testing-ue5`

**Files:**
- Create: `dadaia_workspace/public/skills/game-testing-ue5/SKILL.md`
- Modify: task markers (T158/TA12)

- [ ] **Step 1: Mark T158/TA12 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/skills/game-testing-ue5/SKILL.md`**

````markdown
---
name: game-testing-ue5
description: >
  UE5 Functional Testing Framework, Gauntlet Automation, PIE screenshots, severity matrix
  e report HTML com evidências. Protocolo de pesquisa de bugs conhecidos antes de cada
  sessão de testes.
applyTo: "repos/redacted-slug/redacted-slug-v2/**"
trusted_sources:
  - dev.epicgames.com
  - forums.unrealengine.com
  - issues.unrealengine.com
  - github.com
  - reddit.com/r/unrealengine
---

# game-testing-ue5

Referência para o game-tester. Carregue ao definir acceptance criteria ou executar
uma sessão de testes em redacted-slug-v2.

---

## 1. Protocolo Pré-Sessão (obrigatório)

Antes de qualquer sessão de testes:

```
1. WebSearch issues.unrealengine.com "UE5 <versão alvo> known issues"
2. WebSearch forums.unrealengine.com "<sistema testado> bug <versão>"
3. Registrar bugs conhecidos relevantes no report antes de testar
4. Isso evita reportar bugs da engine como bugs do jogo
```

---

## 2. UE5 Functional Testing Framework

### Setup básico

```cpp
// Criar FunctionalTest actor no level de teste:
// 1. Place Actor → FunctionalTest
// 2. Subclassificar em Blueprint ou C++

UCLASS()
class AFlight_Test_BasicControls : public AFunctionalTest
{
    GENERATED_BODY()

protected:
    virtual void PrepareTest() override
    {
        // Spawnar aeronave em posição conhecida
        FVector SpawnLoc(0, 0, 5000);  // 50m de altitude
        TestAircraft = GetWorld()->SpawnActor<APlayerAircraft>(SpawnLoc, FRotator::ZeroRotator);
    }

    virtual void StartTest() override
    {
        // Simular input de throttle completo por 5 segundos
        TestAircraft->SetThrottleInput(1.0f);
        SetTimer(5.0f);
    }

    void OnTimer()
    {
        // Verificar: velocidade deve ser > 200 knots após 5s com throttle máximo
        const float SpeedKnots = TestAircraft->GetAirspeed() * 0.000539957f;
        AssertTrue(SpeedKnots > 200.0f,
            FString::Printf(TEXT("Airspeed %f kts after 5s throttle"), SpeedKnots));
        FinishTest(EFunctionalTestResult::Succeeded, TEXT("Speed OK"));
    }
};
```

### Rodar via CLI

```bash
# Headless — sem abrir editor:
UnrealEditor-Cmd.exe "AeroFightersV2.uproject" \
  -ExecCmds="Automation RunTests Flight.BasicControls" \
  -Unattended -NullRHI -Log \
  -ReportOutputPath="TestResults/"
```

---

## 3. PIE Screenshot — Evidência Automatizada

```cpp
// No FunctionalTest, antes de AssertTrue:
void CaptureEvidence(const FString& TestName)
{
    const FString ScreenshotName = FString::Printf(
        TEXT("%s_%s"),
        *TestName,
        *FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"))
    );
    FScreenshotRequest::RequestScreenshot(ScreenshotName, false, false);
}
```

```bash
# Screenshots salvos em:
# <project>/Saved/Screenshots/WindowsEditor/
```

---

## 4. Formato do Quality Report

```html
<!-- Template obrigatório para quality report HTML -->
<!DOCTYPE html>
<html>
<head><title>Quality Report — {game} — {feature}</title></head>
<body>
<h1>Quality Report</h1>
<p><strong>Jogo:</strong> {game} | <strong>Feature:</strong> {feature}</p>
<p><strong>UE5 Version:</strong> {version} | <strong>Data:</strong> {date}</p>
<p><strong>Resultado:</strong> PASS / FAIL</p>

<h2>Sumário por Severity</h2>
<table>
  <tr><th>Severity</th><th>Total</th><th>Open</th></tr>
  <tr><td>Critical</td><td>{n}</td><td>{n}</td></tr>
  <tr><td>High</td><td>{n}</td><td>{n}</td></tr>
  <tr><td>Medium</td><td>{n}</td><td>{n}</td></tr>
  <tr><td>Low</td><td>{n}</td><td>{n}</td></tr>
</table>

<h2>Bugs Encontrados</h2>
<!-- Por cada bug: -->
<h3>BUG-{n}: {título} [{severity}] [{sub-domínio: lógica|design}]</h3>
<p><strong>Reproduced:</strong> {steps}</p>
<p><strong>Expected:</strong> {behavior}</p>
<p><strong>Actual:</strong> {behavior}</p>
<img src="{screenshot_path}" alt="Evidence screenshot"/>
<p><strong>Direcionar para:</strong> game-developer | game-designer</p>

<h2>Bugs Conhecidos da Engine (não contar como bugs do jogo)</h2>
<!-- Registrar bugs encontrados no protocolo pré-sessão -->
</body>
</html>
```

---

## 5. Severity Matrix

| Nível | Critério | Bloqueia deploy? |
|---|---|---|
| Critical | Crash, corrupção de dados, jogo inicia mas não fecha | Sim — sempre |
| High | Feature core quebrada sem workaround | Sim |
| Medium | Feature degradada, workaround disponível | Não (registrar como debt) |
| Low | Cosmético, não afeta gameplay | Não |

**Regra:** task só pode ser marcada `[x]` DONE se não houver bugs Critical ou High abertos.
````

- [ ] **Step 3: Commit**

```bash
git add dadaia_workspace/public/skills/game-testing-ue5/SKILL.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-testing-ue5 skill (T158/TA12)"
```

---

## Task 15: Workflow — `game-spec-definition`

**Files:**
- Create: `dadaia_workspace/public/workflows/game-spec-definition.workflow.md`
- Modify: task markers (T159/TA13)

- [ ] **Step 1: Mark T159/TA13 IN PROGRESS and commit**

- [ ] **Step 2: Create the workflow file**

Create `dadaia_workspace/public/workflows/game-spec-definition.workflow.md`:

```yaml
---
name: game-spec-definition
description: >
  Discovery → 5-way parallel specialist analysis (arch + devops + game-developer +
  game-designer + game-tester) → synthesis. Replaces spec-refinement for game contexts.
  Optional web specialists (backend-engineer + frontend-engineer) via include_web_specialists=true.
version: 0.1.0
schema_version: "1"
when_to_use: "Active context is a game project (redacted-slug). For all other contexts, use spec-refinement."
inputs:
  context:
    type: string
    required: true
    description: Active spec context name (must be a redacted-slug context).
  topic:
    type: string
    required: false
    default: "next-game-feature"
    description: Free-form topic label (e.g. redacted-slug-v2).
  include_web_specialists:
    type: boolean
    required: false
    default: false
    description: When true, adds backend-engineer and frontend-engineer to the parallel analysis group.
stages:
  - id: discovery
    agent: product-engineer
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-game-discovery.html"
      must_include: ["Findings", "Decisões necessárias", "Acceptance Criteria Draft"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.topic"
        as: topic
    gate:
      kind: operator-approval
      prompt: "Approve game discovery report before triggering parallel analysis?"

  - id: arch_review
    agent: software-architect
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-game-arch.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: devops_review
    agent: devops-engineer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/devops-engineer/{run_ts}-game-devops.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: gameplay_analysis
    agent: game-developer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/game-developer/{run_ts}-gameplay-analysis.html"
      must_include: ["Mechanic Viability", "JSBSim Feasibility"]
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: design_analysis
    agent: game-designer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/game-designer/{run_ts}-design-analysis.html"
      must_include: ["Map Feasibility", "Asset Pipeline", "Research Findings"]
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: qa_criteria
    agent: game-tester
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-acceptance-criteria.html"
      must_include: ["Acceptance Criteria", "Known UE5 Risks"]
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: synthesis
    agent: product-engineer
    needs: [arch_review, devops_review, gameplay_analysis, design_analysis, qa_criteria]
    expected_output:
      path: "specs/features/{topic}/SPEC.md"
      must_include: ["Status", "Critérios de Aceite"]
    inputs:
      - kind: stage_output
        from: stages.arch_review.output
        as: arch_report
      - kind: stage_output
        from: stages.devops_review.output
        as: devops_report
      - kind: stage_output
        from: stages.gameplay_analysis.output
        as: gameplay_report
      - kind: stage_output
        from: stages.design_analysis.output
        as: design_report
      - kind: stage_output
        from: stages.qa_criteria.output
        as: qa_report
    gate:
      kind: operator-approval
      prompt: "Approve the synthesized GAME SPEC before promoting it to 'Em revisão'?"

exit_criteria:
  - all_stages: completed
---

# game-spec-definition

Workflow de definição de spec exclusivo para projetos de jogo. Substitui `spec-refinement`
quando o contexto ativo é `redacted-slug` ou outro projeto de jogo.

Os 5 especialistas paralelos substituem os especialistas genéricos do spec-refinement:
`game-developer` (viabilidade de mecânicas), `game-designer` (pipeline de assets e mapas),
e `game-tester` (acceptance criteria e riscos UE5 conhecidos) substituem `qa-engineer`,
`frontend-engineer` e `backend-engineer`.

Para jogos com componentes de backend (leaderboard, matchmaking, EOS), use
`include_web_specialists=true` para adicionar `backend-engineer` e `frontend-engineer`
ao grupo paralelo de especialistas.

**Coordenação:** todos os agentes seguem o Decision Authority Matrix definido em
`game-agents-coordination.md`. Divergências são resolvidas via `product-engineer`;
conflitos não resolvidos disparam `dadaia-grill-me` com o operador.
```

- [ ] **Step 3: Validate schema**

```bash
cd /home/marco/workspace/dadaia/repos/dadaia-workspace
dadaia public stage
# Expected: no schema validation errors for game-spec-definition
```

- [ ] **Step 4: Commit**

```bash
git add dadaia_workspace/public/workflows/game-spec-definition.workflow.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-spec-definition workflow (T159/TA13)"
```

---

## Task 16: Workflow — `game-dev-cycle`

**Files:**
- Create: `dadaia_workspace/public/workflows/game-dev-cycle.workflow.md`
- Modify: task markers (T160/TA14)

- [ ] **Step 1: Mark T160/TA14 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/workflows/game-dev-cycle.workflow.md`**

```yaml
---
name: game-dev-cycle
description: >
  Ciclo de implementação exclusivo para games: game-tester define acceptance criteria →
  game-designer implementa assets estáticos → game-developer implementa lógica →
  game-tester valida com UE5 Automation + PIE screenshots.
version: 0.1.0
schema_version: "1"
when_to_use: "SPEC.md com Status: Aprovado + task OPEN em TASKS.md de projeto redacted-slug."
inputs:
  context:
    type: string
    required: true
    description: Active spec context (redacted-slug project).
  task_id:
    type: string
    required: true
    description: Approved task identifier from TASKS.md (e.g. T001).
  game:
    type: string
    required: true
    description: Game directory name (e.g. redacted-slug-v2).
stages:
  - id: acceptance_criteria
    agent: game-tester
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-{task_id}-criteria.html"
      must_include: ["Test Scenarios", "Expected Behaviors", "Acceptance Criteria"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id
    gate:
      kind: operator-approval
      prompt: "Approve acceptance criteria and test scenarios before implementation starts?"

  - id: design_impl
    agent: game-designer
    needs: [acceptance_criteria]
    expected_output:
      path: ".dadaia/reports/{context}/game-designer/{run_ts}-{task_id}-design.html"
      must_include: ["Assets Implemented", "Design Decisions"]
    inputs:
      - kind: stage_output
        from: stages.acceptance_criteria.output
        as: criteria_report
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id
    gate:
      kind: operator-approval
      prompt: "Approve static assets before logic implementation starts?"

  - id: logic_impl
    agent: game-developer
    needs: [design_impl]
    expected_output:
      path: ".dadaia/reports/{context}/game-developer/{run_ts}-{task_id}-impl.html"
      must_include: ["Implementation Complete", "Tests Pass"]
    inputs:
      - kind: stage_output
        from: stages.design_impl.output
        as: design_report
      - kind: stage_output
        from: stages.acceptance_criteria.output
        as: criteria_report
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id
    gate:
      kind: operator-approval
      prompt: "Approve logic implementation before validation?"

  - id: validation
    agent: game-tester
    needs: [logic_impl]
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-{task_id}-quality.html"
      must_include: ["Quality Report", "Severity", "PIE Screenshots"]
    inputs:
      - kind: stage_output
        from: stages.logic_impl.output
        as: impl_report
      - kind: stage_output
        from: stages.acceptance_criteria.output
        as: criteria_report
    gate:
      kind: operator-approval
      prompt: "Approve quality report? (No Critical/High bugs = PASS)"

exit_criteria:
  - all_stages: completed
---

# game-dev-cycle

Ciclo de implementação exclusivo para games com 3 agentes especializados.

O `game-tester` abre e fecha o ciclo: define critérios antes da implementação
e valida com UE5 Automation + PIE screenshots depois.

**Em caso de falha na validação:**
- Bugs de design → game-designer corrige → re-validation
- Bugs de lógica → game-developer corrige → re-validation
- O game-tester classifica e direciona cada bug para o agente correto.

**Coordenação:** seguir o Decision Authority Matrix de `game-agents-coordination.md`.
```

- [ ] **Step 3: Validate and commit**

```bash
dadaia public stage
git add dadaia_workspace/public/workflows/game-dev-cycle.workflow.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-dev-cycle workflow (T160/TA14)"
```

---

## Task 17: Workflow — `game-bugfix`

**Files:**
- Create: `dadaia_workspace/public/workflows/game-bugfix.workflow.md`
- Modify: task markers (T161/TA15)

- [ ] **Step 1: Mark T161/TA15 IN PROGRESS and commit**

- [ ] **Step 2: Create `dadaia_workspace/public/workflows/game-bugfix.workflow.md`**

```yaml
---
name: game-bugfix
description: >
  Fast-track para bugs reportados por usuário não capturados pelo game-tester.
  game-tester reproduz e classifica → game-developer ou game-designer corrige →
  game-tester valida regressão.
version: 0.1.0
schema_version: "1"
when_to_use: "Bug reportado por usuário em produção não identificado pelo game-tester."
inputs:
  context:
    type: string
    required: true
    description: Active spec context (redacted-slug project).
  bug_description:
    type: string
    required: true
    description: Description of the reported bug with reproduction steps if available.
  game:
    type: string
    required: true
    description: Game directory name (e.g. redacted-slug-v2).
stages:
  - id: reproduce
    agent: game-tester
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-bug-reproduce.html"
      must_include: ["Bug Classification", "Evidence", "Reproduction Steps"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.bug_description"
        as: bug_description
    gate:
      kind: operator-approval
      prompt: "Confirm reproduction and bug classification before fix?"

  - id: fix_logic
    agent: game-developer
    needs: [reproduce]
    on_failure: skip
    expected_output:
      path: ".dadaia/reports/{context}/game-developer/{run_ts}-bug-fix.html"
      must_include: ["Fix Applied", "Tests Updated"]
    inputs:
      - kind: stage_output
        from: stages.reproduce.output
        as: bug_report
    gate:
      kind: operator-approval
      prompt: "Approve logic fix before regression testing?"

  - id: fix_design
    agent: game-designer
    needs: [reproduce]
    on_failure: skip
    expected_output:
      path: ".dadaia/reports/{context}/game-designer/{run_ts}-bug-fix.html"
      must_include: ["Fix Applied", "Asset Updated"]
    inputs:
      - kind: stage_output
        from: stages.reproduce.output
        as: bug_report
    gate:
      kind: operator-approval
      prompt: "Approve design fix before regression testing?"

  - id: regression
    agent: game-tester
    needs: [fix_logic, fix_design]
    expected_output:
      path: ".dadaia/reports/{context}/game-tester/{run_ts}-bug-regression.html"
      must_include: ["Regression Result", "Test Suite Updated"]
    inputs:
      - kind: stage_output
        from: stages.reproduce.output
        as: original_bug
    gate:
      kind: operator-approval
      prompt: "Approve regression report and close bug?"

exit_criteria:
  - all_stages: completed
---

# game-bugfix

Fast-track para bugs reportados por usuários não identificados pelo game-tester.

O game-tester classifica o bug (lógica vs design) no estágio `reproduce`.
Os estágios `fix_logic` e `fix_design` são mutuamente exclusivos — apenas o relevante
é executado (via `on_failure: skip` no outro).

O `regression` stage final garante que o fix não introduziu regressão e que o
test suite foi atualizado para prevenir recorrência.
```

- [ ] **Step 3: Validate and commit**

```bash
dadaia public stage
git add dadaia_workspace/public/workflows/game-bugfix.workflow.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): add game-bugfix workflow (T161/TA15)"
```

---

## Task 18: Workflow — Update `tdd-cycle`

**Files:**
- Modify: `dadaia_workspace/public/workflows/tdd-cycle.workflow.md`
- Modify: task markers (T163/TA16)

- [ ] **Step 1: Mark T163/TA16 IN PROGRESS and commit**

- [ ] **Step 2: Update tdd-cycle.workflow.md**

In `dadaia_workspace/public/workflows/tdd-cycle.workflow.md`, update two places:

**Frontmatter description:**
```yaml
description: implementer ↔ qa-engineer alternating red-green-refactor with optional product consult. The implementer is parameterized — pass implementer_agent=frontend-engineer | backend-engineer | software-engineer. Game agents use game-dev-cycle instead.
```

**`implementer_agent` input default and description:**
```yaml
  implementer_agent:
    type: string
    required: false
    default: software-engineer
    description: Which engineer runs green_impl and refactor. One of frontend-engineer, backend-engineer, software-engineer. NOTE: game-developer, game-designer, game-tester use game-dev-cycle workflow instead.
```

- [ ] **Step 3: Validate and commit**

```bash
dadaia public stage
git add dadaia_workspace/public/workflows/tdd-cycle.workflow.md \
        specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "feat(game-agents-split): update tdd-cycle, remove game-developer from implementer (T163/TA16)"
```

---

## Task 19: Propagation

**Files:** all projected files in `.claude/`, `.agents/`, `.codex/`, `.opencode/`
- Modify: task markers (T164, T165/TA17, TA18)

- [ ] **Step 1: Mark T164/TA17 IN PROGRESS and commit**

- [ ] **Step 2: Run stage + install**

```bash
cd /home/marco/workspace/dadaia/repos/dadaia-workspace
dadaia public stage
dadaia public install --target all
```

Expected: no errors. New entries appear in `.dadaia/agentic/manifest.json`.

- [ ] **Step 3: Run doctor**

```bash
dadaia public doctor
```

Expected output — all entries must show `[ok]`:
```
[ok] agents/game-developer
[ok] agents/game-designer
[ok] agents/game-tester
[ok] skills/game-unreal-developer
[ok] skills/game-flight-dynamics
[ok] skills/game-unreal-designer
[ok] skills/game-visual-design
[ok] skills/game-geospatial-pipeline
[ok] skills/game-audio-design
[ok] skills/game-testing-ue5
[ok] rules/game-agents-coordination
[ok] rules/game-developer-scope
[ok] workflows/game-spec-definition
[ok] workflows/game-dev-cycle
[ok] workflows/game-bugfix
[ok] workflows/tdd-cycle
```

If any entry shows `[drift]` or `[missing]`, run:
```bash
dadaia public install --target all --force
dadaia public doctor
```

- [ ] **Step 4: Final commit**

```bash
# Update markers
git add specs/TASKS.md specs/features/game-agents-split/TASKS.md
git commit -m "chore(game-agents-split): propagation complete — all entries [ok] (T164/T165)"
```

---

## Verification Checklist

After Task 19 completes, verify end-to-end:

- [ ] `dadaia public doctor` → all game-related entries `[ok]`
- [ ] Open Claude Code → `@game-designer` agent is available
- [ ] Open Claude Code → `@game-tester` agent is available
- [ ] `@game-designer` loads `game-unreal-designer` skill correctly
- [ ] `@game-tester` loads `game-testing-ue5` skill correctly
- [ ] `@game-developer` no longer lists `game-map-architect` in skills table
- [ ] `game-agents-coordination` rule is active (visible in `.claude/rules/`)
- [ ] `game-spec-definition` workflow is visible in `.claude/workflows/`
- [ ] `game-dev-cycle` workflow is visible in `.claude/workflows/`
- [ ] `tdd-cycle` description no longer mentions `game-developer` as implementer option
