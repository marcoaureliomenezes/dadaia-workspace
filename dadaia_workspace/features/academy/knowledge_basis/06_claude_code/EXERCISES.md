# Exercicios e Checkpoints — Sessao 2: Claude Code Quick Start

Estes exercicios consolidam o modelo mental correto de operacao com Claude Code.
Cada exercicio e verificavel: se voce nao consegue completar, o modulo correspondente da sessao aponta onde revisar.

---

## Exercicio 1 — Inspecione o que Esta Ativo

**Objetivo:** Verificar quais instrucoes e rules estao disponíveis para o agente na sessao atual.

**Instrucao:**

No terminal, execute:

```bash
ls .claude/rules/
ls .claude/commands/
ls .claude/skills/
```

Para cada arquivo encontrado, classifique-o como:

- **Rule:** instrucao persistente de comportamento
- **Command:** fluxo reutilizavel ativado por slash
- **Skill:** conhecimento especializado carregado sob demanda

**Criterio de validacao:**

Voce passou se conseguir classificar corretamente ao menos 3 arquivos de cada tipo sem precisar abri-los.

---

## Exercicio 2 — Diagnostique um Framing Ruim

**Objetivo:** Transformar um pedido vago num pedido com contexto suficiente.

**Instrucao:**

Aqui esta um pedido tipico de quem ainda nao sabe trabalhar com agentes:

```text
"Refatora o modulo de processamento de dados."
```

Reescreva o pedido informando ao agente:

1. Qual arquivo ou modulo especifico esta em escopo
2. Qual o comportamento atual e o comportamento esperado
3. O que fica fora do escopo
4. Qual tool ou recurso o agente pode usar

**Criterio de validacao:**

Sua versao reescrita deve ter pelo menos 4 linhas e responder as 4 perguntas acima.
Se ficou menor que isso, esta incompleto.

---

## Exercicio 3 — Crie um Slash Command Minimo

**Objetivo:** Praticar a criacao de um command customizado para um fluxo recorrente.

**Instrucao:**

Crie um arquivo em `.claude/commands/` chamado `meu-resumo.md` com o seguinte conteudo minimo:

```markdown
---
description: Gera um resumo do contexto atual do workspace para orientar a proxima sessao.
---

## Passos

1. Leia `.dadaia/contexts/` e identifique os repositorios materializados.
2. Liste os comandos disponíveis em `.claude/commands/`.
3. Apresente um resumo de no maximo 10 linhas.
```

Depois, no Claude Code, teste invocar o command digitando:

```
/meu-resumo
```

**Criterio de validacao:**

O agente executou o fluxo sem erros de interpretacao.
Se ele nao reconheceu o command, verifique o frontmatter e o nome do arquivo.

Apos o exercicio, voce pode deletar o arquivo se nao quiser manter.

---

## Exercicio 4 — Memoria e Persistencia

**Objetivo:** Verificar o que persiste entre sessoes e o que desaparece.

**Instrucao:**

Para cada item abaixo, classifique como **persiste entre sessoes** ou **perdido ao fechar**:

```
Um arquivo criado em .claude/rules/
Uma conversa no chat do Claude Code
Um arquivo criado em .dadaia/tmp/python/
Uma nota salva em /memories/
Um contexto no interior do loop de inferencia do agente
```

**Criterio de validacao:**

- `.claude/rules/`: persiste
- Chat: perdido (a nao ser que seja salvo externamente)
- `.dadaia/tmp/python/`: persiste no disco, mas e efemero por convencao
- `/memories/`: persiste
- Contexto interno do agente: perdido ao fechar

Se voce errou algum, releia `02_commands_skills_e_memoria.md`.

---

## Checkpoint Final — Sessao 2

Voce esta pronto para avancar para a Sessao 3 se:

- [ ] Identifica rules, commands e skills sem abrir os arquivos
- [ ] Consegue reescrever um pedido vago em pelo menos 4 linhas informativas
- [ ] Criou e invocou um slash command customizado
- [ ] Sabe o que persiste e o que nao persiste entre sessoes

Se algum item ficou incompleto, volte para o modulo especifico antes de continuar.
