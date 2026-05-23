# Constitution: dadaia-workspace

> Este documento define as leis imutáveis que governam todo o desenvolvimento do dadaia-workspace.
> Todo agente de IA trabalhando neste projeto DEVE seguir estas regras em toda tarefa.
> Atualizado apenas pelo arquiteto após revisão da equipe.

---

## Propósito do Projeto

dadaia-workspace é uma biblioteca Python e uma CLI que transforma um diretório em um **workspace AI-native multi-runtime** para desenvolvimento multi-repositório orientado por SDD. O produto organiza repositórios, contextos de trabalho, estado durável em JSON e artefatos de agente para Claude Code, OpenCode e Codex em um único fluxo previsível e seguro.

---

## Pilares do Produto

dadaia-workspace é definido por três pilares imutáveis. Toda decisão arquitetural ou de produto deve fortalecer pelo menos um pilar sem comprometer os outros dois. Esta seção precede a stack porque os pilares são invariantes; a stack é consequência.

### Pilar 1 — SDD-native multi-projeto

O workspace é gerenciado por Spec-Driven Development desde a raiz: cada repositório clonado é um Spec Context Project com `specs/constitution.md`, `specs/memory/`, `specs/foundation/SPEC.md` e a trilha atômica `specs/releases/<v-id>/` → `specs/_archive/releases/<v-id>/`. Enforcement: o gate `sdd-spec-gate.sh` projetado em `.dadaia/scripts/` exige uma task `[-]` em algum `TASKS.md` antes de qualquer edição de produção, e `dadaia specs doctor` valida as 11 invariantes estruturais. Floor mínimo: nenhuma feature pode ser implementada sem `SPEC.md` aprovado; nenhuma alteração em `specs/` pula a revisão de consistência; specs encerradas vivem apenas em `specs/_archive/releases/`.

### Pilar 2 — Orquestração multi-agente nativa

Workflows e agentes especialistas são primitivos de primeira classe, não convenções textuais: 10 agentes universais (`software-architect`, `software-engineer`, `product-engineer`, `qa-engineer`, `devops-engineer`, `frontend-engineer`, `backend-engineer`, `game-developer`, `game-designer`, `game-tester`) e workflows declarativos (`*.workflow.md` com `parallel_group` opcional) vivem em `dadaia_workspace/public/agents/` e `dadaia_workspace/public/workflows/`, são distribuídos via `dadaia public stage` + `dadaia public install`. Enforcement: rules de escopo (`game-developer-scope`, `dadaia-workspace-dev-guardrail`) garantem fronteiras de autoridade entre agentes; o handoff cross-agent é estruturado por reports HTML em `.dadaia/reports/<repo>/<agent>/`. Floor mínimo: Claude Code é o runtime de referência para orquestração — só nele `parallel_group` é dispatch real; nos demais runtimes a orquestração paralela degrada conforme o Pilar 3.

### Pilar 3 — Multi-AI-platform (Claude Code, Codex, OpenCode)

Os três runtimes oficialmente suportados — **Claude Code** (Anthropic), **Codex** (OpenAI) e **OpenCode** — consomem o mesmo conjunto de assets agentic através de uma pipeline única: `dadaia_workspace/public/` → `.dadaia/agentic/` (staging com manifest SHA256 em `.dadaia/agentic/manifest.json`) → projeções runtime-specific em `.claude/`, `.codex/`, `.opencode/` e `.agents/`. Enforcement: `dadaia public doctor` compara source × staging × projeção com cinco status (`ok`, `drift`, `missing`, `unsupported`, `not-applicable`) e a rule `dadaia-workspace-dev-guardrail`, sempre ativa, lê `.dadaia/agentic/manifest.json` para identificar arquivos lib-originated e proibir edição direta nas projeções. Floor mínimo da paridade: skills, agents, commands e rules têm projeção honesta em todos os runtimes que os suportam nativamente; workflows com `parallel_group` permanecem Claude-exclusive até existir runtime de orquestração paralela nos demais — em OpenCode degradam para sequencial (`[partial]`), em Codex são `[not-applicable]` (sem dispatch). A ampliação para um quarto runtime (Gemini CLI, Cursor, Aider, etc.) é uma emenda constitucional, não uma feature.

---

## Stack Tecnológica (Obrigatória)

| Componente | Tecnologia | Versão mínima |
|---|---|---|
| Linguagem | Python | 3.12+ |
| Package manager | Poetry | latest stable |
| CLI framework | Typer | latest stable |
| Ambiente Python isolado | `venv` (stdlib) | — |
| Estado persistido | JSON via `json` + `os.replace()` (stdlib) | — |
| Catálogo de repositórios | openpyxl | latest stable |
| Operações git | subprocess (stdlib) | — |
| Testes | pytest | latest stable |
| Formatação e lint | ruff | latest stable |
| Type checking | mypy | latest stable |

**Nenhuma tecnologia fora desta lista pode ser adicionada sem revisão e atualização desta constituição.**

**SQLite não faz parte da stack.** O estado do workspace é gerenciado inteiramente por arquivos JSON.

---

## Segurança (Não-Negociáveis)

- **NUNCA** exponha credenciais, tokens ou secrets em código-fonte, specs ou logs.
- **NUNCA** armazene tokens git em `.dadaia/`, `.agents/`, `.claude/`, `.codex/`, `.opencode/` ou em qualquer arquivo do projeto.
- Todas as operações git usam **exclusivamente** as credenciais do sistema operacional (`~/.gitconfig`, SSH keys, credential manager do OS).
- **NUNCA** faça log de URLs com tokens embutidos.
- **SEMPRE** valide entradas do usuário na camada CLI antes de chamar serviços.
- **NUNCA** apague diretórios de repositório em `repos/` sem que o ciclo de vida de deactivate tenha sido concluído com sucesso (commit + push verificados).

---

## Princípios de Arquitetura

### Arquitetura Oficial
O produto adota uma arquitetura em quatro camadas com uma composition root explícita:

```
CLI  →  Features  →  Core  ←  Infrastructure
           \                  /
            \                /
             └─ container ──┘
```

- `cli/` orquestra input e output.
- `features/` contém regras de negócio e depende apenas de `core/`.
- `core/` contém modelos, exceções e Protocols; não depende de nenhuma outra camada do projeto.
- `infrastructure/` implementa os Protocols de `core/`.
- `dadaia_workspace/container.py` é a **composition root**. Ele pode conhecer `features/` e `infrastructure/`, mas **não faz parte do core**.

### Regras de Dependência
- A camada **CLI** nunca acessa diretamente filesystem, git ou estado JSON de forma não mediada.
- Nenhuma feature importa outra feature.
- Nenhum módulo dentro de `core/` importa `features/`, `cli/` ou `infrastructure/`.
- Toda dependência externa usada por `features/` deve passar por um `Protocol` definido em `core/`.

### Estados do Spec Context Project
Os únicos estados válidos são:
- `inativo`
- `ativo`

A flag `is_primary` (`bool`) distingue, dentro de `ativo`, qual contexto é o primário do workspace. Somente um contexto pode ter `is_primary=True` ao mesmo tempo. **Não existe estado `standby`.**

### Ciclo de Vida de Repositórios
- Um contexto `inativo` não tem repo clonado em disco.
- Um contexto `ativo` tem repo clonado em `repos/<slug>/`.
- **`activate`**: se o repo não está em disco, clona automaticamente via `git clone`.
- **`deactivate`**: executa git commit (se houver mudanças) + git push (se houver remote) antes de remover o repo do disco. Se o git sync falhar, a operação é abortada para evitar perda de dados.

### JSON como Fonte da Verdade
- O estado de todos os contextos vive em `.dadaia/states/spec_contexts.json`.
- O ponteiro do contexto primário vive em `.dadaia/states/primary_context.json`.
- Toda escrita nesses arquivos é atômica: write para `.tmp` → `os.replace()`.
- O estado pode ser diagnosticado e reparado por `dadaia doctor [--fix]`.

### Workspace Runtime Externo ao Repositório
- O **dadaia workspace runtime** vive no diretório de trabalho do usuário, fora do repositório da biblioteca `dadaia-workspace/`.
- A pasta raiz de estado do workspace é `<workspace-root>/.dadaia/`.
- A estrutura canônica de `.dadaia/` é definida **somente** em `specs/memory/architecture.md`.

### Ambiente Python do Workspace
- O ambiente Python isolado do workspace vive em `<workspace-root>/.dadaia/.venv/`.
- Após o bootstrap do workspace, agentes e automações devem usar esse ambiente para comandos Python e pip.
- O uso de Python global só é aceitável antes da criação de `.dadaia/.venv` ou para criar a própria venv.

### Artefatos Efêmeros
- Scripts Python efêmeros pertencem somente a `<workspace-root>/.dadaia/tmp/python/`.
- JSONs e dados transitórios efêmeros pertencem somente a `<workspace-root>/.dadaia/tmp/json/`.
- Artefatos efêmeros não devem ser criados em `dadaia-workspace/`, em `specs/`, em `tests/` ou na raiz do repositório.

### Artefatos de Agente
- Neste repositório, `dadaia_workspace/public/` é a única localização versionada para rules, skills, commands, scripts, agents, templates, workflows, plugins, data e schemas universais do produto.
- `dadaia-workspace/.agents/`, `dadaia-workspace/.claude/`, `dadaia-workspace/.codex/` e `dadaia-workspace/.opencode/` não fazem parte da arquitetura de authoring do produto e não devem ser usados como fonte canônica.
- `<workspace-root>/.dadaia/agentic/` é uma área local gerada pela CLI a partir do pacote instalado. Ela contém manifest com versão do pacote, hashes, timestamp de geração e versão de schema.
- `<workspace-root>/.agents/skills/` é o destino universal para skills reutilizáveis entre runtimes que suportam o padrão de Agent Skills.
- O comando `dadaia public stage` materializa os artefatos versionados de `dadaia_workspace/public/` em `.dadaia/agentic/`.
- O comando `dadaia public install --target all|claude|codex|opencode|agents` projeta os artefatos staged para os runtimes suportados, gerando `.dadaia/agentic/` antes se necessário.
- Claude Code recebe projeções em `.claude/agents/`, `.claude/commands/`, `.claude/skills/` e `.claude/settings.json`.
- OpenCode recebe projeções em `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/` e `opencode.json`, usando comandos, permissões e instruções nativas em vez de hooks inexistentes.
- Codex recebe projeções em `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/` e skills compartilhadas em `.agents/skills/`.
- `AGENTS.md` é o documento universal de regras e personas para runtimes que leem instruções no workspace root.
- Os 4 agentes especializados (`architect-agent`, `product-auditor-agent`, `product-engineer-agent`, `soft-engineer-agent`) são distribuídos em `dadaia_workspace/public/agents/` e projetados para cada runtime conforme suas capacidades nativas.
- A skill `dadaia-grill-me` é distribuída em `dadaia_workspace/public/skills/dadaia-grill-me/` e instalada em `.agents/skills/`, além das projeções runtime-specific quando suportadas.
- A rule `dadaia-workspace-dev-guardrail` é sempre ativa e proíbe edição direta de qualquer asset lib-originated em `.agents/`, `.claude/`, `.codex/` ou `.opencode/`. Assets lib-originated são identificados por comparação com o manifest staged em `.dadaia/agentic/`.
- `dadaia public doctor` diagnostica drift entre pacote, staging e projeções runtime, reportando `ok`, `missing`, `drift` e `unsupported`.

### Integração CLI-First para Agentes
- A CLI oficial `dadaia` é a interface primária do produto para consumo por humanos e agentes.
- Toda capacidade oficialmente suportada para automação deve ser exposta por comando CLI com help no comando raiz, no grupo e no subcomando correspondente.
- Skills, workflows e automações devem usar a CLI oficial sempre que a capacidade desejada existir nela.
- Se a CLI ainda não cobrir uma necessidade operacional, o único fallback permitido para automação é criar script Python efêmero em `<workspace-root>/.dadaia/tmp/python/` e gravar saída estruturada em `<workspace-root>/.dadaia/tmp/json/`.

---

## Qualidade de Código

- Cobertura mínima: **80%** para código novo na camada `features/`.
- `core/models/` e `core/exceptions.py` devem ter cobertura completa.
- Toda função pública deve ter type hints completos.
- Nenhum `print()` fora da CLI.
- O código deve passar em `ruff format`, `ruff check` e `mypy --strict`.
- Falhas devem preservar a cadeia de causa entre infraestrutura, feature e CLI.
- Mensagens de exceção e de erro de CLI devem informar a capacidade ou comando que falhou, o contexto ou recurso relevante e a próxima ação segura de recuperação quando ela existir.

---

## Workflow de Desenvolvimento (SDD)

- **NUNCA** implemente uma feature sem `SPEC.md` aprovado.
- **NUNCA** avance de fase (`SPEC.md` → `PLAN.md` → `TASKS.md` → implementação) sem aprovação humana explícita.
- Toda alteração em `specs/` deve passar por uma revisão de consistência antes de ser considerada pronta.
- Se restarem conflitos, ambiguidades ou buracos após a revisão, eles devem ser registrados em `z_bug_specs.md`.
- Se a implementação divergir da spec, atualize a spec primeiro. Nunca ajuste a spec para justificar o código já escrito.
- **Versão atômica**: specs ativas em `specs/releases/<v-id>/` representam apenas o estado atual; specs encerradas vão para `specs/_archive/releases/<v-id>/`. Hotfix releases (PATCH≥1) seguem o mesmo caminho. Não há rascunhos órfãos fora dessas trilhas.

---

## Mapa de Responsabilidade das Specs

- `specs/memory/architecture.md` é a fonte única da estrutura do workspace runtime e da árvore `.dadaia/`.
- `specs/memory/product.md` é a fonte única da definição do produto, dos usuários e do modelo conceitual.
- `specs/memory/tech-stack.md` é a fonte única da política de toolchain, `.dadaia/.venv` e execução Python.
- `specs/foundation/SPEC.md` é a fonte única da arquitetura de implementação e dos guardrails anti-drift.
- `specs/SPEC.md` é a fonte única do comportamento do produto e da superfície top-level da CLI.
- `specs/features/*/SPEC.md` possuem apenas contratos específicos de feature.
- `specs/PLAN.md` e `specs/TASKS.md` são documentos derivados e não podem redefinir contratos dos documentos acima.

---

## Workspace Runtime

- O template canônico do workspace runtime é definido em `specs/memory/architecture.md`.
- O bootstrap deve reconciliar a estrutura mínima do workspace sem destruir conteúdo já existente.

---

## Architectural Decision Records

Registros canônicos de decisões arquiteturais com impacto multi-feature. Cada ADR é
imutável após adoção: alterações requerem novo ADR que cite e supere o anterior, nunca
edição in-place. Os ADRs aqui são consequência atômica da release `token-cost-bigbang-v1`
(closed 2026-05-20). Decisão completa, rastreabilidade ao audit binding e métricas vivem
em `specs/_archive/releases/token-cost-bigbang-v1/CLOSURE.md`.

### ADR-X1 — Provider-agnostic instruction files

**Decisão:** `AGENTS.md` é o documento canônico de workspace-root instruction. `CLAUDE.md`
é emitido pelo `dadaia public install` como stub de 1 linha (`# See AGENTS.md for workspace
rules and agent personas.`). Qualquer runtime que suporte `@`-include pode resolver o stub
nativamente; runtimes que não suportam lêem o texto do stub manualmente e seguem o
redirecionamento.

**Justificativa:** evita duplicação byte-identical entre `AGENTS.md` e `CLAUDE.md` (até
então a fonte única `data/AGENTS.md` era fanned-out via Option C). Reduz a superfície de
drift entre os dois documentos e desacopla a CLI da identidade de runtime do consumidor.

**Consequências:** `CLAUDE.md` em workspace-root e em consumer-repos passa a ser stub
mínimo; `dadaia public doctor` verifica byte-identity do stub contra a string canônica;
runtimes sem `@`-include resolvem manualmente.

### ADR-X2 — Skill scoping policy (Tier-A vs Tier-B)

**Decisão:** 11 skills Tier-A (uso universal entre agentes) permanecem catalogadas em
`dadaia_workspace/public/skills/` e são projetadas em todos os runtimes suportados. 22
skills Tier-B (específicas por agente) migram para `docs/agent-knowledge/<agent>/<topic>.md`
e são carregadas on-demand pelo agente owner via referência inline no body. O catálogo
público (e os doctors) expõem apenas Tier-A.

**Justificativa:** o catálogo único de 33 skills inflava o system-prompt floor de todos os
runtimes; mover 22 Tier-B para per-agent on-demand reduz `cache_read / msg` de ~159 K para
o target ≤ 80 K (audit §8 P-02).

**Consequências:** `dadaia public install` projeta apenas Tier-A; agent bodies carregam
ponteiros explícitos para `docs/agent-knowledge/<agent>/`; doctor não mais flagga ausência
de Tier-B nos catálogos runtime.

### ADR-X3 — Agent size budget

**Decisão:** cada agente cumpre dois limites estruturais: `description:` ≤ 200 caracteres;
body ≤ 350 linhas. Report templates extensos e knowledge surfaces longas são extraídos
para `docs/agent-knowledge/<agent>/templates/*.md`. O body do agente mantém apenas
ponteiro de 1 linha referenciando o template extraído.

**Justificativa:** agentes acima desses limites inflavam o input token cost por dispatch
(`description` lida sempre; body lido em context bootstrap) sem retorno proporcional em
qualidade de output.

**Consequências:** lint rule em `dadaia public doctor` flagga agente fora do orçamento;
templates de report viram artefatos versionados em `docs/agent-knowledge/`.

### ADR-X4 — Default model Sonnet 4.6 (com override Opus per-dispatch)

**Decisão:** todos os 20 agentes da topologia usam `claude-sonnet-4-6` como modelo padrão.
Override `DADAIA_MODEL_OVERRIDE=opus` é o mecanismo de escalação per-dispatch para tarefas
que exijam Opus (greenfield architecture, multi-spec drift, memory atomicity writes).
`researcher` usa `claude-haiku-4-5-20251001` (Haiku 4.5). `security-reviewer` opera em
dois modos: scan-mode = Haiku; triage-mode = Sonnet, declarado pelo dispatcher.

**Justificativa:** os 7 agentes anteriormente Opus (`project-manager`, `project-auditor`,
`product-engineer`, `software-architect`, `ai-engineer`, `game-designer`, `game-tester`)
respondiam por ~$700–900/mês adicionais sem qualidade dispatch-by-dispatch superior
mensurável; D-12 dropou o multi-mode pattern por inviabilidade arquitetural (Claude Code
fixa `model:` no registration do agente).

**Consequências:** workspace passa de modelo-misto para Sonnet-default; escalação a Opus
exige variável ambiente explícita por sessão; Haiku 4.5 viabiliza fan-out de `researcher`
em phases evidence-heavy (ADR-X6).

### ADR-X5 — Schema handoff-v1.1 (sidecar-first emission)

**Decisão:** `handoff-v1.schema.json` avança para versão v1.1. Novos campos obrigatórios:
`findings[].detail_md`, `findings[].fix_recommendation`, `scope`, `metrics`. Campo
`artifact.path` (HTML) torna-se opcional. `schema_version` aceita literais
`"handoff-v1"` e `"handoff-v1.1"`. Migration: big-bang — todos os 20 agentes reescritos
em lockstep para emitir sidecar v1.1 como default; HTML só é emitido sob `--with-report`
explícito ou `next_handoff.agent == "human"`.

**Justificativa:** HTML reports não-lidos respondiam por ~78% do output token cost; o
schema enriquecido em v1.1 permite que dispatchers e auditors consumam findings
estruturados a partir do sidecar JSON sem renderizar HTML.

**Consequências:** `dadaia reports validate` distingue v1.0 vs v1.1; `dadaia reports lint`
flagga orphan HTMLs (no sidecar), oversized HTMLs (>30 KB) e missing schema fields; agent
prompts carregam linguagem sidecar-first.

### ADR-X6 — Dispatch-to-researcher canonical pattern

**Decisão:** para phases evidence-heavy (audit, code-review, security-scan,
spec-refinement, cross-cutting-feature), o padrão canônico é o orquestrador
(`project-manager`, `project-auditor`, `software-architect`, `code-reviewer`,
`security-reviewer`, `devops-engineer`) despachar N agentes `researcher` (Haiku 4.5) em
paralelo, cada um com pergunta tightly-scoped. O orquestrador sintetiza a partir dos
sidecars — não faz Read inline de file sets extensos. Playbook documentado em
`dadaia_workspace/public/skills/project-orchestration/SKILL.md`.

**Justificativa:** Read inline em arquivos grandes pelos modelos Sonnet/Opus quebra o
target `cache_read / msg ≤ 80 K`; delegando a Haiku via sidecar, o cost token cai em ~70%
para a mesma cobertura de evidência.

**Consequências:** 4 workflows read-heavy (`audit-cycle`, `code-review-fan-out`,
`cross-cutting-feature`, `spec-refinement`) ganham stage `researcher` injetada; orquestrador
consome sidecars não-HTML.

### ADR-X7 — Plugin scope policy (frontend-design)

**Decisão:** o plugin `frontend-design` é restrito aos agentes `frontend-engineer` e
`design-specialist`. Todos os outros agentes do workspace devem recusar invocações com
`[PLUGIN SCOPE ERROR]`. Enforcement por (a) rule `dadaia_workspace/public/rules/plugin-scope.md`
mirroring `game-developer-scope.md`; (b) allow-list line explícita nos bodies de
`frontend-engineer.md` e `design-specialist.md`; (c) verificação pelo `dadaia public doctor`
do alinhamento allow-list ↔ rule.

**Justificativa:** o plugin polui o context surface de agentes non-UI e cria risco de
design-pattern leakage fora da superfície UI/UX. Mirror do pattern já existente para
`game-developer-scope`.

**Consequências:** plugin permanece instalado mas só dois agentes podem invocá-lo;
mensagem padronizada `[PLUGIN SCOPE ERROR]` quando dispatcher tentar despachar agente
não autorizado com skill/tool do plugin.
