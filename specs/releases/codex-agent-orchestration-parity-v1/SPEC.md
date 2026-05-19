# Spec: Release — codex-agent-orchestration-parity-v1

> **Status:** Draft
> **Release ID:** codex-agent-orchestration-parity-v1
> **Owner:** product-engineer
> **Created:** 2026-05-19
> **Phase:** DISCOVERY
> **Branch:** `release/codex-agent-orchestration-parity-v1` (already cut from `main`
> at the `agents-r3-v1` archive tip, post merge of PR #13 — git tip `bd40e83`)
> **Predecessor:** `agents-r3-v1` (CLOSED + ARCHIVED on 2026-05-19) — last release in
> the `agents-rN-v1` series; it shipped the 16 → 20 agent topology, the
> `software-engineer` split into `software-engineer-python` + `software-engineer-node`,
> and the three new Tier-3 specialists `data-engineer` + `data-analyst` + `ai-engineer`
> (Opus 4.7, owner exclusivo de `dadaia_workspace/public/{skills,rules,workflows,commands,agents,hooks}/**`).
> **Discovery inputs:**
> - Backlog canonical entry: `specs/backlog/candidates.md` line 26 (full scope, ADR list,
>   minimum gates, non-goals, owner context).
> - Operator's promotion intent at `specs/backlog/candidates.md` line 17 (now removed by
>   this P0 since the release is active, not queued).
> - Atomic memory (post `agents-r3-v1` CLOSURE):
>   - `specs/memory/architecture.html` — agent-topology layer reflects 20 agents.
>   - `specs/memory/product/index.html` — feature catalog with data + BI + AI bullets.
>   - `specs/memory/product/agent-orchestration.html` — 20-agent surface, Decision
>     Authority Matrix with five new rows, `ai-engineer` write-allowlist.
>   - `specs/memory/tech-stack.html` — runtimes (Claude / Codex / OpenCode) currently
>     listed without parity caveats.
> - Constitution: `specs/constitution.md` Pilar 2 (orquestração multi-agente) — still
>   stack-neutral; this release does NOT modify constitution.
> - Source surface exercised by this release (read in P0; edits gated to P3+):
>   - `dadaia_workspace/public/agents/*.md` — 20 canonical persona files (verified count).
>   - `dadaia_workspace/public/workflows/*.workflow.md` — 7 canonical workflows
>     (`audit-cycle`, `code-review-fan-out`, `cross-cutting-feature`, `game-dev-cycle`,
>     `hotfix-release`, `onboarding-new-repo`, `spec-refinement`).
>   - `dadaia_workspace/public/skills/**`, `public/rules/**`, `public/commands/**`,
>     `public/hooks/**` — projection sources.
>   - `dadaia_workspace/infrastructure/public_assets.py` — installer (`_install_codex`,
>     `_install_claude`, projection helpers).
>   - `dadaia_workspace/features/agents/dispatcher/` — `ClaudeAgentDispatcher` (kept) +
>     `CodexAgentDispatcher` (to be hardened for parity-best-effort + parallel +
>     unsupported-capability).
>   - `.codex/` current projection state (P0 inspection):
>     - `.codex/config.toml` — 15 lines, ZERO `[agents.*]` blocks, ZERO
>       `developer_instructions`, ZERO `agents.<name>.config_file` registrations.
>     - `.codex/agents/` — directory **does not exist** (no custom agents projected).
>     - `.codex/workflows/` — 5 files present; missing `audit-cycle.workflow.md` and
>       `code-review-fan-out.workflow.md` vs canonical 7 → confirmed drift.
>     - `.codex/rules/` — only 2 files (`game-agents-coordination.md`,
>       `game-developer-scope.md`).
>   - `.claude/agents/` — 20 files present (parity reference; MUST remain byte-identical
>     after this release per the non-goals).

---

## 1. Context — Operator's promotion intent (verbatim)

The bullet that promoted this release, quoted from `specs/backlog/candidates.md` line 17
(now removed by P0 since the release became active):

> **`codex-agent-orchestration-parity-v1`** — escolhida pelo operador 2026-05-19 após
> fechamento de `agents-r3-v1`. Stacks após `release/panel-r5-v1` e
> `release/agents-r3-v1` mergearem em `main`. Inicia com cut-branch +
> product-engineer authoring SPEC/PLAN/TASKS em fase DISCOVERY. ACTIVE.md permanece
> `release: none` até P0 commit.

The full canonical scope (line 26 of the same file) is reproduced in §2 (Functional
Requirements) and §3 (Acceptance Criteria) below.

---

## 2. Objective

Revalidar e reconstruir a paridade Codex dos **20 agentes** (não 16 — pós `agents-r3-v1`)
e dos **7 workflows canônicos** sem alterar a projeção Claude. O delta principal:

1. **Custom Codex agents nativos** — gerar `.codex/agents/<name>.toml` para cada um dos
   20 agentes canônicos, com `developer_instructions` completos derivados do corpo
   markdown da persona, e registrá-los em `[agents.<name>] config_file = "..."` dentro
   de `.codex/config.toml`.
2. **Model mapping Claude → Codex** — toda assignment `claude-opus-4-7` /
   `claude-sonnet-4-6` da frontmatter canônica é traduzida para um identificador Codex
   válido (default + override quando aplicável). Nenhum `claude-*` pode vazar para a
   projeção Codex.
3. **Skills via `.agents/skills`** — projetar o conteúdo de `public/skills/**` para
   o consumer surface de Codex, sem duplicar texto canônico.
4. **Rules** — separar rules **comportamentais** (renderizadas como prose dentro do
   `AGENTS.md` raiz ou do corpo do agente) das rules **executáveis** (renderizadas como
   arquivos `.rules`).
5. **Dispatchers Codex-aware** — `project-manager` e `project-auditor` ganham orquestração
   Codex explícita com subagents; o `CodexAgentDispatcher` é fortalecido para parity
   best-effort, paralelo quando suportado, e `unsupported-capability` explícito quando
   não.
6. **Workflows como recipes** — transformar `.workflow.md` em recipes Codex-executáveis
   ou em invocations geradas a partir de um `WorkflowDefinition` neutro.
7. **Doctor mais forte** — `dadaia public doctor` passa a detectar `.codex/workflows`
   stale, agentes Codex ausentes/inválidos, e drift sem declarar falsa paridade.

**Arquitetura obrigatória ao promover** (verbatim do backlog):
- Uma fonte canônica em `dadaia_workspace/public/**`.
- Renderers/adapters runtime-specific (Claude renderer preservado byte-identical; Codex
  renderer novo).
- `WorkflowDefinition` neutro consumido pelos dois renderers.
- `_install_claude` e `ClaudeAgentDispatcher` preservados (zero edição funcional).
- Sem reescrever o texto canônico de `project-manager` / `project-auditor` que
  referencia o Agent tool — runtime-specific transforms acontecem no renderer Codex.

---

## 3. Functional Requirements

### FR1 — ADR-1: Codex Agent Projection Format

Decidir e documentar **o formato exato** de cada `.codex/agents/<name>.toml`. Inputs
obrigatórios: agent persona canônica markdown + frontmatter (`tier`, `model`, `tools`,
`skills`, `maxTurns`, `input_contract`, `paths.write_allowlist`). Output esperado:

- TOML parseável (`tomllib.load` retorna sem erro).
- Bloco mínimo: `name = "<agent>"`, `model = "<codex-mapped>"`,
  `developer_instructions = """<não-vazio>"""`.
- Campos adicionais (`tools`, `skills`, `paths.write_allowlist`) só são adicionados se
  forem suportados pelo runtime Codex e se a ADR aprovar — sem campos Codex-only sem
  ADR registrada.

A ADR vive em `dadaia_workspace/public/docs/adrs/` ou em `specs/releases/<id>/adrs/`
(decisão em P1). Deve ser citada em todos os testes de parsing.

### FR2 — ADR-2: Runtime-Specific Prompt Transform

O texto canônico do `project-manager` e do `project-auditor` referencia o **Agent tool**
do Claude Code. Codex não tem Agent tool nativo — usa subagents/recipes. ADR-2 define a
função de transformação determinística que, dado o markdown canônico, produz o
`developer_instructions` Codex sem reescrever o markdown canônico no repositório. A
função vive em `dadaia_workspace/infrastructure/runtime_transforms/codex.py` (ou
caminho equivalente decidido em P1) e tem suite de golden tests.

### FR3 — ADR-3: Dispatcher Capability Matrix

Tabela explícita por dispatcher (`project-manager`, `project-auditor`) × runtime
(Claude, Codex) × capability (sequential dispatch, parallel dispatch, fan-out, audit
loop, unsupported-capability fallback). Matrix vive em `public/skills/project-
orchestration/SKILL.md` ou ADR dedicada (decidido em P1) e é exercitada pelos testes
do dispatcher.

### FR4 — ADR-4: Workflow Runtime Boundary

Decidir quem renderiza workflows para Codex: (a) o `_install_codex` em
`public_assets.py` (renderer estático no install time) ou (b) um adapter runtime que
gera invocations on-demand a partir de um `WorkflowDefinition` neutro. Em qualquer caso,
**não há campos Codex-only no workflow canônico sem ADR aprovada** (non-goal #2).

### FR5 — ADR-5: Model Mapping

Tabela explícita `claude-opus-4-7 → <codex-id>` e `claude-sonnet-4-6 → <codex-id>` (e
quaisquer outros models presentes na frontmatter dos 20 agentes). Mapping vive em
`dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py` (ou equivalente).
Acceptance: nenhum identificador `claude-*` aparece em `.codex/**` após install
(grep returns ZERO).

### FR6 — ADR-6: Null Claude Regression Suite

Suite de testes que valida **paridade negativa**: após qualquer mudança Codex, o conteúdo
de `.claude/agents/`, `.claude/workflows/`, `.claude/skills/`, `.claude/rules/`,
`.claude/commands/`, `.claude/hooks/` permanece **byte-identical** ao estado pré-release
(hash-by-hash). Esta suite é o guard contra o non-goal #1 ("não alterar projeção
Claude"). Implementação prevista: snapshot golden de `find .claude -type f -print0 |
xargs sha256sum | sort` antes/depois do install.

### FR7 — `.codex/agents/<name>.toml` para todos os 20 agentes

Gerar 20 arquivos TOML, um por agente canônico. Cada arquivo:
- Parseável por `tomllib`.
- `developer_instructions` é **não-vazio** (string non-empty após strip).
- Nenhum `claude-*` em `model` ou em qualquer campo string.
- Registrado em `.codex/config.toml` via `[agents.<name>] config_file = "agents/<name>.toml"`.

### FR8 — Dispatchers Codex hardening

`dadaia_workspace/features/agents/dispatcher/CodexAgentDispatcher`:
- Testes sequenciais: dispatcher resolve um agente e produz a invocação Codex correta.
- Testes paralelos (best-effort): fan-out múltiplo respeita capability matrix.
- Testes de capability ausente: dispatcher devolve `unsupported-capability` com motivo
  legível, **sem** falhar silenciosamente.

`ClaudeAgentDispatcher` permanece intacto (FR6 é o guard).

### FR9 — Workflow projection: 7 workflows canônicos vs `.codex/workflows/`

Hoje `.codex/workflows/` tem 5 arquivos (`cross-cutting-feature`, `game-dev-cycle`,
`hotfix-release`, `onboarding-new-repo`, `spec-refinement`) — falta `audit-cycle` e
`code-review-fan-out`. Após a release, `.codex/workflows/` deve refletir
**exatamente os 7 canônicos** (ou todos os 7 renderizados na forma que ADR-4 definir).
Doctor passa a detectar drift em ambos os sentidos.

### FR10 — `dadaia public doctor` reforçado

Adicionar checks que detectam:
- Agente canônico sem `.codex/agents/<name>.toml` correspondente.
- `.codex/agents/<name>.toml` sem registro `[agents.<name>]` em `config.toml`.
- `.codex/workflows/` com lista diferente de `public/workflows/`.
- Qualquer string `claude-*` em `.codex/**`.
- `developer_instructions` vazio em qualquer `.codex/agents/*.toml`.

Doctor retorna não-zero em qualquer um desses casos com mensagem identificando o agente
ou workflow drift.

### FR11 — Rules separação comportamental vs executável

Inventariar `dadaia_workspace/public/rules/**` em duas categorias:
- **Comportamental** (prose normativa) → renderizada como prose dentro de `AGENTS.md`
  raiz ou no corpo do agente Codex correspondente.
- **Executável** (`.rules` consumido por runtime) → projetada como arquivo `.rules`.

Critério de classificação e mapeamento vive em ADR (parte de FR1 ou ADR-7 a critério
de P1). Acceptance: `.codex/rules/` contém apenas rules **executáveis**; rules
comportamentais aparecem inline no surface Codex que as consome.

### FR12 — Skills projetadas via `.agents/skills`

Projetar `dadaia_workspace/public/skills/**` para `.agents/skills/` no consumer surface
Codex, com hash-equivalência ao conteúdo canônico (não há divergência de texto entre
Claude/Codex no nível de skill — diferenças ficam em rules + agente).

---

## 4. Acceptance Criteria (minimum gates from backlog line 26)

Os gates abaixo são citação direta do backlog canônico. Cada um é máquina-verificável
e tem evidência registrada na CLOSURE.

- **AC1 — Golden tests for `.claude/agents` and `.claude/workflows`.** Snapshot SHA-256
  by-file de `.claude/agents/**` e `.claude/workflows/**` pré-release MUST igualar o
  pós-release. Comando: `find .claude/{agents,workflows} -type f -print0 | xargs -0
  sha256sum | sort > /tmp/post.txt && diff /tmp/pre.txt /tmp/post.txt`. Evidência:
  diff vazio + ambos hashes commitados em `.dadaia/reports/dadaia-workspace/product-engineer/<...>.html`.
- **AC2 — `.codex/agents/*.toml` parseável com `developer_instructions` não-vazio.**
  Para cada arquivo: `tomllib.load(open(f, "rb"))` retorna sem erro; o campo
  `developer_instructions` existe e `.strip() != ""`.
- **AC3 — No `claude-*` leaking to Codex config.** `grep -rE '(^|[^a-zA-Z0-9_-])claude-'
  .codex/` retorna ZERO linhas (exit 1). Vale para `config.toml`, `agents/*.toml`,
  `workflows/**`, `rules/**`, `hooks.json`.
- **AC4 — Dispatcher Codex sequential test.** `pytest -q tests/unit/features/agents/
  test_codex_dispatcher_sequential.py` exits 0. Testa um único agente despachado via
  Codex resolve para a invocação esperada.
- **AC5 — Dispatcher Codex parallel best-effort test.** `pytest -q tests/unit/features/
  agents/test_codex_dispatcher_parallel.py` exits 0. Fan-out múltiplo respeita a
  capability matrix de ADR-3.
- **AC6 — Dispatcher Codex unsupported-capability test.** `pytest -q tests/unit/
  features/agents/test_codex_dispatcher_unsupported.py` exits 0. Capability ausente é
  devolvida com motivo legível; **não** falha silenciosamente nem declara falsa paridade.
- **AC7 — Doctor detects `.codex/workflows` stale.** Após remover artificialmente um
  workflow de `.codex/workflows/`, `dadaia public doctor` retorna não-zero apontando o
  drift. (Teste integration.)
- **AC8 — Doctor detects Codex agent absent or invalid.** Após remover ou corromper
  artificialmente um `.codex/agents/<name>.toml`, doctor retorna não-zero com
  mensagem nomeando o agente.
- **AC9 — Doctor refuses false parity.** Se um agente canônico não tem `.codex/agents/
  <name>.toml`, doctor não pode reportar `[ok]`; deve reportar drift explícito.
- **AC10 — `dadaia specs doctor` green.** `0 errors / 0 warnings` contra o workspace
  pós-release, incluindo memory atom updates landed em CLOSURE.
- **AC11 — Memory atoms updated atomically.** Em CLOSURE: `specs/memory/architecture.html`
  ganha um bloco no agent-topology layer descrevendo a renderer split
  (canonical → Claude/Codex adapters); `specs/memory/product/agent-orchestration.html`
  ganha a capability matrix; `specs/memory/tech-stack.html` registra a parity guard
  para Codex. Forbidden sections (`Changelog`, `History`, `Histórico`, `Versions`)
  permanecem ausentes.
- **AC12 — Operator review of ADRs.** As 6 ADRs (FR1–FR6) são lidas end-to-end pelo
  operator antes de PLAN ser aprovado. Evidência: explicit operator OK em CLOSURE.

---

## 5. Out of Scope (non-goals from backlog line 26)

Os non-goals são citação direta do backlog canônico e bloquetam mudanças escopo creep:

- **NG1 — Não alterar projeção Claude.** Conteúdo de `.claude/{agents,workflows,skills,
  rules,commands,hooks}/**` permanece byte-identical (FR6 + AC1 são os guards).
- **NG2 — Não criar campos Codex-only no workflow canônico sem ADR aprovada.** Qualquer
  campo runtime-specific exige ADR registrada antes de PLAN ser aprovado. Se um campo
  Codex-only emergir em PLAN sem ADR, PLAN é rejeitado.
- **NG3 — Não implementar hotfix direto sem SPEC/PLAN/TASKS aprovados.** A release segue
  o pipeline 8-fase normal. Não há shortcut "small fix" mesmo para drifts evidentes.
  Drifts encontrados durante implementação que não cabem no escopo são empurrados para
  `backlog/candidates.md`.

Itens adicionais (deferidos para releases futuras, registrados aqui para backlog-return
em CLOSURE):

- **NG4 — Não reescrever texto canônico de `project-manager` / `project-auditor`.** O
  texto que referencia Agent tool permanece intacto; ADR-2 cuida da transform.
- **NG5 — Não estender `WorkflowDefinition` para campos Codex-only.** Workflow neutro.
- **NG6 — OpenCode parity** continua fora — release sucessora se justificado.

---

## 6. Boundaries — what gets written, what is preserved

| Surface | Action in this release |
|---|---|
| `dadaia_workspace/public/agents/**` | READ-ONLY (canonical persona text preserved verbatim) |
| `dadaia_workspace/public/workflows/**` | READ-ONLY (`WorkflowDefinition` neutro inalterado) |
| `dadaia_workspace/public/skills/**` | READ-ONLY (re-projetado para `.agents/skills`) |
| `dadaia_workspace/public/rules/**` | READ-ONLY (classificação executável vs comportamental é metadata, não edição) |
| `dadaia_workspace/infrastructure/public_assets.py` | EDIT (novo `_install_codex_agents`, fortalece `_install_codex_workflows`, hardens `doctor()` checks) |
| `dadaia_workspace/infrastructure/runtime_transforms/codex.py` | NEW (ADR-2 transform) |
| `dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py` | NEW (ADR-5 mapping) |
| `dadaia_workspace/features/agents/dispatcher/CodexAgentDispatcher` | EDIT (hardening) |
| `dadaia_workspace/features/agents/dispatcher/ClaudeAgentDispatcher` | READ-ONLY (FR6 guard) |
| `.codex/agents/**` | NEW (20 TOML files) |
| `.codex/config.toml` | EDIT (gain 20 `[agents.<name>]` registrations) |
| `.codex/workflows/**` | EDIT (gain `audit-cycle`, `code-review-fan-out` — final list per ADR-4) |
| `.codex/rules/**` | EDIT (only executable rules; comportamental projeta para agent body) |
| `.claude/**` | READ-ONLY (NG1 + AC1) |
| `specs/memory/**` | READ-ONLY exceto CLOSURE (3 atoms updated em CLOSURE — AC11) |
| `specs/constitution.md` | NEVER (stack-neutral; nenhuma constitutional change) |

---

## 7. Dependencies and Risks

**Dependencies:**

- `agents-r3-v1` está CLOSED + ARCHIVED (operator confirmou em P0; `_archive/releases/
  agents-r3-v1/` existe; `dadaia specs doctor` baseline green).
- `agents-r2-v1` path-scope gate (`sdd-spec-gate.sh` step 6) está vigente — `ai-engineer`
  herda enforcement automático sobre `public/{skills,rules,workflows,commands,agents,hooks}/**`.
- Branch `release/codex-agent-orchestration-parity-v1` já foi cortado de `main` no
  tip `bd40e83` (operator confirmou).

**Risks + mitigations:**

| Risk | Mitigation |
|---|---|
| Edits a `.claude/**` durante implementação | FR6 + AC1 golden suite roda em cada commit que toque `infrastructure/public_assets.py` |
| `developer_instructions` fica truncado ou perde conteúdo do persona body | ADR-2 transform + golden tests por agente (20 fixtures) |
| Mapping Claude→Codex usa identifier inválido | AC2 parseability + AC3 zero-leak grep + AC9 doctor false-parity refusal |
| Workflow runtime boundary (ADR-4) muda escopo durante PLAN | ADR é gating de PLAN approval; PLAN não pode flippar pra Aprovado sem ADR-4 aprovada |
| Drift entre `.codex/agents/`, `config.toml`, e canonical agent list | FR10 doctor checks são parte do AC, não opcionais |
| Backlog candidato `agent-topology-guard-i6-skill-link-validation-v1` ainda aberto | Não é dependência hard — I6 é guardrail de skills, não de Codex parity; pode rodar em release paralela |

---

## 8. Open Questions (DISCOVERY phase — must be resolved before SPEC flips to Aprovado)

These are the grill-me topics. Each MUST have a recorded answer (operator or via
inspection) before SPEC moves to `**Status:** Aprovado`.

- **OQ1 — ADR storage location.** ADRs (FR1–FR6) live in `dadaia_workspace/public/docs/
  adrs/` (workspace-canonical, projected to consumers) or `specs/releases/<id>/adrs/`
  (release-local, archived with the release)? Trade-off: canonical → discoverable
  long-term; release-local → atomicity preserved per release.
- **OQ2 — Codex model identifiers.** Quais são os identifiers Codex válidos hoje (Codex
  CLI version pinned in `tech-stack.html`) para mapear `claude-opus-4-7` e
  `claude-sonnet-4-6`? Inspecionar `.codex/config.toml` atual ou Codex docs.
- **OQ3 — Workflow runtime boundary** (ADR-4). Render-at-install (estático) ou
  render-at-dispatch (dinâmico via `WorkflowDefinition`)? Decisão arquitetural com
  impacto em PLAN.
- **OQ4 — Rules classification authority.** Quem classifica cada arquivo em
  `public/rules/` como comportamental vs executável: `ai-engineer` (owner do surface),
  `product-engineer` (curator do delta), ou critério mecânico (e.g. presença de
  diretivas executáveis)?
- **OQ5 — Capability matrix granularity.** ADR-3 lista capabilities como
  `{sequential, parallel, fan-out, audit-loop, unsupported}` — esta lista está
  completa para os 2 dispatchers, ou faltam capabilities (e.g. `escalation`,
  `delegation-chain`)?
- **OQ6 — `.codex/hooks.json` parity.** Hooks atual em `.codex/hooks.json` mirror `.claude/`
  ou tem divergência? Se diverge, é proposital (capability gap) ou drift?
- **OQ7 — Commands surface.** `.claude/commands/` está populado por `agents-r3-v1`?
  Se sim, `.codex/commands/` precisa parity nesta release ou fica deferido?
- **OQ8 — Backlog dependency `agent-topology-guard-i6-skill-link-validation-v1`.** Esta
  release deve esperar I6 land (skill-link validation) antes de doctor hardening, ou
  doctor hardening aqui já é suficiente?
- **OQ9 — `data/AGENTS.md` mention of Codex parity.** Após esta release, o lib's source
  `data/AGENTS.md` (≤ 280-line invariant) deve ganhar uma seção mencionando Codex
  parity guards, ou parity é detalhe de infrastructure invisível para consumer repos?
- **OQ10 — Golden snapshot baseline.** Quando o pre-release `.claude/**` hash baseline
  é capturado: no P0 commit, no SPEC approval, ou no início do P3 (implementation)?
  Impacto: define o "antes" do FR6 / AC1.

---

**Status:** Draft
