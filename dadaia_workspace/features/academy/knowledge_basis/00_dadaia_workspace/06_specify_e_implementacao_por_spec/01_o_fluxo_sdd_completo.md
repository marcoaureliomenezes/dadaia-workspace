# 01. O Fluxo SDD Completo

## O problema que SDD resolve

Quando um agente recebe um pedido ambiguo, ele nao para para perguntar.
Ele infere. E as inferencias silenciosas acumulam debito tecnico invisivel.

O SDD (Spec-Driven Development) existe para eliminar a inferencia silenciosa antes da implementacao.

## As cinco fases

O pipeline completo tem cinco fases. Cada uma e travada por aprovacao humana.

```
Foundation → Specify → Plan → Tasks → Implement
```

Nenhuma fase comecar sem aprovacao humana da anterior. Isso nao e burocracia: e o que separa execucao confiavel de vibe coding.

### Fase 0 — Foundation

**O que e:** Artefatos permanentes que governam todo o projeto.

Inclui:

- `constitution.md` — leis imutatveis do projeto
- `memory/architecture.md` — decisoes de arquitetura consolidadas
- `memory/product.md` — visao e proposito do produto
- `memory/tech-stack.md` — stack aprovada e restricoes tecnologicas

**Quem escreve:** O arquiteto humano. Nao o agente.

**Quando muda:** Raramente. Requer revisao e consenso.

**Por que importa:** Foundation e o que o agente LE antes de qualquer implementacao. Se foundation esta desatualizado, o agente parte de premissas erradas.

### Fase 1 — Specify

**O que e:** A descricao precisa do que deve ser construido.

Inclui:

- `SPEC.md` — comportamento esperado, requisitos funcionais, nao-funcionais, fora de escopo
- Feature specs especializadas quando o projeto tem multiplas areas

**Quem escreve:** O humano, com ou sem ajuda do agente.

**Regra critica:** O agente so pode sugerir. Voce aprova ou rejeita.

**Como saber se a spec esta pronta:** Qualquer pessoa consegue implementar sem te perguntar nada substantivo.

### Fase 2 — Plan

**O que e:** A descricao de COMO a spec vai ser implementada.

Inclui:

- `PLAN.md` — decisoes de design, estrutura de arquivos, dependencias, riscos

**Quem escreve:** O agente, com base na spec aprovada.

**Quem aprova:** Voce. Antes de qualquer codigo ser escrito.

**O que deve aparecer no plano:**
- Quais arquivos serao criados, modificados ou deletados
- Dependencias entre mudancas
- Riscos tecnicos ou de reversibilidade

### Fase 3 — Tasks

**O que e:** O plano quebrado em unidades pequenas e verificaveis.

Inclui:

- `TASKS.md` — lista numerada de tarefas com criterio de conclusao

**Quem escreve:** O agente, com base no plano aprovado.

**Quem aprova:** Voce.

**O que deve aparecer em cada task:**
- O que fazer (acao concreta)
- O que verifica conclusao (criterio observavel)
- Se a task e dependente de outra

### Fase 4 — Implement

**O que e:** A execucao das tasks aprovadas.

O agente executa. Voce revisa a PR ou os arquivos gerados.

**Regra de ouro:** O agente so implementa o que esta em `TASKS.md`. Nada mais.

Se o agente adicionar algo que nao estava nas tasks, isso e drift — e precisa voltar para revisao de spec.

---

## Os tres niveis de maturidade SDD

| Nivel | Nome | Descricao |
|---|---|---|
| 1 | Spec-First | Spec escrita antes da IA gerar codigo; pode ser descartada apos |
| 2 | Spec-Sync | Spec e mantida em sincronia com o codigo ao longo do tempo |
| 3 | Spec-Native | Spec e a fonte de verdade; codigo e testes sao derivados dela |

Comece no Nivel 1. Avance para o Nivel 2 em projetos de media duracao.
O Nivel 3 e para sistemas onde a especificacao e tao central que qualquer mudanca comeca por ela.

---

## Por que aprovacao humana em cada fase

Cada aprovacao humana e uma barreira contra:

- o agente interpretar a spec de forma diferente do que voce pretendia;
- o plano escalar para fora do escopo;
- tasks serem escritas de forma ambigua e gerarem implementacoes diferentes do esperado.

Sem esses pontos de parada, o agente e rapido — mas rapido na direcao errada.
