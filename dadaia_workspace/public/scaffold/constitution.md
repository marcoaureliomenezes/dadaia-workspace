---
specs_pattern_version: 4
---
# Constitution: <Project Name>

> Este documento define as leis imutáveis que governam todo o desenvolvimento de <project-name>.
> Todo agente de IA trabalhando neste projeto DEVE seguir estas regras em toda tarefa.
> Atualizado apenas pelo arquiteto após revisão da equipe.

---

## 1. Propósito do Projeto

<!-- Descreva em 2-3 frases o que este projeto faz e para quem. -->

---

## 2. Stack Tecnológica (Obrigatória)

| Componente | Tecnologia | Versão mínima |
|---|---|---|
| Linguagem | <!-- ex: Python --> | <!-- ex: 3.12+ --> |
| Package manager | <!-- ex: Poetry --> | <!-- ex: latest stable --> |

**Nenhuma tecnologia fora desta lista pode ser adicionada sem revisão e atualização desta constituição.**

---

## 3. Segurança (Não-Negociáveis)

- **NUNCA** exponha credenciais, tokens ou secrets em código-fonte, specs ou logs.
- **SEMPRE** valide entradas do usuário na camada CLI antes de chamar serviços.

---

## 4. Princípios de Arquitetura

<!-- Descreva a arquitetura canônica do projeto aqui. -->

---

## 5. Qualidade de Código

- Cobertura mínima: **80%** para código novo.
- Toda função pública deve ter type hints completos.
- O código deve passar no linter e type-checker configurados antes de qualquer merge.

---

## 6. Workflow de Desenvolvimento (SDD)

- **NUNCA** implemente uma feature sem `SPEC.md` aprovado.
- **NUNCA** avance de fase (`SPEC.md` → `PLAN.md` → `TASKS.md` → implementação) sem aprovação humana explícita.
- Se a implementação divergir da spec, atualize a spec primeiro. Nunca ajuste a spec para justificar o código.
- Nenhuma mudança de camada é feita sem respeitar a fronteira de importação declarada nos
  princípios de arquitetura (§4): módulos de nível mais baixo nunca importam módulos de
  nível mais alto.

---

## 7. Mapa de Responsabilidade das Specs

- `specs/memory/architecture.md` é a fonte única da estrutura do runtime e das decisões de arquitetura.
- `specs/memory/product.md` é a fonte única da definição do produto e dos usuários.
- `specs/memory/tech-stack.md` é a fonte única da política de toolchain.
- `specs/foundation/SPEC.md` é a fonte única da arquitetura de implementação.
- `specs/SPEC.md` é a fonte única do comportamento do produto.
- `specs/features/*/SPEC.md` possuem apenas contratos específicos de feature.

---

## 9. Autoridade de Dispatch

Apenas o(s) agente(s) coordenador(es) do projeto despacham sub-agentes; todo agente
implementador ou revisor é um worker que reporta ao seu dispatcher e nunca despacha
outros agentes por conta própria. O dispatcher permanece a autoridade única durante
todo o ciclo de vida da tarefa que abriu — outra sessão nunca assume esse papel. O
detalhamento operacional do modelo de coordenação vive na lei da workspace
(`DADAIA.md` §2).

---

## 11. Checkpoints de Revisão

Revisão de código, QA e segurança são checkpoints — disciplina mediada por handoff
`APPROVE`/`REQUEST_CHANGES`, nunca um bloqueio mecânico por si só (o bloqueio mecânico
real é o gate de push descrito na `DADAIA.md` §3). Uma tarefa só é marcada `[x]` após
os revisores aplicáveis aprovarem o mesmo commit; qualquer `REQUEST_CHANGES` reabre a
tarefa (`[-]` → volta ao trabalho). A cadência exata (qual revisor, em qual etapa do
release) segue a `DADAIA.md` §5.

---

## 13. Propriedade da Memória

`specs/memory/**` tem um único autor: o agente responsável por specs/planejamento de
release, e apenas nas fases de definição e de fechamento de release. Todo outro agente
lê a memória livremente mas nunca a escreve. Memória é o estado atual do produto, não
um changelog — histórico e decisões superadas vivem no fechamento do release
(`CLOSURE.md`) e no arquivo, nunca em `specs/memory/**`.

---

## 14. Papel dos Agentes de IA

Cada agente de IA escalonado por este projeto é classificado como **ADDITIVE** (só
adiciona — bugs, backlog, relatórios, auditorias) ou **MUTATING** (edita specs,
memória, código de produção ou a superfície de agentes de IA). Um agente MUTATING só
escreve dentro do seu conjunto de caminhos declarado; nenhum agente escreve fora do
domínio descrito em sua própria persona.
