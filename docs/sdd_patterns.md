# SDD Patterns — Spec-Driven Development Standard

> **Versão:** 1.0  
> **Escopo:** Aplicável a todos os projetos gerenciados pelo dadaia-workspace  
> **Fonte:** Sintetizado do curso *Spec-Driven Development — From Vibe Coding to Intent Engineering* (Módulos 1–7)

---

## 1. O que é SDD e por que existe

**Spec-Driven Development (SDD)** é uma metodologia de desenvolvimento que exige que toda funcionalidade seja completamente especificada *antes* de qualquer implementação com IA ou humanos.

O problema que resolve:

| Problema | Consequência sem SDD |
|---|---|
| IA não lê mentes | Preenche lacunas com suposições silenciosas |
| IA perde contexto entre sessões | Decisões arquiteturais são esquecidas ou contraditas |
| IA otimiza para "parece correto" | Código plausível mas subtilmente errado |
| IA raramente faz perguntas | Ambiguidade vira débito técnico invisível |

**Princípio central:** A IA é um *executor* poderoso, não um *arquiteto*. Ela precisa de uma especificação precisa do *que* construir antes de construir corretamente.

---

## 2. Conceitos Fundamentais

### 2.1 Spec vs Documento de Contexto

| Dimensão | Spec | Contexto / Memory Bank |
|---|---|---|
| **Escopo** | Feature ou componente específico | Todo o projeto |
| **Vida útil** | Duração da feature | Persiste em todas as sessões |
| **Propósito** | Guia a implementação de uma mudança específica | Fornece contexto operacional permanente |
| **Exemplos** | `SPEC.md`, `PLAN.md`, `TASKS.md` | `constitution.md`, `product.md`, `tech-stack.md` |
| **Quem atualiza** | Autor da feature | Arquiteto / convenções acordadas pela equipe |
| **Carregado quando** | Trabalhando na feature relevante | Toda sessão de IA |

### 2.2 Os Três Níveis de Maturidade SDD

| Nível | Nome | Descrição |
|---|---|---|
| **1** | Spec-First | Spec escrita antes da IA gerar código; pode ser descartada após |
| **2** | Spec-Sync | Spec é mantida em sincronia com o código ao longo do tempo |
| **3** | Spec-Native | Spec é a fonte de verdade; código e testes são derivados dela |

**Recomendação:** Comece no Nível 1. Avance para Nível 2 em projetos de longa duração.

---

## 3. Pipeline Completo SDD

```
┌──────────────────────────────────────────────────────────────────────┐
│                      SDD COMPLETE PIPELINE                          │
│                                                                      │
│  Phase 0        Phase 1      Phase 2     Phase 3     Phase 4        │
│  FOUNDATION  →  SPECIFY  →   PLAN    →   TASKS   →  IMPLEMENT      │
│                                                                      │
│  constitution   SPEC.md      PLAN.md     TASKS.md   Code + Tests   │
│  memory bank                                                         │
│                                                                      │
│    [Human]      [Human]     [Human]     [Human]     [Human]         │
│   (one-time)   (approve)   (approve)   (approve)   (review PR)     │
└──────────────────────────────────────────────────────────────────────┘
```

**Regra absoluta:** Nenhuma fase começa sem aprovação humana da fase anterior. A IA executa; o humano aprova.

---

## 4. Estrutura de Arquivos

### 4.1 Projeto Simples (feature única ou escopo pequeno)

```
project-root/
  specs/
    constitution.md       ← Leis imutáveis do projeto (lida em toda sessão)
    SPEC.md               ← O que o projeto deve fazer (behavior-first)
    PLAN.md               ← Como será implementado tecnicamente
    TASKS.md              ← Lista ordenada de tarefas atômicas
    memory/
      product.md          ← Descrição do produto e usuários
      tech-stack.md       ← Tecnologias, versões, justificativas
      architecture.md     ← Design do sistema, ADRs
```

### 4.2 Projeto com Múltiplos Domínios (médio porte)

```
project-root/
  specs/
    constitution.md       ← Lei global do projeto
    SPEC.md               ← Visão geral do projeto (pode referenciar sub-specs)
    memory/
      product.md
      tech-stack.md
      architecture.md
    foundation/           ← Componentes de infraestrutura base
      SPEC.md
      PLAN.md
      TASKS.md
    domains/              ← Domínios de negócio independentes
      payments/
        SPEC.md
        PLAN.md
        TASKS.md
      users/
        SPEC.md
        PLAN.md
        TASKS.md
```

### 4.3 Projeto Complexo (múltiplos domínios + features)

```
project-root/
  specs/
    constitution.md       ← Lei global (always-on em toda sessão de IA)
    SPEC.md               ← Spec do projeto inteiro (roadmap de alto nível)
    memory/
      product.md          ← O que o sistema é e para quem
      tech-stack.md       ← Stack tecnológico com versões
      architecture.md     ← Diagrama de sistema, ADRs
      data-catalog.md     ← Esquemas de dados (projetos data-heavy)
      aws-resources.md    ← Recursos de infra (projetos cloud)
    foundation/           ← Base da plataforma (infra, auth, logging)
      SPEC.md
      PLAN.md
      TASKS.md
    domains/              ← Domínios de negócio
      [domain-name]/
        SPEC.md
        PLAN.md
        TASKS.md
    features/             ← Features cross-domain ou temporárias
      [feature-name]/
        SPEC.md
        PLAN.md
        TASKS.md
```

**Regra de escalabilidade:** Comece com a estrutura simples. Adicione `foundation/`, `domains/`, ou `features/` somente quando houver mais de uma área de desenvolvimento autônoma.

---

## 5. Templates de Artefatos

### 5.1 `constitution.md`

O arquivo mais crítico. Carregado em **toda** sessão de IA. Deve ser conciso e cobrir apenas regras imutáveis.

```markdown
# Constitution: [Project Name]

> Este documento define as leis imutáveis que governam todo o desenvolvimento.
> Todo agente de IA trabalhando neste projeto DEVE seguir estas regras em toda tarefa.

## Propósito do Projeto
[1–3 frases descrevendo o que o sistema faz e para quem]

## Stack Tecnológico
- Linguagem principal: [linguagem + versão]
- Framework: [framework + versão]
- Banco de dados: [banco + versão]
- Testes: [framework de testes]

## Segurança (Não-Negociáveis)
- NUNCA exponha credenciais, API keys ou secrets no código
- SEMPRE use queries parametrizadas (nunca string interpolation em SQL)
- SEMPRE valide e sanitize input do usuário na borda do sistema
- NUNCA faça log de dados sensíveis (senhas, tokens, PII)

## Princípios de Arquitetura
- [Padrão arquitetural principal: ex. hexagonal, layered, event-driven]
- [Regra de separação de responsabilidades]
- [Regra de dependência entre módulos]

## Qualidade de Código
- [Cobertura mínima de testes]
- [Padrão de formatação / linting]
- [Nomenclatura de arquivos e módulos]

## Workflow de Desenvolvimento
- Nunca implemente sem um SPEC.md aprovado
- Nunca avance de fase sem aprovação humana explícita
- Commit após cada tarefa completada do TASKS.md
```

---

### 5.2 `SPEC.md`

Descreve *o que* o sistema deve fazer. **Sem tecnologia.** Orientado a comportamento.

```markdown
# Spec: [Feature / Project Name]

> **Status:** [ ] Draft | [ ] In Review | [x] Approved  
> **Versão:** 1.0  
> **Autor:** [nome]  
> **Aprovador:** [nome]

## Contexto
[Por que esta feature existe? Qual problema resolve?]

## Usuários e Goals

### US-001: [User Story]
- **Como** [tipo de usuário]
- **Quero** [ação ou capacidade]
- **Para** [objetivo ou valor]

**Critérios de Aceite:**
- Dado [contexto], quando [ação], então [resultado esperado]
- Dado [edge case], quando [ação], então [resultado esperado]

### US-002: [User Story]
...

## Requisitos Funcionais

- FR-001: [Requisito no formato EARS/GEARS]
- FR-002: [Requisito no formato EARS/GEARS]
- FR-003: [Requisito no formato EARS/GEARS]

## Requisitos Não-Funcionais

- NFR-001: [Performance] The system shall [comportamento mensurável]
- NFR-002: [Segurança] [Requisito no formato EARS/GEARS]
- NFR-003: [Disponibilidade] [Requisito no formato EARS/GEARS]

## Fora de Escopo
- [O que esta spec explicitamente NÃO cobre]
- [O que está adiado para uma future spec]

## Questões Abertas
- [ ] [Pergunta que precisa de resposta antes da implementação]
```

---

### 5.3 `PLAN.md`

Descreve *como* a spec será implementada. Gerado pela IA a partir do `SPEC.md` aprovado; revisado pelo humano.

```markdown
# Plan: [Feature Name]

> **Status:** [ ] Draft | [ ] In Review | [x] Approved  
> **Referência:** [link para SPEC.md]  
> **Branch:** feature/[feature-name]

## Decisões Técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| [componente] | [tecnologia] | [por que, alinhado com constitution] |

## Arquitetura

### Diagrama de Componentes
```mermaid
graph TD
  [...]
```

## Estrutura de Diretórios
```
src/
  [módulo]/
    [arquivo].[ext]
```

## Esquema de Dados
```sql
[definições de schema]
```

## Contrato de API

### [METHOD] /[endpoint]
**Request:**
```json
{ [schema] }
```
**Response 200:**
```json
{ [schema] }
```
**Respostas de Erro:**
- 400: [condição]
- 401: [condição]
- 500: [condição]

## Dependências
- `[pacote@versão]`: [por que é necessário]

## Considerações de Segurança
- [Decisões técnicas de segurança específicas desta feature]

## Considerações de Performance
- [Estratégia de cache, indexação, etc.]
```

---

### 5.4 `TASKS.md`

Decompõe o `PLAN.md` em tarefas atômicas. Cada tarefa deve ser completável em uma única interação de IA.

```markdown
# Tasks: [Feature Name]

> **Status:** [ ] In Progress | [x] Done  
> **Referência:** [SPEC.md] | [PLAN.md]

## Checklist Pré-Implementação
- [ ] SPEC.md revisado e aprovado
- [ ] PLAN.md revisado e aprovado
- [ ] Todas as questões abertas resolvidas
- [ ] Branch criada: `feature/[feature-name]`

## Tarefas

### Fase 1: Fundação
- [ ] T01: [Descrição] — *Verificável por: [critério objetivo]*
- [ ] T02: [Descrição] — *Verificável por: [critério objetivo]*

### Fase 2: Implementação Core
- [ ] T03: [Descrição] (depende de T01) — *Verificável por: [critério]*
- [ ] T04: [Descrição] (depende de T02, T03) — *Verificável por: [critério]*

### Fase 3: Testes
- [ ] T05: Testes unitários para [componente] — *Verificável por: cobertura > X%*
- [ ] T06: Testes de integração para [endpoint/job] — *Verificável por: todos os cenários passando*

### Fase 4: Documentação e Finalização
- [ ] T07: Atualizar documentação relevante
- [ ] T08: Commit final e PR aberto

## Definition of Done
- [ ] Todas as tarefas marcadas
- [ ] Todos os testes passando
- [ ] Código revisado
- [ ] Spec atualizada se a implementação divergiu da intenção original
```

---

## 6. Sintaxe EARS/GEARS para Requisitos

Todo requisito em `SPEC.md` deve usar um dos padrões abaixo. Nunca escreva requisitos vagos.

### 6.1 Padrões EARS

| Padrão | Template | Quando usar |
|---|---|---|
| **Ubíquo** | `The <system> shall <behavior>.` | Sempre verdadeiro, sem condição |
| **Event-Driven** | `When <trigger event>, the <system> shall <behavior>.` | Disparado por um evento |
| **State-Driven** | `While <system state>, the <system> shall <behavior>.` | Ativo apenas em um estado |
| **Optional Feature** | `Where <feature is included>, the <system> shall <behavior>.` | Condicional à configuração |
| **Error/Unwanted** | `If <unwanted condition>, then the <system> shall <behavior>.` | Tratamento de erros e exceções |

**Padrões compostos:**
```
When <event A> AND <event B>, the <system> shall <behavior>.
While <state A> AND <duration elapsed>, the <system> shall <behavior>.
```

### 6.2 Vocabulário GEARS (otimizado para LLMs)

| Palavra-chave | Tipo | Uso |
|---|---|---|
| `shall` | Obrigação | Requisito mandatório |
| `should` | Recomendação | Preferível mas não mandatório |
| `must not` | Proibição | Comportamento explicitamente proibido |
| `when` | Gatilho de evento | Requisito reativo |
| `while` | Condição de estado | Ativo durante estado |
| `if` | Erro/exceção | Tratamento de borda |
| `given` | Pré-condição | Setup de contexto (estilo BDD) |
| `then` | Resultado | Resultado após pré-condição + gatilho |

### 6.3 Tabela de Transformação: Vago → Executável

| Requisito Vago | Requisito EARS/GEARS |
|---|---|
| "Senhas devem ser seguras" | `The system shall enforce a minimum password length of 12 characters, require at least one uppercase letter, one number, and one special character.` |
| "Tratar erros adequadamente" | `If any unhandled exception occurs, then the system shall log the full stack trace and return a 500 error with a unique error ID.` |
| "O app deve ser rápido" | `The API shall respond to 95% of requests within 200ms under a load of 1000 concurrent users.` |
| "Usuários podem fazer upload" | `When the user selects a file for upload, the system shall validate that the file format is one of [JPEG, PNG, PDF] and the size does not exceed 10MB.` |

---

## 7. Checklists de Qualidade

### 7.1 Checklist: SPEC.md está boa?

- [ ] Todos os requisitos usam sintaxe EARS/GEARS
- [ ] Cada critério de aceite é testável (existe um teste que prova que está done)
- [ ] Não há requisitos contraditórios
- [ ] Todas as questões abertas foram resolvidas ou explicitamente adiadas
- [ ] Itens fora de escopo estão listados explicitamente
- [ ] A spec é agnóstica de tecnologia (sem mencionar banco, framework, biblioteca)
- [ ] Um não-técnico consegue validar se o requisito foi atendido ou não
- [ ] A spec foi revisada por pelo menos 2 pessoas (produto + engenharia)

### 7.2 Checklist: PLAN.md está bom?

- [ ] Todos os FR e NFR do SPEC.md têm uma resposta técnica no plano
- [ ] Todas as escolhas tecnológicas respeitam a `constitution.md`
- [ ] O schema de dados cobre todos os requisitos de dados
- [ ] Todos os endpoints têm contratos de request/response completos (incluindo erros)
- [ ] Considerações de segurança estão explicitamente endereçadas
- [ ] O plano não introduz features que não estão na spec (gold plating)

### 7.3 Checklist: TASKS.md está bom?

- [ ] Cada tarefa é completável em uma única sessão de IA (tipicamente < 500 linhas impactadas)
- [ ] Cada tarefa tem um critério de conclusão claro e objetivo
- [ ] Tarefas estão ordenadas por dependência (fundacionais antes das dependentes)
- [ ] Tarefas de teste estão explicitamente listadas (não assumidas)
- [ ] Há tarefas de documentação quando necessário
- [ ] A Definition of Done está clara

---

## 8. Antipadrões a Evitar

| Antipadrão | Descrição | Correção |
|---|---|---|
| **Vague Spec** | Requisitos sem sujeito, verbo modal ou comportamento mensurável | Aplicar EARS/GEARS a cada requisito |
| **Technology Leak** | Mencionar banco, framework ou biblioteca no SPEC.md | Mover para PLAN.md |
| **Monolithic Task** | Tarefas que impactam > 500 linhas de código | Decompor em subtarefas menores |
| **Missing Edge Cases** | Spec não descreve o que acontece em falhas ou inputs inválidos | Adicionar padrão EARS `If <unwanted condition>` |
| **Undresolved Questions** | Questões abertas no SPEC.md antes de avançar para PLAN | Resolver antes de aprovar |
| **Spec-to-Code Drift** | Implementação diverge da spec silenciosamente | Nunca ajustar a spec para bater com o código; re-implementar |
| **Gold Plating** | PLAN.md adiciona features além do que a spec pede | Limitar ao escopo do SPEC.md aprovado |
| **Skipping Gates** | Começar implementação sem SPEC + PLAN + TASKS aprovados | Seguir o pipeline completo, sempre |

---

## 9. Sizing de Specs por Complexidade

| Tamanho da mudança | Linhas impactadas | Abordagem SDD |
|---|---|---|
| Trivial | < 20 linhas | Tarefa única; SDD ceremony pode ser simplificado |
| Pequeno | 20–100 linhas | 1–3 tasks; spec leve |
| Médio | 100–500 linhas | 5–10 tasks; SPEC + PLAN + TASKS completos |
| Grande | 500–2000 linhas | 10–25 tasks; considere dividir em múltiplas specs |
| Epic | > 2000 linhas | Dividir em specs independentes |

---

## 10. Prompt Padrão de Implementação por Tarefa

Use este padrão ao instruir a IA a implementar cada tarefa:

```
Implemente a Tarefa T[N]: [Descrição da tarefa]

Contexto:
- SPEC.md: [requisitos funcionais que esta tarefa atende]
- PLAN.md: [decisões técnicas relevantes]
- constitution.md: [regras de código que se aplicam]
- Tarefas anteriores concluídas: T01, T02, ...

Entregável:
- [Arquivos exatos a criar ou modificar]
- Critério de verificação: [como confirmar que está done]

NÃO implemente outras tarefas. Apenas T[N].
```

---

## 11. Referência Rápida — O que vai onde

| Conteúdo | Arquivo |
|---|---|
| Leis imutáveis do projeto | `constitution.md` |
| O que o produto faz e para quem | `memory/product.md` |
| Stack tecnológica e versões | `memory/tech-stack.md` |
| Design do sistema e ADRs | `memory/architecture.md` |
| O que a feature deve fazer (behavior) | `SPEC.md` |
| Como a feature será implementada | `PLAN.md` |
| Lista ordenada de tarefas atômicas | `TASKS.md` |
| Tecnologia específica de um módulo | `PLAN.md` (nunca `SPEC.md`) |
| Critérios de aceite testáveis | `SPEC.md` → seção de User Stories |
| Contrato de API completo | `PLAN.md` |
| Diagrama de componentes | `PLAN.md` |
