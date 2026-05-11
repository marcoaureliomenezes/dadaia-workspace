# 02. Artefatos e Escrita Executavel

## Nem todo markdown e uma spec

Um dos pontos mais uteis do artigo da Birgitta e separar `specs` de `memory bank`.

- `memory bank` guarda contexto amplo do projeto.
- `spec` descreve a mudanca ou funcionalidade relevante para uma tarefa especifica.

Se voce mistura tudo, o agente perde foco.

## O conjunto minimo de artefatos

As referencias externas e o padrao interno do `dadaia-workspace` convergem em quatro artefatos chave:

### `constitution.md`

Define leis permanentes: arquitetura, seguranca, convencoes, workflow.

### `SPEC.md`

Define o que deve ser feito e por que.

### `PLAN.md`

Traduz intencao em estrategia tecnica.

### `TASKS.md`

Quebra o plano em unidades pequenas, ordenadas e verificaveis.

## EARS, GEARS e disciplina de linguagem

Na Parte 2 da serie da DSA, a precisao de escrita vira tema central. A ideia de EARS e GEARS e simples: reduzir ambiguidade por meio de padroes de frase que tornam requisitos mais parseaveis para humanos e LLMs.

Exemplo de evolucao:

- vago: "o sistema deve ser rapido"
- melhor: "quando o usuario solicitar a listagem, o sistema deve responder em ate 2 segundos"

Quanto mais verificavel e contextualizado o requisito, menor a margem para improviso silencioso.

## Markdown como lingua franca

As referencias destacam por que markdown venceu esse espaco:

- boa densidade semantica por token;
- hierarquia natural por cabecalhos;
- facilidade para combinar texto, tabelas, blocos de codigo e diagramas.

Mas isso nao e uma desculpa para verbosidade sem criterio.

## O alerta importante

O Technology Radar da Thoughtworks e a analise de Birgitta chamam atencao para o outro lado: alguns workflows SDD geram artefatos longos, repetitivos e dificeis de revisar.

Ou seja: o problema nao se resolve trocando revisao de codigo por revisao de markdown em massa.

Boa spec nao e a mais longa. E a que reduz ambiguidade sem inflar o custo de revisao.