# Spec: Release — agent-comms-v1

> **Status:** Aprovado
> **Release ID:** agent-comms-v1
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Source candidate:** `specs/backlog/candidates.md` L22 (§ Candidatas ativas)
> **Pipeline (D4):** PE Discovery → architect impact → SE rec → PE Synthesis → SE impl
> **Discovery inputs:**
> - PE Discovery: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T231301Z-agent-comms-discovery.html`
> - Architect Impact: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T232055Z-agent-comms-impact.html`
> - SE Recommendation: `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-16T232905Z-agent-comms-implementation.html`

---

## Objetivo

Materializar o contrato `handoff-schema-v1` que hoje é referenciado por 10 agentes em
`dadaia_workspace/public/agents/*.md` (21 ocorrências canônicas + 61 projetadas, total 82
ocorrências) mas que **nunca existiu em disco** (Discovery F1):
`find dadaia-workspace/ -name "*.schema.json"` retorna vazio. Esta release transforma a
referência simbólica em referência operacional via 5 entregas atômicas:

1. **Schema canônico** `handoff-v1.schema.json` em `dadaia_workspace/public/schemas/` (novo
   tipo de asset), projetado staging-only para `.dadaia/agentic/schemas/`.
2. **CLI top-level** `dadaia reports validate` (irmão de `dadaia orchestrate`), validador
   stdlib-only sem novas dependências de runtime.
3. **Skill standalone** `dadaia-handoff-emitter` que instrui os agentes a emitir o sidecar
   `<stem>.handoff.json` adjacente a cada report HTML.
4. **3 agentes piloto** (product-engineer, software-architect, software-engineer) consumem a
   skill e passam a emitir handoff verificável; os outros 7 agentes migram em releases v2-v7.
5. **Migração-e-deleção de `z_bug_specs.md`** (raiz + `specs/z_bug_specs.md`) para
   `specs/backlog/candidates.md` (entries abertas) + `specs/_archive/legacy-bug-specs/`
   (histórico), com patches em 3 consumers (skill, command, template) e em
   `sdd-spec-gate.sh:117`. Fim da fonte-de-verdade dual.

Esta release também encerra dois drifts documentais antigos (constitution L106 e procedimento
de update da constitution) como FR6/FR7, integrando-os ao escopo via decisões pré-resolvidas
Q2/Q8.

---

## Status & Activation

**Status:** Aprovado (queued — activation pending closure of `dadaia-workspace-panel-v1`).

A release `dadaia-workspace-panel-v1` está em phase `TASKS` em `specs/releases/ACTIVE.md`
(Discovery F4 + Architect Q1). O invariante release-singleton (product-engineer agent
contract L407–423) proíbe duas releases ativas simultâneas. Portanto:

- SPEC + PLAN + TASKS de `agent-comms-v1` são aprovados nesta sessão.
- `ACTIVE.md` **não é modificado** — continua apontando para `dadaia-workspace-panel-v1`.
- Implementação (SE Impl, Phase 5 do D4) só inicia após `panel-v1` arquivar em
  `_archive/releases/`. O operador fará o flip de `ACTIVE.md` para `agent-comms-v1` no início
  daquela sessão.
- A release está enfileirada como sucessor documentado, não como standby informal.

---

## Contexto & Motivação

A auditoria de orquestração `2026-05-15-orchestration-audit.md` identificou um padrão
"build-on-stale-layer": `input_contract` foi declarado no fechamento de GAP-INPUT-001
(ver `specs/z_bug_specs.md` L126–131) prometendo contrato verificável, mas o referente
`handoff-schema-v1` aponta para vácuo. O Discovery do PE confirmou empiricamente: 44 arquivos
distribuídos referenciam o schema, zero existem. Esta release fecha essa dívida com **um
único contrato** que vive em `public/schemas/`, segue a cadeia de projeção existente
(`public/` → `.dadaia/agentic/`), e é validável via CLI determinística — sem adicionar
nenhuma dependência ao tech-stack da constitution L17–28.

A Architectural Impact Analysis (Phase 2) ratificou as escolhas do Discovery e adicionou 12
decisões arquiteturais (A1–A12) que fecham todas as decisões delegadas. O ponto-chave é que
`reports_validation` é uma feature peer de `orchestration`, não submódulo: o `ValidatorPort`
Protocol em `core/` permite que `OrchestrationService` em v2 receba o validador via
composition root sem violar constitution L67 ("Nenhuma feature importa outra feature").

A SE Recommendation (Phase 3) operacionalizou A1–A12 em uma matriz de 13 tasks distribuídas
em 5 waves, com 9 NEW + 10 MODIFIED files identificados por path absoluto, tier-1/2/3 TDD
strategy, exit-code matrix da CLI, e plano de migração de `z_bug_specs.md` com patches-before-deletes
estrito (mitigação de AR1 risco HIGH).

A pré-resolução das questões Q1–Q8 escaladas pelo arquiteto e PE Discovery (decisão do
operador para evitar segunda rodada de grill-me) define: `agent-comms-v1` queued/Aprovado
sem flip de `ACTIVE.md` (Q1); constitution L106 patch incluído via FR6 (Q2); ownership dual
de `public/agents/*.md` documentado em ADR-006 (Q3); validator stdlib-only (Q4); schema
shape per research §4.1 + A7 (Q5); sem workflow seed para D4 (Q6); regex de path loose `^[a-zA-Z0-9_./{}-]+$` (Q7);
procedimento de update da constitution documentado em ADR-007 (Q8).

A migração de `z_bug_specs.md` é tratada como operação documental sequenciada (A11), não como
parte da feature técnica. O 4º consumer descoberto pelo PE (F8: `sdd-spec-gate.sh:117`)
entra no mesmo task atômico que move os arquivos para `_archive/`.

---

## Escopo

### In-scope (D1)

- Criação de `dadaia_workspace/public/schemas/handoff-v1.schema.json` (Draft 2020-12).
- Patch de `_COPY_DIRS` em `dadaia_workspace/infrastructure/public_assets.py:35` para adicionar `"schemas"`.
- Novo pacote `dadaia_workspace/features/reports_validation/` (`__init__.py` + `service.py`).
- Novo Protocol `dadaia_workspace/core/protocols/handoff_validator.py` + dataclass `dadaia_workspace/core/models/handoff.py` + exceptions em `core/exceptions.py`.
- Adapter stdlib-only `dadaia_workspace/infrastructure/stdlib_handoff_validator.py`.
- Composition wiring em `dadaia_workspace/container.py` (nova `build_reports_validation_service`).
- Novo Typer app top-level `dadaia_workspace/cli/commands/reports.py` registrado em `cli/main.py`.
- Skill standalone `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md`.
- Patches em frontmatter + body de 3 agentes piloto: `product-engineer.md`, `software-architect.md`, `software-engineer.md`.
- Migração de `z_bug_specs.md` (raiz + `specs/`) para `specs/_archive/legacy-bug-specs/` + bullets em `specs/backlog/candidates.md`.
- Patches em 4 consumers de `z_bug_specs.md`: spec-reviewer skill, refine-specs command, repo-AGENTS.md template, `sdd-spec-gate.sh:117`.
- Patch em `specs/constitution.md` L106 enumerando os 10 tipos de asset (rules, skills, commands, scripts, agents, templates, workflows, plugins, data, schemas).
- TDD: 28 testes (10 unit validator, 8 unit service, 6 unit models, 10 integration CLI, 4 E2E pipeline).

### Out-of-scope (deferido a backlog)

- `dadaia reports next` (v2): comando para descobrir próximo handoff esperado dado o estado atual.
- `dadaia reports emit` / MCP integration (v3): emissão programática via servidor MCP em vez de skill markdown.
- Evaluator de qualidade de findings (v4): validação semântica do conteúdo, não apenas estrutura.
- Migração dos 7 agentes não-piloto (qa-engineer, devops-engineer, backend-engineer, frontend-engineer, game-developer, game-designer, game-tester) — waves 2–7 separadas.
- CI gate `dadaia reports validate --strict` (NFR4): aguarda 100% adoption.
- Workflow seed "spec-discovery-chain" para o padrão D4 (Q6): D4 é one-time, não recorrente.
- Hash-mismatch enforcement em strict mode: warning-only em v1, gate em v2.

---

## Functional Requirements

### FR1 — Schema JSON canônico + asset type novo

**O que:** criar `dadaia_workspace/public/schemas/handoff-v1.schema.json` (JSON Schema Draft
2020-12) com `$schema = "https://json-schema.org/draft/2020-12/schema"`. Campos obrigatórios
(per Q5 = research §4.1 + A7): `schema_version` (literal `"handoff-v1"`), `agent` (string),
`context` (string), `produced_at` (ISO 8601 via `format: date-time` + regex), `artifact`
(objeto com `type`, `path`, `content_hash`). Campos opcionais: `release_id`, `findings[]`
(severity enum `CRITICAL|HIGH|MEDIUM|LOW|INFO`), `decisions_required[]`, `next_handoff`.
`artifact.path` usa pattern loose `^[a-zA-Z0-9_./{}-]+$` (Q7 — suporta templates com `{context}`).
`additionalProperties: false` em todos os objetos.

**Projeção (A1, A6):** patch single-line `_COPY_DIRS` em `infrastructure/public_assets.py:35` adicionando
`"schemas"`. Schema fica disponível em `.dadaia/agentic/schemas/handoff-v1.schema.json` após
`dadaia public stage`. **NÃO** projetado para `.claude/schemas/`, `.codex/schemas/`,
`.opencode/schemas/` (consumido só pela CLI, não pelo runtime do agente — economiza 3
duplicações).

### FR2 — CLI `dadaia reports validate`

**O que:** novo Typer app top-level (A3) montado em `cli/main.py` como
`app.add_typer(reports.app, name="reports")`. Subcomando `validate` com signature:

```
dadaia reports validate [PATHS...] [--all] [--release <id>] [--strict|--no-strict] [--json]
```

Exit codes: `0` = todos válidos (ou violations em non-strict); `1` = violation em strict;
`2` = file not found; `3` = bad invocation (sem PATHS nem `--all`, ou workspace não
inicializado). Default `--strict=false` (NFR2). Output humano-legível por padrão; JSON
estruturado via `--json`. Cobre por dentro: ler JSON, validar via `ValidatorPort`,
opcionalmente recomputar `content_hash` e comparar.

### FR3 — Skill `dadaia-handoff-emitter`

**O que:** criar `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md` (A5). A
skill referencia o schema por path lógico `.dadaia/agentic/schemas/handoff-v1.schema.json`
(A10 — não duplica o schema dentro do markdown). Protocolo em 3 passos:
(1) `sha256sum` do report HTML; (2) montar dicionário com obrigatórios + opcionais aplicáveis;
(3) `Write` do arquivo `<stem>.handoff.json` adjacente. Skill projetada para
`.agents/skills/dadaia-handoff-emitter/` + projeções runtime-specific via mecanismo padrão.

### FR4 — 3 agentes piloto emitem handoff.json

**O que (A12):** três agentes recebem patches mínimos:

- **Frontmatter (YAML, SE-owned per Q3):** adicionar `dadaia-handoff-emitter` à lista `skills:`.
- **Markdown body (PE-owned per Q3):** adicionar um parágrafo na seção apropriada
  ("Output rules" ou equivalente) instruindo: "Após finalizar qualquer report HTML em
  `.dadaia/reports/`, invocar a skill `dadaia-handoff-emitter` para emitir o sidecar
  `<stem>.handoff.json` no mesmo diretório."

Agentes-alvo: `dadaia_workspace/public/agents/product-engineer.md`,
`dadaia_workspace/public/agents/software-architect.md`,
`dadaia_workspace/public/agents/software-engineer.md`.

### FR5 — Migração e deleção de `z_bug_specs.md`

**O que:** operação documental sequenciada (A11) em **ordem estrita**:

1. Append em `specs/backlog/candidates.md`: bullet em `## Hotfixes pendentes` para
   BUG-003 (`dadaia import` não reescreve paths absolutos — pendente em
   `specs/z_bug_specs.md` L10-14); bullet em `## Candidatas ativas` para `cli-asset-granular`
   (G3 mantido baixa prio em raiz L23-25).
2. Patch dos 4 consumers em `dadaia_workspace/public/`:
   - `skills/dadaia-workspace-spec-reviewer/SKILL.md` (3 linhas: L3, L22, L63)
   - `commands/dadaia-workspace-refine-specs.md` (3 linhas: L2, L21, L28)
   - `templates/repo-AGENTS.md` (1 linha: L20)
   - `scripts/sdd-spec-gate.sh` (L117 — remover entry `*/z_bug_specs.md` do glob; F8 descoberto pelo PE)
3. `dadaia public stage && dadaia public install --target all --force` + `dadaia public doctor` verde.
4. `git mv specs/z_bug_specs.md specs/_archive/legacy-bug-specs/z_bug_specs-specs-2026-05-08.md`
   + `git mv z_bug_specs.md specs/_archive/legacy-bug-specs/z_bug_specs-root-2026-05-08.md`.
5. Verificação: `find . -name "z_bug_specs.md" -not -path "*/_archive/*"` vazio;
   `grep -rn "z_bug_specs" dadaia_workspace/public/ .claude/ .opencode/ .codex/ .agents/ .dadaia/agentic/` vazio.

**Invariante:** patches antes de deletes. Reversão da ordem cria janela em que
`refine-specs` lê arquivo inexistente.

### FR6 — Patch constitution L106 (close drift documental)

**O que (Q2):** editar `specs/constitution.md` L106 para enumerar os **10 tipos** de asset
hoje suportados em `dadaia_workspace/public/`:

> "Neste repositório, `dadaia_workspace/public/` é a única localização versionada para
> rules, skills, commands, scripts, agents, templates, workflows, plugins, data e schemas
> universais do produto."

Resolve drift pré-existente (Discovery F2 + Architect Q2): a lista original tinha 6 tipos
mas o diretório real contém 10. Requer explicit operator confirmation per
`public/agents/product-engineer.md` L451 — confirmação registrada via aprovação desta SPEC
(per ADR-007 abaixo).

---

## Non-Functional Requirements

### NFR1 — Backwards compatibility total

Reports HTML existentes em `.dadaia/reports/<context>/<agent>/*.html` permanecem válidos.
`OrchestrationService` continua passando `output_path` entre stages como string. A
introdução do sidecar é puramente aditiva.

### NFR2 — Janela de transição: `--strict=false` default em v1

`dadaia reports validate` default non-strict. Reports sem sidecar emitem warning, não erro.
Em v2 o default vira `true` e CI bloqueia. Evita big-bang: os 7 agentes não-piloto migram
em releases subsequentes sem bloquear este.

### NFR3 — Zero novas dependências de runtime

Validator é stdlib-only (Q4 + A4) usando `json`, `re`, `datetime.fromisoformat`. Whitelist
explícita de keywords suportados (`type`, `required`, `enum`, `pattern`, `properties`,
`items`, `additionalProperties`, `format`, `minimum`, `minItems`). Schema com keyword
fora do whitelist (`oneOf`, `allOf`, `$ref`) levanta `HandoffSchemaError` no init.
Constitution L17–28 (tech-stack) **não toca**.

### NFR4 — Sem CI gate em v1

`.github/workflows/ci.yml` **não** ganha job que rode `dadaia reports validate --strict`.
Adicionar gate em CI fica para v2 (depende de NFR2: todos os 10 agentes devem emitir handoff
confiavelmente, senão CI vermelho permanente).

### NFR5 — Token-overhead budget tipicamente <3%

Sidecar `.handoff.json` mínimo: ~500 bytes (apenas obrigatórios); típico: <2 KB; aviso
WARNING se >4 KB. Para report HTML médio de 50–70 KB, overhead ~3% no pior caso.

### NFR6 — Migração de `z_bug_specs.md` não quebra refine-specs

Ordem patches→propagate→delete é estrita. Em nenhum ponto intermediário o fluxo de
refine-specs deve apontar para arquivo inexistente. Doctor verde após cada step da migração
é precondição do próximo.

### NFR7 — Idempotência da projeção

`FileSystemPublicAssetManager` reconhece `schemas/` após patch A6. Rodar
`dadaia public install --target all --force` duas vezes consecutivas produz diff zero;
`dadaia public doctor` retorna `[ok]` em todas as projeções (incluindo
`stage:schemas/handoff-v1.schema.json`).

### NFR8 — Cobertura ≥80% na camada feature

Constitution L131 exige ≥80% de cobertura em `features/`. Tier-1 unit + Tier-2 integration
+ Tier-3 E2E somam 28 testes; cobertura medida em `tests/coverage.xml` no CI já existente.

---

## Decisões (D + A + ADR series)

Decisões consolidam três camadas: operador (D), arquiteto (A), e pré-resolvidas pelo operador
nesta synthesis (Q → ADR quando estrutural).

### Operator decisions (D)

| ID | Tema | Decisão |
|----|------|---------|
| D1 | Escopo v1 | schema + validate CLI + emitter skill + 3 pilotos + z_bug migration. v2/v3/v4 deferidos a backlog. |
| D2 | z_bug | Migrado e deletado **in-release** (não diferir). |
| D3 | Release id | `agent-comms-v1` (slug, não SemVer — release criada antes do cutoff 2026-06-01 do `sdd-hotfix-track-v1`). |
| D4 | Pipeline order | PE Discovery → architect impact → SE rec → PE Synthesis → SE impl (one-time desta release). |

### Architect decisions (A)

| ID | Tema | Decisão |
|----|------|---------|
| A1 | Schema location | `public/schemas/handoff-v1.schema.json`; projeção staging-only para `.dadaia/agentic/schemas/`. Não duplica em runtime trees. |
| A2 | Feature module | Novo pacote `features/reports_validation/`. **Não** estender `orchestration/`. **Não** chamar `handoff/`. |
| A3 | CLI namespace | Novo top-level Typer app `dadaia reports` (irmão de `orchestrate`). Não submontar sob `orchestrate`. |
| A4 | Validator | stdlib-only (`json`, `re`, `datetime`). Whitelist explícita de keywords. ~85 LoC. |
| A5 | Skill | Standalone `public/skills/dadaia-handoff-emitter/SKILL.md`. |
| A6 | `_COPY_DIRS` patch | Single-line em `infrastructure/public_assets.py:35` adicionando `"schemas"`. |
| A7 | Model | `HandoffDocument` frozen dataclass em `core/models/handoff.py` + sub-models `ArtifactRef`, `Finding`, `NextHandoff`. |
| A8 | Protocol | `ValidatorPort` em `core/protocols/handoff_validator.py` + 2 exceptions em `core/exceptions.py`. |
| A9 | Composition | `build_reports_validation_service()` em `container.py`. CLI não instancia `StdlibHandoffValidator` direto. |
| A10 | Skill content | Skill referencia schema por path; não duplica conteúdo. Single source of truth. |
| A11 | z_bug migration | Operacional, orquestrada por TASKS. **Não** parte da feature `reports_validation`. |
| A12 | Pilotos | product-engineer + software-architect + software-engineer. |

### Pre-resolved questions (Q → resolved during synthesis briefing)

| ID | Tema | Resolução |
|----|------|-----------|
| Q1 | ACTIVE.md conflict | SPEC+PLAN+TASKS aprovados; **ACTIVE.md não modificado** (continua apontando para panel-v1). Release queued — implementação inicia quando panel-v1 arquivar. |
| Q2 | Constitution L106 drift | Incluído via FR6. Patch L106 enumera 10 asset types. |
| Q3 | Ownership `public/agents/*.md` | Dual ownership: SE owns frontmatter YAML (contrato), PE owns markdown body (instruções). Registrado em **ADR-006**. |
| Q4 | Validator impl | stdlib-only (alinhado com A4). |
| Q5 | Schema shape | Research §4.1 + A7 mirror. Required: agent, context, schema_version, produced_at, artifact{type,path,content_hash}. Optional: release_id, findings[], decisions_required[], next_handoff. |
| Q6 | Workflow seed | Sem novo workflow para D4 em v1. D4 é one-time. "spec-discovery-chain" virou candidato backlog v2. |
| Q7 | `artifact.path` regex | Loose `^[a-zA-Z0-9_./{}-]+$` (suporta `{context}`, `{run_ts}`). |
| Q8 | Constitution update procedure | Mudanças constitucionais em uma release requerem FR explícito + verification triple no aceite. Registrado em **ADR-007**. |

### ADRs

**ADR-006 — Ownership dual de `public/agents/*.md`.**
*Decisão:* arquivos em `dadaia_workspace/public/agents/*.md` têm dois owners: SE owns o
YAML frontmatter (campos `input_contract`, `produces_outputs`, `skills`, `model`, `tools` —
contrato técnico verificável), PE owns o corpo markdown abaixo do frontmatter (instruções
comportamentais, system prompt, persona). Ambos podem editar respeitando a fronteira;
edição cross-domain requer coordenação. *Racional:* o frontmatter é máquina-legível e
afeta runtime parsing; o body afeta semântica do agente. *Consequência:* este FR4 toca os
dois domínios (frontmatter + body) — PE e SE coordenam via TASKS.md.

**ADR-007 — Procedimento de update da constitution em release.**
*Decisão:* alterações em `specs/constitution.md` durante uma release requerem (a) FR
explícito na SPEC referenciando o número da linha alvo e o novo conteúdo proposto; (b)
verification triple no critério de aceite (description + comando + expected output); (c)
operator confirmation registrada via aprovação da SPEC com `**Status:** Aprovado` (o ato
de aprovar a SPEC é o consent para o patch L106 listado em FR6); (d) doctor pós-patch
verde. *Racional:* a constitution é lei do produto; mudanças sem fluxo formalizado criam
drift como Discovery F2 evidenciou. *Consequência:* FR6 desta release segue o procedimento
ADR-007 — é o primeiro caso de uso explícito.

---

## Critérios de aceite (verification triples)

| FR | Verificação | Comando | Esperado |
|----|-------------|---------|----------|
| FR1 | Schema é JSON Draft 2020-12 válido | `jq '."$schema"' dadaia_workspace/public/schemas/handoff-v1.schema.json` | `"https://json-schema.org/draft/2020-12/schema"` |
| FR1 | Schema projetado para staging | `ls .dadaia/agentic/schemas/handoff-v1.schema.json` | arquivo existe |
| FR1 | Schema **não** projetado para `.claude/` | `ls .claude/schemas/ 2>&1` | `No such file or directory` |
| FR2 | CLI registrada | `dadaia --help \| grep reports` | `reports  Inspect and validate agent handoff reports.` |
| FR2 | Validate aceita handoff válido | `dadaia reports validate <fixture-valid.handoff.json>` | exit 0, "Summary: 1 valid" |
| FR2 | Validate rejeita em strict | `dadaia reports validate <fixture-invalid.handoff.json> --strict` | exit 1, mensagem com campo faltante |
| FR3 | Skill projetada | `ls .agents/skills/dadaia-handoff-emitter/SKILL.md` | arquivo existe |
| FR3 | Doctor verde após install | `dadaia public doctor \| grep handoff-emitter` | `[ok]` em todas linhas |
| FR4 | 3 pilotos têm skill no frontmatter | `grep -l "dadaia-handoff-emitter" dadaia_workspace/public/agents/{product-engineer,software-architect,software-engineer}.md` | 3 arquivos |
| FR5 | z_bug ausente do live tree | `find . -name "z_bug_specs.md" -not -path "*/_archive/*" -not -path "*/.git/*"` | vazio |
| FR5 | Nenhuma referência stale | `grep -rn "z_bug_specs" dadaia_workspace/public/ .claude/ .opencode/ .codex/ .agents/ .dadaia/agentic/` | vazio |
| FR5 | `sdd-spec-gate.sh:117` sem ref | `grep "z_bug_specs" dadaia_workspace/public/scripts/sdd-spec-gate.sh` | vazio |
| FR6 | Constitution L106 atualizado | `grep -c "rules, skills, commands, scripts, agents, templates, workflows, plugins, data" specs/constitution.md` | `≥1` |
| NFR3 | Validator não usa external dep | `grep -E "^import (jsonschema\|pydantic)" dadaia_workspace/infrastructure/stdlib_handoff_validator.py` | vazio |
| NFR7 | Install idempotente | `dadaia public install --target all --force && git status --short` (1ª vez); rodar 2ª vez | 2ª execução: zero changes |
| NFR8 | Coverage ≥80% no feature | `pytest --cov=dadaia_workspace.features.reports_validation --cov-fail-under=80` | exit 0 |
| Global | Doctor verde | `dadaia specs doctor` | 0 errors, 0 warnings |
| Global | ACTIVE.md inalterado | `cat specs/releases/ACTIVE.md` | `release: dadaia-workspace-panel-v1` `phase: TASKS` |

---

## Backlog gerado por esta release

A serem adicionados em `specs/backlog/candidates.md` na CLOSURE (não nesta sessão):

- `reports-next-cli` — `dadaia reports next` (v2): descobre o próximo handoff esperado dado o estado atual do workspace (owner: software-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope).
- `reports-mcp-server` — MCP integration (v3): emissão programática de handoff via servidor MCP ao invés de skill markdown (owner: software-architect, contexto: SPEC `agent-comms-v1` § Out-of-scope).
- `reports-evaluator` — Evaluator semântico (v4): valida qualidade dos findings, não apenas estrutura JSON (owner: qa-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope).
- `agent-comms-wave-2` — Migrar `qa-engineer` para piloto (próxima onda) (owner: product-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope).
- `agent-comms-wave-3-7` — Migrar `devops-engineer`, `backend-engineer`, `frontend-engineer`, e 3 `game-*` (owner: product-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope).
- `reports-ci-gate` — Adicionar job em `.github/workflows/ci.yml` rodando `dadaia reports validate --all --strict` após 100% adoption (owner: devops-engineer, contexto: SPEC `agent-comms-v1` NFR4).
- `reports-hash-mismatch-enforcement` — Promover hash-mismatch de warning para erro em strict (v2) (owner: software-engineer, contexto: SPEC `agent-comms-v1` § Out-of-scope).
- `spec-discovery-chain-workflow` — Workflow seed para o padrão D4 (PE→architect→SE→PE→SE), se virar recorrente (owner: product-engineer, contexto: SPEC `agent-comms-v1` Q6).
- `reports-handoff-schema-v2` — Evolução do schema para suportar `oneOf` e `$ref` (requer upgrade do validator) (owner: software-architect, contexto: SPEC `agent-comms-v1` AR5).

---

## Riscos (release-level)

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|-------|---------------|---------|-----------|
| R1 | ACTIVE.md conflict não resolvido pelo operador | Baixa (Q1 pré-resolvida) | Médio | SPEC declara queued/Aprovado explicitamente; operador faz flip quando panel-v1 arquivar |
| R2 | Delete-before-patch quebra `refine-specs` | Média (humano facilmente erra ordem) | Alto | TASKS força T-AC-11 (patches+doctor green) como precondição estrita de T-AC-12 (git mv); SE Recommendation Section 9 numerada |
| R3 | StdlibHandoffValidator silenciosamente ignora keyword unsupported em v1.x | Média (futuro) | Alto | Whitelist explícita no `__init__`; raise `HandoffSchemaError` em qualquer key fora; teste `test_unsupported_schema_keyword_raises_handoff_schema_error` (AR5) |
| R4 | YAML frontmatter dos pilotos corrompido | Média | Médio | `dadaia public stage` recarrega frontmatter; teste de integração `test_schema_staged_after_public_install` cobre |
| R5 | Drift se `_COPY_DIRS` patch é mergeado depois do schema | Média | Médio | Wave 0 inclui T-AC-04 (`_COPY_DIRS`) como dep de T-AC-05 (validator usa schema staged); teste E2E `test_schema_projection_idempotent` cobre |
| R6 | Transition window: agentes não-piloto sem handoff | Média | Baixo | NFR2 default `--strict=false`; NFR4 sem CI gate; CLI emite warning, não erro |
| R7 | Pilotos regridem (remover skill sem CI gate) | Baixa em v1 | Baixo | NFR4 explicitamente difere; aceitar até v2 |
| R8 | Constitution L106 patch interpretado como mudança de produto | Baixa | Baixo | ADR-007 formaliza procedimento; FR6 é meta-edit (close drift), não mudança semântica |
| R9 | `container.py` crescendo (God Object) | Baixa | Baixo | Aceitar em v1 (AR8); reavaliar quando builders > 10 |
| R10 | Hash-mismatch em handoff válido (operador renomeia HTML) | Baixa | Baixo | Warning não bloqueia v1; v2 trata em strict (backlog `reports-hash-mismatch-enforcement`) |

---

## Out of scope (reafirmado)

- Flip de `ACTIVE.md` para `agent-comms-v1` (acontece quando panel-v1 arquivar — sessão futura).
- Migração dos 7 agentes não-piloto (waves 2–7 separadas).
- CI gate (NFR4, v2).
- Workflow seed `spec-discovery-chain` (Q6).
- Schema v1.x evolução para `oneOf`/`$ref` (backlog).

---

## Referências

- Discovery PE: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-16T231301Z-agent-comms-discovery.html`
- Architect Impact: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T232055Z-agent-comms-impact.html`
- SE Recommendation: `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-16T232905Z-agent-comms-implementation.html`
- Auditoria precedente: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-15-orchestration-audit.md`
- Constitution: `specs/constitution.md` (L106 alvo de FR6, L17–28 referenciada por NFR3, L131 referenciada por NFR8)
- Backlog: `specs/backlog/candidates.md` (L22 origem; entries promovidas em CLOSURE)
- ACTIVE.md: `specs/releases/ACTIVE.md` (Q1 — não modificado)
- Release singleton rule: `dadaia_workspace/public/agents/product-engineer.md` L407–423
- z_bug source files (a arquivar): `z_bug_specs.md` (raiz), `specs/z_bug_specs.md`
- z_bug consumers (a patchar): `dadaia_workspace/public/skills/dadaia-workspace-spec-reviewer/SKILL.md`, `dadaia_workspace/public/commands/dadaia-workspace-refine-specs.md`, `dadaia_workspace/public/templates/repo-AGENTS.md`, `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
