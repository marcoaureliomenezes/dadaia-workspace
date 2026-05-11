# Exercicios e Checkpoints — Sessao 4: SDD Quick Start

Estes exercicios transformam o entendimento teorico de SDD em pratica verificavel.
O objetivo e chegar ao fim desta sessao com uma spec real escrita, nao apenas lida.

---

## Exercicio 1 — Audite um Pedido Vago

**Objetivo:** Identificar o que falta em um pedido tipico de vibe coding antes de enviar para o agente.

**Instrucao:**

Aqui esta um pedido real que alguem poderia enviar sem SDD:

```text
"Cria um novo script que processa os dados da API e salva no banco."
```

Liste pelo menos 5 perguntas que esse pedido deixa sem resposta.
Para cada pergunta, escreva o que o agente vai ter que assumir silenciosamente se voce nao responder.

**Criterio de validacao:**

Voce passou se conseguiu identificar pelo menos 5 lacunas.
Exemplos de lacunas esperadas: qual API, qual endpoint, qual schema de entrada, qual banco, qual tabela, qual formato de saida, qual tratamento de erro, quais casos de borda.

---

## Exercicio 2 — Escreva uma Feature Spec Minima

**Objetivo:** Transformar uma intencao vaga em um `SPEC.md` utilizavel.

**Instrucao:**

Escolha uma feature pequena — pode ser ficticia — e escreva um `SPEC.md` com pelo menos:

- Titulo e versao
- Contexto (1 paragrafo)
- User story principal (formato "Como X, quero Y, para Z")
- 3 requisitos funcionais (RF-001, RF-002, RF-003)
- 1 requisito nao-funcional (RNF-001)
- Fora de escopo (pelo menos um item)

**Criterio de validacao:**

Sua spec esta utilizavel se qualquer pessoa — ou agente — consegue implementar sem te perguntar nada alem de detalhes cosmeticos.
Se alguem precisar perguntar algo fundamental, a spec esta incompleta.

---

## Exercicio 3 — Ordene os Documentos

**Objetivo:** Verificar se voce internalizou a ordem de revisao de artefatos SDD.

**Instrucao:**

Os documentos abaixo estao fora de ordem. Coloque-os na ordem correta de revisao antes de comecar uma implementacao:

```
PLAN.md
feature spec especifica
TASKS.md
memory/tech-stack.md
constitution.md
SPEC.md (global)
memory/architecture.md
```

**Criterio de validacao:**

Ordem correta: `constitution` → `memory/architecture` → `memory/tech-stack` → `SPEC.md` (global) → feature spec → `PLAN.md` → `TASKS.md`

Se voce errou a ordem, releia `03_sdd_na_pratica_no_dadaia_workspace.md`.

---

## Exercicio 4 — Fluxo Real com /work-on-spec

**Objetivo:** Aplicar SDD dentro do workspace usando o command canonico.

**Instrucao:**

Use a feature spec que voce escreveu no Exercicio 2.
Salve num diretorio de rascunho em `.dadaia/tmp/` (nao em `specs/` real ainda).

No Claude Code, invoque:

```
/work-on-spec
```

Siga o fluxo e observe como o agente:
1. Carrega o contexto da spec
2. Propoe um `PLAN.md`
3. Aguarda aprovacao humana antes de avancar
4. Gera `TASKS.md` somente apos aprovacao do plano

**Criterio de validacao:**

Voce passou se observou pelo menos um ponto de aprovacao humana no fluxo.
Se o agente pulou alguma fase sem pedir aprovacao, isso e um sinal de que a spec estava incompleta ou o command nao foi seguido corretamente.

---

## Checkpoint Final — Sessao 4

Voce esta pronto para avancar para a Sessao 5 se:

- [ ] Consegue listar pelo menos 5 lacunas em um pedido vago
- [ ] Escreveu um `SPEC.md` com todos os elementos minimos
- [ ] Sabe a ordem correta de revisao dos artefatos SDD
- [ ] Observou pelo menos um ponto de aprovacao humana num fluxo real com `/work-on-spec`

Se algum item ficou incompleto, volte para o modulo especifico antes de continuar.
