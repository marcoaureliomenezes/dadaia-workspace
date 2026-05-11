# Exercicios e Checkpoints — Sessao 1: O Que e o Dadaia Workspace?

Estes exercicios consolidam o mapa mental do workspace antes de voce entrar em qualquer sessao pratica.
Nao sao decorativos. Cada um tem criterio de validacao.

---

## Exercicio 1 — Inspecione o Runtime

**Objetivo:** Confirmar que voce consegue identificar as areas principais do runtime do usuario.

**Instrucao:**

No terminal, execute:

```bash
ls -la .dadaia
ls -la .claude
```

Liste por escrito (em texto ou mentalmente) o que cada pasta de primeiro nivel representa.

**Criterio de validacao:**

Voce passou se conseguir classificar corretamente pelo menos 4 areas:

| Area | Responsabilidade esperada |
|---|---|
| `.dadaia/academy/` | Material de aprendizagem duravel |
| `.dadaia/tmp/` | Artefatos efemeros e transitorios |
| `.dadaia/contexts/` | Contextos materializados de repositorios |
| `.claude/commands/` | Slash commands instalados para o agente |
| `.claude/rules/` | Instrucoes persistentes de comportamento |
| `.claude/skills/` | Capacidades especializadas ativaveis por dominio |

---

## Exercicio 2 — Duravel vs Efemero

**Objetivo:** Distinguir o que tem ciclo de vida longo do que e transitorio.

**Instrucao:**

Para cada caminho abaixo, classifique como **duravel** ou **efemero** e justifique em uma frase:

```
.dadaia/academy/01_o_que_e_o_dadaia_workspace/README.md
.dadaia/tmp/json/contexto_gerado.json
.dadaia/contexts/dd_chain_explorer/README.md
.dadaia/tmp/python/script_auxiliar.py
.claude/commands/dadaia-academy.md
```

**Criterio de validacao:**

- `academy/`, `contexts/`, `commands/`: duravel
- `tmp/json/`, `tmp/python/`: efemero

Se voce errou algum, releia `02_arquitetura_do_runtime.md`.

---

## Exercicio 3 — Explique Para Outra Pessoa

**Objetivo:** Testar se o entendimento e transferivel.

**Instrucao:**

Escreva 3 a 5 frases explicando o que o `dadaia-workspace` organiza, como se estivesse enviando uma mensagem para um colega que nunca ouviu falar do produto.

**Criterio de validacao:**

Sua explicacao deve cobrir pelo menos tres dos cinco elementos a seguir:

1. Runtime do usuario (`.dadaia/`)
2. Assets de agente (`.claude/`)
3. Contextos de trabalho (contextos materializados)
4. Governanca de specs (`specify/` ou `specs/`)
5. Aprendizado continuo (Academy)

---

## Exercicio 4 — Responda sem Consultar

**Objetivo:** Verificar retencao das quatro questoes centrais da sessao.

**Instrucao:**

Feche os arquivos da sessao. Responda de memoria:

1. O que o `dadaia-workspace` organiza no meu ambiente?
2. Qual a diferenca entre `.dadaia/`, `.claude/`, `specs/` e os repos materializados?
3. Como o produto combina CLI, assets de agente e contratos de contexto?
4. Por que o fluxo inteiro foi desenhado para ser orientado a SDD?

**Criterio de validacao:**

Voce passou se conseguir dar uma resposta coerente para cada pergunta sem mais de 30 segundos de hesitacao.

Se alguma ficou em branco, anote qual e releia o modulo correspondente.

---

## Checkpoint Final — Sessao 1

Voce esta pronto para avancar para a Sessao 2 se:

- [ ] Consegue identificar as areas do runtime sem consultar
- [ ] Distingue o que e duravel do que e efemero
- [ ] Consegue explicar o produto para outra pessoa em 3 a 5 frases
- [ ] Respondeu as quatro perguntas centrais de memoria

Se algum item ficou incompleto, volte para o modulo especifico antes de continuar.
