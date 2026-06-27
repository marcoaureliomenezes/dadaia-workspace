# 04. Pi como o Quarto Harness do dadaia-workspace

Consulta oficial: 2026-05-09. Integracao dadaia: WS-PI-6 (release v0.1.30).

Os modulos 01-03 ensinam o Pi como ferramenta isolada. Este modulo posiciona o Pi
dentro do dadaia-workspace: ele e o **quarto harness** suportado, ao lado de Claude
Code, Codex e OpenCode. Aqui voce aprende o fluxo de entrada, a fronteira de
confianca (trust boundary) e como selecionar o Pi por etapa em workflows.

## Os quatro harnesses

O dadaia-workspace projeta a mesma fonte canonica (`dadaia_workspace/public/`) para
cada harness suportado:

| Harness | Camada | Superficie projetada |
|---|---|---|
| Claude Code | Layer-1 (entrada) + Layer-2 (worker) | `.claude/` |
| Codex | Layer-1 (entrada) + Layer-2 (worker) | `.codex/` |
| OpenCode | Layer-1 (entrada, advisory) | `.agents/` (compartilhado) |
| **Pi** | Layer-1 (entrada) + Layer-2 (worker) | `.pi/` |

O Pi entrou como quarto harness nas releases v0.1.18-v0.1.21 (WS-PI-1..4). A release
v0.1.30 (WS-PI-6) fecha o residual de telemetria: as sessoes do Pi passam a ser
lidas pelo painel.

## Fluxo de entrada (enter-pi)

1. Instale e autentique o Pi (modulo 01).
2. A partir da raiz do workspace, entre no diretorio do projeto e rode `pi`.
3. O Pi carrega `.pi/**` **apenas apos o operador conceder trust** ao projeto. A
   superficie `.pi/` e *post-trust executavel*: o Pi a executa como TypeScript nao
   sandboxed depois do trust. Por isso ela e lib-originated (rastreada pelo
   manifest), nunca carrega segredos ou caminhos locais do operador, e **nunca** deve
   ser editada a mao no lugar — edite a fonte em `public/` e reprojete.
4. Faca o bind do contexto como em qualquer harness:
   `.dadaia/.venv/bin/dadaia context bind <contexto>` (modo padrao `read`; use
   `--mode implementation --release <id>` para trabalho mutante).

## Trust boundary (interativo vs headless)

A fronteira de confianca do Pi como harness Layer-1 e governada nativamente por
`AGENTS.md` mais a extensao Ring-1 post-trust `.pi/extensions/dadaia-sdd-gate.ts`,
que delega ao `pre_gate` em Python.

- **Interativo (`pi`)**: a extensao de gate carregada apos o trust roda e participa
  da aplicacao do SDD gate, como o hook PreToolUse do Claude.
- **Headless / one-shot (`pi --mode json`)**: usado como worker Layer-2 atras do
  `PiHeadlessAdapter`. Nesse caminho, a cobertura deterministica vem dos
  **git chokepoints** (pre-commit lease gate + pre-push security-verdict gate), que
  rodam como git hooks independentemente de qualquer hook de harness.

Regra de ouro: nunca afirme "aplicacao por hook de harness no Pi" sem qualificar o
caminho. Os chokepoints de git protegem ambos os caminhos; a extensao de gate cobre
o interativo apos o trust.

## Selecionar o Pi por etapa (`--harness pi`)

O motor de workflows do dadaia (`dadaia lifecycle`) escolhe o harness por etapa. Para
rodar uma etapa (ou um pipeline) com o Pi como worker Layer-2:

```bash
.dadaia/.venv/bin/dadaia lifecycle pipeline --harness pi
```

A resolucao de harness segue a precedencia CLI > overlay > catalogo (governanca de
modelo de workflow). Com `--harness pi`, o resolvedor seleciona os modelos do Pi
(perfis com `harness: pi`) e o `PiHeadlessAdapter` executa cada etapa via
`pi --mode json`. O Pi roda na assinatura Codex do operador (modelos GPT, ex.
`gpt-5.5`), nao em modelos Claude.

## Telemetria do Pi no painel (WS-PI-6)

A partir de v0.1.30, as sessoes do Pi aparecem na telemetria local:

- O leitor `features/telemetry/reader/pi.py` ingere **somente metadados** das sessoes
  em `~/.pi/agent/sessions/<dir-slug>/<ts>_<id>.jsonl` — id de sessao, cwd, modelId,
  timestamps e mtime do arquivo. **Nunca** le corpos de mensagem (invariante T1): o
  tipo de linha `message` (texto do usuario, thinking do assistente, chamadas e
  resultados de tool, uso de tokens) e excluido por completo.
- O `PiRuntimeAdapter` em `features/telemetry/aggregator/runtimes.py` (chave `"pi"` em
  `ADAPTER_REGISTRY`) classifica liveness (active/idle/ended) pelo mtime do arquivo de
  sessao e degrada para `idle` em qualquer falha de IO.
- Custo do Pi e desconhecido (sem precificacao por evento): `cost_known=False`,
  `cumulative_cost_usd=None`. Nunca e fabricado (lei L2 — sem telemetria falsa).

## Checklist do quarto harness

- [ ] Pi instalado e autenticado (modulo 01).
- [ ] Projeto com trust concedido; `.pi/**` carregado apos o trust.
- [ ] Contexto vinculado via `dadaia context bind`.
- [ ] Entender que hooks de gate sao interativo-pos-trust; headless e coberto por
      chokepoints de git.
- [ ] Saber rodar uma etapa com `dadaia lifecycle ... --harness pi`.
- [ ] Saber que a telemetria do Pi e metadata-only e custo-desconhecido.

## Resultado esperado

Ao final, voce deve conseguir posicionar o Pi como quarto harness do
dadaia-workspace: entrar com trust, vincular contexto, selecionar o Pi por etapa em
workflows e entender a fronteira de confianca e a postura de telemetria (metadata
only, custo desconhecido).
