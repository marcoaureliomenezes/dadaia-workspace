# 02. Escrevendo Specs Executaveis

## O que torna uma spec executavel

Uma spec executavel e aquela que elimina as perguntas substantivas antes da implementacao.

Nao e sobre comprimento. E sobre completude operacional.

A diferenca entre uma spec boa e uma ruim nao esta em quantos topicos ela tem.
Esta em quantas inferencias silenciosas o agente precisa fazer para comecar a trabalhar.

**Spec ruim:**
> Criar uma feature para gerenciar contextos de repositorio.

**Spec executavel:**
> A feature `context-management` deve permitir que o usuario:
> - liste contextos materializados em `.dadaia/contexts/`
> - materialize um novo contexto a partir de um repo do catalogo
> - remova um contexto sem deletar o repositorio fonte
>
> Criterio de conclusao: `dadaia context list` retorna os contextos com nome e caminho. `dadaia context add` clona e registra. `dadaia context remove` apaga apenas o diretorio em `.dadaia/contexts/`.
>
> Fora de escopo: nao sincroniza, nao valida permissoes de repositorio.

---

## Elementos obrigatorios de um SPEC.md

### Cabecalho

```markdown
# SPEC — [Nome da Feature]

**Versao:** 1.0
**Status:** Draft | Review | Approved | Implemented
**Autor:** [nome]
**Data:** [data]
```

### Contexto

Um paragrafo descrevendo o problema que a feature resolve e por que ele existe agora.
Nao repita o titulo. Explique o problema.

### User Stories

```markdown
Como [persona], quero [capacidade], para [valor recebido].
```

### Requisitos Funcionais

```markdown
RF-001 — [Descricao clara do comportamento esperado]
RF-002 — ...
```

Cada RF deve ser verificavel de forma independente.
Se voce nao consegue escrever um teste ou uma checagem para ele, esta incompleto.

### Requisitos Nao-Funcionais

```markdown
RNF-001 — [Restricao de desempenho, seguranca, compatibilidade ou operacao]
```

### Fora de Escopo

Liste explicitamente o que NAO sera feito.
Isso e tao importante quanto o que sera feito.
Evita que o agente adicione comportamentos nao solicitados por achar que sao "obvios".

### Criterio de Conclusao

Descreva como voce vai verificar que a feature esta completa.
Pode ser um comando, um arquivo esperado, um comportamento observavel.

---

## Hierarquia de specs no dadaia-workspace

O `dadaia-workspace` organiza specs em niveis:

```
specs/
  constitution.md           ← Foundation (imutavel)
  memory/                   ← Contexto permanente
    architecture.md
    product.md
    tech-stack.md
  SPEC.md                   ← Spec global do projeto
  PLAN.md                   ← Plano global (derivado do SPEC)
  TASKS.md                  ← Tasks globais
  foundation/
    SPEC.md                 ← Foundation especializada
  features/
    [nome-da-feature]/
      SPEC.md               ← Feature spec
      PLAN.md               ← Plano da feature
      TASKS.md              ← Tasks da feature
```

**Regra de revisao:**

Voce sempre le da base para o topo antes de implementar algo.
`constitution` → `memory` → `SPEC` global → feature spec → `PLAN` → `TASKS`.

Inverter essa ordem garante inconsistencia.

---

## Erros comuns ao escrever specs

### Erro 1: Requisitos que descrevem implementacao, nao comportamento

**Ruim:**
> RF-001 — O sistema deve usar Pydantic para validar os dados.

**Correto:**
> RF-001 — O sistema deve rejeitar entradas sem campo `name` com mensagem de erro descritiva.

Como implementar e detalhe de plano, nao de spec.

### Erro 2: Fora de escopo vazio

Se voce nao listou nada fora de escopo, o agente vai assumir que tudo e escopo.

Coloque pelo menos dois itens explicitamente fora.

### Erro 3: Criterio de conclusao ausente

Sem criterio, "concluido" vira subjetivo.
O agente entrega algo que "parece" certo. Voce aceita porque parece razoavel.
Nenhum dos dois verificou.

### Erro 4: Spec aprovada sem revisao de constitution

Se voce comecou a escrever a feature spec sem reler `constitution.md`, ha risco de violar restricoes arquiteturais ou de stack que ja foram decididas.

Sempre leia constitution antes de comecar qualquer spec.

---

## Como o agente deve usar a spec durante a implementacao

Na pratica do `dadaia-workspace`, o agente deve:

1. Ler `constitution.md` e `memory/` antes de qualquer tarefa.
2. Carregar a feature spec aprovada.
3. Seguir apenas o que esta no `TASKS.md` aprovado.
4. Nao adicionar nada que nao esta nas tasks, mesmo que "faca sentido".
5. Reportar ao humano se encontrar algo nao coberto pelas tasks antes de prosseguir.

Se o agente desviar desse protocolo, e um sinal de que o framing foi insuficiente.
