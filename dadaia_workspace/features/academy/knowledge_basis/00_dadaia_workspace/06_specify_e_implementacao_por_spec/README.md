# Sessao 6: Specify e Implementacao por Spec

Esta sessao transforma SDD de teoria em workflow operacional.

A Sessao 4 mostrou o modelo mental e os artefatos. Aqui voce vai executar o ciclo completo: do `constitution` ao `TASKS.md`, com aprovacao humana em cada fase, dentro da estrutura real do `dadaia-workspace`.

O objetivo e que voce termine sabendo conduzir uma implementacao sem prompt solto — usando specs como instrucao primaria e o agente como executor verificavel.

## O que voce vai dominar

1. O pipeline SDD completo: Foundation → Specify → Plan → Tasks → Implement com aprovacao humana em cada transicao.
2. Como escrever specs executaveis — que o agente segue sem inferencia silenciosa.
3. Como usar `constitution.md`, `memory/`, feature specs e `TASKS.md` em sequencia correta.
4. Como o layout real de `dadaia-workspace` materializa esse fluxo no runtime do usuario.

## Ordem sugerida

1. [01_o_fluxo_sdd_completo.md](./01_o_fluxo_sdd_completo.md)
2. [02_escrevendo_specs_executaveis.md](./02_escrevendo_specs_executaveis.md)
3. [03_implementacao_guiada_por_spec_no_dadaia_workspace.md](./03_implementacao_guiada_por_spec_no_dadaia_workspace.md)
4. [EXAMPLE.md](./EXAMPLE.md)
5. [EXERCISES.md](./EXERCISES.md)
6. [REFERENCES.md](./REFERENCES.md)

## Resultado esperado

Ao final desta sessao, voce deve conseguir:

- Pegar uma intencao vaga e transformar em uma `SPEC.md` com fronteiras reais.
- Conduzir o agente atraves das fases de plano e tasks sem pular aprovacoes humanas.
- Usar os commands `/work-on-spec` e `/dadaia-academy` como entrada do workflow, nao como atalho de chat.
- Identificar quando uma spec esta incompleta antes de comecar a implementacao.
