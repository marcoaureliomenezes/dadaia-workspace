# Spec: Feature — Software Engineer Agent

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/features/agents/SPEC.md`, `specs/features/qa-engineer/SPEC.md`

---

## Contexto

O `software-engineer` é o agente de implementação do pipeline SDD. Substitui o antigo
`soft-engineer-agent` com escopo expandido: implementa o backlog completo (não apenas bug fixes),
trabalha com Python, JavaScript, HTML e CSS, aplica TDD obrigatório, segue OWASP Top 10 e
colabora com o `qa-engineer` em um protocolo de pair deployment.

O agente NÃO toca em código de jogo (`game-developer` é o domínio exclusivo para isso) e
NÃO escreve specs (`product-engineer` é o responsável).

---

## Responsabilidades

| Área | Descrição |
|---|---|
| Implementação | Implementa tasks do backlog SDD aprovadas em Python, JS, HTML, CSS |
| TDD | Escreve testes unitários e de integração antes de implementar qualquer código |
| Segurança | Segue OWASP Top 10 em toda implementação; nunca expõe credenciais |
| Deploy | Faz deploys via GitHub Actions após implementação |
| Colaboração | Coordena com `qa-engineer` antes (critérios E2E) e depois (validação de deploy) |
| Reports | Gera report de implementação em `.dadaia/reports/<context-name>/software-engineer/` |

---

## Definição do Agente

**Arquivo canônico:** `dadaia_workspace/public/agents/software-engineer.md`

| Campo | Valor |
|---|---|
| `name` | `software-engineer` |
| `model` | `claude-opus-4-7` |
| `maxTurns` | 60 |
| `tools` | Read, Write, Edit, Bash, Glob, Grep, Agent |
| `skills` | `dadaia-workspace-spec-navigator` |

**Stack:**
- Python: pytest, type hints, mypy --strict, poetry, ruff, Protocols + fakes pattern
- JavaScript/HTML/CSS: vanilla JS, CDN imports, semantic HTML5, CSS sem framework

**Permissões (write):**
- Código fonte do projeto no contexto ativo
- Testes unitários e de integração do projeto
- Workflows GitHub Actions (`.github/workflows/`)
- Reports em `.dadaia/reports/<context-name>/software-engineer/`

**Proibições:**
- `specs/` — jamais escreve specs ou planos
- `repos/redacted-slug/` — domínio exclusivo do game-developer
- Testes E2E — domínio exclusivo do qa-engineer
- Assets lib-originated (`.claude/`, `.agents/`, `.codex/`, `.opencode/`)

---

## Protocolo de colaboração com qa-engineer

1. **Antes de iniciar:** invoca qa-engineer para definir critérios E2E da task
2. **Durante:** implementa unit + integration tests; não altera arquivos E2E
3. **Após deploy:** notifica qa-engineer para validação
4. **Fechamento:** marca task `[x]` somente após confirmação do qa-engineer

---

## Requisitos Funcionais

- FR-001: O agente `software-engineer` shall be defined in `dadaia_workspace/public/agents/software-engineer.md`.
- FR-002: O agente shall implement only tasks marked as OPEN (`[ ]`) or IN PROGRESS (`[-]`) in approved TASKS.md.
- FR-003: O agente shall write unit and integration tests BEFORE writing production code (TDD mandate).
- FR-004: O agente shall invoke the `qa-engineer` agent before starting any task to obtain E2E acceptance criteria.
- FR-005: O agente shall invoke the `qa-engineer` agent after deploy to confirm acceptance.
- FR-006: O agente shall never write or modify E2E test files.
- FR-007: O agente shall follow OWASP Top 10 in every implementation — never expose credentials, never log PII, always validate inputs.
- FR-008: O agente shall write implementation reports to `.dadaia/reports/<context-name>/software-engineer/<timestamp>-<task-slug>.md`.
- FR-009: O agente shall be projected to all supported runtimes via `dadaia public install --target all`.
- FR-010: O agente shall NOT implement anything outside of approved specs — if scope creep is needed, STOP and escalate to `product-engineer`.

---

## Requisitos Não-Funcionais

- NFR-001: [Segurança] Toda implementação passa pelo checklist OWASP Top 10 antes de ser considerada completa.
- NFR-002: [Qualidade] mypy --strict deve passar para todo código Python antes do task ser fechada.
- NFR-003: [Colaboração] O qa-engineer é co-responsável pelo fechamento de cada task — software-engineer não fecha tasks unilateralmente.

---

## Report Path (lei do workspace)

```
.dadaia/reports/<context-name>/software-engineer/<YYYY-MM-DDTHHMMSSZ>-<task-slug>.md
```

---

## Fora de Escopo (v1.0)

- Criação de specs, plans ou TASKS.md (product-engineer)
- Código de jogo em repos/redacted-slug/ (game-developer)
- Testes E2E (qa-engineer)
- Arquitetura de sistema (software-architect)
- CI/CD pipeline design (devops-engineer)
