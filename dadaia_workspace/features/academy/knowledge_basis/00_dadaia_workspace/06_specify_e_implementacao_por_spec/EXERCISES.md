# Exercicios e Checkpoints — Sessao 6: Specify e Implementacao por Spec

Estes exercicios fecham o ciclo. Voce vai praticar cada fase do pipeline SDD de forma verificavel.

---

## Exercicio 1 — Releia Foundation Antes de Especificar

**Objetivo:** Criar o habito de revisar artefatos permanentes antes de comecar qualquer spec.

**Instrucao:**

Execute no terminal ou via agente:

```bash
cat dadaia-workspace/specs/constitution.md | head -60
cat dadaia-workspace/specs/memory/tech-stack.md
```

Anote as duas restricoes mais relevantes para uma feature que voce esta considerando implementar.

**Criterio de validacao:**

Voce passou se as restricoes que anotou sao de `constitution` ou `memory`, nao de uma feature spec.
Se anotou apenas detalhes de implementacao, releia o modulo `01_o_fluxo_sdd_completo.md`.

---

## Exercicio 2 — Escreva uma Spec Real para o Seu Workspace

**Objetivo:** Produzir uma `SPEC.md` para uma feature pequena que voce realmente quer implementar.

**Instrucao:**

Escolha uma melhoria ou feature nova para o seu workspace — pode ser um novo command, uma nova sessao da Academy, uma automacao simples.

Escreva `SPEC.md` em `.dadaia/tmp/` (rascunho) com todos os elementos obrigatorios:

- Titulo e versao
- Contexto
- User story principal
- RF-001, RF-002, RF-003
- RNF-001
- Fora de escopo (pelo menos dois itens)
- Criterio de conclusao

**Criterio de validacao:**

Peca para outra pessoa ou para o agente identificar o que ficou ambiguo.
Se o agente ou colega precisar te perguntar algo substantivo para implementar, a spec esta incompleta.

---

## Exercicio 3 — Execute o Ciclo com /work-on-spec

**Objetivo:** Conduzir o pipeline SDD completo em um caso real.

**Instrucao:**

Use a spec que voce escreveu no Exercicio 2.

1. Mova-a para `specs/features/[nome-da-feature]/SPEC.md` se considerar aprovada.
2. Invoque o command:

```text
/work-on-spec
```

3. Aguarde o `PLAN.md`. Nao aprove automaticamente.
4. Revise o plano com pelo menos duas perguntas:
   - O agente esta planejando algo fora do escopo da spec?
   - O plano menciona riscos?
5. Se o plano estiver correto, aprove e aguarde o `TASKS.md`.
6. Revise cada task com o mesmo criterio.

**Criterio de validacao:**

Voce passou se:

- Observou pelo menos um ponto de aprovacao humana real (voce nao deixou o agente passar automaticamente)
- Identificou e corrigiu pelo menos uma imprecisao no plano ou nas tasks
- O agente implementou apenas o que estava nas tasks aprovadas

---

## Exercicio 4 — Detecte Drift

**Objetivo:** Identificar quando o agente saiu do escopo aprovado e saber o que fazer.

**Instrucao:**

Revise o output do exercicio anterior.

Responda:

1. O agente criou, modificou ou deletou algo que nao estava nas tasks?
2. Se sim, isso e considerado drift — o que voce deve fazer com esse codigo?
3. Como voce poderia ter prevenido esse drift antes da implementacao comecar?

**Criterio de validacao:**

- Se houve drift: o codigo deve ser revertido ou uma nova task deve ser criada, revisada e aprovada antes de manter.
- Prevencao: tasks mais precisas com criterios de conclusao verificaveis elimina a maior parte do drift.

---

## Checkpoint Final — Sessao 6

Voce domina o ciclo SDD no dadaia-workspace se:

- [ ] Rele foundation antes de escrever qualquer spec
- [ ] Consegue escrever um `SPEC.md` que elimina perguntas substantivas
- [ ] Conduz o ciclo completo com aprovacoes humanas em cada fase
- [ ] Identifica e corrige drift antes de aceitar o codigo

Se algum item ficou incompleto, este e o momento de voltar — nao de avancar.
O ciclo SDD tem fraqueza na entrada: se a spec for fraca, todas as fases seguintes amplificam o problema.

---

## Checkpoint da Trilha Completa

Se voce chegou ate aqui com todos os checkpoints das sessoes 1 a 6 preenchidos:

- [ ] Sessao 1: sabe o que o workspace organiza
- [ ] Sessao 2: opera Claude Code com disciplina suficiente
- [ ] Sessao 3: usa Open Code em modo interativo e nao interativo
- [ ] Sessao 4: entende SDD como artefato operacional, nao como burocracia
- [ ] Sessao 5: tem criterio para escolher arquitetura de agent
- [ ] Sessao 6: conduz implementacao por spec de ponta a ponta

Voce passou da fase de onboarding. A partir daqui, o aprendizado acontece na pratica.
Use `/dadaia-academy` para navegar material adicional ou sugerir novas sessoes.
