# Spec: Feature — Specialized Agents

> **Status:** Em revisão
> **Versão:** 1.1
> **Autor:** Marco Menezes
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/memory/architecture.md`, `specs/features/agent-rules-skills/SPEC.md`, `specs/features/multi-agent-orchestration/SPEC.md`
> **Consolidado por:** `specs/features/universal-agentic-assets/SPEC.md`

---

## Contexto

O dadaia-workspace distribui agentes canônicos em `dadaia_workspace/public/agents/`. Claude Code recebe esses agentes como sub-agentes em `.claude/agents/`; OpenCode recebe projeções nativas quando suportado; Codex recebe as personas via `AGENTS.md`, `.codex/rules/` e skills universais, sem fingir suporte a sub-agentes Claude Code. Os **5 agentes do pipeline SDD** colaboram em um fluxo de desenvolvimento orientado por SDD:

```
software-architect       product-auditor-agent
     │                          │
     │ reports (arquitectura)   │ reports (specs vs impl)
     └──────────────┬───────────┘
                    │
              product-engineer
                    │ (lê reports, escreve Specs/Plan/Tasks)
                    │
              software-engineer ──── qa-engineer
                    │ (implementa + TDD)   │ (E2E + deploy validation)
                    └──────────────────────┘
```

Além do core-5, existem **agentes de domínio** com specs próprias: `devops-engineer` (CI/CD, git flow) e `game-developer` (código de jogo exclusivo). Esses agentes não fazem parte do pipeline SDD e são definidos em `specs/features/devops-engineer/` e `specs/features/game-developer/`.

Nenhum agente tem permissão irrestrita de escrita. Cada um tem um path canônico de output e um papel único no fluxo.

---

## Glossário

| Termo | Definição |
|---|---|
| **Agente especializado** | Persona canônica versionada em `dadaia_workspace/public/agents/` e projetada para cada runtime conforme suporte nativo |
| **Sub-agente Claude Code** | Projeção `.md` em `.claude/agents/` com frontmatter YAML; invocado via `claude --agent <name>` ou pelo operador via Task tool |
| **`dadaia-grill-me` skill** | Skill compartilhada de revisão crítica; usada pelo software-architect e product-auditor-agent para identificar buracos e inconsistências |
| **Report path** | Diretório canônico onde cada agente pode escrever outputs; definido por agente e criado por `dadaia init` |
| **Frontmatter de agente** | Seção YAML no topo do arquivo `.md` do agente: `name`, `description`, `model`, `tools` |

---

## Usuários e Goals

### US-001: Revisão arquitetural autônoma

**Critérios de Aceite:**
- Dado um repositório com código e specs, quando o operador invoca o `software-architect`, então o agente lê o código, identifica problemas arquiteturais (acoplamento, código legado, código morto, drift entre arquitetura especificada e implementada) e gera um report em `.dadaia/reports/<context-name>/software-architect/`.
- O agente NUNCA escreve fora de `.dadaia/reports/<context-name>/software-architect/`.
- O agente usa `dadaia-grill-me` skill para revisar specs e planos criticamente.

### US-002: Auditoria de specs vs implementação

**Critérios de Aceite:**
- Dado um repositório, quando o operador invoca o `product-auditor-agent`, então o agente lê specs e código, executa testes disponíveis e detecta drift entre Spec e implementação.
- O agente registra todos os problemas encontrados em `.dadaia/reports/<context-name>/product-auditor-agent/`.
- O agente NUNCA modifica specs, código ou qualquer outro path além do seu report dir.
- O agente usa `dadaia-grill-me` skill para formular questões de consistência sobre as specs.

### US-003: Refinamento de Specs e Tasks

**Critérios de Aceite:**
- Dado reports de review disponíveis em `.dadaia/reports/`, quando o operador invoca o `product-engineer`, então o agente lê os reports e as specs existentes e cria ou atualiza `SPEC.md`, `PLAN.md` e `TASKS.md` alinhados aos problemas identificados.
- Tasks geradas incluem: arquivos afetados, contratos a mudar e pontos da codebase tocados.
- O agente NUNCA escreve código de implementação.
- O agente NUNCA modifica relatórios ou outros arquivos fora de `specs/`.

### US-004: Implementação guiada por SDD + TDD

**Critérios de Aceite:**
- Dado specs e tasks aprovados, quando o operador invoca o `software-engineer`, então o agente invoca o `qa-engineer` para obter critérios E2E, escreve testes antes de implementar, e segue a arquitetura especificada pelo `product-engineer`.
- Após deploy, o `qa-engineer` executa a suite E2E e confirma ou bloqueia o fechamento da task.
- Bugs encontrados em features fora do escopo da tarefa atual são reportados em `.dadaia/reports/<context-name>/software-engineer/` — nunca corrigidos silenciosamente.
- O agente NUNCA altera specs ou backlog diretamente.

---

## Definição dos 5 Agentes do Pipeline SDD

### `software-architect`

**Papel:** Especialista em arquitetura de software, qualidade de código e arquitetura de testes.

**Capacidades:**
- Identifica acoplamento excessivo, código legado que deveria ser reconstruído, features built on top of stale code
- Detecta código morto e deprecated; recomenda o que deletar vs. reconstruir para manter atomicidade de features
- Avalia arquitetura de testes: pirâmide unit/integration/e2e, uso de fakes vs. mocks, cobertura
- Usa `dadaia-grill-me` skill para revisar specs e planos criticamente, identificando buracos e inconsistências

**Permissões (write):** Somente `.dadaia/reports/<context-name>/software-architect/`  
**Proibições:** Jamais escreve em `specs/`, código de produção, `tests/`, ou qualquer outro path  
**Model:** `claude-opus-4-7`

### `product-auditor-agent`

**Papel:** Auditor de Specs vs. implementação. Analisa um repositório por vez.

**Capacidades:**
- Lê Specs (constitution, SPEC.md, feature specs) e compara com a implementação real
- Executa testes E2E para detectar drift funcional entre Spec e código
- Identifica inconsistências, buracos em especificações e conflitos entre specs
- Usa `dadaia-grill-me` skill para formular questões que expõem inconsistências nas specs

**Permissões (write):** Somente `.dadaia/reports/<context-name>/product-auditor-agent/`  
**Proibições:** Jamais modifica specs, código, testes ou qualquer outro path  
**Model:** `claude-opus-4-7`

### `product-engineer`

**Papel:** Engenheiro de produto responsável por Specs, Plans e Tasks. Analisa um repositório por vez.

**Capacidades:**
- Lê reports de `software-architect` e `product-auditor-agent` antes de qualquer ação
- Cria e atualiza `SPEC.md`, `PLAN.md` e `TASKS.md` baseado nos reports e nas specs existentes
- Tasks geradas identificam: arquivos afetados, contratos a mudar, pontos específicos na codebase — facilitando a divisão de trabalho
- Sempre considera reports arquiteturais e de auditoria para garantir que as alterações nas specs tocam os lugares certos

**Permissões (write):** Somente `specs/` do repositório em contexto (SPEC.md, PLAN.md, TASKS.md, z_bug_specs.md)  
**Proibições:** Jamais escreve código de implementação, testes ou relatórios  
**Model:** `claude-opus-4-7`

### `software-engineer`

**Papel:** Engenheiro de software full-stack. Implementa o backlog seguindo SDD + TDD + OWASP. Parceiro de pair deployment com o `qa-engineer`.

**Capacidades:**
- Lê specs e tasks; implementa usando técnica TDD (testes primeiro, depois implementação)
- Respeita estritamente a arquitetura especificada pelo `product-engineer`
- Aplica OWASP Top 10 em toda implementação — jamais expõe credenciais ou valida PII
- Invoca `qa-engineer` antes de iniciar (critérios E2E) e após deploy (validação)
- Nunca modifica testes E2E — esses são domínio exclusivo do `qa-engineer`

**Permissões (write):**
- Código de produção e testes unitários/integração do repositório em contexto
- `.dadaia/reports/<context-name>/software-engineer/` para implementation reports

**Proibições:** Jamais altera specs, PLAN.md, TASKS.md, testes E2E ou `repos/tauan-games/`  
**Model:** `claude-opus-4-7`

### `qa-engineer`

**Papel:** Guardião da qualidade de testes. Único autorizado a criar e modificar testes E2E. Valida deploys e audita a pirâmide de testes.

**Capacidades:**
- Define critérios de aceite E2E (Given/When/Then) antes de cada implementação
- Executa suite E2E após deploy e valida resultado por cenário
- Audita pirâmide unit/integration/E2E; rejeita slope tests, magic mock inflation e volume padding
- Colabora com `game-developer` para automação de testes de jogos

**Permissões (write):**
- Testes E2E do projeto em contexto
- `.dadaia/reports/<context-name>/qa-engineer/` para deploy validation e test quality audit reports

**Proibições:** Jamais escreve código de produção, testes unitários/integração, specs ou código de jogo  
**Model:** `claude-opus-4-7`

---

## Requisitos Funcionais

### Definição de Agentes

- FR-001: The system shall provide 5 specialized SDD pipeline agents: `software-architect`, `product-auditor-agent`, `product-engineer`, `software-engineer`, and `qa-engineer`. Domain agents (`devops-engineer`, `game-developer`) are defined in their own feature specs.
- FR-002: Each agent shall be defined as a markdown file in `dadaia_workspace/public/agents/` with a YAML frontmatter block specifying `name`, `description`, `model`, and `tools`.
- FR-003: The `software-architect` and `product-auditor-agent` shall reference the `dadaia-grill-me` skill in their system prompts.
- FR-004: Each agent's system prompt shall explicitly state which directories the agent is allowed to write to and which are prohibited.

### Permissões de Escrita (por agente)

- FR-005: `software-architect` write scope: exclusively `.dadaia/reports/<context-name>/software-architect/`.
- FR-006: `product-auditor-agent` write scope: exclusively `.dadaia/reports/<context-name>/product-auditor-agent/`.
- FR-007: `product-engineer` write scope: exclusively `specs/` of the active context repository.
- FR-008: `software-engineer` write scope: production code + unit/integration tests of the active context repository, and `.dadaia/reports/<context-name>/software-engineer/`.
- FR-008b: `qa-engineer` write scope: E2E tests of the active context repository, and `.dadaia/reports/<context-name>/qa-engineer/`.

### Report Directories

- FR-009: `dadaia init` shall create the `reports/` root directory under `.dadaia/`. Agents create their own `<context-name>/<agent-name>/` subdirectories at runtime — no static pre-creation is required.
- FR-010: Report files written by agents shall follow the naming convention `<YYYY-MM-DDTHHMMSSZ>-<topic>.md`.

### `dadaia-grill-me` Skill

- FR-011: The system shall provide a skill named `dadaia-grill-me` at `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`.
- FR-012: The skill shall instruct the agent to ask incisive questions that expose: missing behavior contracts, conflicting requirements, ambiguous state machine transitions, missing traceability, and weak acceptance criteria.
- FR-013: The skill shall produce its output as a structured list: question → finding → recommendation.
- FR-014: The skill shall be referenced by name in the `software-architect` and `product-auditor-agent` system prompts.

### Distribuição

- FR-015: Agent files shall live at `dadaia_workspace/public/agents/` and be projected to runtime-native destinations via `dadaia public install --target all|claude|opencode|codex`.
- FR-016: The `dadaia-grill-me` skill shall live at `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md` and be installed to `<workspace-root>/.agents/skills/dadaia-grill-me/SKILL.md`, plus runtime-specific skill directories when supported.
- FR-017: `dadaia public install` shall include `agents/` in the staged artifact set and shall report unsupported runtime agent projection as `unsupported` instead of fabricating parity.

### Input Contract (obrigatório por agente)

> Adicionado pela evolução `multi-agent-orchestration`. Resolve o gap apontado na literatura v1/v2: sem contrato declarado, agentes invocados em sessões "frescas" inventam contexto. Falha cedo, falha clara.

- **FR-018:** Every agent file in `dadaia_workspace/public/agents/` shall declare an `input_contract` block in the YAML frontmatter with three fields: `requires_inputs` (list), `produces_outputs` (list), `stop_if_missing` (bool, default `true`).
- **FR-019:** Each element of `requires_inputs` shall declare: `name` (snake_case), `kind` (one of `string | path | report`), `source` (one of `workflow_input | report_path | stdin`), `description` (short text), `stop_if_missing` (bool, default `true`).
- **FR-020:** Each element of `produces_outputs` shall declare: `name` (snake_case), `kind` (typically `report`), `path` (template; may contain `{context}`, `{run_id}`, `{ts}` placeholders), `schema_ref` (e.g., `handoff-schema-v1` or a feature-specific schema id).
- **FR-021:** When `stop_if_missing: true`, the agent's system prompt shall instruct: "if any required input is missing, do not start work; emit a clear error citing the missing input and its declared source."
- **FR-022:** Reports produced by an agent (under `produces_outputs[*].path`) shall conform to **Handoff Schema v1** (see section "Handoff Schema v1" below). Schema evolutions require a SemVer bump (`handoff-schema-v2`) and a deprecation window.

#### Bloco padrão de `input_contract` (referência)

```yaml
input_contract:
  requires_inputs:
    - name: context
      kind: string
      source: workflow_input
      description: "Active Spec Context Project name (e.g. dadaia-workspace)"
      stop_if_missing: true
    - name: discovery_report             # exemplo para agente que consome report do Stage 0
      kind: report
      source: report_path
      description: "Path to the discovery report produced by product-engineer"
      stop_if_missing: true
  produces_outputs:
    - name: orchestration_arch_report
      kind: report
      path: .dadaia/reports/{context}/software-architect/{ts}-orchestration-arch.md
      schema_ref: handoff-schema-v1
  stop_if_missing: true
```

### Handoff Schema v1

> Definido por esta spec; consumido por `specs/features/multi-agent-orchestration/SPEC.md` via `must_include` checks por stage.

Todo report inter-agente em `.dadaia/reports/<context>/<agent>/<ts>-<type>.md` shall begin with:

```markdown
# <Tipo> — <Contexto>

Data: <ISO 8601 UTC>
Agente: <nome do agente>
Spec Context: <nome>
Inputs:
- <path absoluto ou relativo a workspace-root de cada input consumido>
Escopo: <1–3 linhas>

---

## Findings
<seção obrigatória>

## Riscos
<seção obrigatória — pode ser "Nenhum identificado nesta rodada">

## Decisões necessárias
<seção obrigatória — lista de decisões que precisam do operador ou de outro agente>

## Recomendações
<seção obrigatória — direta, sem hedging>

## Artefatos consultados
<seção obrigatória — paths versionados; rastreabilidade>

## Próximo gate
<seção obrigatória — nomeia o próximo stage do workflow ou o gate operacional>
```

- **FR-023:** The `dadaia orchestrate` workflow runner shall validate that reports produced by stages whose `expected_output.must_include` lists the canonical section headings above contain those exact headings; missing headings emit `stage_failed` with a clear message.

---

## Requisitos Não-Funcionais

- NFR-001: [Isolamento] Cada agente opera com um escopo de escrita estritamente limitado. O sistema prompt é a única barreira de segurança — nenhum mecanismo de enforcement em código é implementado (é responsabilidade do operador respeitar os agentes corretos para cada tarefa).
- NFR-002: [Colaboração] A sequência canônica de uso é: software-architect → product-auditor-agent → product-engineer → soft-engineer-agent. Os agentes não se chamam entre si automaticamente — o operador orquestra.
- NFR-003: [Qualidade dos reports] Reports devem ser legíveis por humanos e estruturados o suficiente para serem consumidos pelo agente da próxima etapa.
- NFR-004: [Manutenibilidade] Cada arquivo de agente em `dadaia_workspace/public/agents/` é autossuficiente — não depende de state externo para sua definição.

---

## Estrutura de Arquivos

### Pacote (fonte canônica)

```
dadaia_workspace/
  public/
    agents/
      software-architect.md
      product-auditor-agent.md
      product-engineer.md
      software-engineer.md      ← substitui soft-engineer-agent
      qa-engineer.md            ← novo agente de qualidade E2E
      devops-engineer.md        ← definido em specs/features/devops-engineer/
      game-developer.md         ← definido em specs/features/game-developer/
    skills/
      dadaia-grill-me/
        SKILL.md
      dadaia-workspace-spec-navigator/
        SKILL.md
      dadaia-workspace-spec-reviewer/
        SKILL.md
```

### Runtime workspace

```
<workspace-root>/
  .dadaia/
    reports/                     ← criado por dadaia init (agentes criam subpaths em runtime)
      <context-name>/
        software-architect/      ← criado pelo agente na primeira execução
        product-auditor-agent/
        software-engineer/
        qa-engineer/
  .agents/
    skills/
      dadaia-grill-me/
        SKILL.md                 ← skill universal
  .claude/
    agents/
      software-architect.md      ← instalado por dadaia public install
      product-auditor-agent.md
      product-engineer.md
      software-engineer.md
      qa-engineer.md
      devops-engineer.md
      game-developer.md
    skills/
      dadaia-grill-me/
        SKILL.md                 ← instalado por dadaia public install
  .codex/
    rules/
  .opencode/
    agents/
```

---

## Formato do Arquivo de Agente (`.md`)

```markdown
---
name: architect-agent
description: >
  Architecture specialist. Reviews code quality, coupling, dead code,
  and test architecture. Writes reports only to .dadaia/reports/architect-agent-review/.
model: claude-opus-4-7
tools:
  - Read
  - Bash
  - Write
---

[system prompt — regras de comportamento, escopo de escrita, skill dadaia-grill-me]
```

---

## Fora de Escopo (v1.0)

- Orquestração automática entre agentes (pipeline sem operador)
- Agentes com permissões de push para git remoto
- Agente de deploy ou CI/CD
- Integração com ferramentas de issue tracking (Linear, GitHub Issues)
- Múltiplos modelos por agente (model routing)
