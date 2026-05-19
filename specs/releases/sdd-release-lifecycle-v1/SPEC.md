# Spec: Release — sdd-release-lifecycle-v1

> **Status:** Aprovado
> **Release ID:** sdd-release-lifecycle-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Source SPEC:** `specs/features/sdd-release-lifecycle/SPEC.md` (Draft → consumido por esta release; será arquivado na Fase 6)

---

## Objetivo

Implantar o novo modelo SDD release-based no Spec Context Project `dadaia-workspace` e
auto-validar o padrão executando a própria implantação como a primeira release sob o novo
padrão. Esta é uma release **dogfood**: se o modelo não consegue suportar sua própria
execução, o modelo está errado.

Esta release cobre as **Fases 0–6** do plano dogfood. Fases 7–9 (outros repos +
re-projeções + CLOSURE da meta-release) ficam para release subsequente.

---

## Contexto

A feature `sdd-release-lifecycle` (Draft em `specs/features/sdd-release-lifecycle/SPEC.md`)
define a estrutura canônica: `specs/memory/{product,architecture,tech-stack}` como fonte
atômica, `specs/releases/<id>/` para work-in-flight, `specs/_archive/releases/` para
histórico, e um ciclo de 8 fases (Discovery → SPEC → PLAN → TASKS → Implementation →
Closure → Memory Update → Archive).

Esta release executa essa definição **+ uma extensão crítica**: memory deixa de ser
markdown e passa a ser HTML rico (Mermaid + screenshots), porque o memory descreve a
visão total do produto/projeto e exige formato adequado para ser legível por humanos e
agentes. Demais artefatos (SPEC, PLAN, TASKS, CLOSURE, constitution, backlog) permanecem
em markdown.

---

## Decisões fixadas (esta release)

Estas decisões fecham as 4 questões abertas da feature fonte mais 9 decisões adicionais
sobre formato e execução. São contrato desta release — qualquer alteração exige nova
release.

| ID | Tema | Decisão |
|----|------|---------|
| D1 | Review referenciado | É o próprio SPEC.md de `sdd-release-lifecycle` — não há report separado |
| D2 | Escopo de migração big-bang | Big-bang em rondas. Esta release cobre dadaia-workspace. Outros repos em release seguinte |
| D3 | Sinalização de release ativa | `specs/releases/ACTIVE.md` com duas linhas: `release: <id>` e `phase: <DISCOVERY\|SPEC\|PLAN\|TASKS\|IMPLEMENTATION\|CLOSURE\|ARCHIVED>` |
| D4 | Meta-release dogfood | `sdd-release-lifecycle-v1` em `specs/releases/sdd-release-lifecycle-v1/` |
| D5 | Limite PLAN.md 300 linhas | Warning no doctor para releases existentes; hard error para releases com `Created: >= 2026-05-17` |
| D6 | CLOSURE.md exige evidência | Sim. Cada validação é triple `{description, command, evidence}` onde evidence é SHA, stdout snippet ou path de report |
| D7 | Formato de drifts em CLOSURE | Seção `## Drifts`; cada drift é `### <slug>` com campos `Description:` / `Resolution:` / `Memory updates:` |
| D8 | Atomicidade do memory | Gate v3 bloqueia edit em `specs/memory/*.html` e `*.md` exceto quando `ACTIVE.md` phase = `CLOSURE` |
| D9 | Compat legacy | Env var `SDD_LEGACY_FEATURES=1` durante esta release; flip para `0` ao concluir Phase 6 |
| D10 | CLI doctor | Python real (módulo + pytest), não bash MVP |
| D11 | Formato de memory | **HTML** (não markdown). Templates fixos em `dadaia_workspace/public/templates/memory-{product,architecture,tech-stack}.html.j2`. Resto dos specs permanece markdown |
| D12 | Diagramas em memory | Mermaid embedded para fluxos/arquitetura + screenshots PNG em `specs/assets/<scope>/<id>.png` referenciados via `<img>`. Doctor valida links quebrados |
| D13 | Autoria HTML | HTML puro com placeholders preenchidos pelo agente. Sem build step. Templates Jinja2 vivem no canonical e são renderizados a cada release que toca memory |

---

## Deltas

### Delta de produto

- `dadaia-workspace` ganha estrutura `specs/releases/`, `specs/backlog/`,
  `specs/_archive/releases/`, `specs/_archive/legacy-features/`, `specs/_archive/legacy-memory/`,
  `specs/assets/`
- 20+ pastas de `specs/features/<name>/` são triadas: implementadas → archive com CLOSURE
  retroativa; drafts sem implementação → backlog/candidates + archive legacy
- Memory HTML novo substitui (e arquiva) memory markdown atual
- Nova release ativa: `sdd-release-lifecycle-v1` ela mesma

### Delta de arquitetura

- Agente `product-engineer` opera por release (8 fases) em vez de feature solta
- Skills `dadaia-workspace-spec-navigator`, `-spec-reviewer`, `dadaia-task-manager` ficam
  release-aware (leem `releases/ACTIVE.md` e `releases/<id>/`)
- Nova skill `dadaia-release-closure` define template e protocolo de CLOSURE
- Novos templates Jinja2 em `dadaia_workspace/public/templates/memory-*.html.j2`
- Gate `.dadaia/scripts/sdd-spec-gate.sh` evolui para v3: bloqueia memory fora de
  CLOSURE; bloqueia `_archive/`; loga release-id

### Delta de tech-stack

- Nenhuma dependência nova obrigatória (Jinja2 já é dependência padrão Python para
  templates; será adicionada se ausente no pyproject)
- Mermaid via CDN `https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js` (sem network
  em build, somente em render no browser do operador)
- pytest continua sendo o test runner do CLI

### Delta de operação

- Hook PreToolUse (gate v3) muda comportamento de bloqueio para incluir memory e archive
- `dadaia public install` continua sendo o único caminho para propagar agentes/skills
  alterados

---

## Arquivos de memory afetados

Esta release atualiza, ao fechar (Phase 6 / CLOSURE), todos os três arquivos canônicos do
dadaia-workspace, agora em HTML:

- `specs/memory/product.html` — visão atual do produto dadaia-workspace
- `specs/memory/architecture.html` — arquitetura corrente (CLI, gate v3, projection chain,
  release lifecycle)
- `specs/memory/tech-stack.html` — Python 3.11+, typer, Jinja2, bash hooks, pytest

Markdown legado (`specs/memory/*.md`), se existir, é movido para
`specs/_archive/legacy-memory/<timestamp>/` antes da escrita HTML.

---

## Critérios de aceite

- [ ] `specs/releases/sdd-release-lifecycle-v1/{SPEC,PLAN,TASKS}.md` existem com Status: Aprovado
- [ ] `specs/releases/ACTIVE.md` existe e aponta para `sdd-release-lifecycle-v1` / phase IMPLEMENTATION
- [ ] Agente `product-engineer` (canonical + projeções) descreve lifecycle de 8 fases por release
- [ ] Skills spec-navigator, spec-reviewer, task-manager são release-aware
- [ ] Nova skill `dadaia-release-closure` existe e descreve CLOSURE.md template
- [ ] Templates Jinja2 `memory-{product,architecture,tech-stack}.html.j2` existem em canonical
- [ ] Gate v3 bloqueia edit em `specs/memory/*.html` exceto em phase CLOSURE
- [ ] Gate v3 bloqueia edit em `specs/_archive/*`
- [ ] `dadaia specs doctor` existe como CLI command e roda os 11 checks
- [ ] Testes pytest cobrem positivos e negativos dos checks do doctor
- [ ] Todas as 23 features de `specs/features/` são triadas; pasta `features/` fica vazia ou só com legacy archives
- [ ] `specs/memory/{product,architecture,tech-stack}.html` existem renderizados a partir dos templates
- [ ] `specs/_archive/releases/<id>/` contém CLOSURE.md para cada feature implementada arquivada
- [ ] `dadaia specs doctor` retorna 0 warnings de legacy paths para dadaia-workspace
- [ ] `dadaia public doctor` retorna `[ok]` em todos os targets

---

## Fora de escopo

- Migração de outros repos (redacted-slug-barbe, redacted-slug-explorer, workflow-tools, redacted-slug,
  redacted-slug-wave6, dadaia-agents, redacted-slug, redacted-slug) — release subsequente
- Re-projeções `--force` em todos os tools (release subsequente após Phase 7)
- CLOSURE.md desta meta-release e `git mv` para `_archive/` — release subsequente
- Implementação de comandos CLI além de `dadaia specs doctor`
- Mudança no comportamento de `dadaia-grill-me` ou outros reports HTML
- Alteração no formato de TASKS markers `[ ]/[-]/[x]` — permanecem markdown
- Resolver backlog funcional de features individuais arquivadas (ex: dev-server-registry
  continua aberto como release futura, mas não é implementado aqui)

---

## Dependências e riscos

| Risco | Mitigação |
|-------|-----------|
| Bootstrap dogfood paradox: usar release-based antes do tooling estar pronto | Phase 1 cria scaffold manual; Phase 2-5 desenvolvem tooling sob o scaffold |
| Gate v3 bloquear edição que antes era permitida | Compat env `SDD_LEGACY_FEATURES=1` durante Phase 6 |
| Migração quebrar busca por TASKS de releases ativas | Gate continua recursivo sobre todo `specs/`; releases novas e features antigas convivem |
| HTML memory inviabilizar edição rápida | Templates fixos + apenas product-engineer escreve em CLOSURE, então edição manual é exceção |
| Doctor flagrar falsos positivos em features legacy | Compat window: legacy = warning até cutoff, error depois |
| `dadaia public install` propagar agente antes de skills estarem prontos | Phase 2 só termina quando skills (Phase 3) também terminam — install rodado uma vez no final |

---

## Referências

- Source SPEC: `specs/features/sdd-release-lifecycle/SPEC.md`
- Constitution: `specs/constitution.md`
- Memory atual: `specs/memory/{product,architecture,tech-stack}.md` (será arquivado)
- Plan dogfood completo: `/home/marco/.claude/plans/devemos-melhorar-o-streamed-snail.md`
- Gate atual: `.dadaia/scripts/sdd-spec-gate.sh` (v2)
- Agente atual: `dadaia_workspace/public/agents/product-engineer.md`
