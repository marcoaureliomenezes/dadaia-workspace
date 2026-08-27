---
slug: quality-assurance
title: Quality Assurance
category: core
tldr: QA standards, anti-slop rules, and test discipline for this workspace.
summary: Documents QA standards, anti-slop laws, test discipline (TDD, no fabricated tests), and the pre-commit/pre-push gate sequence.
tags:
  - quality-assurance
  - testing
  - anti-slop
last_updated: "2026-08-12"
release_origin: v0.2.1
---

## Padrões de qualidade

**Base greenfield (vale até a primeira release consolidar padrões próprios):**

- TDD: todo comportamento novo nasce com um teste que falha primeiro; correção de bug
  reproduz o defeito em teste antes do fix.
- Testes rodam com `pytest -p no:cacheprovider` (nenhum cache dentro do repo) e devem
  passar verdes antes de qualquer commit de fechamento de task.
- Anti-slop: nenhum teste fabricado que não asserta comportamento real; nenhum
  requisito sem critério de aceitação observável (entrada, saída ou falha verificável
  de fora).
- Revisões julgam o artefato apresentado pelos critérios acima; num contexto novo, a
  ausência de histórico não é motivo de rejeição — o SPEC vigente define a base.

## Disciplina de testes

Tamanho por diretório: SMALL = `tests/unit` + `tests/contract`; MEDIUM =
`tests/integration`; LARGE = `tests/e2e`. Protocolo completo (intenção, admissão,
rebaixamento, poda, flaky/quarentena): skill `dadaia-test-stewardship`. Lei de nível de
projeto: constitution, seção "Disciplina de Testes".
