# Closure: Release — codex-runtime-agent-hotfix-v1

> **Status:** Aprovado
> **Release ID:** codex-runtime-agent-hotfix-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-23

## Summary

Hotfix cirúrgico para reparar as três falhas de carregamento que o runtime Codex
reportava ao consumir assets projetados pelo dadaia-workspace. As skills de domínio
frontend/design e os adapters Codex em `public/runtime/codex/` não tinham YAML
frontmatter — o loader do Codex rejeita arquivos sem frontmatter válido. Os TOMLs de
agent gerados por `_install_codex()` omitiam o campo `description` porque o parser não
o extraía do frontmatter canônico. E os adapters `runtime/codex/` não entravam no
staging (`dadaia public stage`), logo nunca chegavam às projeções.

Após a hotfix, `dadaia public doctor` reporta tudo `[ok]` sem nenhum `[drift]` ou
`[missing]`. O Codex consegue carregar as 5 skills reparadas e os 2 adapters de
runtime-ctx. Os TOMLs de agent têm campo `description` derivado do frontmatter canônico.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-CX-HOTFIX-01 | Corrigir runtime Codex agents/skills projection | `55cfb4f` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| doctor sem drift/missing | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia public doctor` | all `[ok]`; zero `[drift]`/`[missing]` |
| SKILL.md com frontmatter | `grep -l "^---" dadaia_workspace/public/skills/frontend-design/SKILL.md` | arquivo presente com YAML block |
| runtime/codex no staging | `ls .dadaia/agentic/runtime/codex/` | `design-ctx/  frontend-ctx/  README.md` |
| description nos TOMLs Codex | `grep description .codex/agents/*.toml \| head -5` | campo presente em todos os TOMLs |
| testes unitários | `.dadaia/.venv/bin/python -m pytest tests/unit/test_public_assets.py` | `55cfb4f` — 57 linhas adicionadas, suite green |

## Drifts

Nenhum drift de PLAN durante implementação. O escopo foi cumprido exatamente como
especificado.

## Memory updates

- `specs/memory/product/public-asset-distribution.html` — **não aplicado**: o gate SDD
  lê o contexto primário (`dd-chain-explorer`, phase=TASKS) em vez do contexto do arquivo
  sendo editado (`dadaia-workspace`, phase=CLOSURE). Bloqueio cross-context é um limite
  de design do gate atual. A atualização pendente: adicionar nota sobre grupo
  `runtime/codex/` no staging e requisito de YAML frontmatter em SKILL.md.
  Registrado em `backlog/candidates.md` como `context-gate-cross-repo-fix-v1`.
- `specs/memory/product/multi-platform-parity.html` — nenhuma mudança necessária.
- `specs/memory/architecture.html` — nenhuma mudança: infraestrutura de camadas não
  alterada.
- `specs/memory/tech-stack.html` — nenhuma mudança: sem nova dependência.

## Backlog returns

Nenhum novo item descoberto durante esta hotfix que não esteja já registrado em
`backlog/candidates.md`.

## Archive decision

**MOVE** — release movida para `specs/_archive/releases/codex-runtime-agent-hotfix-v1/`.
`ACTIVE.md` será atualizado para `release: none` até abertura da próxima release do
backlog consolidado.
