# PLAN — codex-runtime-agent-hotfix-v1

**Status:** Aprovado

## Estratégia

1. Declarar frontmatter mínimo e descritivo nas skills universais e Codex-only que o loader rejeita.
2. Ajustar a pipeline de public assets para copiar `runtime/` para `.dadaia/agentic/`.
3. Ajustar o renderer Codex de agent TOML para preservar `description`.
4. Acrescentar testes unitários de regressão para staging de runtime, skills com frontmatter e TOMLs Codex com descrição.
5. Regerar apenas projeções Codex necessárias por CLI, sem editar `.claude/**` diretamente.

## Arquivos previstos

- `dadaia_workspace/public/skills/*/SKILL.md`
- `dadaia_workspace/public/runtime/codex/*/SKILL.md`
- `dadaia_workspace/infrastructure/public_assets.py`
- `tests/unit/test_public_assets.py`
- `tests/unit/infrastructure/test_public_assets.py`

## Validação

- `.dadaia/.venv/bin/python -m pytest tests/unit/test_public_assets.py tests/unit/infrastructure/test_public_assets.py`
- `dadaia public stage`
- `dadaia public install --target codex --force`
- `dadaia public doctor`
