# 04. Codex Advanced

Consulta oficial: 2026-05-09.

Uso avancado de Codex nao e "usar mais agentes". E saber quando automatizar, quando delegar, quando manter uma thread unica e como controlar custo, contexto e risco.

## Codex SDK

O Codex SDK permite controlar agents locais programaticamente. A documentacao oficial descreve uso para:

- CI/CD;
- ferramentas internas;
- apps que controlam Codex;
- agents proprios que acionam Codex;
- workflows complexos de engenharia.

Instalacao:

```bash
npm install @openai/codex-sdk
```

Exemplo minimo:

```typescript
import { Codex } from "@openai/codex-sdk";

const codex = new Codex();
const thread = codex.startThread();

const result = await thread.run(
  "Make a plan to diagnose and fix the CI failures"
);

console.log(result);
```

Continuar a mesma thread:

```typescript
const result = await thread.run("Implement the plan");
console.log(result);
```

Retomar thread antiga:

```typescript
const threadId = "<thread-id>";
const thread2 = codex.resumeThread(threadId);
const result = await thread2.run("Pick up where you left off");
console.log(result);
```

Use SDK quando voce quer repetibilidade. Nao use SDK so para substituir uma sessao interativa simples.

## Non-interactive mode

`codex exec` serve para rodar tarefas em modo nao interativo.

Exemplo:

```bash
codex exec "Revise o PR atual e liste bugs de alta severidade"
```

Bom para:

- checagens em CI;
- geracao de relatorios;
- auditorias repetiveis;
- tarefas com prompt fechado.

Ruim para:

- descoberta aberta;
- decisoes de produto;
- tarefas que exigem varias aprovacoes;
- operacoes destrutivas.

## Subagents

Subagents permitem que Codex crie agentes especializados, geralmente em paralelo, e depois consolide os resultados.

A documentacao oficial destaca pontos importantes:

- Codex so cria subagents quando voce pede explicitamente.
- Subagents consomem mais tokens que uma execucao single-agent equivalente.
- Codex coordena spawn, instrucoes, espera, coleta de resultados e fechamento.
- Subagents herdam sandbox e approvals da sessao principal.
- A CLI permite inspecionar threads com `/agent`.

Use subagents para:

- exploracao independente de areas diferentes do repo;
- review por temas, como seguranca, testes, performance e manutencao;
- implementacao paralela com ownership claro de arquivos;
- verificacao em paralelo enquanto o agente principal trabalha em outro ponto.

Evite subagents quando:

- a tarefa cabe em uma thread;
- as subtarefas dependem fortemente uma da outra;
- voce esta perto do limite;
- o risco de conflito de edicao e alto;
- voce ainda nao sabe explicar o output esperado.

Prompt bom para subagents:

```bash
Spawn 3 agents em paralelo:
1. explorer: revisar riscos de seguranca em services/auth.
2. explorer: revisar cobertura de testes em services/billing.
3. explorer: revisar performance em services/search.
Nao editem arquivos. Ao final, consolide achados por severidade com paths.
```

## Custom agents

Codex tem agents embutidos:

- **default** — agente geral.
- **worker** — foco em execucao e implementacao.
- **explorer** — foco em leitura e investigacao.

Custom agents podem ser definidos em arquivos TOML:

- `~/.codex/agents/` para agents pessoais.
- `.codex/agents/` para agents do projeto.

Campos essenciais:

- `name`
- `description`
- `developer_instructions`

Campos opcionais podem controlar modelo, effort, sandbox, MCP e skills.

Regra pratica:

- Use **explorer** para perguntas de codebase.
- Use **worker** para patch com ownership claro.
- Use **default** para coordenacao e sintese.
- Crie custom agent so quando o papel se repetir muitas vezes.

## Agents SDK da OpenAI

O OpenAI Agents SDK e diferente do Codex SDK.

Pense assim:

- **Codex SDK** — controla Codex como agente de engenharia em repositorios.
- **OpenAI Agents SDK** — cria seus proprios agents de produto, automacao ou backend.

O Agents SDK cobre:

- definicao de agents;
- tools;
- guardrails;
- handoffs;
- orchestration;
- tracing;
- sessions;
- voice/realtime agents;
- MCP;
- evals.

Use Agents SDK quando:

- voce esta construindo um produto com agents;
- precisa de handoff entre especialistas;
- quer tracing e avaliacao;
- precisa expor tools proprias;
- quer controlar estado, memoria e sessoes.

Use Codex quando:

- o problema e engenharia de software;
- o agente precisa ler, editar e testar repositorios;
- voce quer operar dentro do workspace.

## Padroes de orquestracao

Comece simples:

- **Single agent** — melhor default para quase tudo.
- **Prompt chaining** — bom para fluxo previsivel.
- **Parallel explorers** — bom para revisao independente.
- **Orchestrator + workers** — bom quando ha decomposicao real.
- **Evaluator + optimizer** — bom quando qualidade importa mais que velocidade.

No dadaia Workspace, o padrao recomendado e:

- Planejar com uma thread principal.
- Usar explorers para levantar fatos independentes.
- Usar workers apenas com ownership claro.
- Consolidar com a thread principal.
- Validar com testes/comandos reais.

## Riscos avancados

Os principais riscos nao sao tecnicos; sao operacionais:

- **context pollution** — muita informacao irrelevante piora decisao.
- **context rot** — sessoes longas acumulam premissas antigas.
- **fan-out caro** — subagents aumentam custo e latencia.
- **conflito de edicao** — workers mexem nos mesmos arquivos.
- **approval invisivel** — subagent pode pedir aprovacao enquanto voce esta em outra thread.
- **falsa autonomia** — agente executa sem criterio de pronto.

Mitigacoes:

- use `/compact` em sessoes longas;
- limite cada subagent a uma pergunta ou ownership;
- feche agents concluidos;
- peça paths e evidencias;
- rode testes antes de encerrar;
- mantenha SDD/AGENTS.md como fonte de governanca.

## Operacao segura com agents

Antes de usar subagents, responda:

- A tarefa e paralelizavel?
- Cada agent tem saida objetiva?
- Eles precisam editar arquivos?
- Os arquivos de cada worker sao disjuntos?
- O custo extra se justifica?

Se a resposta for incerta, nao use multi-agent.

## Como decidir

- **Quero automatizar Codex em repo** — Codex SDK.
- **Quero criar produto agentico** — OpenAI Agents SDK.
- **Quero revisar varias dimensoes independentes** — subagents explorers.
- **Quero implementar feature grande** — plano central + workers com ownership.
- **Quero economizar tokens** — single agent, modelo menor, contexto menor.

## Referencias oficiais

- Codex SDK: https://developers.openai.com/codex/sdk
- Codex subagents: https://developers.openai.com/codex/subagents
- Codex CLI: https://developers.openai.com/codex/cli
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
- Agents SDK orchestration: https://openai.github.io/openai-agents-python/multi_agent/
