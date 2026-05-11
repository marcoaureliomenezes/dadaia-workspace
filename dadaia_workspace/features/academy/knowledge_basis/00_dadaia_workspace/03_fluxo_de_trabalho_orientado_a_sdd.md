# 03. Fluxo de Trabalho Orientado a SDD

## O produto foi desenhado para impedir improviso

O `dadaia-workspace` assume uma ideia forte:

> o agente precisa operar sobre contratos explicitos, nao sobre intuicao.

Por isso, o workspace nao organiza apenas arquivos. Ele organiza um modo de trabalhar.

## O pipeline mental esperado

O fluxo canonico e este:

1. Entender o problema.
2. Especificar o que o sistema deve fazer.
3. Congelar as decisoes relevantes.
4. Planejar como implementar.
5. Quebrar em tarefas verificaveis.
6. So entao implementar.

No contexto do produto, isso se traduz em artefatos como:

- `constitution.md`
- `SPEC.md`
- `PLAN.md`
- `TASKS.md`

## Por que isso importa ainda mais com agentes

Um engenheiro humano, diante de ambiguidade, tende a perguntar.

Um agente, diante de ambiguidade, tende a inferir.

E essa inferencia quase sempre parece plausivel o bastante para passar despercebida por algum tempo.

O SDD existe para reduzir esse espaco de inferencia silenciosa.

## Como o dadoia-workspace operacionaliza isso

### 1. Contratos persistentes

As specs relevantes ficam acessiveis e reutilizaveis ao longo do tempo.

### 2. Contexto ativo explicito

O produto evita que o agente tente descobrir o foco do trabalho por adivinhacao.

### 3. Assets de agente com governanca

Rules e skills lembram o agente de que nem toda tarefa deve virar codigo imediatamente.

### 4. Academy no runtime

O aprendizado necessario para operar o sistema deixa de ficar espalhado e entra no proprio workspace.

## A ordem canonica de revisao

Quando uma tarefa afeta specs, a ordem de leitura importa. A ordem canonica atual e:

1. `constitution`
2. `memory/architecture`
3. `memory/product`
4. `memory/tech-stack`
5. `foundation/SPEC`
6. `specs/SPEC`
7. feature specs relevantes
8. `PLAN` e `TASKS`
9. `z_bug_specs`

Esse detalhe parece operacional, mas na pratica ele impede que documentos derivados passem a mandar mais do que os documentos donos do contrato.

## O que um usuario maduro faz depois desta sessao

Depois de entender o fluxo, o proximo passo nao e sair criando automacoes complexas.

O proximo passo e usar o workspace com disciplina:

- validar a estrutura do runtime;
- localizar o contexto certo;
- confirmar a governanca de specs;
- e so depois chamar agente, skill ou command para agir.

Esse e o ponto em que o workspace para de ser uma colecao de pastas e passa a funcionar como um sistema coerente.