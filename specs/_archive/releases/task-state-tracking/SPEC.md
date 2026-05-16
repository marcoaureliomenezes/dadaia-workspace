# Spec: Feature — Task State Tracking

> **Status:** Em revisão
> **Versão:** 0.1
> **Autor:** Marco Menezes
> **Refinamento:** `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-15T000709Z-refine-specs-fase7.md`
> **Consumido por:** `sdd-enforcement` (mesma rodada)

---

## Contexto

`TASKS.md` em todo o produto usa marcadores binários `[ ]` (OPEN) e `[x]` (DONE). Quando um agente inicia uma task, **não há sinal observável** de que ela está em andamento — outro agente paralelo pode pegar a mesma task, causando conflito de escrita ou duplicação de trabalho. Não há rastreabilidade de "quem pegou o quê".

Esta feature introduz um terceiro estado, `[-]` (IN PROGRESS), com protocolo claro de transição. O mecanismo é uma **skill** (`dadaia-task-manager`) que toda agente consulta antes de tocar produção. Sem CLI nova. Sem schema novo.

A `task-state-tracking` é pré-requisito da `sdd-enforcement` v2: o gate v2 valida `[-]` em TASKS.md.

---

## Glossário

| Termo | Definição |
|---|---|
| **OPEN** | Marker `[ ]`. Task não iniciada. Default. |
| **IN PROGRESS** | Marker `[-]`. Algum agente reservou a task; trabalho ativo. |
| **DONE** | Marker `[x]`. Task implementada, verificada, commitada. |
| **transição** | Mudança de marker numa linha de `TASKS.md`. Toda transição é commitada. |
| **dadaia-task-manager** | Skill universal que define o protocolo. Vive em `public/skills/dadaia-task-manager/SKILL.md`. |

---

## Usuários e Goals

### US-TST-001: Reservar uma task antes de tocar arquivos

- **Como** agente de implementação
- **Quero** marcar a task que vou trabalhar com `[-]` antes de qualquer edição
- **Para** evitar que outro agente paralelo pegue a mesma task

**Critérios de Aceite:**
- Dado um `TASKS.md` com a linha `- [ ] T123 — Foo`, quando o agente decide trabalhar nela, então o agente edita `[ ]` → `[-]` e commita a mudança antes de prosseguir.
- Dado um `TASKS.md` onde já existe `- [-] T456`, quando o agente quer iniciar `T123`, então o agente conclui ou abandona `T456` (transitando de volta para `[ ]` ou para `[x]`) antes de marcar `T123` como `[-]`.

### US-TST-002: Concluir a task com commit

- **Como** agente que terminou a task
- **Quero** marcar `[-]` → `[x]` e commitar
- **Para** registrar entrega e liberar fila

**Critérios de Aceite:**
- Dado um `TASKS.md` com `- [-] T123`, quando o agente conclui, então o agente edita `[-]` → `[x]` e commita.
- O commit que finaliza uma task **deve** ter no mesmo diff o `[x]` e o resultado da implementação (não separar).

### US-TST-003: Skill é o único contrato

- **Como** operador
- **Quero** que todo agente siga o mesmo protocolo
- **Para** evitar drift entre agents

**Critérios de Aceite:**
- A skill `dadaia-task-manager` é projetada por `dadaia public install --target all` para `.agents/skills/`, `.claude/skills/`, `.opencode/skills/`, `.codex/skills/`.
- Os 6 agents em `public/agents/` referenciam `dadaia-task-manager` em sua lista `skills:`.

---

## Requisitos Funcionais

- **FR-TST-001:** Markers válidos em `TASKS.md` shall be exactly three: `[ ]` (OPEN), `[-]` (IN PROGRESS), `[x]` (DONE). Other forms (`[X]`, `[ X ]`, `[/]`) are not recognized.
- **FR-TST-002:** Toda task line in `TASKS.md` shall match the regex `^\s*-\s*\[[ \-x]\]\s+\w+`.
- **FR-TST-003:** A new skill shall live at `dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md`. Frontmatter shall declare `name: dadaia-task-manager`, `description: <one-line>`, `model: claude-haiku-4-5-20251001` (consumed by agents, not as standalone agent).
- **FR-TST-004:** The skill body shall describe the 4-step protocol:
  1. Read the relevant `TASKS.md` and identify the task to execute.
  2. Edit the marker `[ ]` → `[-]` and commit immediately (commit message: `chore(tasks): start <task-id>`).
  3. Execute the work.
  4. Edit the marker `[-]` → `[x]` and commit together with the implementation (commit message: `<type>: <description> (<task-id>)`).
- **FR-TST-005:** The skill shall include the **invariant rule**: never two `[-]` markers simultaneously in the same `TASKS.md` file. If found, the agent shall abort and report to the operator.
- **FR-TST-006:** The skill shall include a **recovery rule** for crashed sessions: if the agent finds a `[-]` it cannot trace back to its current work, it shall report to the operator before transitioning — never silently flip to `[x]`.
- **FR-TST-007:** Each agent in `public/agents/` shall declare `dadaia-task-manager` in its `skills:` frontmatter list. Applies to all 6 agents (product-engineer, software-architect, software-engineer, qa-engineer, devops-engineer, game-developer).
- **FR-TST-008:** `foundation/SPEC.md` shall be amended (in the same PR) to list `[ ]/[-]/[x]` as the **canonical task state contract** with normative force.

---

## Requisitos Não-Funcionais

- **NFR-TST-001 [Observabilidade]:** Toda transição produz um commit. O histórico git é a única fonte de verdade sobre quem pegou o quê e quando.
- **NFR-TST-002 [Atomicidade]:** A transição `[ ]` → `[-]` deve ocorrer antes da primeira edição em produção. O gate v2 (`sdd-enforcement`) faz cumprir.
- **NFR-TST-003 [Simplicidade]:** Nenhuma CLI nova. Nenhum schema JSON. Apenas a skill e a convenção de marker. Mudanças futuras podem promover para CLI se métricas justificarem.

---

## Decisões Arquiteturais

### ADR-TST-001: Skill > CLI > convenção sem suporte

A pergunta grill-me ofereceu três níveis. O operador escolheu skill. Justificativa: skill é distribuída universalmente (todos os runtimes), é texto consumível por LLM, e dispensa código novo. Uma CLI dedicada seria over-engineering para v0.1.

### ADR-TST-002: Marker `[-]` é "current session only"

`[-]` deve voltar a `[ ]` ou ir para `[x]` antes do agente encerrar. Não há `[-]` persistente entre sessões. Recuperação manual quando isso falha está coberta por FR-TST-006.

### ADR-TST-003: O commit `chore(tasks): start <task-id>` é obrigatório

Sem o commit, o estado `[-]` não é observável por outros agentes. O custo de um commit extra é trivial; o ganho de rastreabilidade é alto.

---

## Estrutura de Arquivos

```
dadaia_workspace/
  public/
    skills/
      dadaia-task-manager/
        SKILL.md             ← NOVO
    agents/
      product-engineer.md    ← +1 entry em skills:
      software-architect.md  ← +1 entry em skills:
      software-engineer.md   ← +1 entry em skills:
      qa-engineer.md         ← +1 entry em skills:
      devops-engineer.md     ← +1 entry em skills:
      game-developer.md      ← +1 entry em skills:
specs/
  foundation/SPEC.md         ← amend: contrato normativo `[ ]/[-]/[x]`
tests/
  e2e/features/
    test_public_pipeline.py  ← estender EXPECTED_SKILLS
```

---

## Critérios de Aceite (Spec Aprovada)

- [ ] `public/skills/dadaia-task-manager/SKILL.md` existe e atende FR-TST-003..006.
- [ ] Os 6 agents em `public/agents/` listam `dadaia-task-manager` em `skills:`.
- [ ] `foundation/SPEC.md` documenta o contrato normativo dos 3 markers.
- [ ] `tests/e2e/features/test_public_pipeline.py::EXPECTED_SKILLS` inclui `dadaia-task-manager`.
- [ ] `dadaia public install --target all` projeta a skill para 4 runtimes.
- [ ] `dadaia public doctor` retorna `[ok]` para `skills/dadaia-task-manager/SKILL.md` em todos os 4 alvos.

---

## Riscos e Mitigações

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| R1 | Skill ignorada por agentes que não a referenciam | Alta | FR-TST-007 obriga inclusão; teste E2E valida `dadaia-task-manager` em todos os agents |
| R2 | Commit extra `chore(tasks): start` polui o histórico | Baixa | Squash no merge é responsabilidade do operador; trade-off aceitável pelo benefício de rastreabilidade |
| R3 | Agente esquece de retornar `[-]` → `[x]` | Média | Skill é explícita; gate v2 não desbloqueia próxima task até o `[-]` ser resolvido |
| R4 | Conflito de merge em `TASKS.md` quando dois agentes editam paralelo | Média | Convenção de "uma task por agente por sessão" + resolução manual de conflito |

---

## Fora de Escopo (v0.1)

- CLI `dadaia task {start, finish, abandon}` — adiada para v0.2 se métricas justificarem.
- Histórico timeline `[ ] → [-] → [x]` com timestamps explícitos.
- Lock distribuído via filesystem (ex: `.dadaia/locks/<task-id>`) — não necessário enquanto o commit-as-lock funcionar.
- Validação automática de "nunca dois `[-]`" via hook — convenção é suficiente em v0.1.

---

## Questões Abertas

*Nenhuma.* Refinamento via grill-me concluído.
