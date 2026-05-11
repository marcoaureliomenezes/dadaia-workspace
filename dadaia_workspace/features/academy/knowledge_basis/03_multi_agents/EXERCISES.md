# Exercicios e Checkpoints — Sessao 5: Agents e Multi Agent Orchestration Quick Start

Estes exercicios desenvolvem o criterio necessario para escolher a arquitetura certa de agent.
A tentacao de usar multi-agent onde um single agent basta e um dos erros mais caros em pratica.

---

## Exercicio 1 — Classifique a Arquitetura Certa

**Objetivo:** Desenvolver criterio para escolher entre single agent, workflow fixo e orquestracao.

**Instrucao:**

Para cada cenario abaixo, decida qual arquitetura e mais adequada e justifique em um ou dois periodos:

**Cenario A:**
Voce quer que o agente leia um arquivo de log, identifique erros e gere um relatorio markdown.

**Cenario B:**
Voce quer revisar uma pull request com checagens independentes de seguranca, testes e design, cada uma exigindo contexto especializado e podendo rodar em paralelo.

**Cenario C:**
Voce quer um assistente que responda perguntas sobre o produto. As perguntas sao imprevisiveis e variam muito de tema.

**Criterio de validacao:**

- Cenario A: single agent (tarefa sequencial, contexto unico)
- Cenario B: orchestrator + workers em paralelo (contextos independentes, beneficio real de paralelismo)
- Cenario C: single agent com bom framing (nao ha beneficio em multi-agent para respostas conversacionais livres)

Se classificou diferente, releia `02_quando_orquestrar_e_qual_padrao_usar.md`.

---

## Exercicio 2 — Desenhe um Pipeline de Orquestracao

**Objetivo:** Traduzir um problema real em um diagrama textual de orquestracao.

**Instrucao:**

Dado o problema abaixo, desenhe o pipeline de orquestracao mais simples que resolve:

**Problema:**
Voce precisa revisar um conjunto de notebooks Databricks antes de um deploy. A revisao envolve:
- verificar se todos os notebooks tem um cabecalho de documentacao
- checar se algum notebook acessa dados de producao em ambiente de DEV
- gerar um relatorio consolidado de achados

**Instrucao de desenho:**
Use texto puro. Nao precisa de diagrama grafico.
Identifique: quem e o planner, quem sao os workers (se houver), quem e o synthesizer.

**Criterio de validacao:**

Uma resposta matura reconhece que esse caso pode funcionar como single agent com tres passos sequenciais, ou como orchestrator + dois workers pequenos se as checagens forem custosas.
A resposta nao matura e montar cinco agents diferentes sem justificativa.

---

## Exercicio 3 — Identifique os Riscos de Governanca

**Objetivo:** Tornar os riscos operacionais de multi-agent concretos e nomeados.

**Instrucao:**

Liste pelo menos 3 riscos concretos que surgem ao usar um sistema multi-agent sem os guardrails corretos.
Para cada risco, escreva uma frase descrevendo a consequencia pratica.

**Criterio de validacao:**

Exemplos de riscos esperados:

- **Contexto compartilhado inconsistente:** Workers com visoes diferentes do estado causam decisoes contraditorias no synthesizer.
- **Custo nao monitorado:** Cada subagente consome tokens independentemente; o custo total escala mais rapido do que o esperado.
- **Ausencia de observabilidade:** Sem logs estruturados por agent, e impossivel debugar onde o pipeline falhou.
- **Loop sem saida:** Orchestrators que nao tem criterio de encerramento ficam disparando workers indefinidamente.
- **Falta de aprovacao humana:** Agents que tomam acoes irreversiveis sem um ponto de revisao humana explodiam erros silenciosos em producao.

Se listou menos de 3 ou os riscos sao vagos demais, releia `03_guardrails_memoria_e_governanca.md`.

---

## Exercicio 4 — Avalie a Arquitetura do Workspace

**Objetivo:** Aplicar o modelo mental de ochestration sobre um exemplo real.

**Instrucao:**

Abra o arquivo `.claude/commands/dadaia-academy.md` e leia os passos de navigacao.

Responda:

1. O command `/dadaia-academy` usa um padrao de single agent ou orchestration?
2. Existe algum ponto onde o agente poderia ser substituido por um worker especializado?
3. Qual guardrail do command impede que o agente escreva fora da area autorizada?

**Criterio de validacao:**

- Pergunta 1: single agent (o command nao dispara subagentes, e um fluxo sequencial de steps)
- Pergunta 2: possivelmente o step de geracao de conteudo poderia ser um worker, mas o custo de complexidade nao justifica ainda
- Pergunta 3: o step de guardrails instrui explicitamente a nao escrever fora de `.dadaia/academy/`

---

## Checkpoint Final — Sessao 5

Voce esta pronto para avancar para a Sessao 6 se:

- [ ] Classifica corretamente entre single agent, workflow fixo e orquestracao
- [ ] Consegue esbocar um pipeline de orquestracao minimo para um problema real
- [ ] Nomeou pelo menos 3 riscos de governanca com consequencias concretas
- [ ] Analisou a arquitetura de um command real do workspace

Se algum item ficou incompleto, volte para o modulo especifico antes de continuar.
