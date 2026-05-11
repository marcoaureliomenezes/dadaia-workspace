# Exemplo Pratico - Rodando uma Tarefa Real com Claude Code

Este exemplo mostra um fluxo enxuto, mas maduro, para pedir uma alteracao em um projeto sem cair em prompt vago.

## Cenario

Voce quer introduzir uma nova feature em um workspace com specs e rules ja existentes.

Em vez de pedir apenas "implementa isso", voce quer preparar a sessao para que Claude Code opere com o contrato certo.

## Passo 1: Garanta que as instrucoes persistentes estao bem posicionadas

Claude Code le `CLAUDE.md` no startup e carrega `rules` conforme escopo e leitura de arquivos.

Checklist minimo:

- existe `CLAUDE.md` na raiz relevante;
- existe `.claude/rules/` para instrucoes modulares;
- nao ha conflitos obvios entre regras gerais e regras path-scoped.

Se a base ainda nao existe, o proprio Claude Code oferece `/init` para propor uma estrutura inicial.

## Passo 2: Entre em plan mode quando o problema ainda nao estiver bem fechado

Em vez de pular direto para implementacao, use:

```text
/plan adicionar uma nova sessao canonica na Dadaia Academy e ajustar as specs afetadas
```

Esse passo reduz inferencia prematura. O agente primeiro organiza abordagem, dependencias e impacto.

## Passo 3: Use a sessao para inspecionar contexto e ferramentas

Perguntas uteis no inicio:

- "Quais tools voce tem disponiveis nesta sessao?"
- "Quais arquivos de memoria e instrucoes foram carregados?"
- "Quais specs eu deveria ler antes de editar?"

Se houver duvida sobre memoria, abra `/memory`.

## Passo 4: Execute a mudanca em escopo pequeno e validado

Um bom prompt de implementacao costuma ter esta forma:

```text
Leia primeiro a spec principal, a arquitetura e a feature spec relevante. Depois implemente a mudanca minima necessaria, preserve o contrato atual da CLI, valide o resultado e me mostre os riscos restantes.
```

Esse framing obriga Claude Code a:

- construir contexto antes de editar;
- limitar o escopo;
- preservar contratos existentes;
- e reportar riscos, nao apenas diff.

## Passo 5: Use slash commands como alavanca, nao como muleta

Comandos como `/memory`, `/permissions`, `/diff`, `/tasks` e `/review` existem para reduzir friccao operacional.

O erro comum e achar que slash command substitui criterio. Nao substitui.

Ele acelera uma operacao, mas o framing tecnico continua sendo responsabilidade de quem conduz a sessao.

## O que este exemplo fixa

1. Claude Code funciona melhor quando recebe contrato e contexto antes de codigo.
2. `CLAUDE.md` guia comportamento, mas nao substitui configuracao enforced.
3. Slash commands aumentam produtividade quando usados dentro de um fluxo disciplinado.
4. O melhor prompt nao e o mais bonito; e o que reduz ambiguidade operacional.