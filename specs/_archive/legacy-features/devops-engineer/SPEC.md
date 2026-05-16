# Spec: Feature — DevOps Engineer Agent

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/SPEC.md`, `specs/constitution.md`, `specs/features/agents/SPEC.md`, `specs/features/agent-rules-skills/SPEC.md`

---

## Contexto

O `devops-engineer` é um **agente de domínio** — opera fora do pipeline SDD core-4
(software-architect → product-auditor-agent → product-engineer → soft-engineer-agent).
Seu domínio é exclusivamente automação de CI/CD, governança de Git flow e estratégias
de deploy, atuando sobre qualquer repositório do workspace.

O agente não escreve código de aplicação, não modifica specs e não toca em `repos/redacted-slug/`.

---

## Responsabilidades

| Área | Descrição |
|---|---|
| CI/CD | Criar, auditar e melhorar workflows GitHub Actions em qualquer repo |
| Git Flow | Enforçar disciplina de branching, branch protection, PR reviews, CODEOWNERS |
| Deploy | Guiar estratégias de deploy: blue/green, canary, rolling; Docker → ECR; Web; Terraform |
| Relatórios | Gerar reports de auditoria em `.dadaia/reports/devops-engineer/` |

---

## Definição do Agente

**Arquivo canônico:** `dadaia_workspace/public/agents/devops-engineer.md`

| Campo | Valor |
|---|---|
| `name` | `devops-engineer` |
| `model` | `claude-opus-4-7` |
| `maxTurns` | 40 |
| `tools` | Read, Bash, Glob, Grep, Write, Edit |
| `skills` | `github-actions-pipelines`, `devops-gitflow-governance`, `devops-deploy-strategies` |

**Permissões (write):**
- `.dadaia/reports/devops-engineer/` — reports de auditoria
- `.github/workflows/` em qualquer repo ativo no workspace
- Arquivos de configuração CI/CD (`.github/`, `Makefile`, scripts de deploy)

**Proibições:**
- Jamais modifica código de aplicação (`dadaia_workspace/`, código de produto)
- Jamais modifica `specs/` ou qualquer arquivo de spec SDD
- Jamais toca em `repos/redacted-slug/` (domínio exclusivo do `game-developer`)
- Jamais modifica arquivos em `.claude/`, `.agents/`, `.codex/`, `.opencode/` que sejam lib-originated

---

## Requisitos Funcionais

- FR-001: O agente `devops-engineer` shall be defined in `dadaia_workspace/public/agents/devops-engineer.md` with complete YAML frontmatter.
- FR-002: O agente shall use the `github-actions-pipelines` skill for all GitHub Actions authoring and review.
- FR-003: O agente shall use the `devops-gitflow-governance` skill for all git flow and branch protection decisions.
- FR-004: O agente shall use the `devops-deploy-strategies` skill for all deployment pipeline decisions.
- FR-005: O agente shall write all audit reports to `.dadaia/reports/devops-engineer/`.
- FR-006: O agente shall scope pipeline complexity to match the project's actual size and criticality (no over-engineering).
- FR-007: O agente shall use `gh` CLI to inspect GitHub state, read job logs, and manage branch protection.
- FR-008: O agente shall be projected to all supported runtimes via `dadaia public install --target all`.

## Skills Requeridas

| Skill | Finalidade |
|---|---|
| `github-actions-pipelines` | Anatomia de workflows, triggers, matrix builds, OIDC, caching, reusable workflows |
| `devops-gitflow-governance` | Branching, branch protection, PR policy, CODEOWNERS, release process |
| `devops-deploy-strategies` | Docker/ECR, PyPI, Web (S3+CF, ECS), Terraform; blue/green, canary, rollback |

---

## Requisitos Não-Funcionais

- NFR-001: [Escopo restrito] O agente opera apenas sobre automação — nunca sobre lógica de negócio.
- NFR-002: [Complexidade mínima] Pipelines devem ser tão simples quanto o projeto exige. Complexidade injustificada é uma violação do escopo do agente.
- NFR-003: [Agnóstico de contexto] O agente pode operar em qualquer repo do workspace, não apenas no contexto primário ativo.

---

## Fora de Escopo (v1.0)

- Provisionamento de infraestrutura cloud (Terraform apply, AWS console)
- Configuração de ambientes de produção diretamente em servidores
- Código de aplicação, testes de produto, ou specs SDD
- Qualquer arquivo em `repos/redacted-slug/`
