# 03. Codex Pricing

Consulta oficial: 2026-05-09.

Pricing no Codex tem duas camadas:

- **Uso pelo plano ChatGPT/Codex** — limites, mensagens locais, cloud tasks, code reviews e creditos.
- **Uso por API key** — cobranca por tokens conforme pricing da OpenAI API.

Nao misture os dois modelos mentais. No plano ChatGPT, voce acompanha limites e creditos. Na API, voce acompanha tokens, cache, output, ferramentas e chamadas.

## O que consome limite no Codex

O consumo varia por:

- tamanho do repo e dos arquivos lidos;
- quantidade de contexto carregado;
- complexidade da tarefa;
- modelo escolhido;
- uso de subagents;
- uso de imagem;
- uso de fast mode;
- tarefas locais vs cloud tasks.

Uma mensagem simples pode consumir pouco. Uma tarefa longa com exploracao, varias leituras de arquivos, testes, subagents e revisoes pode consumir muito mais.

## Como ver limites e consumo

Use estes pontos de controle:

- **Codex usage dashboard** — mostra limites atuais da conta.
- **/status** — durante uma sessao CLI, mostra estado e limites restantes quando disponivel.
- **API dashboard** — para chamadas com API key.
- **billing/usage da organizacao** — para ambientes Business, Enterprise ou API.

Comando dentro da CLI:

```bash
/status
```

Regra pratica:

- Antes de tarefa grande, veja `/status`.
- Durante tarefa longa, compacte contexto quando fizer sentido.
- Depois de tarefa cara, registre modelo usado e motivo.

## Limites por plano

A documentacao oficial de Codex mostra faixas aproximadas por janela de 5 horas. Esses numeros mudam com modelo, plano e promocoes.

Em 2026-05-09, exemplos visiveis na documentacao:

- **Business**
  - `gpt-5.5`: cerca de 15 a 80 mensagens locais por 5h.
  - `gpt-5.4`: cerca de 20 a 100 mensagens locais por 5h.
  - `gpt-5.4-mini`: cerca de 60 a 350 mensagens locais por 5h.
  - `gpt-5.3-codex`: cerca de 30 a 150 mensagens locais, 10 a 60 cloud tasks, 20 a 50 code reviews por 5h.

- **Pro 20x**
  - `gpt-5.5`: cerca de 300 a 1600 mensagens locais por 5h.
  - `gpt-5.4`: cerca de 400 a 2000 mensagens locais por 5h.
  - `gpt-5.4-mini`: cerca de 1200 a 7000 mensagens locais por 5h.
  - `gpt-5.3-codex`: cerca de 600 a 3000 mensagens locais, 200 a 1200 cloud tasks, 400 a 1000 code reviews por 5h.

- **API key**
  - uso local extra pode ser cobrado por pricing padrao da API;
  - cloud tasks e code reviews podem nao estar disponiveis da mesma forma;
  - `gpt-5.5` pode nao estar disponivel via API key no Codex, conforme docs atuais.

Essas faixas sao estimativas oficiais, nao garantia fixa. A propria OpenAI indica que limites podem compartilhar janela de 5 horas e ter limites semanais adicionais.

## Creditos

Creditos entram quando:

- voce passa do limite incluso;
- seu plano permite comprar capacidade extra;
- sua organizacao usa flexible pricing;
- voce roda tarefas adicionais com API key.

O consumo por credito depende do mix de:

- input tokens;
- cached input tokens;
- output tokens;
- modelo;
- recursos extras, como imagem;
- speed/fast mode quando aplicavel.

## API pricing

Quando voce usa API diretamente, pense em tokens.

Valores oficiais em 2026-05-09:

- **GPT-5.5**
  - input: US$5.00 por 1M tokens
  - cached input: US$0.50 por 1M tokens
  - output: US$30.00 por 1M tokens

- **GPT-5.4**
  - input: US$2.50 por 1M tokens
  - cached input: US$0.25 por 1M tokens
  - output: US$15.00 por 1M tokens

- **GPT-5.4 mini**
  - input: US$0.75 por 1M tokens
  - cached input: US$0.075 por 1M tokens
  - output: US$4.50 por 1M tokens

Batch API pode reduzir custos em workloads assincronos. Prompt caching reduz custo quando trechos grandes se repetem.

## Como controlar custo

Taticas de alto impacto:

- **Reduzir contexto** — aponte arquivos especificos em vez de pedir "leia tudo".
- **Usar modelo certo** — mini para tarefas leves, modelo forte para alto risco.
- **Evitar subagents por reflexo** — eles consomem mais tokens que single agent.
- **Pedir plano antes de implementar** — reduz iteracao errada.
- **Pedir diff e verificacao objetiva** — evita retrabalho.
- **Compactar quando a sessao cresce** — use `/compact`.
- **Separar pesquisa de implementacao** — pesquisa ampla pode rodar com modelo menor ou em subagents bem delimitados.

Prompt economico:

```bash
Leia somente specs/features/payment/SPEC.md, PLAN.md e TASKS.md. Diga se o SDD esta aprovado e liste no maximo 5 riscos antes de qualquer implementacao.
```

Prompt caro:

```bash
Leia o repo inteiro e melhore tudo que achar necessario.
```

## Como monitorar no dia a dia

Rotina recomendada:

- Antes da sessao: verificar modelo atual e `/status`.
- Durante: limitar escopo por arquivo, tarefa ou spec.
- Antes de subagents: confirmar que subtarefas sao independentes.
- Antes de API: estimar tokens e modelo.
- Depois: registrar qual modelo funcionou melhor para aquele tipo de tarefa.

Para o dadaia Workspace, vale manter um log simples por tarefa:

- modelo usado;
- tipo de tarefa;
- se usou subagents;
- se precisou refazer;
- qualidade final;
- custo percebido ou limite consumido.

## Quando usar API key

Use API key quando:

- voce precisa rodar automacao propria;
- quer medir custo token a token;
- precisa integrar com backend;
- quer rodar tarefas locais alem do limite incluso do plano;
- precisa de controle programatico via SDK/API.

Evite API key quando:

- voce so esta operando Codex interativamente;
- ainda nao sabe estimar tokens;
- a tarefa cabe no plano ChatGPT;
- nao ha budget definido.

## Como decidir

- **Estou aprendendo?** Use plano ChatGPT/Codex e monitore `/status`.
- **Estou perto do limite?** Troque para mini, reduza contexto ou pare a sessao.
- **Preciso automatizar?** Avalie API key e pricing por tokens.
- **Tenho muitas tarefas parecidas?** Considere Batch API, prompt caching e prompts menores.
- **Vou usar imagem?** Espere consumo maior de limites/creditos.

## Referencias oficiais

- Codex pricing: https://developers.openai.com/codex/pricing
- Codex models: https://developers.openai.com/codex/models
- OpenAI API pricing: https://openai.com/api/pricing/
- Rate limits: https://developers.openai.com/api/docs/rate-limits
- Prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
