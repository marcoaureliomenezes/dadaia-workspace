---
slug: tech-stack
title: Tech Stack
category: core
tldr: Linguagens, runtimes e dependências do workspace.
summary: Documenta Python 3.12, Poetry, mistune, e demais dependências de runtime e dev.
tags: [tech-stack, python, dependencies]
agent_tier: inject
token_estimate: 280
last_updated: "2026-06-01"
release_origin: memory-markdown-source-v1
---

## Propósito

Documentação das tecnologias usadas no workspace.

## Stack principal

| Linguagem | Versão | Uso |
|-----------|--------|-----|
| Python | 3.12 | Runtime principal |
| Bash | 5.x | Scripts de infraestrutura |

## Dependências runtime

| Pacote | Versão | Camada | Justificativa |
|--------|--------|--------|--------------|
| mistune | ~3.0 | features/panel | Renderizador Markdown para memória |
| jinja2 | ^3.1 | features | Templates HTML |
| pyyaml | ^6.0 | core | Parsing de YAML |

## Estado runtime tocado

- `.dadaia/.venv/` — virtual environment gerenciado pelo Poetry

## Dependências

- Python 3.12+
- Poetry para gestão de dependências
