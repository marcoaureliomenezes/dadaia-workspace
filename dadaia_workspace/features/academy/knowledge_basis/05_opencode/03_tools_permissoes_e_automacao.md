# 03. Tools, Permissoes e Automacao

## O modelo de tools e bastante explicito

Open Code lista claramente suas tools built-in e como controla o acesso a elas por permissions.

Entre as principais estao:

- `bash`
- `edit`
- `write`
- `read`
- `grep`
- `glob`
- `lsp` em modo experimental
- `apply_patch`
- `skill`
- `todowrite`
- `webfetch`
- `websearch`
- `question`

## Permissoes como contrato operacional

Em `opencode.json`, o campo `permission` permite definir se cada tool sera:

- `allow`
- `ask`
- `deny`

Esse design e importante porque ajuda a transformar risco em configuracao, nao em improviso durante a tarefa.

## Um detalhe especialmente util

A documentacao deixa claro que `write` e `apply_patch` sao controlados pela permissao `edit`.

Em outras palavras: se voce quer governar mudancas de arquivo, a chave mental principal e `edit`.

## `lsp` e automacao mais madura

O `lsp` ainda aparece como experimental, mas ja cobre operacoes importantes como definicoes, referencias, hover, symbols e call hierarchy.

Quando combinado com commands e skills, isso transforma o Open Code em algo bem mais interessante que um simples gerador de respostas.

## `websearch` versus `webfetch`

A propria documentacao faz uma distincao util:

- `websearch` para descoberta;
- `webfetch` para recuperar conteudo de uma URL especifica.

Essa separacao ajuda a desenhar prompts melhores e a controlar custo de contexto.

## Quando Open Code brilha mais

Open Code brilha quando voce quer:

1. padronizar workflows agentic por config;
2. tratar prompts como assets versionaveis;
3. combinar rules, commands, skills e permissions em uma mesma ergonomia;
4. operar em times que misturam interacao manual e automacao.

## Resumo executivo da sessao

Se Claude Code te ensina a operar bem uma sessao, Open Code te empurra um pouco mais na direcao de tratar essa operacao como sistema configuravel.