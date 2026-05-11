# 03. Guardrails, Memoria e Governanca

## Multi-agent sem guardrails vira entropia acelerada

Quanto mais agents voce adiciona, mais forte fica a necessidade de governanca.

As referencias do Azure e do material interno convergem nisso: agente serio precisa de runtime, observabilidade, identidade, seguranca e memoria com desenho explicito.

## Memoria nao e um detalhe secundario

O Azure destaca algo importante: memoria de agent nao e so "historico de chat".

Ela precisa sustentar:

- continuidade entre passos;
- fatos aprendidos;
- estado operacional;
- contexto compartilhado quando varios agents colaboram;
- separacao quando cada agent precisa manter sua propria persona ou historico.

Em outras palavras: memoria pode ser compartilhada, isolada ou hibrida. E essa escolha muda o comportamento do sistema.

## O que precisa ser observavel

Se voce nao consegue responder o que cada agent fez, quando fez e por que fez, voce nao tem um sistema confiavel.

Minimo desejavel:

- trace das decisoes importantes;
- logs de tool calls;
- estado de execucao;
- erros e retries;
- criterio de sucesso ou falha final.

## Guardrails praticos

Boas perguntas de governanca:

1. Quais tools cada agent pode usar?
2. Quais dados cada agent pode enxergar?
3. Quais acoes exigem aprovacao humana?
4. Qual criterio impede loops infinitos?
5. Quem publica o output final?

## Governanca enterprise versus hobby project

No enterprise, entram camadas adicionais:

- identidade;
- RBAC;
- isolamento de rede;
- filtros de seguranca;
- versionamento de agent;
- publicacao controlada;
- avaliacao continua.

Mesmo em projetos menores, o principio e o mesmo: autonomia deve ser bounded.

## Regra final desta sessao

Um system de agents so e maduro quando sua orquestracao deixa claro:

- quem decide;
- quem executa;
- quem lembra;
- quem valida;
- e quem para.

Sem isso, voce nao tem orquestracao. Tem apenas varias fontes de comportamento dificil de auditar.