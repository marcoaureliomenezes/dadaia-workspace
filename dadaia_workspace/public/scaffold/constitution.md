# Constitution: <Project Name>

> Este documento define as leis imutáveis que governam todo o desenvolvimento de <project-name>.
> Todo agente de IA trabalhando neste projeto DEVE seguir estas regras em toda tarefa.
> Atualizado apenas pelo arquiteto após revisão da equipe.

---

## Propósito do Projeto

<!-- Descreva em 2-3 frases o que este projeto faz e para quem. -->

---

## Stack Tecnológica (Obrigatória)

| Componente | Tecnologia | Versão mínima |
|---|---|---|
| Linguagem | <!-- ex: Python --> | <!-- ex: 3.12+ --> |
| Package manager | <!-- ex: Poetry --> | <!-- ex: latest stable --> |

**Nenhuma tecnologia fora desta lista pode ser adicionada sem revisão e atualização desta constituição.**

---

## Segurança (Não-Negociáveis)

- **NUNCA** exponha credenciais, tokens ou secrets em código-fonte, specs ou logs.
- **SEMPRE** valide entradas do usuário na camada CLI antes de chamar serviços.

---

## Princípios de Arquitetura

<!-- Descreva a arquitetura canônica do projeto aqui. -->

---

## Qualidade de Código

- Cobertura mínima: **80%** para código novo.
- Toda função pública deve ter type hints completos.
- O código deve passar no linter e type-checker configurados antes de qualquer merge.

---

## Workflow de Desenvolvimento (SDD)

- **NUNCA** implemente uma feature sem `SPEC.md` aprovado.
- **NUNCA** avance de fase (`SPEC.md` → `PLAN.md` → `TASKS.md` → implementação) sem aprovação humana explícita.
- Se a implementação divergir da spec, atualize a spec primeiro. Nunca ajuste a spec para justificar o código.

---

## Mapa de Responsabilidade das Specs

- `specs/memory/architecture.md` é a fonte única da estrutura do runtime e das decisões de arquitetura.
- `specs/memory/product.md` é a fonte única da definição do produto e dos usuários.
- `specs/memory/tech-stack.md` é a fonte única da política de toolchain.
- `specs/foundation/SPEC.md` é a fonte única da arquitetura de implementação.
- `specs/SPEC.md` é a fonte única do comportamento do produto.
- `specs/features/*/SPEC.md` possuem apenas contratos específicos de feature.
