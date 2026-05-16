# PLAN: sdd-enforcement v0.1

> Endereça `specs/features/sdd-enforcement/SPEC.md`.

## Sequência

1. Reescrever `dadaia_workspace/public/scripts/sdd-spec-gate.sh` para v2:
   - manter case dos paths VPS (compat);
   - adicionar case `$WS/repos/$PRIMARY_SLUG/*`;
   - substituir verificação "SPEC.md aprovado" por busca por `^\s*-\s*\[-\]\s+` em `$PRIMARY_SPECS_DIR/TASKS.md` ou `$PRIMARY_SPECS_DIR/features/*/TASKS.md`;
   - mensagens orientadas por intenção.
2. `dadaia public stage && dadaia public install --target all --force` para distribuir.
3. Estender `tests/integration/test_hooks.py` com 4 casos:
   - block: primary ativo, zero `[-]`, file_path em `repos/<primary>/`
   - pass: primary ativo, ≥1 `[-]`, mesmo file_path
   - pass (fail-open): sem `primary_context.json`
   - pass: file_path fora de produção (ex: README.md)

## Sem dependências em Python

Implementação 100% em bash. Nenhuma mudança em `dadaia_workspace/`.

## Aceite

- Tests passam; gate v2 instalado; `dadaia public doctor` reporta `[ok]` para o script.
