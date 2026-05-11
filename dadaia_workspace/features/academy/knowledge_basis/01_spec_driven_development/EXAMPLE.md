# Exemplo Pratico - Saindo de um Pedido Vago para um Fluxo SDD Utilizavel

O objetivo deste exemplo e mostrar a menor versao util de SDD. Nao um ritual pesado. Um fluxo suficientemente claro para reduzir inferencia silenciosa.

## Pedido inicial ruim

```text
Quero uma feature para organizar cursos na Academy.
```

Esse pedido e insuficiente porque nao diz:

- para quem a feature existe;
- qual problema resolve;
- qual estrutura deve ser gerada;
- o que fica fora do escopo;
- quais contratos nao podem quebrar.

## Reescrevendo em formato de intencao

Antes de qualquer implementacao, a conversa precisa cristalizar algo assim:

```text
Quero uma feature chamada Dadaia Academy.
Ela deve operar em .dadaia/academy.
Ela deve oferecer sessoes numeradas em markdown.
Cada sessao deve conter README.md, EXAMPLE.md, REFERENCES.md e arquivos numerados.
O comando deve existir como slash command de agente e nao como novo subcomando do CLI congelado.
```

Agora ja existe material suficiente para gerar uma `SPEC.md` com fronteiras reais.

## Fase 1: `SPEC.md`

Aqui entram:

- contexto;
- user stories;
- requisitos funcionais;
- nao-funcionais;
- fora de escopo.

O foco ainda nao e tecnologia. E contrato.

## Fase 2: `PLAN.md`

Agora o sistema escolhe como implementar:

- onde os artefatos vao viver;
- como nomear as sessoes;
- se a feature toca CLI, slash commands ou apenas runtime;
- que documentos precisam ser atualizados.

## Fase 3: `TASKS.md`

Aqui o plano vira unidades pequenas e verificaveis, por exemplo:

1. atualizar spec principal do produto;
2. adicionar feature spec da Academy;
3. normalizar diretorios da Academy;
4. materializar a sessao 1;
5. materializar a sessao 2;
6. validar consistencia.

## Fase 4: implementacao

So depois disso o agente edita arquivos.

Esse encadeamento parece mais lento no inicio, mas em tarefas reais ele reduz:

- retrabalho;
- contradicoes;
- proliferacao de artefatos errados;
- e mudancas que parecem corretas, mas quebram contratos antigos.

## O que este exemplo fixa

1. SDD nao comeca em codigo; comeca em intencao estruturada.
2. O ganho nao e burocracia, e reducao de ambiguidade.
3. Um fluxo minimo de `SPEC -> PLAN -> TASKS -> implementacao` ja muda bastante a qualidade da execucao.
4. O valor real aparece quando o agente para de adivinhar e passa a operar sobre contratos.