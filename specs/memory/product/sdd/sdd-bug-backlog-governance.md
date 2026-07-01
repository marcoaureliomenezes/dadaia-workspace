---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: Event-sourced JSONL bug store + backlog-consistency engine + bug/backlog → release governance (grill, disposition, audit-disposition law, security-gated push).
summary: >-
  Owns the bug + backlog governance mechanism: the event-sourced JSONL bug store
  (bug-event-v1; dadaia bugs append|status|stats; reported + one terminal event),
  the backlog-consistency engine (subject registry, fail-closed classifier,
  backlog doctor BL-*, consumed_backlog ledger + removal-on-release), the
  bug/backlog → release protocol (PM-dispatched pick, sanitize, mandatory grill,
  bug-always-solved/supersession), the audit-disposition law, the alpha-N/rc-N
  maturation model, and the mechanically gated push boundary.
tags:
  - sdd
  - governance
  - release-lifecycle
  - backlog
  - bugs
  - alpha-rc-model
  - backlog-ownership
agent_tier: self-pull
token_estimate: 1550
last_updated: '2026-07-01'
release_origin: v0.1.47
---

Skill: `dadaia-release-definition` · Rules: `release-governance.md`, `backlog-ownership.md`, `bug-registration-guardrail.md` (always-on)

## Propósito

Define como **bugs são registrados e dispostos**, como o **backlog se mantém um SET
consistente**, e como **bugs + backlog viram releases** que maturam e são revisadas.
Três pilares: o bug event store, o backlog-consistency engine, e o protocolo
bug/backlog → release com seus gates.

## O que é

### Bug event store (JSONL, event-sourced)

Bugs são **eventos JSONL**, nunca arquivos Markdown com frontmatter de status. O store
vive em `specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl` — arquivos append-only por janela de
hora, com rotation ceiling por row-count — e é **git-tracked** (o `.gitignore` do
source repo re-inclui `specs/bugs/*.jsonl`). Cada linha é um JSON validado contra
**`bug-event-v1`** antes do append: em falha de validação nada é escrito e o comando
sai non-zero.

- **Registro:** `dadaia bugs append --bug-id <slug> --event reported --title …
  --severity … --surface … --component … --context … --tag … --symptom … --repro …
  --expected … --notes …` — o evento `reported` exige todos esses campos.
- **Disposição (terminal):** um `bug_id` carrega **no máximo UM evento terminal** de
  `{resolved, superseded, deferred, rejected}` (`resolved --release <id>`;
  `superseded --superseded-by <slug>`; `deferred`/`rejected --reason <texto>`),
  appendado pela release que o dispõe — nunca no registro. Um `reported` posterior
  **reabre** o `bug_id` (limpa o terminal anterior; reopen legítimo não é
  double-terminal).
- **`archived` é anotação NÃO-terminal:** arquivar a fonte legada de um bug é um
  `git mv` para `specs/bugs/_archive/` e **não emite evento**.
- **Inspeção:** `dadaia bugs status` (bugs abertos) e `dadaia bugs stats` (agregados
  por severity/status). `features/bugs/service.py` folda o stream em estado corrente
  por `bug_id`.
- **Redaction:** nenhum campo carrega paths absolutos do operador, IPs, hostnames ou
  segredos; o `redact()` do store é backstop, não licença.
- **Invariante mecânica:** SPEC-DOC-033 ([[specs-doctor]]) valida schema por linha,
  rotation ceiling e coerência de eventos (terminal sem `reported` prévio ⇒ ERROR;
  terminal duplo ⇒ ERROR).
- **Coexistência:** `dadaia bug new` (scaffolder Markdown legado) ainda existe na
  CLI, mas o caminho canônico de registro é `dadaia bugs append` — nenhum workflow
  novo escreve bug como `.md`.

### Backlog-consistency engine (`features/backlog/`)

O backlog é um SET deduplicado, conflict-free e não-stale, enforçado mecanicamente:

- **Schema de item:** frontmatter `intents[]`, cada intent `Subject{kind, ref} →
  change`; `kind ∈ {code, api, cli, panel, doc, invariant, catalog}`; refs tipadas,
  nunca free text (refs `code` são module-relative `path#symbol`; paths
  operator-local/repo privado rejeitados).
- **Registry canônico de subjects** (`subject_registry.py`): auto-derivado da árvore
  viva a cada run (nunca um arquivo armazenado) — kinds `code`/`cli`/`catalog`/`doc`/
  `invariant`; `panel`/`api` ligam apenas pela alias map do operador
  (`.dadaia/states/backlog_subject_aliases.txt`). O modelo propõe um subject; Python
  liga a um anchor e **HALTa** em unresolved/ambiguous (nunca silent NEW).
- **Classifier fail-closed** (`classifier.py`): intersecção de anchors vazia ⇒
  `UNRELATED` (sem modelo); mesmos anchors + mesma change ⇒ `DUPLICATE`; anchor
  compartilhado + change divergente ⇒ **`DIVERGENT_CONFLICT`** por default — o modelo
  só pode fazer downgrade com merge explícito provado-compatível.
- **`dadaia backlog doctor`** (o enforcement real — backlog é gitignored + ADDITIVE,
  então o gate de file-write não o classifica): BL-SCHEMA / BL-DUP / BL-CONFLICT /
  BL-STALE, exit non-zero em violação. Roda em CI (job `backlog-doctor`) e no
  pre-commit chokepoint **escopado**: BL-* bloqueia apenas commits cujos staged paths
  intersectam `specs/backlog/**` — debt pré-existente não bloqueia commit não
  relacionado; a varredura completa fica no CI.
- **Removal-on-release (loop fechado):** a linha `**Consumes:** <slugs>` do SPEC →
  post-step de `dadaia lifecycle release define` escreve o ledger
  `specs/_archive/<release>/consumed_backlog.json` (fail-loud `ConsumesBindError` em
  slug/anchor irresolvível; granularidade full-slug) → `dadaia lifecycle close` roda o
  removal residual-aware (rewrite-down-to-residual default; full removal só a zero
  residual, com cópia durável em `_archive/<release>/consumed-backlog/<slug>.md`
  ANTES do unlink). BL-STALE casa por exact slug membership contra o ledger.

### Ownership

`project-manager` **cura** `specs/backlog/**`; `product-engineer` **lê** o backlog
PM-curado para autorar SPEC/PLAN/TASKS e nunca cura. Não há gate de ownership —
`specs/backlog/**` é ADDITIVE e sempre flui; a única trava determinística do produto é
o lease single-session por Spec Context. Enforcement de consistência é o doctor acima.

## Fluxo de uso

### Bug/Backlog → Release (skill `dadaia-release-definition`)

1. **Dispatch.** PM despacha PE para definir uma release a partir dos bugs abertos
   (`dadaia bugs status`) + backlog. PE nunca auto-inicia.
2. **Sanitização.** Itens stale/inválidos recebem disposição explícita (backlog:
   status terminal + archive move; bugs: evento `deferred`/`rejected` com reason).
   Nunca deletar — arquivar.
3. **Pick.** Bugs abertos e audits não-dispostos **outrank** backlog plano. Todo bug
   picked é resolvido na release (**bug-always-solved**), a menos que um item de
   backlog picked o supersede — então evento `superseded --superseded-by <slug>` + as
   TASKS do item cobrem o aceite do bug. Nunca dropado silenciosamente.
4. **Audit-disposition law:** todo audit gera exatamente UMA release de remediação que
   dá disposição explícita a CADA finding (fixed / superseded / deferred-com-reason /
   rejected-com-reason); o audit arquiva para `specs/audits/_archive/` só quando
   totalmente disposto E a release aprovada (SPEC-DOC-036/038 são o backstop).
5. **Grill obrigatório** (`dadaia-grill-me`) sobre o set picked ANTES da SPEC.
6. **SPEC** como Draft → `Aprovado`. Ao fim da release, PE appenda os eventos
   terminais dos bugs dispostos.

### Maturação e push boundary

- Uma release é `v<M>.<m>.<p>` numa branch única `feature/{version}`, maturando por
  segmentos `alpha-N → rc-N` (cada segmento com SPEC/PLAN/TASKS/CLOSURE quando usado;
  `ACTIVE.md` carrega `segment:` opcional). Hotfix é uma release normal que ships do
  `alpha-1` (PATCH ≥ 1; [[sdd-hotfix-track]] é referência superseded).
- **Commits** nunca são review-blocked (só o pre-commit lease gate + backlog-doctor
  escopado). **Push** é gated mecanicamente: o pre-push hook roda `dadaia ci
  preflight` (ruff format/check, mypy --strict, pytest — excluindo
  `tests/performance`) E o security-verdict check — um handoff `security-reviewer`
  APPROVED com `metrics.commit_sha` igual a cada sha pushed ([[sdd-gate-v3]]).
- **Gates semânticos** (`features/lifecycle/gates.py`) validam handoffs QA/security/
  code-review por agent, context, release, verdict, hash, sha, age e severity — são
  os gates que os dadaia-workflows consomem ([[lifecycle-foundation]]).
- **Blocked/resume:** quando uma ação externa não pode executar, `dadaia lifecycle
  preflight` retorna BLOCKED tipado com comando exato + resume token.

## Trigger típico

Registro de bug em qualquer sessão (ADDITIVE, sem lease, sem bind); início de ciclo de
release (PM despacha PE); disposição de bugs/audits no fim de uma release; commit
tocando `specs/backlog/**`.

## Diferencial

Toda decisão de release tem dono explícito; todo bug tem destino declarado num stream
auditável e validado por schema; o backlog não acumula duplicatas nem conflitos
silenciosos; audits nunca viram leitura-e-esquecimento; e o push boundary é um gate
mecânico, não uma convenção.

## Estado runtime tocado

- `specs/bugs/*.jsonl` (git-tracked; append via `dadaia bugs append`) +
  `specs/bugs/_archive/` (fontes legadas movidas por `git mv`).
- `specs/backlog/**` (gitignored no source repo; ADDITIVE) +
  `.dadaia/states/backlog_subject_aliases.txt`.
- `specs/_archive/<release>/consumed_backlog.json` + `consumed-backlog/<slug>.md`.
- `specs/releases/ACTIVE.md`, `specs/releases/<ver>/**`.
- Git hooks: `pre-commit-lease-gate.sh` (+ backlog-doctor escopado),
  `pre-push-ci-gate.sh` (preflight + verdict).

## Dependências

- [[sdd-gate-v3]] — classes de path (bugs/backlog/audits ADDITIVE; `_archive` FROZEN
  antes de ADDITIVE) e os chokepoints git.
- [[specs-doctor]] — SPEC-DOC-033 (invariante do event store), 031/035 (disposição de
  backlog), 036/038 (disposição/arquivamento de audits).
- [[lifecycle-foundation]] / [[dadaia-workflows]] — os workflow bodies
  (release_definition, backlog_definition, bug_report) que orientam este fluxo.
- [[public-asset-distribution]] — propaga skill + rules + git-hook scripts.
