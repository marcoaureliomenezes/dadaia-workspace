# SPEC — codex-runtime-agent-hotfix-v1

**Status:** Aprovado

## Contexto

O runtime Codex reporta falhas ao carregar skills e agents projetados pelo `dadaia-workspace`:

- Skills sem YAML frontmatter em `SKILL.md`.
- Agent role definitions Codex sem `description`.
- Runtime adapters Codex em `public/runtime/codex/` não entram no staging.

O operador aprovou esta hotfix em 2026-05-22 e esclareceu que a restrição é não alterar entidades/projeções Claude diretamente. A correção pode modificar os assets canônicos e a pipeline necessária para consertar o ambiente Codex.

## Escopo

- Corrigir `SKILL.md` canônicos que são carregados pelo Codex para conter YAML frontmatter válido.
- Garantir que runtime adapters Codex sejam staged e instalados a partir de `dadaia_workspace/public/runtime/codex/`.
- Garantir que `.codex/agents/*.toml` inclua `description` derivada do frontmatter canônico.
- Adicionar testes para impedir regressão de frontmatter e descrição em agents Codex.

## Fora de escopo

- Editar projeções Claude diretamente em `.claude/**`.
- Alterar personas de agentes Claude por motivo funcional não relacionado ao loader Codex.
- Fechar ou reescrever releases arquivadas.

## Critérios de aceite

- Nenhum `SKILL.md` citado no erro do Codex fica sem frontmatter.
- `dadaia public stage` inclui `runtime/codex/**` no manifest.
- `dadaia public install --target codex --force` gera TOMLs de agents com `description`.
- Testes unitários relevantes passam usando `.dadaia/.venv/bin/python`.
