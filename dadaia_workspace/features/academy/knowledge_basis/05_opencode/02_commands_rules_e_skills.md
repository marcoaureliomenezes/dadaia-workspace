# 02. Commands, Rules e Skills

## Commands customizados sao parte central do produto

A documentacao do Open Code deixa claro que commands customizados sao assets de primeira classe.

Voce pode defini-los:

- em `.opencode/commands/*.md`;
- em `~/.config/opencode/commands/*.md`;
- ou via JSON em `opencode.json`.

## Por que isso e poderoso

Cada command pode carregar:

- `description` para aparecer na UI;
- `agent` para selecionar quem executa;
- `model` para override de modelo;
- `subtask` para forcar subagent;
- placeholders como `$ARGUMENTS`, `$1`, `$2`;
- `@arquivo` para injetar arquivos;
- `!comando` para injetar shell output.

Isso permite empacotar workflows completos em markdown legivel.

## Rules no Open Code

O mecanismo principal de regras e `AGENTS.md`.

Ele pode existir:

- no projeto;
- globalmente em `~/.config/opencode/AGENTS.md`.

O Open Code tambem oferece compatibilidade com convencoes do Claude Code:

- `CLAUDE.md`
- `~/.claude/CLAUDE.md`
- `.claude/skills/`

Essa compatibilidade e muito relevante para ambientes como este workspace, que ja tratam `.claude/` como ambiente importante de agentes.

## Precedencia importa

Quando o Open Code sobe, ele busca arquivos de regras com precedencia definida. Se houver `AGENTS.md` e `CLAUDE.md`, `AGENTS.md` vence naquela categoria.

Isso significa que migracoes parciais exigem clareza: manter dois centros concorrentes de instrucao tende a criar confusao se voce nao souber qual deles esta ativo.

## Skills no Open Code

Skills sao definidas por `SKILL.md` dentro de diretorios nomeados.

A descoberta suporta varios caminhos, inclusive:

- `.opencode/skills/<name>/SKILL.md`
- `.claude/skills/<name>/SKILL.md`
- `.agents/skills/<name>/SKILL.md`

Ou seja: skills tambem servem como ponto de convergencia entre ecossistemas.

## Regra pratica

Se o workflow precisa ser disparado explicitamente por slash command, pense em command.

Se o workflow precisa ser uma capacidade reutilizavel carregada sob demanda, pense em skill.

Se o comportamento precisa valer como instrucoes persistentes do projeto, pense em `AGENTS.md` ou nas instrucoes configuradas via `opencode.json`.