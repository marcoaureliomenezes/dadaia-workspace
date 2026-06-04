---
name: dadaia-task-manager
description: >
  Protocolo obrigatório para todo agente que vá modificar arquivos de produção
  dentro de um Spec Context Project. Define como reservar, executar e concluir
  tasks em TASKS.md usando os 3 markers canônicos: [ ] OPEN → [-] IN PROGRESS → [x] DONE.
  Combinado com o gate sdd-spec-gate.sh v2, garante rastreabilidade total de
  "quem pegou o quê" e impede que dois agentes paralelos editem a mesma task.
applyTo: "specs/**/TASKS.md"
---

# dadaia-task-manager — Task State Protocol

## Contrato dos 3 markers

| Marker | Estado | Semântica |
|---|---|---|
| `[ ]` | OPEN | Task declarada, ninguém trabalhando nela. Default. |
| `[-]` | IN PROGRESS | Algum agente reservou. Trabalho ativo. |
| `[x]` | DONE | Implementada, verificada, commitada. |

**Regra invariante:** nunca dois `[-]` simultâneos no mesmo `TASKS.md`. Se você
encontrar dois `[-]` ao começar uma sessão, **pare** e reporte ao operador.

## Protocolo de 4 passos

Quando você for trabalhar em produção (qualquer arquivo coberto pelo gate
`sdd-enforcement`), siga estes 4 passos **na ordem**:

### Passo 1 — Identificar a task

Leia o `TASKS.md` relevante (primary: `specs/releases/<active>/TASKS.md`, resolvido via
`specs/releases/ACTIVE.md`; Legacy compat: se `releases/ACTIVE.md` ausente, cair em
`specs/features/<feat>/TASKS.md` com `SDD_LEGACY_FEATURES=1`).
Identifique a task que você vai executar. Ela **deve** existir e estar `[ ]`
(OPEN). Se não estiver em OPEN, abra interrupção com o operador antes de
prosseguir.

### Passo 2 — Reservar (`[ ]` → `[-]`) e commitar

Use Edit/Write para mudar o marker da task de `[ ]` para `[-]`. Em seguida,
faça um commit **isolado** apenas dessa mudança:

```
chore(tasks): start <task-id>
```

Exemplo:
```
chore(tasks): start T128
```

Esse commit é o **lock observável** que diz "agente X reservou a task". Outros
agentes em sessões paralelas verão esse commit via `git pull` ou ao reler o
arquivo.

### Passo 3 — Executar o trabalho

Faça a implementação. Pode haver múltiplos commits durante essa fase
(intermediários, refactors, fixes). O marker permanece `[-]` durante todo o
trabalho.

### Passo 4 — Concluir (`[-]` → `[x]`) e commitar

Quando terminar e os critérios de aceite da task estiverem satisfeitos:

1. Mude o marker `[-]` → `[x]`.
2. Faça o **último commit da task** com convencional commits, incluindo no
   diff tanto o marker `[x]` quanto qualquer arquivo final ainda pendente.

Exemplo de commit final:
```
feat(orchestration): implement run.resume idempotency (T128)
```

## Recovery — quando algo dá errado

### Encontrei um `[-]` antigo de outra sessão

**Não flip silenciosamente para `[x]`.** Você não sabe se a task foi concluída
ou abandonada. Pare, leia o `git log` para entender o histórico, e reporte ao
operador antes de qualquer transição.

### Encontrei dois `[-]` simultâneos

Violação da invariante. Pare. Reporte ao operador. Espere a decisão antes de
qualquer edição em produção.

### Preciso abandonar uma task sem concluir

Mude o marker `[-]` → `[ ]` e commit:
```
chore(tasks): abandon <task-id>
```
Documente o motivo na mensagem do commit. Outro agente pode pegar a task
depois.

### O gate `sdd-spec-gate.sh` me bloqueou

Significa que:
- (a) você não tem nenhuma task `[-]` no `TASKS.md` relevante e está
  tentando editar produção, ou
- (b) a resolução do contexto ativo falhou (env var `DADAIA_CONTEXT` ausente e nenhum context `alive` em `spec_contexts.json`).

Em (a): volte ao Passo 1–2. Em (b): rode `dadaia context show --json` para verificar
o context ativo; se ausente, execute `eval $(dadaia context bind <name> --mode read)` ou peça ao operador.

## Onde TASKS.md vive

O gate v3 procura tasks `[-]` recursivamente em todo `<primary_specs_dir>/`, com prioridade:

- **Primário:** `<primary_specs_dir>/releases/<active-release-id>/TASKS.md` — onde a
  release ativa (apontada por `<primary_specs_dir>/releases/ACTIVE.md`) mantém suas tasks.
- **Legacy compat:** `<primary_specs_dir>/features/*/TASKS.md` — habilitado quando a env
  var `SDD_LEGACY_FEATURES=1` (default durante janela de migração). Após a release de
  migração concluir, esse fallback é desligado.
- **Raiz (legado):** `<primary_specs_dir>/TASKS.md` — só durante a migração; após, é
  reportado pelo doctor como erro estrutural.

A presença de **pelo menos uma** task `[-]` em qualquer um desses caminhos libera o gate
para todo o `repos/<primary_slug>/`. O gate não valida que a task `[-]` cobre exatamente
o arquivo-alvo — é responsabilidade sua estar trabalhando no escopo declarado pela task.

TASKS.md **permanece em markdown** mesmo após a migração de memory para HTML. Os markers
`[ ]/[-]/[x]` são contrato máquina e exigem parsing simples por grep.

## Por que o commit extra `chore(tasks): start`?

Sem ele, o estado `[-]` não é observável por outros agentes nem registrado no
histórico. O custo de um commit extra é trivial; o ganho de rastreabilidade é
alto. Se a poluição do histórico incomodar, o operador faz **squash no merge**
do PR — política de cada repo.

## Em uma frase

> Antes de tocar qualquer arquivo de produção: declare a task com `[-]` e
> commit. Antes de encerrar: feche com `[x]` e commit. Sem exceção.
