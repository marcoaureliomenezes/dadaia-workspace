# PLAN: task-state-tracking v0.1

> Endereça `specs/features/task-state-tracking/SPEC.md`.

## Sequência

1. Criar `dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md` com o protocolo de 4 passos.
2. Atualizar os 6 agents em `dadaia_workspace/public/agents/*.md` para incluir `dadaia-task-manager` em `skills:`.
3. Amend em `specs/foundation/SPEC.md`: adicionar seção "Task State Contract" listando os 3 markers como contrato normativo.
4. Atualizar `tests/e2e/features/test_public_pipeline.py::EXPECTED_SKILLS` adicionando `dadaia-task-manager`.
5. `dadaia public stage && dadaia public install --target all --force`.
6. Validar `dadaia public doctor` reporta `[ok]` para a skill em todos os 4 alvos.

## Sem mudanças em Python

A feature é 100% asset-only.
