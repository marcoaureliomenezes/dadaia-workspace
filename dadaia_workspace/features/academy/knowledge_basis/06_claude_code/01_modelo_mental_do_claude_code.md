# 01. Modelo Mental do Claude Code

## Claude Code nao e so um chat no terminal

Claude Code combina pelo menos quatro mecanismos que voce precisa distinguir:

1. Conversa atual.
2. Instrucoes persistentes via `CLAUDE.md` e `.claude/rules/`.
3. Auto memory.
4. Tools com permissao e efeitos concretos no ambiente.

Se voce mistura essas quatro camadas, fica dificil entender por que o agente agiu de um jeito e nao de outro.

## Contexto de conversa

Tudo que voce pede durante a sessao entra no contexto atual. Esse contexto e grande, mas nao infinito.

Por isso comandos como `/compact` existem: eles resumem a conversa para liberar espaco sem jogar fora o fio da tarefa.

## Instrucoes persistentes

`CLAUDE.md` e onde voce escreve o que deveria valer em toda sessao:

- padroes de codigo;
- comandos de build e test;
- arquitetura do projeto;
- workflows recorrentes.

As `rules` em `.claude/rules/` ajudam quando voce quer modularizar comportamento ou aplicar instrucoes apenas em certos caminhos.

Ponto importante: essas instrucoes entram como contexto, nao como enforcement duro.

## Auto memory

Auto memory e diferente de `CLAUDE.md`.

- `CLAUDE.md`: voce escreve regras e contexto intencional.
- auto memory: Claude salva learnings recorrentes para uso futuro.

Segundo a documentacao, o indice principal desse mecanismo e `MEMORY.md`, e apenas o inicio dele e carregado automaticamente em cada sessao. O restante fica sob leitura sob demanda.

Isso significa duas coisas:

1. memoria deve ser concisa;
2. memoria nao substitui projeto bem instruido.

## Tools sao capacidade operacional

Claude Code nao raciocina no vazio. Ele trabalha com tools explicitas como:

- `Read`
- `Edit`
- `Bash`
- `LSP`
- `WebFetch`
- `Monitor`
- `Skill`

Cada uma altera o que o agente pode verificar, editar, observar ou automatizar.

Quando a sessao parece inteligente de verdade, normalmente e porque o conjunto de tools e o framing estavam certos.

## Regra pratica

Quando algo parecer estranho, pergunte a si mesmo:

- faltou contexto?
- faltou instrucao persistente?
- faltou memoria relevante?
- ou faltou a tool adequada?

Esse diagnostico e mais util do que discutir se o agente foi "bom" ou "ruim".