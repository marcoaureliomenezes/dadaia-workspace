# 02. Codex Models

Consulta oficial: 2026-05-09.

Este estudo separa duas coisas que costumam confundir no inicio:

- **Modelos disponiveis no Codex** — usados na CLI, IDE, app e SDK do Codex.
- **Modelos da OpenAI API** — usados quando voce chama a API diretamente e paga por tokens.

Eles se sobrepoem em varios nomes, mas disponibilidade, pricing e limites podem mudar conforme voce entra com ChatGPT, API key, plano individual, Business ou Enterprise.

## Modelos recomendados no Codex

### gpt-5.5

Modelo mais forte recomendado pela OpenAI para Codex quando aparece no seletor.

Use para:

- features complexas em codebase grande;
- debugging dificil;
- arquitetura e refactors de alto risco;
- pesquisa tecnica profunda;
- computer use e workflows com muitas ferramentas;
- revisao de PRs grandes;
- docs que exigem sintese e julgamento.

Evite para:

- tarefas repetitivas pequenas;
- formatacao simples;
- perguntas de baixo risco;
- subagents numerosos quando cada subtask e simples.

Observacao importante: a documentacao oficial indica que `gpt-5.5` esta disponivel no Codex quando voce entra com ChatGPT, mas nao com autenticacao por API key.

Comando:

```bash
codex -m gpt-5.5
```

### gpt-5.4

Modelo frontier mais economico que `gpt-5.5`, com forte capacidade de coding, raciocinio, uso de tools e fluxos agenticos.

Use para:

- trabalho profissional diario;
- implementacao de features bem especificadas;
- reviews medios;
- escrita de specs e planos;
- debugging moderado;
- quando `gpt-5.5` nao estiver liberado.

E o melhor default quando voce quer qualidade alta sem sempre pagar o topo.

Comando:

```bash
codex -m gpt-5.4
```

### gpt-5.4-mini

Modelo rapido e eficiente para tarefas leves, coding responsivo e subagents.

Use para:

- exploracao de arquivos;
- sumarizacao de trechos;
- tarefas pequenas e bem delimitadas;
- workers/subagents com escopo estreito;
- docs simples;
- verificacoes independentes.

Evite para:

- decisoes arquiteturais grandes;
- debugging incerto;
- migracoes arriscadas;
- tarefas onde erro custa caro.

Comando:

```bash
codex -m gpt-5.4-mini
```

### gpt-5.3-codex

Modelo especializado em engenharia de software complexa. Segundo a documentacao oficial, suas capacidades de coding tambem alimentam `gpt-5.4`.

Use para:

- codigo complexo;
- refactors com muitos arquivos;
- investigacao de bugs profundos;
- revisao tecnica rigorosa;
- tarefas longas com testes.

No Codex atual, ele segue relevante quando voce quer um modelo explicitamente otimizado para software engineering.

Comando:

```bash
codex -m gpt-5.3-codex
```

### gpt-5.3-codex-spark

Research preview text-only para iteracao quase instantanea em coding. A documentacao indica disponibilidade para assinantes ChatGPT Pro.

Use para:

- loops curtos de edicao;
- perguntas rapidas sobre codigo;
- pequenas alteracoes interativas;
- iteracao quando velocidade vale mais que profundidade.

Evite para:

- multimodal;
- tarefas longas;
- decisoes criticas;
- trabalho que exige estabilidade de disponibilidade.

Comando:

```bash
codex -m gpt-5.3-codex-spark
```

### gpt-5.2

Modelo anterior, ainda util como alternativa geral para coding e tarefas agenticas.

Use para:

- compatibilidade com ambientes onde modelos novos nao aparecem;
- comparacao de qualidade;
- tarefas gerais que nao exigem o topo atual.

Comando:

```bash
codex -m gpt-5.2
```

## Modelos para documentacao

Para escrever docs, a decisao nao e so "qual modelo escreve melhor". O ponto e quanto contexto e julgamento a tarefa exige.

- **Docs conceituais profundas** — use `gpt-5.5` ou `gpt-5.4`.
- **README, changelog, resumo de PR** — use `gpt-5.4` ou `gpt-5.4-mini`.
- **Material com fontes atuais** — use modelo forte com browsing/docs oficiais.
- **Reescrita de tom ou correcao** — use `gpt-5.4-mini`.

Regra pratica:

- Se a doc envolve decisao, comparacao e risco de desinformacao, use modelo forte.
- Se a doc so organiza material ja conhecido, use mini.

## Modelos para codigo

- **Feature nova grande** — `gpt-5.5`.
- **Feature bem especificada** — `gpt-5.4`.
- **Bug dificil** — `gpt-5.5` ou `gpt-5.3-codex`.
- **Bug simples** — `gpt-5.4` ou `gpt-5.4-mini`.
- **Refactor mecanico** — `gpt-5.4-mini`, com testes.
- **Review de seguranca** — `gpt-5.5`.
- **Exploracao em paralelo** — subagents com `gpt-5.4-mini`, sintetizados por `gpt-5.4` ou `gpt-5.5`.

## Modelos para imagem, audio e multimodal

Codex pode trabalhar com inputs multimodais em algumas superficies, mas geracao especializada normalmente usa modelos/API especificos.

Para imagem:

- Use modelos de imagem da OpenAI API quando a tarefa for gerar ou editar imagem.
- Use Codex para integrar, automatizar, salvar assets e conectar a UI.
- Use modelo forte quando imagem fizer parte de uma decisao de produto ou frontend.

Para audio:

- Use modelos de speech/transcription/realtime da OpenAI API quando a tarefa for audio.
- Use Codex para escrever scripts, pipelines, validadores e documentacao.
- Nao trate modelo de coding como substituto de modelo especializado de audio.

Para documentacao de pipelines multimodais:

- Use `gpt-5.5` quando o material combina codigo, custos, modelos e arquitetura.
- Use `gpt-5.4-mini` apenas para editar texto final ou criar checklists.

## API pricing de modelos principais

Valores oficiais da pagina de API pricing em 2026-05-09:

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

Esses valores sao para API. No Codex via plano ChatGPT, o consumo aparece como limites/creditos de Codex, nao como uma fatura token a token para cada mensagem local.

## Como escolher modelo sem desperdiçar

Use esta heuristica:

- **Alta incerteza + alto impacto** — `gpt-5.5`.
- **Trabalho profissional normal** — `gpt-5.4`.
- **Tarefa pequena e bem delimitada** — `gpt-5.4-mini`.
- **Muitos subagents independentes** — `gpt-5.4-mini` nos subagents, modelo forte na sintese.
- **Codigo muito dificil** — `gpt-5.5` ou `gpt-5.3-codex`.
- **Iteracao instantanea** — `gpt-5.3-codex-spark`, se disponivel.

## Erros comuns

- Usar modelo topo para tudo.
- Usar mini para decisao arquitetural.
- Criar muitos subagents para tarefa que cabe em uma thread.
- Confundir limite de plano ChatGPT com pricing da API.
- Trocar modelo sem olhar `/status` e sem registrar o motivo.

## Como decidir

- **Estou explorando repo grande?** Use `gpt-5.4-mini` para exploradores e `gpt-5.4` para sintese.
- **Vou editar producao?** Use `gpt-5.4` ou `gpt-5.5`.
- **Preciso de maxima qualidade?** Use `gpt-5.5`.
- **Estou perto do limite?** Reduza contexto, use mini e evite subagents.
- **Estou chamando API diretamente?** Calcule tokens e veja pricing oficial.

## Referencias oficiais

- Codex models: https://developers.openai.com/codex/models
- OpenAI API models: https://developers.openai.com/api/docs/models
- OpenAI API pricing: https://openai.com/api/pricing/
- Codex pricing: https://developers.openai.com/codex/pricing
