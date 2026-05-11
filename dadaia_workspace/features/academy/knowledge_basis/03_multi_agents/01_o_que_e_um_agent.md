# 01. O Que e um Agent

## Um agent nao e um chatbot com marketing melhor

Um ponto recorrente nas referencias internas e externas e este: um agent precisa agir, observar e decidir se terminou.

Em termos praticos, um agent:

1. recebe um objetivo;
2. decide o proximo passo;
3. usa tools ou acoes estruturadas;
4. observa o resultado do ambiente;
5. continua ate atingir uma condicao de parada.

## Componentes minimos

As referencias do Azure e do material interno convergem em um nucleo simples:

- `model`
- `instructions`
- `tools`

Na pratica real, quase sempre voce tambem precisa de:

- memoria ou estado;
- run loop;
- stopping conditions;
- safety constraints;
- observabilidade.

## Tipos uteis de agent

### Copilot

Ajuda o usuario, mas nao opera com alta autonomia.

### Autonomous agent

Consegue planejar e agir em varios passos com menor dependencia de confirmacao humana.

### Multi-agent system

Varios agents especializados colaboram ou se coordenam para atingir um objetivo maior.

## Agent versus workflow

Essa diferenca e essencial.

### Workflow

O caminho ja esta definido por voce.

Exemplo:

1. resumir
2. classificar
3. encaminhar

### Agent

O caminho e decidido durante a execucao.

Exemplo:

1. ler o bug report;
2. escolher quais arquivos abrir;
3. rodar testes;
4. investigar logs;
5. decidir se precisa de esclarecimento;
6. propor ou implementar a correcao.

## Quatro perguntas obrigatorias

Se voce nao consegue responder estas perguntas, ainda nao desenhou bem o agent:

1. Que decisao o model realmente esta tomando?
2. Qual ground truth do ambiente ele enxerga?
3. O que encerra a execucao?
4. O que acontece quando falha?

Sem isso, a autonomia vira ficcao confiante.