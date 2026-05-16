# Spec: Feature — SDD Release Lifecycle

> **Status:** Draft
> **Feature ID:** sdd-release-lifecycle
> **Owner:** product-engineer
> **Created:** 2026-05-16

---

## Contexto

O processo SDD atual do workspace dadaia tem uma intencao correta, mas a operacao real esta
fragmentada entre repos. O padrao documentado diz que o pipeline e:

```text
SPEC.md [Aprovado] -> PLAN.md [Aprovado] -> TASKS.md [Aprovado] -> Implementacao
```

Na pratica, os repos analisados (`dadaia-workspace`, `portifolio`, `dadaia-bots`,
`tauan-games`) apresentam divergencias:

- `memory/` nem sempre existe ou nem sempre e a fonte atomica do produto atual.
- `SPEC.md`, `PLAN.md` e `TASKS.md` estao sendo usados como backlog permanente,
  historico, roadmap e contrato de implementacao ao mesmo tempo.
- Specs implementadas permanecem vivas no backlog ativo.
- Status nao canonicos aparecem em varios formatos: `[x] Approved`, `Accepted`,
  `Implementado`, `Source of Truth`, `[ ] Draft`.
- O gate atual valida apenas a existencia de alguma task `[-]`, mas nao valida o
  pipeline completo SPEC -> PLAN -> TASKS aprovado.
- O arquivamento varia por repo: alguns usam `_archive`, outros deletam, outros mantem
  specs antigas vivas.

Esta feature redefine o ciclo de vida SDD como um processo orientado a release, com
`memory/` como fonte atomica permanente do estado atual do projeto.

---

## Objetivo

Estabelecer um padrao unico e enforceavel para gestao de specs em todos os Spec Context
Projects do workspace dadaia.

O novo padrao deve garantir que:

1. `memory/` sempre contenha a visao atomica atual do produto.
2. `SPEC.md`, `PLAN.md` e `TASKS.md` sejam criados por release, nao como backlog infinito.
3. Ao concluir uma release, os deltas implementados sejam incorporados ao `memory/`.
4. Releases concluidas sejam arquivadas de forma padronizada.
5. Agentes e hooks bloqueiem implementacoes que nao sigam o ciclo aprovado.
6. Repos existentes possam ser migrados de forma incremental.

---

## Glossario

| Termo | Definicao |
|---|---|
| Memory | Conjunto de arquivos em `specs/memory/` que descreve o estado atual e atomico do projeto. |
| Release spec | `SPEC.md`, `PLAN.md` e `TASKS.md` dentro de `specs/releases/<release-id>/`. |
| Release ativa | Release em desenvolvimento, aprovada para implementacao, ainda nao arquivada. |
| Closure | Documento de fechamento de release que prova validacao, tasks concluidas e atualizacao de memory. |
| Archive | Historico de releases concluidas em `specs/_archive/releases/<release-id>/`. |
| Backlog candidate | Ideia ou feature ainda nao aprovada para release. Nao autoriza implementacao. |

---

## Estrutura Canonica de Specs

Todo Spec Context Project deve convergir para a seguinte estrutura:

```text
specs/
  constitution.md
  memory/
    product.md
    architecture.md
    tech-stack.md
    operations.md        # opcional
    security.md          # opcional
  releases/
    <release-id>/
      SPEC.md
      PLAN.md
      TASKS.md
      CLOSURE.md         # criado somente no fechamento
  backlog/
    ideas.md
    candidates.md
  _archive/
    releases/
      <release-id>/
        SPEC.md
        PLAN.md
        TASKS.md
        CLOSURE.md
```

### Regras estruturais

- `specs/memory/product.md`, `specs/memory/architecture.md` e
  `specs/memory/tech-stack.md` sao obrigatorios em todo contexto.
- `specs/releases/<release-id>/SPEC.md` descreve somente o delta daquela release.
- `specs/releases/<release-id>/PLAN.md` descreve como implementar o delta aprovado.
- `specs/releases/<release-id>/TASKS.md` descreve tarefas executaveis e rastreaveis.
- `specs/releases/<release-id>/CLOSURE.md` registra conclusao, validacao e incorporacao
  ao memory.
- `specs/backlog/` pode conter ideias e candidatos, mas nunca autoriza implementacao.
- `specs/_archive/` e historico. Agentes nao devem usar archive como fonte primaria para
  implementar.

---

## Status Canonico

Somente estes status sao validos para gates SDD:

```text
**Status:** Draft
**Status:** Em revisão
**Status:** Aprovado
```

Para fins de implementacao, somente `**Status:** Aprovado` libera o proximo gate.

Status como `[x] Approved`, `Accepted`, `Implementado`, `Completed`, `Source of Truth`,
`[ ] Draft` ou variantes em ingles nao contam como aprovacao.

Informacoes como "implementado", "concluido" ou "arquivado" devem aparecer em
`CLOSURE.md` ou em secoes historicas, nunca como status de gate.

---

## Ciclo de Vida SDD por Release

### 1. Discovery

O `product-engineer` deve carregar:

1. `specs/constitution.md`
2. todos os arquivos em `specs/memory/`
3. `specs/backlog/`
4. releases ativas em `specs/releases/`
5. reports especialistas em `.dadaia/reports/<context>/`

Se ainda houver ambiguidade, o `product-engineer` deve usar `dadaia-grill-me`.

### 2. SPEC da Release

O `product-engineer` cria `specs/releases/<release-id>/SPEC.md` com status Draft.

A SPEC deve declarar:

- objetivo da release;
- deltas de produto;
- deltas de arquitetura;
- deltas de tech-stack;
- deltas de seguranca ou operacao, se aplicavel;
- arquivos de `memory/` que deverao ser atualizados no fechamento;
- criterios de aceite da release;
- itens fora de escopo;
- dependencias e riscos.

### 3. PLAN da Release

`PLAN.md` so pode ser criado depois da SPEC aprovada.

O PLAN deve conter:

- estrategia de implementacao;
- camadas afetadas;
- ordem de execucao;
- riscos tecnicos;
- plano de validacao.

O PLAN nao deve conter blocos extensos de codigo, comandos de commit ou roteiro linha a
linha de implementacao. Como regra operacional, PLANs acima de 300 linhas devem ser
revisados e compactados ou movidos para design docs auxiliares.

### 4. TASKS da Release

`TASKS.md` so pode ser criado depois do PLAN aprovado.

Cada task deve conter:

- id estavel;
- descricao;
- owner esperado;
- arquivos ou subsistema alvo;
- pre-condicoes;
- criterio de pronto;
- indicacao de paralelismo quando aplicavel.

Estados validos:

```text
[ ] OPEN
[-] IN PROGRESS
[x] DONE
```

Por default, uma release deve ter no maximo uma task `[-]`. Multiplas tasks `[-]` so sao
permitidas quando o `TASKS.md` declarar explicitamente que elas sao paralelas e nao
competem pelo mesmo write set.

### 5. Implementacao

Agentes de implementacao so podem modificar arquivos de producao quando:

- existe uma release ativa;
- `SPEC.md`, `PLAN.md` e `TASKS.md` da release ativa possuem `**Status:** Aprovado`;
- existe task aplicavel marcada `[-]`;
- o agente esta atuando dentro do escopo da task.

### 6. Closure

Quando todas as tasks da release estiverem `[x]`, o `product-engineer` deve criar
`CLOSURE.md`.

O closure deve registrar:

- resumo do que foi entregue;
- tasks concluidas;
- validacoes executadas;
- arquivos de `memory/` atualizados;
- drifts resolvidos;
- debitos ou follow-ups retornados para `specs/backlog/`;
- decisao de arquivamento.

### 7. Atualizacao de Memory

Antes de arquivar uma release, o `product-engineer` deve atualizar o memory aplicavel:

- `memory/product.md`: comportamento atual, usuarios, capacidades e limites do produto.
- `memory/architecture.md`: arquitetura atual, camadas, fluxos, contratos, estado runtime.
- `memory/tech-stack.md`: tecnologias aprovadas, versoes, toolchain, comandos, restricoes.
- `memory/security.md`: controles atuais, ameacas aceitas, non-negotiables, se existir.
- `memory/operations.md`: runbooks, ambientes, lifecycle operacional, se existir.

O memory nunca deve ser tratado como changelog. Ele deve descrever o produto como ele e
agora.

### 8. Arquivamento

A release concluida deve ser movida de:

```text
specs/releases/<release-id>/
```

para:

```text
specs/_archive/releases/<release-id>/
```

Depois do arquivamento, nenhum agente deve usar essa release como fonte de implementacao.
Historico incremental continua sendo responsabilidade do Git; o archive existe para
auditoria humana de releases.

---

## Requisitos Funcionais

### RF-001 — Memory obrigatorio

Todo contexto deve possuir:

- `specs/memory/product.md`
- `specs/memory/architecture.md`
- `specs/memory/tech-stack.md`

Se algum deles estiver ausente, `dadaia specs doctor` deve reportar erro.

### RF-002 — Releases como unidade de SDD

Novas specs executaveis devem viver em `specs/releases/<release-id>/`.

`PLAN.md` e `TASKS.md` fora de `specs/releases/<release-id>/` devem ser tratados como
legado durante a migracao e como erro apos a migracao.

### RF-003 — Backlog nao autoriza implementacao

Arquivos em `specs/backlog/` podem documentar ideias, candidatos e prioridades, mas nunca
podem liberar implementacao.

### RF-004 — Closure obrigatorio

Uma release nao pode ser arquivada sem `CLOSURE.md`.

### RF-005 — Memory update obrigatorio

`CLOSURE.md` deve listar quais arquivos de `memory/` foram atualizados. Se a release nao
exigir update de algum memory file, o motivo deve ser registrado explicitamente.

### RF-006 — Status canonico

Ferramentas e agentes devem reconhecer somente:

- `**Status:** Draft`
- `**Status:** Em revisão`
- `**Status:** Aprovado`

Qualquer outro status deve ser reportado como nao canonico.

### RF-007 — Gate SDD v3

O hook `sdd-spec-gate.sh` deve evoluir para validar:

1. contexto primario resolvido;
2. release ativa encontrada;
3. `SPEC.md`, `PLAN.md` e `TASKS.md` da release ativa aprovados;
4. ao menos uma task aplicavel `[-]`;
5. status canonico;
6. archive ignorado como fonte de aprovacao.

### RF-008 — Task scope

O gate deve continuar permitindo meta-edits em specs, mas edits de producao devem exigir
task ativa da release. Em v3, o gate deve pelo menos reportar o arquivo de `TASKS.md` que
liberou a edicao.

### RF-009 — Product-engineer atualizado

O agente `product-engineer` deve ser atualizado para operar por release, nao por feature
solta. Ele deve ser responsavel por:

- criar SPEC Draft da release;
- criar PLAN somente apos SPEC aprovada;
- criar TASKS somente apos PLAN aprovado;
- atualizar memory no fechamento;
- criar CLOSURE;
- arquivar release concluida.

### RF-010 — Spec navigator atualizado

A skill `dadaia-workspace-spec-navigator` deve carregar primeiro `constitution.md` e
`memory/*`, depois a release ativa. Ela deve ignorar `_archive/` por default.

### RF-011 — Spec reviewer atualizado

A skill `dadaia-workspace-spec-reviewer` deve validar:

- presenca dos memory files obrigatorios;
- status canonico;
- release ativa com gates corretos;
- ausencia de release concluida fora de archive;
- ausencia de PLAN/TASKS executaveis fora de release;
- closure com incorporacao ao memory.

### RF-012 — Task manager atualizado

A skill `dadaia-task-manager` deve operar sobre `specs/releases/<release-id>/TASKS.md`.
Ela deve documentar como declarar tasks paralelas de forma segura.

### RF-013 — Specs doctor

Adicionar comando:

```bash
dadaia specs doctor
```

Checks minimos:

- memory obrigatorio existe;
- status canonicos;
- releases ativas tem SPEC/PLAN/TASKS validos;
- releases arquivadas tem CLOSURE;
- nao ha PLAN/TASKS vivos fora de `specs/releases/`;
- `_archive/` nao esta sendo usado como gate;
- CLOSURE referencia updates de memory.

### RF-014 — Migracao incremental

O sistema deve suportar uma fase de migracao na qual estruturas legadas ainda existam, mas
sejam reportadas pelo doctor como warnings. Apos uma release de migracao, esses warnings
devem virar erros.

---

## Requisitos Nao-Funcionais

- O novo padrao deve ser simples o bastante para humanos seguirem sem ferramenta.
- O gate deve falhar fechado para edicoes de producao quando a release ativa nao estiver
  aprovada.
- O doctor deve produzir output claro para agente e humano.
- A migracao nao deve apagar historico sem decisao explicita.
- O archive deve ser ignorado por automacao de implementacao.
- `memory/` deve permanecer curto e consultavel; nao deve virar dump historico.

---

## Migracao dos Repos Existentes

### dadaia-workspace

- Criar release de migracao para o novo ciclo SDD.
- Migrar backlog real de `specs/TASKS.md` para `specs/releases/<release-id>/` ou
  `specs/backlog/`.
- Fechar e arquivar specs implementadas como `workspace-import`, `sdd-enforcement`,
  `task-state-tracking` e `multi-agent-orchestration`.
- Reescrever `dev-server-registry` como release futura, removendo o PLAN de 2.287 linhas
  do fluxo executavel.

### portifolio

- Converter `_archive/2026-05-14/` para `_archive/releases/<release-id>/` quando aplicavel.
- Quebrar `specs/TASKS.md` de 1.700 linhas em releases.
- Incorporar entregas concluidas em `memory/*`.

### dadaia-bots

- Criar `constitution.md` se ausente.
- Criar `memory/product.md`, `memory/architecture.md`, `memory/tech-stack.md`.
- Consolidar `product-manifesto-v3.md` e `product-overview.md` no memory atomico.
- Converter Wave 1 em `specs/releases/<release-id>/`.

### tauan-games

- Criar `memory/architecture.md`.
- Normalizar status `[x] Approved` para `**Status:** Aprovado`.
- Converter specs grandes de Aero Fighters em releases menores.
- Arquivar releases concluidas apos incorporar ao memory.

---

## Criterios de Aceite

- [ ] `product-engineer` descreve o ciclo release-based e closure obrigatorio.
- [ ] `dadaia-workspace-spec-navigator` carrega memory e release ativa no novo padrao.
- [ ] `dadaia-workspace-spec-reviewer` detecta status nao canonico e releases sem closure.
- [ ] `dadaia-task-manager` opera sobre TASKS de release.
- [ ] `sdd-spec-gate.sh` valida gates completos da release ativa.
- [ ] `dadaia specs doctor` reporta problemas estruturais de specs.
- [ ] `dadaia-workspace`, `portifolio`, `dadaia-bots` e `tauan-games` possuem plano de
  migracao registrado.
- [ ] Nenhuma release concluida permanece viva fora de `_archive/releases/`.
- [ ] Toda release arquivada possui `CLOSURE.md`.
- [ ] `memory/` reflete o estado atual apos fechamento de release.

---

## Fora de Escopo

- Migrar todos os repos nesta primeira SPEC sem PLAN aprovado.
- Implementar comandos CLI antes da aprovacao do pipeline SDD.
- Apagar specs antigas sem closure ou decisao humana explicita.
- Alterar semver real de pacotes publicados.
- Resolver backlog funcional de features existentes como `dev-server-registry`.

---

## Riscos

| Risco | Mitigacao |
|---|---|
| Migracao quebrar agentes existentes | Fase de compatibilidade com warnings antes de erros. |
| Archive virar nova fonte de verdade | Navigator e gate ignoram `_archive/` por default. |
| Memory virar changelog | Closure registra historico; memory registra estado atual. |
| PLANs continuarem gigantes | Reviewer/doctor reportam PLAN acima de limite operacional. |
| Multiplas tasks `[-]` sem controle | Task manager exige declaracao explicita de paralelismo seguro. |

---

## Questoes Abertas

1. Qual formato exato identifica uma release ativa: arquivo `ACTIVE.md`, campo em
   `specs/releases/<release-id>/SPEC.md`, ou estado em `.dadaia/states/`?
2. O limite de 300 linhas para PLAN deve ser hard error ou warning do doctor?
3. `CLOSURE.md` deve exigir hashes/commits de validacao ou apenas comandos e resultados?
4. A migracao dos repos existentes deve ocorrer em uma release unica ou uma release por repo?
