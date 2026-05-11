# Exemplo Pratico — De uma Intencao Vaga ao Ciclo SDD Completo

Este exemplo percorre as cinco fases do SDD usando um caso real: adicionar um novo command ao workspace.

O objetivo nao e mostrar o formato perfeito. E mostrar o que acontece em cada transicao e por que a aprovacao humana em cada fase muda o resultado.

---

## Ponto de partida: a intencao vaga

```text
"Quero um command que liste os contexts ativos do workspace."
```

Esse pedido, enviado diretamente para o agente, produziria algo. Talvez ate algo util.
Mas voce nao saberia o que ele assumiu. E nao teria como reproduzir nem verificar.

---

## Fase 0 — Revisao de Foundation

Antes de qualquer especificacao, releia o que ja esta decidido:

```bash
cat dadaia-workspace/specs/constitution.md
cat dadaia-workspace/specs/memory/tech-stack.md
```

O que voce encontra de relevante:

- Commands devem viver em `.claude/commands/`
- Commands sao arquivos markdown com frontmatter
- O CLI congelado nao recebe novos subcomandos
- Qualquer escrita de artefato fica restrita ao runtime do usuario

Agora voce sabe o que e imutavel. Prosseguindo.

---

## Fase 1 — Specify: do vago para o executavel

Abra um novo arquivo em `specs/features/list-contexts-command/SPEC.md`.

Aqui esta uma versao minima mas executavel:

```markdown
# SPEC — list-contexts-command

**Versao:** 1.0
**Status:** Draft
**Autor:** marco
**Data:** 2026-04-27

## Contexto

O workspace materializa contextos de repositorios em `.dadaia/contexts/`.
Atualmente nao ha uma forma rapida de listar esses contextos ativados via agente.
Este command resolve isso sem tocar no CLI congelado.

## User Story

Como usuario do workspace, quero invocar `/list-contexts` no agente para ver quais repositorios estao materializados.

## Requisitos Funcionais

RF-001 — O command deve listar todos os subdiretorios de `.dadaia/contexts/`.
RF-002 — Se o diretorio estiver vazio, deve informar que nenhum contexto esta ativo.
RF-003 — O output deve incluir nome do contexto e caminho relativo.

## Requisitos Nao-Funcionais

RNF-001 — O command nao deve criar, modificar ou deletar arquivos.
RNF-002 — Deve funcionar mesmo se `.dadaia/contexts/` nao existir (retorna mensagem apropriada).

## Fora de Escopo

- Materializar novos contextos
- Remover ou atualizar contextos existentes
- Mostrar historico de uso dos contextos

## Criterio de Conclusao

Ao invocar `/list-contexts`, o agente retorna uma lista de contextos com nome e caminho, ou uma mensagem informando ausencia de contextos.
```

Aprovado? Prosseguindo.

---

## Fase 2 — Plan: como vai ser implementado

O agente recebe a spec e gera um `PLAN.md`:

```markdown
# PLAN — list-contexts-command

## O que vai ser criado

- `.claude/commands/list-contexts.md` — novo command com instrucoes de execucao

## O que nao vai ser tocado

- CLI (`dadaia-workspace/`)
- Runtime alem de `.claude/commands/`
- Qualquer arquivo existente

## Decisoes de design

- O command usa `ls .dadaia/contexts/` internamente via instrucao para o agente
- Nao requer tool externo — o agente resolve com file system access padrao
- O frontmatter segue o padrao dos outros commands do workspace

## Riscos

- Se o agente nao tiver permissao de tool para listar diretorios, o command falha silenciosamente
- Solucao: a instrucao deve incluir fallback textual se o diretorio nao for acessivel
```

Voce revisa. Faz sentido. Aprova.

---

## Fase 3 — Tasks: unidades verificaveis

O agente gera o `TASKS.md`:

```markdown
# TASKS — list-contexts-command

T-001 — Criar `.claude/commands/list-contexts.md` com frontmatter e steps conforme PLAN.md
  Criterio: arquivo existe, frontmatter tem campo `description`, steps cobrem RF-001 a RF-003

T-002 — Testar invocacao do command no Claude Code
  Criterio: `/list-contexts` retorna output coerente (lista ou mensagem de ausencia)

T-003 — Atualizar README da Academy se o command for referenciado como exemplo
  Criterio: referencia adicionada ou confirmado que nao cabe neste contexto
```

Voce revisa. Aprova T-001 e T-002. Nota que T-003 esta fora do escopo da spec e pede remocao.

Agente remove T-003. Voce aprova a versao final.

---

## Fase 4 — Implement

O agente cria `.claude/commands/list-contexts.md` conforme as tasks.

Voce verifica:

- O arquivo existe em `.claude/commands/`?
- O frontmatter tem campo `description`?
- Os steps cobrem todos os RFs?
- O command funciona ao ser invocado?

Se sim: task concluida. Spec atualizada para `Status: Implemented`.

---

## O que mudou em relacao ao prompt solto

- Voce sabe exatamente o que o agente vai implementar antes de ele comecar.
- Cada linha de codigo pode ser rastreada ate uma task aprovada.
- Se algo estiver errado, voce sabe em qual fase o problema entrou.
- Proxima pessoa que pegar o projeto encontra spec, plano e tasks — nao so codigo.
