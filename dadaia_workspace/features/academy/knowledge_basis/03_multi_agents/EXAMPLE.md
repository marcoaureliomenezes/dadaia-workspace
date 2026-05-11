# Exemplo Pratico - Desenhando um Pipeline de Revisao com Agents sem Overengineering

Vamos partir de um problema comum: revisar uma mudanca de codigo com qualidade e velocidade.

## Solucao ingenua 1: um prompt gigante para um unico chat

Funciona em casos simples, mas costuma falhar quando voce precisa:

- checar arquitetura;
- validar testes;
- procurar riscos de seguranca;
- sintetizar um parecer final.

## Solucao ingenua 2: montar um time de dez agents porque parece avancado

Isso costuma aumentar:

- custo;
- latencia;
- conflitos de contexto;
- dificuldade de sintese.

## Solucao madura inicial

Use o menor padrao que resolve o problema:

### Fase 1: planner

Um agent principal le a tarefa e decide o escopo da revisao.

Saida esperada:

- arquivos mais relevantes;
- quais riscos precisam de review especializado;
- se a tarefa cabe em um unico agent ou pede workers.

### Fase 2: workers em paralelo

So se o problema justificar, dispare especialistas independentes:

- `security-reviewer`
- `test-reviewer`
- `design-reviewer`

Cada um recebe um foco claro e devolve findings estruturados.

### Fase 3: evaluator ou synthesizer

Um agent final consolida os achados, remove duplicatas e prioriza severidade.

## Por que esse desenho e bom

Ele usa multi-agent apenas onde ha ganho real:

- especializacao;
- paralelismo;
- sintese posterior.

Mas evita um erro comum: usar agents se comunicando livremente sem stopping rules e sem dono do estado final.

## Checklist de desenho

Antes de subir para esse padrao, responda:

1. Um unico agent bem instrumentado resolveria?
2. Quais subtarefas sao realmente independentes?
3. Quem e dono do contexto compartilhado?
4. Quem encerra a execucao?
5. O que acontece se um worker falhar?

## O que este exemplo fixa

1. Multi-agent orchestration e uma alavanca, nao uma medalha.
2. O melhor desenho costuma ser incremental: planner, workers quando necessario, synthesizer.
3. Sem memoria, stopping condition e criterio de sintese, um time de agents vira caos caro.