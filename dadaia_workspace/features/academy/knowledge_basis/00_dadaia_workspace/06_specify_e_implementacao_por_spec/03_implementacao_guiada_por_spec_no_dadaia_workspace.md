# 03. Implementacao Guiada por Spec no Dadaia Workspace

## Como o workspace materializa o fluxo SDD

O `dadaia-workspace` nao apenas recomenda SDD. Ele organiza o runtime para que o fluxo aconteca de forma natural.

Os sinais mais visíveis dessa organizacao sao:

- `dadaia-workspace/specs/constitution.md` — a lei maior do produto, always-on
- `dadaia-workspace/specs/memory/` — contexto permanente de arquitetura e produto
- `dadaia-workspace/specs/features/` — uma pasta por feature em desenvolvimento
- `.claude/commands/work-on-spec.md` — o command que conduz o ciclo completo
- `.claude/commands/dadaia-academy.md` — o command que navega o material de aprendizado

Esses artefatos nao estao no workspace por acidente. Estao la porque o produto foi desenhado para que o proprio ambiente ensine a disciplina que espera dos agentes.

---

## O command /work-on-spec

O comando `/work-on-spec` e o ponto de entrada canonico para o ciclo SDD dentro do workspace.

Ao invocar esse command, o agente:

1. Le `constitution.md` e `memory/` para garantir alinhamento com o contexto permanente.
2. Identifica a feature spec ativa ou pede que voce informe qual iniciar.
3. Gera um `PLAN.md` com as decisoes de design, estrutura de arquivos e dependencias.
4. Apresenta o plano e aguarda aprovacao antes de prosseguir.
5. Gera um `TASKS.md` com tarefas verificaveis.
6. Apresenta as tasks e aguarda aprovacao.
7. Inicia a implementacao fase a fase, reportando conclusao de cada task.

Cada ponto de aprovacao humana e explicito. O agente para e espera.

### Como invocar

```text
/work-on-spec
```

Se houver mais de uma feature spec ativa, o agente perguntara qual usar.
Se quiser apontar diretamente, voce pode informar o caminho:

```text
/work-on-spec specs/features/minha-feature/SPEC.md
```

---

## O role do /dadaia-academy no fluxo

O command `/dadaia-academy` e o ponto de entrada para navegacao e aprendizado.

Ele nao executa implementacao. Ele orienta:

- qual sessao da Academy e mais relevante para o contexto atual
- qual material ler antes de comecar uma tarefa especifica
- como gerar ou expandir conteudo dentro de `.dadaia/academy/` quando necessario

Na pratica, voce pode usar `/dadaia-academy` antes de usar `/work-on-spec` quando:

- esta chegando em um novo topico e quer entender o contexto antes de implementar
- precisa revisar um padrao SDD antes de escrever uma spec
- quer verificar qual session cobre o dominio que vai trabalhar

---

## Workflow tipico passo a passo

Este e o fluxo que voce vai usar no dia a dia.

### 1. Contexto permanente primeiro

Antes de qualquer session de implementacao, leia o que e imutavel:

```bash
cat dadaia-workspace/specs/constitution.md
cat dadaia-workspace/specs/memory/architecture.md
cat dadaia-workspace/specs/memory/tech-stack.md
```

Ou instrua o agente a fazer isso pelo contexto da sessao antes de prosseguir.

### 2. Escreva ou revise a feature spec

Abra ou crie `specs/features/[sua-feature]/SPEC.md`.

Siga o template do modulo anterior: contexto, user stories, RFs, RNFs, fora de escopo, criterio de conclusao.

Nao prossiga enquanto a spec nao estiver aprovada.

### 3. Invoque /work-on-spec

```text
/work-on-spec
```

Aguarde o `PLAN.md`. Revise. Aprove ou solicite ajustes.

### 4. Aprove o PLAN.md

Leia o plano com atencao:

- Os arquivos que serao criados ou modificados fazem sentido?
- O plano esta dentro do escopo da spec?
- Existem riscos nao mapeados?

Se aprovar, informe ao agente e aguarde o `TASKS.md`.

### 5. Aprove o TASKS.md

Verifique cada task:

- A acao e clara e unica?
- O criterio de conclusao e verificavel?
- A ordem faz sentido dada as dependencias?

Se aprovar, o agente comeca a implementar.

### 6. Acompanhe a implementacao

A cada task concluida, o agente deve:

- Informar o que foi feito
- Mostrar o criterio de conclusao verificado
- Aguardar confirmacao antes de seguir

Se o agente nao parar entre tasks, o framing do command esta incorreto ou voce autorizou execucao continua sem querer.

### 7. Revise e feche o ciclo

Quando todas as tasks estiverem concluidas:

- Revise os arquivos gerados
- Verifique se os criterios de conclusao da spec foram todos atendidos
- Atualize o `STATUS` da spec para `Implemented`
- Commite as mudancas com uma mensagem que referencia o TASKS.md

---

## Sinais de que o fluxo esta saudavel

- Cada fase tem um artefato aprovado antes de comecar
- O agente nao implementa nada fora das tasks
- Voce consegue rastrear cada linha de codigo ate uma task especifica
- Specs sao atualizadas quando ha mudancas, nao apenas criadas e esquecidas

## Sinais de que o fluxo esta quebrado

- Voce esta pedindo para o agente "so fazer isso rapidinho" sem spec
- O agente adicionou codigo que voce nao pediu "porque achou que fazia sentido"
- `TASKS.md` foi gerado sem voce ter aprovado `PLAN.md`
- Voce esta discutindo implementacao com o agente antes de ter uma spec aprovada
