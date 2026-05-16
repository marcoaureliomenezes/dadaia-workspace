# Spec: Release — agent-sdd-alignment-v1

> **Status:** Aprovado
> **Release ID:** agent-sdd-alignment-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Source SPEC:** none (release nasceu de revisão pós-`sdd-release-lifecycle-v1`)

---

## Objetivo

Fechar o gap cognitivo entre o novo modelo SDD release-based + memory folder catalog (já
implantado em `sdd-release-lifecycle-v1`) e os agentes que **não são** `product-engineer`.
Hoje o gate v3 bloqueia escritas erradas mecanicamente, mas os agentes
`software-architect`, `software-engineer`, `qa-engineer`, `devops-engineer`,
`frontend-engineer` e `backend-engineer` ainda referenciam caminhos legacy
(`specs/memory/architecture.md`, `specs/features/<name>/SPEC.md`,
`specs/features/<name>/TASKS.md`) nos seus workflows. Resultado: ONBOARD/REVIEW silenciosamente
puland leitura de memory; implementadores recebem 0 hits ao procurar `features/<x>/TASKS.md`
e dependem do compat `SDD_LEGACY_FEATURES=1` para qualquer escrita.

Esta release também tampa **dois buracos estruturais** detectados na revisão: `ACTIVE.md`
malformado passa silenciosamente pelo gate (fail-open) e `backlog/candidates.md` não tem
nenhuma validação de schema — risco de virar lixão sem aviso.

---

## Contexto

A meta-release `sdd-release-lifecycle-v1` (`phase: IMPLEMENTATION`, Phase 7 concluída)
implantou:

- `specs/memory/{architecture.html, tech-stack.html, product/index.html + 11 feature HTMLs}`
- `specs/releases/ACTIVE.md` + `specs/releases/<id>/{SPEC,PLAN,TASKS,[CLOSURE]}.md`
- `specs/backlog/{ideas.md, candidates.md}`
- `specs/_archive/{releases,legacy-features,legacy-memory,legacy-root}/`
- Gate v3 (`.dadaia/scripts/sdd-spec-gate.sh`) com bloqueio fase-gated em memory + archive
- `dadaia_workspace/features/specs/doctor.py` com 11 checks estruturais, expostos via
  `dadaia specs doctor` (`dadaia_workspace/cli/commands/specs.py`)

O agente `product-engineer.md` foi reescrito para esse modelo. Os outros 6 agentes
**não foram tocados** e continuam referenciando:

| Agente | Linha | Path legacy referenciado |
|--------|-------|--------------------------|
| software-architect | L89, L158, L258 | `specs/memory/architecture.md`, `architecture.md + foundation/SPEC.md` |
| software-engineer | L109, L144 | `SPEC.md` e `TASKS.md` sem resolver release ativa |
| qa-engineer | L179, L320–322 | `features/<feature>/SPEC.md`, `features/<feature>/TASKS.md`, `memory/architecture.md` |
| devops-engineer | L127, L187, L617, L622 | `specs/features/deploy-pipeline/`, `repos/<slug>/specs/constitution.md` |
| frontend-engineer | L127, L187 | `SPEC.md` e `TASKS.md` sem resolver release ativa |
| backend-engineer | (já limpo na criação) | n/a — verificar |
| game-developer / game-designer | L115, L122, L211–212 | `specs/features/<jogo>/{SPEC,TASKS}.md` — fora de escopo desta release (game-agents-split na backlog) |

Gaps estruturais detectados:

1. `_check_active_md` no doctor exige `release:` e `phase:` mas se ambos estiverem com
   **valor vazio** (ex: `release: ` em uma linha) o split atual aceita string vazia e
   classifica o arquivo como válido — fail-open. Confirmado lendo `_read_active_md`
   linhas 192–200 de `doctor.py`.
2. `backlog/candidates.md` documenta o formato `- <name> — <one-liner> (owner: <agent>, contexto: <link>)`
   mas nenhum check valida que bullets futuros sigam o padrão.
3. Não existe execução automática de `dadaia specs doctor` em CI — toda regressão
   estrutural depende de o operador rodar manualmente.

---

## Decisões fixadas (esta release)

| ID | Tema | Decisão |
|----|------|---------|
| D1 | Escopo de agentes alinhados | Apenas os 6 agentes não-game-engine: software-architect, software-engineer, qa-engineer, devops-engineer, frontend-engineer, backend-engineer. Game agents ficam como release futura (`game-agents-split` já na backlog) |
| D2 | Profundidade da edição em cada agente | **Surgical patch**, não reescrita. Mantém estrutura, voz e seções existentes. Substitui apenas referências de path e adiciona um bloco "Resolving the active release" mirror do `product-engineer.md` quando aplicável |
| D3 | Compat com legacy fora de dadaia-workspace | Manter nota explícita: "Se `releases/ACTIVE.md` não existir, cair em compat legacy `features/<feature>/{SPEC,TASKS}.md` (env `SDD_LEGACY_FEATURES=1`)". Outros repos ainda não migraram |
| D4 | Memory paths para architect | Atualizar referências de `memory/architecture.md` para `memory/architecture.html`; adicionar leitura de `memory/product/index.html` (catálogo) + `memory/tech-stack.html`. **Não** listar todos os feature HTMLs — architect carrega sob demanda |
| D5 | Validação de ACTIVE.md format | Adicionar check estrutural: `release:` value não pode ser empty string nem whitespace puro; `phase:` value idem; ambos devem estar presentes no formato `<key>: <value>` com value não-vazio. Erros usam código `SPEC-DOC-003` (extensão do check 3) |
| D6 | Validação de backlog | Adicionar check estrutural novo (código `SPEC-DOC-012`): `backlog/candidates.md` — toda linha que começa com `- ` (após blank lines, headers `##`, ou seções `## Histórico`) deve casar regex documentado. Headers, blank lines, parágrafos de descrição passam sem aviso |
| D7 | CI hook | Adicionar job novo ao `.github/workflows/ci.yml` chamado `specs-doctor` que instala via Poetry (igual aos demais jobs) e roda `poetry run dadaia specs doctor`. Falha = PR vermelho. Sem pre-commit local nesta release — operador pediu CI primeiro |
| D8 | Stale tasks da release anterior | T-5.2/T-5.3/T-5.4/T-5.5/T-5.6 e T-V.1–T-V.6 do `sdd-release-lifecycle-v1` estão de fato implementadas (CLI existe, 22 tests green, doctor verde). Como `sdd-release-lifecycle-v1` ainda está em IMPLEMENTATION, decisão: **deixar como housekeeping da própria release `sdd-release-lifecycle-v1`**. Esta release não toca o `TASKS.md` daquela. Em vez disso, registramos a observação na seção "Drifts conhecidos" desta SPEC para o operador encerrar quando promover aquela release para CLOSURE |
| D9 | Frontend backend separados? | Sim — patches isolados por agente. backend-engineer já está limpo na criação; verificação grep confirma 0 hits em `specs/features` e `architecture.md` |
| D10 | Skills e workflows legacy-path | Audit revelou 4 skills (`dadaia-task-manager`, `dadaia-release-closure`, `architect-code-audit`, `dadaia-grill-me`) e 4 workflows com refs a `specs/features/<feat>/` ou `specs/memory/*.md` ou `specs/memory/product.html` (singular inexistente). Item E1+E2 incluídos nesta release — surgical patches, mesma política dos agentes |
| D11 | Scaffold portátil para outros repos | Workspace hoje não é replicável a outros repos sem copy-paste manual. Item E3: novo subcomando `dadaia specs init <name>` em `dadaia_workspace/cli/commands/specs.py` + módulo `dadaia_workspace/features/specs/scaffolder.py`. Templates em `public/templates/*.j2` já existem; ganham fallback gracioso para projetos vazios (`{{ project_name }}`, `{{ today }}`, catálogo vazio). ACTIVE.md scaffolda como `release: none / phase: none` — doctor já trata `release: none` (linhas 414/434); precisa adicionar `none` a `CANONICAL_PHASES` |
| D12 | Migration playbook — onde mora | `dadaia_workspace/public/data/` só instala AGENTS.md/reports-AGENTS.md (special-cased); demais arquivos ficam staged mas não propagados. Decisão: gravar o playbook em **`docs/sdd-migration-playbook.md`** (operator-facing, mesmo padrão de `docs/sdd_patterns.md`). Não precisa estar em `public/` — operadores leem do repo dadaia-workspace ao migrar outros repos. Item E4 |
| D13 | `phase: none` é canônico | Atual `CANONICAL_PHASES` rejeita qualquer phase fora das 7 fases SDD. Para suportar repo recém-scaffoldado sem release em andamento, adicionar `"none"` ao set. Pareia com a tratativa existente de `release: none` no doctor |

---

## Deltas

### Delta de agentes

- `software-architect.md` — ONBOARD e REVIEW workflows leem memory HTML correta; ambos os
  modos adicionam leitura de `memory/product/index.html` + `memory/tech-stack.html`.
  Report templates (Architecture Status table) deixam de referenciar `architecture.md`
- `software-engineer.md` — TDD workflow e "Before you start" referenciam
  `specs/releases/<active-release>/{SPEC,TASKS}.md`. Adiciona seção "Resolving the active
  release" mirror do `product-engineer.md`. Compat legacy nota incluída
- `qa-engineer.md` — Spec gate (L315–322) atualizado para release-based; resolve memory
  via HTML; legacy fallback documentado
- `devops-engineer.md` — Workspace Protocol (L608–631) usa release-based paths; exemplo
  "spec conflict" usa caminho de release em vez de `specs/features/deploy-pipeline/`
- `frontend-engineer.md` — mesmo patch que software-engineer
- `backend-engineer.md` — confirmação visual: já está limpo; nada a mudar

### Delta de doctor

- `dadaia_workspace/features/specs/doctor.py`:
  - `_read_active_md` ganha validação de empty value para release e phase
  - Novo método `_check_backlog_schema` (check 12) parse `backlog/candidates.md` e flagra
    bullets que não casam regex documentado
  - `check()` chama o novo método e retorna o resultado

### Delta de tests

- `tests/unit/features/specs/test_doctor.py`:
  - Adicionar 2 testes para ACTIVE.md malformado (empty release, empty phase)
  - Adicionar 3 testes para backlog schema (passing, header skip, malformed bullet)

### Delta de CI

- `.github/workflows/ci.yml` ganha novo job `specs-doctor` (runs-on ubuntu-latest, install
  Poetry como os demais, executa `poetry run dadaia specs doctor` no checkout)

### Delta de constituição/memory

- **Nenhum**. Esta release não muda o produto, só a percepção dos agentes sobre o produto
  já existente. Memory permanece intocado (gate v3 bloquearia mesmo se quiséssemos)

### Delta E1 — Skills com path legacy (4 arquivos, surgical patches)

Cobre `dadaia_workspace/public/skills/` referências divergentes do modelo release-based:

| Skill | Linha aprox. | Patch |
|---|---|---|
| `dadaia-task-manager/SKILL.md` | L32 | "raiz `specs/TASKS.md` ou `specs/features/<feat>/TASKS.md`" → primary `specs/releases/<active>/TASKS.md` (resolver via `ACTIVE.md`); fallback legacy com `SDD_LEGACY_FEATURES=1` |
| `dadaia-release-closure/SKILL.md` | L71 (bullets `Memory updates`) | Substituir `specs/memory/product.html` (file singular, não existe) por catálogo folder: `specs/memory/product/index.html` + per-feature `specs/memory/product/<slug>.html` |
| `architect-code-audit/SKILL.md` | L27 (Phase 0 — Context Loading) | `specs/memory/architecture.md` → `specs/memory/architecture.html` |
| `dadaia-grill-me/SKILL.md` | L196 (tabela "Edições Pendentes") | Exemplo `specs/features/platform/snapshots/SPEC.md` → `specs/releases/<release-id>/SPEC.md` |

### Delta E2 — Workflows com path legacy (4 arquivos)

| Workflow | Linha aprox. | Patch |
|---|---|---|
| `spec-refinement.workflow.md` | L92 + L14 | `path: "specs/features/{topic}/SPEC.md"` → `path: "specs/releases/{release_id}/SPEC.md"`; input `topic` renomeado para `release_id` (descrição: "Release ID under `specs/releases/`") |
| `cross-cutting-feature.workflow.md` | L14 | Renomear input `feature_topic` ou ajustar description para "Release ID under `specs/releases/`" preservando compat com chamadas existentes via alias |
| `architecture-review.workflow.md` | L20 | Description: "When scope=feature, the release id under `specs/releases/`" |
| `game-spec-definition.workflow.md` | L104 | `path: "specs/releases/{release_id}/SPEC.md"` — **path-only patch**. Semântica de game scope (separação de domínio game-agents) permanece tracked na backlog item `game-agents-split`, não nesta release |

### Delta E3 — `dadaia specs init <name>` CLI

- Novo subcomando em `dadaia_workspace/cli/commands/specs.py` no grupo `specs`
- Novo módulo: `dadaia_workspace/features/specs/scaffolder.py` com função pura
  `scaffold(specs_dir: Path, project_name: str, force: bool, templates_dir: Path) -> list[str]`
- Args: `--specs-dir <path>` (default `./specs/`), `--name <project-name>` (default = parent dir name), `--force` (default false)
- Outputs criados (idempotente sem `--force`; se arquivo existe → skip com aviso):
  - `specs/constitution.md` — stub apenas se ausente (conteúdo é operator-owned)
  - `specs/memory/architecture.html` (render de `memory-architecture.html.j2`)
  - `specs/memory/tech-stack.html` (render de `memory-tech-stack.html.j2`)
  - `specs/memory/product/index.html` (render de `memory-product-index.html.j2` com catálogo vazio)
  - `specs/releases/ACTIVE.md` com `release: none\nphase: none`
  - `specs/backlog/candidates.md` (header-only stub)
  - `specs/backlog/ideas.md` (header-only stub)
  - `specs/_archive/releases/.gitkeep`, `specs/_archive/legacy-features/.gitkeep`, `specs/assets/.gitkeep`
- Templates ganham fallback gracioso para projetos vazios: variáveis `{{ project_name }}`,
  `{{ today }}` (ISO date), `{{ last_release_id }}` default "none", catálogo vazio,
  layers vazias, overview placeholder. Verificação visual: render stub para `redacted-slug-barbe`
  e abrir no browser
- Doctor: adicionar `"none"` a `CANONICAL_PHASES` (validação atual rejeitaria `phase: none`).
  Tratamento existente de `release: none` (linhas 414, 434 de doctor.py) permanece — não há
  mudança adicional
- Gate behavior: `release: none` + `phase: none` significa "nada em produção" — gate
  continua bloqueando escritas em `specs/memory/*` e `specs/_archive/*` (fail-safe). Único
  caminho writable é o próprio scaffold scaffolar mais releases. Comportamento confirmado
  pela lógica fase-gated existente
- Tests: `tests/unit/features/specs/test_scaffolder.py` — happy path, idempotência,
  `--force` overwrite, render de templates com placeholders preenchidos

### Delta E4 — Migration playbook

- Novo arquivo: `docs/sdd-migration-playbook.md` (≤ 200 linhas; estilo `docs/sdd_patterns.md`)
- Conteúdo: 6 passos canônicos (preconditions → scaffold → triage → migrar memory →
  ativar ACTIVE → verificar com doctor → ativar context). Referencia
  `sdd-release-lifecycle-v1/SPEC.md` Phase 6 como exemplo trabalhado
- **Localização justificada (D12)**: `public/data/` só propaga AGENTS.md/reports-AGENTS.md;
  outros arquivos lá ficam staged mas não atingem `.agents/`, `.claude/`, `.codex/`,
  `.opencode/`. Playbook é operator-facing (lido manualmente ao migrar um repo), não
  precisa de projeção. `docs/` é o lar natural — mesmo padrão de `docs/sdd_patterns.md`
- Não exige `dadaia public stage/install`; é simples checkin git

---

## Arquivos de memory afetados

Nenhum. Esta release não passa por phase=CLOSURE; ACTIVE.md fica em `phase: TASKS` ao
final desta sessão e progride a partir daí.

---

## Critérios de aceite

- [ ] `specs/releases/agent-sdd-alignment-v1/{SPEC,PLAN,TASKS}.md` existem com `Status: Aprovado`
- [ ] `specs/releases/ACTIVE.md` aponta para `agent-sdd-alignment-v1` (phase=TASKS ao final desta sessão)
- [ ] `dadaia_workspace/public/agents/software-architect.md` ONBOARD workflow lê `memory/architecture.html`, `memory/product/index.html`, `memory/tech-stack.html` (não mais `.md`)
- [ ] `dadaia_workspace/public/agents/software-architect.md` REVIEW workflow idem
- [ ] `dadaia_workspace/public/agents/{software,frontend}-engineer.md` workflows referenciam `specs/releases/<active>/{SPEC,TASKS}.md` com bloco "Resolving the active release"
- [ ] `dadaia_workspace/public/agents/qa-engineer.md` spec gate atualizado para release-based
- [ ] `dadaia_workspace/public/agents/devops-engineer.md` Workspace Protocol atualizado para release-based
- [ ] `dadaia_workspace/public/agents/backend-engineer.md` confirmado limpo (sem patches necessários)
- [ ] `dadaia_workspace/features/specs/doctor.py` valida ACTIVE.md com valores não-vazios
- [ ] `dadaia_workspace/features/specs/doctor.py` valida backlog schema (novo check SPEC-DOC-012)
- [ ] `tests/unit/features/specs/test_doctor.py` tem pelo menos um teste positivo e um negativo para ACTIVE.md empty values + backlog schema
- [ ] `pytest tests/unit/features/specs/test_doctor.py` → green
- [ ] `dadaia specs doctor` no próprio workspace → 0 errors (warnings legacy aceitáveis)
- [ ] `.github/workflows/ci.yml` tem job `specs-doctor` chamando `poetry run dadaia specs doctor`
- [ ] `dadaia public stage && dadaia public install --target all` propagam mudanças sem drift
- [ ] `dadaia public doctor` retorna `[ok]` em todos os targets
- [ ] **E1** — 4 skills patchadas: `dadaia-task-manager`, `dadaia-release-closure`,
      `architect-code-audit`, `dadaia-grill-me`. Greps: `grep -n "features/<feat>/TASKS.md\|memory/product\.html\b\|memory/architecture\.md\|features/platform/snapshots" dadaia_workspace/public/skills/{dadaia-task-manager,dadaia-release-closure,architect-code-audit,dadaia-grill-me}/SKILL.md` → 0 hits fora de blocos "Legacy compat"
- [ ] **E2** — 4 workflows patchados: `spec-refinement`, `cross-cutting-feature`,
      `architecture-review`, `game-spec-definition`. Grep `path: "specs/features/{` em
      `dadaia_workspace/public/workflows/*.workflow.md` → 0 hits
- [ ] **E3** — `dadaia specs init <name>` existe e é idempotente. Comando teste:
      `dadaia specs init --specs-dir /tmp/sdd-init-smoke --name smoke` cria toda a árvore
      esperada; segunda execução não força overwrite. `dadaia specs doctor --specs-dir /tmp/sdd-init-smoke` → 0 errors
- [ ] **E3** — `CANONICAL_PHASES` em `doctor.py` inclui `"none"`
- [ ] **E3** — `tests/unit/features/specs/test_scaffolder.py` 3+ testes verdes (happy path,
      idempotency, --force)
- [ ] **E3** — Templates `public/templates/memory-*.html.j2` aceitam render para projeto
      vazio sem erro Jinja2 (placeholders preenchidos com defaults)
- [ ] **E4** — `docs/sdd-migration-playbook.md` existe, ≤ 200 linhas, com 6 passos canônicos

---

## Fora de escopo

- Game agents (`game-developer`, `game-designer`, `game-tester`) — referenciam
  `specs/features/<jogo>/SPEC.md` mas seguem regime diferente; release futura quando
  `game-agents-split` for promovida da backlog. **Nota E2**: `game-spec-definition.workflow.md`
  recebe patch de path apenas (linha 104); semântica de game scope (separação de domínio
  game-agents) permanece tracked no backlog item `game-agents-split`
- Pre-commit hook local — apenas CI nesta release; pode virar release subsequente
- Mudança no formato canônico de ACTIVE.md (continua `release: <x>` / `phase: <y>`).
  E3 adiciona apenas `release: none / phase: none` como valor canônico de "no active release"
- Refactoring estilístico dos agentes (mantém voz, estrutura, tamanho atuais)
- Backlog enrichment — operador disse explicitamente que adicionará mais itens na
  backlog antes de CLOSURE; esta release termina em TASKS
- **OpenCode hooks** — item 5 do readiness audit; futura release
- **Game agents alignment** — item 6 do readiness audit; backlog `game-agents-split`
- **`primary_context` choice / multi-context** — item 7 do readiness audit; futura release
- **Closing `sdd-release-lifecycle-v1`** — item 8 do readiness audit; tracked em "Drifts
  conhecidos" desta SPEC e na própria release alvo
- **Migrar repos concretos** (`redacted-slug-barbe`, `redacted-slug-explorer`, `redacted-slug`) — E4
  documenta o COMO; cada migração de repo será uma release própria desse repo (não desta)
- **Propagação do migration playbook via dadaia public** — D12: playbook fica em `docs/`,
  não em `public/data/` (que só propaga AGENTS.md/reports-AGENTS.md)

---

## Dependências e riscos

| Risco | Mitigação |
|-------|-----------|
| Patches divergirem da voz/estrutura existente dos agentes | Surgical edit; cada agente tem TASKS separadas; revisor manual do operador antes de IMPLEMENTATION |
| Quebrar workflows que outros repos ainda usam via projeção | Compat legacy preservada: nota explícita "se `releases/ACTIVE.md` ausente, cair em `features/<x>/...`"; env `SDD_LEGACY_FEATURES=1` continua suportada |
| Check de backlog flagrar histórico legítimo | Regex tolera a seção `## Histórico` explicitamente; apenas bullets sob `## Candidatas ativas` são validados estritamente |
| CI job falhar em branches que não rodaram migração | Job só roda quando o repo tem `specs/` (default na main); para repos sem specs, doctor retorna noop |
| `dadaia public install --force` ser necessário e sobrescrever projeções customizadas | Documentado em TASKS: rodar `--force` só após confirmação do operador |
| Stale tasks do `sdd-release-lifecycle-v1` confundirem releases futuras | Documentado em "Drifts conhecidos" e na backlog desta release; operador escolhe quando flipar `[x]` |
| E2 — renomear input de workflow quebrar callers existentes | Manter alias retrocompatível em workflows que ainda referenciam o nome antigo; documentar deprecation no próprio header `description` |
| E3 — `dadaia specs init` sobrescrever specs existentes acidentalmente | Default `force=False`; arquivos pré-existentes geram `[skip]` no output; `--force` é flag explícito |
| E3 — templates Jinja2 quebrarem ao render com placeholders ausentes | Defaults graceful para `last_release_id` ("none"), `architecture_overview` (placeholder), `layers_html` (empty `<p>...</p>`); render testado em `tests/unit/features/specs/test_scaffolder.py` |
| E3 — `phase: none` quebrar gate behavior | Gate v3 é fase-gated apenas para writes em `memory/` e `_archive/`; `phase: none` simplesmente nunca atinge nenhuma das fases write-allowing, então comportamento é fail-safe |
| E4 — playbook ficar desatualizado conforme o modelo evolui | Playbook referencia `sdd-release-lifecycle-v1/SPEC.md` Phase 6 como source-of-truth; quando aquela release mudar, playbook é manualmente revisado (sem auto-sync nesta release) |

---

## Drifts conhecidos (não resolvidos por esta release)

1. **`sdd-release-lifecycle-v1/TASKS.md` tem 11 tasks marcadas `[ ]` que já estão
   implementadas**: T-5.2/T-5.3/T-5.4/T-5.5/T-5.6 (CLI `dadaia specs doctor`) e T-V.1
   até T-V.6 (end-to-end verification). Evidência: `dadaia_workspace/cli/commands/specs.py`
   existe, `dadaia_workspace/features/specs/doctor.py` retorna `[]` em
   `specs/`, `tests/unit/features/specs/test_doctor.py` tem 22 testes green em CI atual.
   **Decisão**: não tocar nesta release. Quando `sdd-release-lifecycle-v1` for promovida
   para CLOSURE, flipar essas tasks para `[x]` e listar em `## Drifts` daquele CLOSURE.md.

2. **Game agents (`game-developer`, `game-designer`) ainda referenciam
   `specs/features/<jogo>/`**: legitimate fora do escopo desta release; tracked em backlog
   como `game-agents-split`. E2 patcha apenas o path do workflow `game-spec-definition`;
   os agentes em si seguem fora de escopo.

3. **Outros 4 readiness audit items**: OpenCode hooks (#5), game agents alignment (#6),
   primary_context choice (#7), closing `sdd-release-lifecycle-v1` (#8). Listados em
   "Fora de escopo"; alguns vão para `backlog/candidates.md` na CLOSURE desta release.

4. **Playbook E4 não é propagado via `dadaia public`**: vive em `docs/`, não em
   `public/data/`. Operadores de outros repos leem direto do dadaia-workspace ao migrar.
   Se no futuro for desejável projeção, basta estender `_VALID_TARGETS` para incluir
   arquivos `data/*.md` arbitrários — não nesta release.

---

## Referências

- Constitution: `specs/constitution.md`
- Memory atual: `specs/memory/{architecture,tech-stack}.html` + `specs/memory/product/index.html`
- Release anterior: `specs/releases/sdd-release-lifecycle-v1/SPEC.md`
- Backlog: `specs/backlog/candidates.md`
- Gate atual: `.dadaia/scripts/sdd-spec-gate.sh` (v3)
- Doctor atual: `dadaia_workspace/features/specs/doctor.py`
- Agente product-engineer (referência de padrão): `dadaia_workspace/public/agents/product-engineer.md`
