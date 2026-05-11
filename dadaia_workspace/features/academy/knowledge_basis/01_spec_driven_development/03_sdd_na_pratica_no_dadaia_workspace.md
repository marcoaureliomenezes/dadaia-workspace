# 03. SDD na Pratica no Dadaia Workspace

## O produto ja foi moldado para esse fluxo

O `dadaia-workspace` nao trata SDD como um anexo. A propria estrutura do produto ja reserva espaco para ele.

Os sinais mais claros sao:

- `specs/constitution.md`
- `specs/SPEC.md`
- `specs/PLAN.md`
- `specs/TASKS.md`
- `specs/memory/`
- feature specs especializadas

## O padrao interno e explicito

O documento `docs/sdd_patterns.md` deixa o contrato ainda mais claro:

- nenhuma fase comeca sem aprovacao humana da fase anterior;
- `constitution` e always-on;
- `memory` guarda contexto permanente;
- specs podem escalar de projeto simples para `foundation`, `domains` e `features`.

## Ordem de revisao importa

Na pratica do workspace, voce nao deve tratar todos os documentos como equivalentes.

Primeiro vem o contrato mais estavel. Depois o derivado.

Uma ordem madura costuma ser:

1. `constitution`
2. `memory/architecture`
3. `memory/product`
4. `memory/tech-stack`
5. spec global
6. feature specs
7. `PLAN`
8. `TASKS`

Essa ordem impede que um plano local reescreva silenciosamente um contrato global.

## O que muda no trabalho com agentes

Quando o agente entra num workspace desses, o objetivo nao e pedir "faz isso".

O objetivo e enquadrar a tarefa assim:

- qual contrato governa o problema;
- qual feature spec manda;
- quais decisoes ja estao congeladas;
- e o que ainda precisa de aprovacao humana.

## O papel da Academy dentro desse desenho

A Dadaia Academy reforca esse modelo porque transforma o proprio runtime em ambiente de aprendizagem operacional.

Ou seja: aprender a usar SDD nao depende de sair do workspace. O workspace passa a ensinar a propria disciplina que espera dos agentes e usuarios.

## Regra final desta sessao

SDD no Dadaia Workspace nao e uma camada decorativa de documentos. E o mecanismo de coordenacao entre intencao, implementacao e governanca.