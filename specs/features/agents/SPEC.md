# Spec: Feature — Specialized Agents

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/memory/architecture.md`, `specs/features/agent-rules-skills/SPEC.md`

---

## Contexto

O dadaia-workspace distribui 4 agentes especializados como sub-agentes Claude Code (`claude agents`). Cada agente é um arquivo markdown em `.claude/agents/` com um system prompt focado, modelo configurado e permissões restritas de escrita. Os agentes colaboram em um fluxo de desenvolvimento orientado por SDD:

```
architect-agent          product-auditor-agent
     │                          │
     │ reports (arquitectura)   │ reports (specs vs impl)
     └──────────────┬───────────┘
                    │
              product-engineer-agent
                    │ (lê reports, escreve Specs/Plan/Tasks)
                    │
              soft-engineer-agent
                    │ (implementa + TDD + bug reports)
```

Nenhum agente tem permissão irrestrita de escrita. Cada um tem um path canônico de output e um papel único no fluxo.

---

## Glossário

| Termo | Definição |
|---|---|
| **Sub-agente Claude Code** | Arquivo `.md` em `.claude/agents/` com frontmatter YAML; invocado via `claude --agent <name>` ou pelo operador via Task tool |
| **`dadaia-grill-me` skill** | Skill compartilhada de revisão crítica; usada pelo architect-agent e product-auditor-agent para identificar buracos e inconsistências |
| **Report path** | Diretório canônico onde cada agente pode escrever outputs; definido por agente e criado por `dadaia init` |
| **Frontmatter de agente** | Seção YAML no topo do arquivo `.md` do agente: `name`, `description`, `model`, `tools` |

---

## Usuários e Goals

### US-001: Revisão arquitetural autônoma

**Critérios de Aceite:**
- Dado um repositório com código e specs, quando o operador invoca o `architect-agent`, então o agente lê o código, identifica problemas arquiteturais (acoplamento, código legado, código morto, drift entre arquitetura especificada e implementada) e gera um report em `.dadaia/reports/architect-agent-review/`.
- O agente NUNCA escreve fora de `.dadaia/reports/architect-agent-review/`.
- O agente usa `dadaia-grill-me` skill para revisar specs e planos criticamente.

### US-002: Auditoria de specs vs implementação

**Critérios de Aceite:**
- Dado um repositório, quando o operador invoca o `product-auditor-agent`, então o agente lê specs e código, executa testes disponíveis e detecta drift entre Spec e implementação.
- O agente registra todos os problemas encontrados em `.dadaia/reports/specs-sdd-review/`.
- O agente NUNCA modifica specs, código ou qualquer outro path além do seu report dir.
- O agente usa `dadaia-grill-me` skill para formular questões de consistência sobre as specs.

### US-003: Refinamento de Specs e Tasks

**Critérios de Aceite:**
- Dado reports de review disponíveis em `.dadaia/reports/`, quando o operador invoca o `product-engineer-agent`, então o agente lê os reports e as specs existentes e cria ou atualiza `SPEC.md`, `PLAN.md` e `TASKS.md` alinhados aos problemas identificados.
- Tasks geradas incluem: arquivos afetados, contratos a mudar e pontos da codebase tocados.
- O agente NUNCA escreve código de implementação.
- O agente NUNCA modifica relatórios ou outros arquivos fora de `specs/`.

### US-004: Implementação guiada por SDD + TDD

**Critérios de Aceite:**
- Dado specs e tasks aprovados, quando o operador invoca o `soft-engineer-agent`, então o agente escreve testes antes de implementar, segue a arquitetura especificada pelo product-engineer-agent e implementa exclusivamente a tarefa solicitada.
- Bugs encontrados em features fora do escopo da tarefa atual são reportados em `.dadaia/reports/bugs/soft-engineer-report/` — nunca corrigidos silenciosamente.
- O agente NUNCA altera specs ou backlog diretamente.

---

## Definição dos 4 Agentes

### `architect-agent`

**Papel:** Especialista em arquitetura de software, qualidade de código e arquitetura de testes.

**Capacidades:**
- Identifica acoplamento excessivo, código legado que deveria ser reconstruído, features built on top of stale code
- Detecta código morto e deprecated; recomenda o que deletar vs. reconstruir para manter atomicidade de features
- Avalia arquitetura de testes: pirâmide unit/integration/e2e, uso de fakes vs. mocks, cobertura
- Usa `dadaia-grill-me` skill para revisar specs e planos criticamente, identificando buracos e inconsistências

**Permissões (write):** Somente `.dadaia/reports/architect-agent-review/`  
**Proibições:** Jamais escreve em `specs/`, código de produção, `tests/`, ou qualquer outro path  
**Model:** `claude-opus-4-7`

### `product-auditor-agent`

**Papel:** Auditor de Specs vs. implementação. Analisa um repositório por vez.

**Capacidades:**
- Lê Specs (constitution, SPEC.md, feature specs) e compara com a implementação real
- Executa testes E2E para detectar drift funcional entre Spec e código
- Identifica inconsistências, buracos em especificações e conflitos entre specs
- Usa `dadaia-grill-me` skill para formular questões que expõem inconsistências nas specs

**Permissões (write):** Somente `.dadaia/reports/specs-sdd-review/`  
**Proibições:** Jamais modifica specs, código, testes ou qualquer outro path  
**Model:** `claude-opus-4-7`

### `product-engineer-agent`

**Papel:** Engenheiro de produto responsável por Specs, Plans e Tasks. Analisa um repositório por vez.

**Capacidades:**
- Lê reports de `architect-agent` e `product-auditor-agent` antes de qualquer ação
- Cria e atualiza `SPEC.md`, `PLAN.md` e `TASKS.md` baseado nos reports e nas specs existentes
- Tasks geradas identificam: arquivos afetados, contratos a mudar, pontos específicos na codebase — facilitando a divisão de trabalho
- Sempre considera reports arquiteturais e de auditoria para garantir que as alterações nas specs tocam os lugares certos

**Permissões (write):** Somente `specs/` do repositório em contexto (SPEC.md, PLAN.md, TASKS.md, z_bug_specs.md)  
**Proibições:** Jamais escreve código de implementação, testes ou relatórios  
**Model:** `claude-opus-4-7`

### `soft-engineer-agent`

**Papel:** Engenheiro de software. Implementa o backlog seguindo SDD + TDD.

**Capacidades:**
- Lê specs e tasks; implementa usando técnica TDD (testes primeiro, depois implementação)
- Respeita estritamente a arquitetura especificada pelo `product-engineer-agent`
- Executa testes após cada mudança para garantir que não há regressões
- Cria bug reports para problemas encontrados fora do escopo da tarefa atual

**Permissões (write):**
- Código de produção (`dadaia_workspace/`) e testes (`tests/`) do repositório em contexto
- Somente `.dadaia/reports/bugs/soft-engineer-report/` para bug reports

**Proibições:** Jamais altera specs, PLAN.md, TASKS.md ou backlog diretamente  
**Model:** `claude-sonnet-4-6`

---

## Requisitos Funcionais

### Definição de Agentes

- FR-001: The system shall provide 4 specialized agents: `architect-agent`, `product-auditor-agent`, `product-engineer-agent`, and `soft-engineer-agent`.
- FR-002: Each agent shall be defined as a markdown file in `dadaia_workspace/public/agents/` with a YAML frontmatter block specifying `name`, `description`, `model`, and `tools`.
- FR-003: The `architect-agent` and `product-auditor-agent` shall reference the `dadaia-grill-me` skill in their system prompts.
- FR-004: Each agent's system prompt shall explicitly state which directories the agent is allowed to write to and which are prohibited.

### Permissões de Escrita (por agente)

- FR-005: `architect-agent` write scope: exclusively `.dadaia/reports/architect-agent-review/`.
- FR-006: `product-auditor-agent` write scope: exclusively `.dadaia/reports/specs-sdd-review/`.
- FR-007: `product-engineer-agent` write scope: exclusively `specs/` of the active context repository.
- FR-008: `soft-engineer-agent` write scope: production code + tests of the active context repository, and `.dadaia/reports/bugs/soft-engineer-report/`.

### Report Directories

- FR-009: `dadaia init` shall create the following report subdirectories under `.dadaia/reports/`:
  - `architect-agent-review/`
  - `specs-sdd-review/`
  - `bugs/soft-engineer-report/`
- FR-010: Report files written by agents shall follow the naming convention `<YYYY-MM-DD>-<topic>.md`.

### `dadaia-grill-me` Skill

- FR-011: The system shall provide a skill named `dadaia-grill-me` at `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`.
- FR-012: The skill shall instruct the agent to ask incisive questions that expose: missing behavior contracts, conflicting requirements, ambiguous state machine transitions, missing traceability, and weak acceptance criteria.
- FR-013: The skill shall produce its output as a structured list: question → finding → recommendation.
- FR-014: The skill shall be referenced by name in the `architect-agent` and `product-auditor-agent` system prompts.

### Distribuição

- FR-015: Agent files shall live at `dadaia_workspace/public/agents/` and be installed to `<workspace-root>/.claude/agents/` via `dadaia public install`.
- FR-016: The `dadaia-grill-me` skill shall live at `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md` and be installed to `<workspace-root>/.claude/skills/dadaia-grill-me/SKILL.md` via `dadaia public install`.
- FR-017: `dadaia public install` shall include `agents/` in the installed artifact set, alongside `rules/`, `skills/`, `commands/`, and `scripts/`.

---

## Requisitos Não-Funcionais

- NFR-001: [Isolamento] Cada agente opera com um escopo de escrita estritamente limitado. O sistema prompt é a única barreira de segurança — nenhum mecanismo de enforcement em código é implementado (é responsabilidade do operador respeitar os agentes corretos para cada tarefa).
- NFR-002: [Colaboração] A sequência canônica de uso é: architect-agent → product-auditor-agent → product-engineer-agent → soft-engineer-agent. Os agentes não se chamam entre si automaticamente — o operador orquestra.
- NFR-003: [Qualidade dos reports] Reports devem ser legíveis por humanos e estruturados o suficiente para serem consumidos pelo agente da próxima etapa.
- NFR-004: [Manutenibilidade] Cada arquivo de agente em `dadaia_workspace/public/agents/` é autossuficiente — não depende de state externo para sua definição.

---

## Estrutura de Arquivos

### Pacote (fonte canônica)

```
dadaia_workspace/
  public/
    agents/
      architect-agent.md
      product-auditor-agent.md
      product-engineer-agent.md
      soft-engineer-agent.md
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
    reports/
      architect-agent-review/    ← criado por dadaia init
      specs-sdd-review/          ← criado por dadaia init
      bugs/
        soft-engineer-report/    ← criado por dadaia init
  .claude/
    agents/
      architect-agent.md         ← instalado por dadaia public install
      product-auditor-agent.md
      product-engineer-agent.md
      soft-engineer-agent.md
    skills/
      dadaia-grill-me/
        SKILL.md                 ← instalado por dadaia public install
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
