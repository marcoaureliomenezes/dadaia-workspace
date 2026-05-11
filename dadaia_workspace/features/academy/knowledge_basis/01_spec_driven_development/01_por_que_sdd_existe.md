# 01. Por Que SDD Existe

## O problema nao e a IA escrever codigo

O problema central apontado por varias referencias recentes e outro:

> a IA preenche lacunas com suposicoes silenciosas quando a intencao nao foi especificada com precisao suficiente.

Esse e o coracao do SDD.

## A transicao de "prompt-and-pray" para intencao estruturada

As referencias da DSA resumem isso bem: para prototipos simples, `vibe coding` pode parecer aceitavel. Para sistemas que precisam durar, isso falha rapido.

Quando o pedido e vago, a IA nao costuma negociar escopo como um engenheiro experiente faria. Ela tende a inferir.

O resultado e codigo plausivel, mas frequentemente errado em detalhes importantes.

## A especificacao como fonte de verdade

Na Parte 1 da serie da DSA, o argumento central e que estamos migrando de um modelo em que o codigo vence a documentacao para um modelo em que a especificacao vira artefato primario.

Isso nao significa que o codigo deixa de importar. Significa que ele passa a ser julgado contra a intencao explicita.

## Tres niveis uteis de maturidade

O artigo da Birgitta Bockeler ajuda a tirar a conversa da nebulosa. Ele separa SDD em tres niveis:

1. `spec-first`: escrever spec antes de codar.
2. `spec-anchored`: manter a spec viva ao longo da evolucao.
3. `spec-as-source`: tratar a spec como artefato principal e editar o codigo o minimo possivel manualmente.

Essa distincao e importante porque muita gente usa o termo SDD como se fosse uma coisa so.

## SDD nao substitui TDD ou BDD

Outra clarificacao importante: SDD opera acima dessas praticas.

- TDD ajuda a validar implementacao.
- BDD ajuda a descrever comportamento.
- SDD organiza a intencao e o pipeline para que a implementacao e a validacao nao nascam de adivinhacao.

## O principal ganho

SDD e, antes de tudo, uma tecnica para reduzir ambiguidade operacional quando humanos e agentes constroem software juntos.