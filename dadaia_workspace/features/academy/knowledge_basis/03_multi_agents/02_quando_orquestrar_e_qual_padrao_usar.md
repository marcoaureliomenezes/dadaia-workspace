# 02. Quando Orquestrar e Qual Padrao Usar

## Regra zero: nao comece com multi-agent

O material interno e muito claro aqui: a maioria das equipes deveria comecar com o menor padrao que funciona.

O progresso normal costuma ser:

1. single prompt
2. prompt com saida estruturada
3. single agent com poucas tools
4. single agent com avaliacao
5. specialists e loops mais ricos
6. multi-agent de verdade

## Padroes principais

### 1. Single agent in a loop

Padrao inicial padrao. Bom para tarefas moderadas quando um contexto e suficiente.

### 2. Prompt chaining

Sequencia fixa de etapas. Otimo para pipelines previsiveis e auditaveis.

### 3. Routing

Um passo inicial classifica e manda o problema para o especialista ou caminho certo.

### 4. Parallelization

Subtarefas independentes rodam simultaneamente. Bom para breadth de revisao e economia de tempo.

### 5. Orchestrator and workers

Um coordenador dinamicamente quebra e delega o trabalho. Bom para problemas grandes com decomposicao incerta.

### 6. Evaluator and optimizer

Um produz, outro critica, o primeiro itera. Excelente quando qualidade importa mais que velocidade.

### 7. Planner, generator, evaluator

Padrao de alto leverage para engenharia. Primeiro delimita escopo, depois implementa, depois valida contra criterios.

### 8. Event-driven orchestration

Agents reagem a gatilhos e eventos. Faz sentido em ambientes mais assincronos e integrados a filas, logs ou automacoes operacionais.

## O que a referencia externa adiciona

O artigo do Medium resume quatro patterns que voce deve conseguir reconhecer sem hesitar:

- sequential
- parallel
- hierarchical
- event-driven

O artigo da IBM reforca a visao enterprise:

- nested agent calls;
- control flow com condicoes e retries;
- context propagation;
- catalogo reutilizavel de agents.

## Heuristica simples de escolha

Use single agent se:

- o problema cabe num contexto;
- ha um dono claro;
- o toolset e pequeno.

Adicione paralelismo se:

- subtarefas forem independentes;
- a sintese for simples;
- a latencia compensar o custo.

Adicione orchestrator se:

- a decomposicao so puder ser decidida durante a execucao;
- houver especialistas com papeis bem distintos.

Adicione event-driven se:

- o sistema reagir a mudancas assincronas do ambiente;
- o fluxo nao for naturalmente linear.

## O erro mais comum

Escolher o padrao pela sensacao de sofisticacao, e nao pela natureza do problema.