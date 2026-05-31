# Closure: Release — opencode-runtime-parity-hardening-v1

> **Status:** Aprovado
> **Release ID:** opencode-runtime-parity-hardening-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-29

## Summary

Esta release fecha três lacunas de completude do produto. (1) **OpenCode runtime parity:**
a projeção OpenCode agora remove o campo `color:` (que quebrava o parse de 3 agentes em
OpenCode 1.14.x), emite um bloco `permission:` por-agente derivado das tools declaradas, ganha
um plugin SDD gate (`sdd-gate.ts`) que espelha o PreToolUse hook do Claude Code, e tem o
`ctx-inject.ts` corrigido para a assinatura atual do hook `chat.message`. (2) **Orquestração via
reports:** o CLI ganhou `dadaia reports next`, que descobre o próximo agente esperado lendo a
sequência de owners do PLAN.md da release ativa e cruzando com os sidecars `.handoff.json` já
emitidos. (3) **Adoção total do agent-comms:** os 6 agentes restantes (`qa-engineer`,
`devops-engineer`, `backend-engineer`, `game-designer`, `game-developer`, `game-tester`) passaram
a declarar e invocar a skill `dadaia-handoff-emitter` — fechando a adoção do contrato de handoff
nos 21 agentes da topologia.

A investigação bloqueante (T-OC-01) foi resolvida contra os type defs oficiais
`@opencode-ai/plugin` e a documentação OpenCode 1.14.x: `permission:` por-agente É suportado;
o evento de intercepção de tool use é `tool.execute.before`; e `chat.message` existe mas teve
sua assinatura alterada para `(input, output)`.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-OC-01 | Investigação OpenCode 1.14.x (permission per-agent + hook event) | (working tree — commit pendente do operador) |
| T-OC-02 | Strip de `color:` na projeção OpenCode | (working tree) |
| T-OC-03 | Bloco `permission:` por-agente na projeção OpenCode | (working tree) |
| T-OC-04 | Plugin `sdd-gate.ts` (SDD gate OpenCode) | (working tree) |
| T-OC-05 | Correção de `ctx-inject.ts` (assinatura `chat.message`) | (working tree) |
| T-OC-06 | Testes de regressão cross-runtime | (working tree) |
| T-RN-01 | Feature layer `reports_next` | (working tree) |
| T-RN-02 | CLI `dadaia reports next` | (working tree) |
| T-RN-03 | Testes unitários + integração `reports next` | (working tree) |
| T-AC-01..06 | `dadaia-handoff-emitter` nos 6 agentes | (working tree) |
| T-AC-07 | Propagação `stage && install --force --target all` | (working tree) |
| T-AC-08 | Testes de regressão dos 6 agentes migrados | (working tree) |
| T-INT-01 | `dadaia public doctor` verde para os 21 agentes | (working tree) |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Suíte completa verde + cobertura ≥ 80% (NFR-1, NFR-5) | `poetry run pytest -q` | `1959 passed, 1 skipped, 1 xpassed in 633.56s` · `Total coverage: 89.57%` |
| Lint limpo (constituição) | `ruff check dadaia_workspace/ tests/` | `All checks passed!` |
| Formatação limpa | `ruff format --check dadaia_workspace/ tests/` | `309 files already formatted` |
| Type checking estrito | `mypy --strict dadaia_workspace/` | `Success: no issues found in 145 source files` |
| Doctor sem drift/missing, 21 agentes [ok] (AC-AC-2, AC-OC-5, NFR-2) | `dadaia public doctor` | `exit=0` · `215 [ok]`, `0 [drift]`, `0 [missing]`; todas as entradas `:agents/` `[ok]` |
| AC-OC-1: nenhum agente OpenCode com `color:` | `pytest …test_no_color_in_any_opencode_agent` | `offenders == []` (12 testes e2e verdes) |
| AC-OC-1 parity: `color:` preservado em Claude | `pytest …test_color_preserved_in_claude_for_color_agents` | game-designer/developer/tester com `color:` em `.claude/agents/` |
| AC-OC-2: `permission:` por-agente na projeção OpenCode | `pytest …TestPermissionProjection` | `edit/bash/webfetch/task` allow/deny conforme tools |
| AC-OC-3: `sdd-gate.ts` via `tool.execute.before` | `pytest …test_sdd_gate_plugin_projected` | plugin projetado, contém `tool.execute.before` + `sdd-spec-gate.sh` |
| AC-OC-4: `ctx-inject.ts` migrado | `pytest …test_ctx_inject_uses_migrated_signature` | contém `chat.message` + `output.parts` |
| AC-RN-1/2: `reports next` + `--json` | `pytest tests/integration/test_cli_reports_next.py` | 5 testes verdes; JSON com `next_agent/release_id/completed_agents/pending_agents` |
| AC-AC-1: `dadaia-handoff-emitter` nos 6 agentes (source + projeções) | `pytest …TestHandoffEmitterMigration` | 2 ocorrências por agente source; presente em projeções claude+opencode |

## Drifts

### install-stale-projection-on-transform-change

**Description:** Após alterar a lógica de transform da projeção OpenCode (T-OC-02 color strip +
T-OC-03 permission), `dadaia public install --target all` (sem `--force`) deixou as projeções de
agentes cujo *source* não mudou em estado stale — `dadaia public doctor` reportou 28 `[drift]`,
incluindo os 21 agentes OpenCode (a lógica de transform mudou, mas o install pula re-projeção
quando o hash do source é idêntico).

**Resolution:** Usado `dadaia public install --force --target all` — o reparo documentado de
drift para mudança de lógica de transform (guardrail §3). Drift zerado (`0 [drift]`, `0 [missing]`).
Trade-off: `--force` regenera todas as projeções; aceitável e necessário quando a lógica de
projeção (não só o source) muda. Sem impacto em `core/`/`features/`.

**Memory updates:** `specs/memory/architecture.html` (descrição do transform OpenCode);
`specs/memory/product/multi-platform-parity.html` (paridade OpenCode atual).

### telemetry-fake-stale-method (pre-existing, fora de escopo, corrigido)

**Description:** A baseline de testes tinha 1 falha pré-existente não relacionada à release:
`tests/unit/features/telemetry/test_service.py::test_refresh_runs_all_readers`. O fake
`_FakeCodexReader` declarava `read_sessions`, mas o serviço de produção chama `read_codex_db`
(o método real). O erro era engolido pelo try/except do serviço, deixando `call_count == 0`.

**Resolution:** Renomeado o método do fake para `read_codex_db`, alinhando com o protocolo de
produção. Corrigido para satisfazer NFR-1 (suíte 100% verde). Bug latente de teste, sem impacto
em produção.

**Memory updates:** nenhum (correção de fixture de teste).

## Memory updates

- `specs/memory/product/index.html` — entrada `agent-comms` atualizada (adoção dos 21 agentes);
  entrada de CLI de reports reflete `validate`/`lint`/`next`.
- `specs/memory/product/agent-comms.html` — estado atual: 21 agentes emitem sidecar; CLI surface
  inclui `dadaia reports next`.
- `specs/memory/product/multi-platform-parity.html` — paridade OpenCode atual: strip de `color:`,
  bloco `permission:` por-agente, plugin `sdd-gate.ts`, `ctx-inject.ts` em `chat.message`.
- `specs/memory/architecture.html` — transform OpenCode (`_prepare_agent_for_opencode` com
  color/permission), plugin `sdd-gate.ts`, feature `reports_next`.
- `specs/memory/tech-stack.html` — sem mudança: release não alterou a toolchain.

## Backlog returns

- `backlog/candidates.md` ← `reports-ci-gate` permanece válido (agora com 21/21 adoção, o
  pré-requisito de "100% adoção" está satisfeito — pronto para promover).
- `backlog/ideas.md` ← avaliar `permission:` `ask` (em vez de `deny`) para categorias sensíveis,
  permitindo confirmação interativa no OpenCode em vez de bloqueio puro.

## Archive decision

**MOVE** — o diretório da release será movido para
`specs/_archive/releases/opencode-runtime-parity-hardening-v1/` via `git mv` e `ACTIVE.md`
apontará para `release: none`. **Pendente de autorização do operador** (o working tree contém
mudanças não-relacionadas e não-commitadas de outros trabalhos; o operador deve separar o commit
da release das mudanças pré-existentes antes do archive).
