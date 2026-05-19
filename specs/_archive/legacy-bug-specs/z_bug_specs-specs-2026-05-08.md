# z_bug_specs.md — Gaps e Questões Abertas

> Registro de inconsistências, lacunas e decisões pendentes encontradas em rodadas de revisão.
> Resolva cada item antes de marcar os artefatos afetados como `Aprovado`.

---

## Bugs Abertos

### BUG-003 — `.claude/settings.json` contém paths VPS hardcoded (`/home/ubuntu/...`) 🟡 FIX PARCIAL (2026-05-14)

**Atualização 2026-05-14:** O symptom local foi resolvido pelo `dadaia public install --target all --force` executado durante a entrega da Fase 9 — ele regenera `.claude/settings.json` com paths absolutos derivados do `workspace_root` atual. Verificação: `jq '.hooks' /home/marco/workspace/dadaia/.claude/settings.json | grep -c /home/ubuntu == 0`.

**Pendência aberta:** o mecanismo de import (`dadaia import`) ainda não detecta nem reescreve paths absolutos que apontem para fora do novo `workspace_root` em arquivos não-lib-originated. Próximo `import` em outra máquina pode reintroduzir o problema. Endereçada por **T-IMP-REWRITE-001** na Fase 10 (release-pipeline): adicionar pass de rewriting de paths absolutos em `dadaia_workspace/features/import_/service.py`.

---

### BUG-003 (histórico original) — `.claude/settings.json` contém paths VPS hardcoded (`/home/ubuntu/...`)

**Arquivo afetado:** `.claude/settings.json` (project-specific, **não** lib-originated — não consta no `manifest.json`)

**Sintomas observados:**
1. Existem dois hooks `UserPromptSubmit` e um `PreToolUse` registrados; dois deles apontam para `/home/ubuntu/workspace/.dadaia/scripts/...` (caminho do VPS), o terceiro para `/home/marco/workspace/dadaia/.dadaia/scripts/ctx-inject.sh` (caminho local correto).
2. Como `/home/ubuntu/...` não existe na máquina local, os dois primeiros hooks falham silenciosamente a cada Prompt/Tool, poluindo a saída com erros.
3. Para o `PreToolUse`, isso significa que o `sdd-spec-gate.sh` **não roda** — gate desativado de fato.

**Causa raiz (hipótese):**
Os entries com `/home/ubuntu/...` vazaram de um `dadaia export` feito no VPS e foram preservados literalmente no `import` na máquina local. O `dadaia import` não reescreve paths absolutos dentro de `.claude/settings.json`.

**Fix proposto:**
- Curto prazo: o operador remove manualmente os dois entries com `/home/ubuntu/...` de `.claude/settings.json` (e deixa apenas o `/home/marco/...` correto).
- Médio prazo: `dadaia import` deve detectar entries de hook com paths absolutos fora do novo workspace e ou (a) reescrevê-los para o novo `workspace-root`, ou (b) emitir warning explícito apontando o conflito. Decisão entre (a) e (b) deve sair via grill com o operador.
- Longo prazo: hooks deveriam ser registrados via `dadaia public install` (lib-originated), e não escritos manualmente no `.claude/settings.json` — eliminaria a classe inteira do bug.

**Verificação:**
```bash
jq '.hooks' /home/marco/workspace/dadaia/.claude/settings.json | grep -c '/home/ubuntu'
# Deve retornar 0 após o fix.
```

---

### BUG-002 — `ctx-inject.sh` resolve `WORKSPACE_ROOT` errado fora de git repo ✅ RESOLVIDO (2026-05-14)

**Fix aplicado:** `dadaia_workspace/public/scripts/ctx-inject.sh` e `sdd-spec-gate.sh` agora resolvem `WORKSPACE_ROOT` via `$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)` — independe de git rev-parse e de `$HOME`. Auditados ambos scripts na rodada. Projetado via `dadaia public stage && dadaia public install --target all --force`. Verificação: hook reporta `[dadaia-workspace]` corretamente tanto rodando do workspace quanto de `/tmp` ou qualquer outro cwd.

---

### BUG-002 (histórico) — `ctx-inject.sh` resolve `WORKSPACE_ROOT` errado fora de git repo

**Arquivo afetado:** `dadaia_workspace/public/scripts/ctx-inject.sh` (lib-originated, projetado em `.dadaia/scripts/ctx-inject.sh`)

**Sintomas observados:**
- Hook `UserPromptSubmit` reporta `[context: none] — run: eval $(dadaia context use <name>)` mesmo quando `primary_context.json` é válido e `dadaia context show --json` retorna `dadaia-workspace`.
- Reproduzido em `/home/marco/workspace/dadaia/` (workspace funcional, mas não-git-repo no diretório raiz).

**Causa raiz:**
`ctx-inject.sh:2` resolve `WORKSPACE_ROOT` via:
```bash
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/workspace")}"
```
Se o workspace **não é um git repo** e `$WORKSPACE_ROOT` não está exportado, o fallback é `$HOME/workspace`. No host local `$HOME/workspace` = `/home/marco/workspace`, **sem** o sufixo `/dadaia` — então o script lê `STATE_FILE=/home/marco/workspace/.dadaia/states/primary_context.json`, que não existe, e cai no ramo "context: none".

**Trace confirmando:**
```bash
$ bash -x ~/workspace/dadaia/.dadaia/scripts/ctx-inject.sh
+ WORKSPACE_ROOT="${WORKSPACE_ROOT:-/home/marco/workspace}"   # fallback errado
+ STATE_FILE=/home/marco/workspace/.dadaia/states/primary_context.json
+ [ ! -f /home/marco/workspace/.dadaia/states/primary_context.json ]
+ echo "[context: none] — run: eval \$(dadaia context use <name>)"
```

**Fix proposto:**
Resolver `WORKSPACE_ROOT` via path do próprio script — é robusto, independe de git e de `$HOME`:
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
```
Source no pacote em `dadaia_workspace/public/scripts/ctx-inject.sh`; após editar:
```bash
dadaia public stage && dadaia public install --target all
```

**Mesmo bug provavelmente afeta `sdd-spec-gate.sh`** — sua resolução de `WORKSPACE_ROOT` precisa ser auditada na mesma rodada.

---

### BUG-001 — `dadaia-switch-context` command: lógica de troca obsoleta e stale v2 language ✅ RESOLVIDO (2026-05-12)

**Arquivo afetado:** `.claude/commands/dadaia-switch-context.md` (project-specific, não lib-originated)

**Sintomas observados em produção:**
1. Step 3 executou `dadaia context deactivate` sem argumento `NAME` → erro: `Missing argument 'NAME'`
2. Step 3 executou `dadaia context deactivate workflow-tools` → erro: primary context cannot be deactivated; must promote another first
3. Step 4 chamava `dadaia context activate` mas não promovia o contexto a primário

**Causa raiz:**
- Step 3 instruía deactivar o contexto primário antes de promover o novo — operação bloqueada pelo CLI v4 (corretamente)
- A lógica de troca de contexto é simplesmente `promote`; deactivate remove o repo do disco e não é a operação correta para switch
- Linguagem v2 stale: referências a `.dadaia/contexts/`, estado `standby` e "materialized copies" — nenhum existe na v4

**Fix aplicado:** Step 3 removido; fluxo correto é: se target está `inativo` → `activate` primeiro; depois sempre `promote`. Toda linguagem v2 stale removida.

---

## Gaps fechados

### GAP-DRIFT-001 — Drift documental `foundation/SPEC.md` ↔ realidade `public/` ✅ FECHADO (2026-05-14)

Antes desta rodada, `foundation/SPEC.md` RF-ARCH-002 (linhas 110–146 da v3.0) listava: 4 agents legacy (`architect-agent`, `product-auditor-agent`, `product-engineer-agent`, `soft-engineer-agent`), 3 rules (`sdd-enforcer`, `spec-governance`, `dev-guardrail`), 4 skills (apenas as SDD/spec), 3 commands. A realidade do diretório `dadaia_workspace/public/` era: 6 agents, 2 rules, 17 skills, 4 commands. Drift documental causava implementações que viam `foundation/SPEC.md` como source of truth e divergiam do estado real.

**Resolução:** RF-ARCH-002 totalmente reescrito na v3.1 listando os nomes exatos dos 6 agents (`product-engineer`, `software-architect`, `software-engineer`, `qa-engineer`, `devops-engineer`, `game-developer`), 2 rules (`dadaia-workspace-dev-guardrail`, `game-developer-scope`), 17 skills enumerados, 4 commands (`dadaia-academy`, `dadaia-workspace-doctor`, `dadaia-workspace-refine-specs`, `spec-context`). Adicionada nota: "Toda atualização em `public/<type>/` deve refletir-se em RF-ARCH-002 via PR único."

### GAP-ORCH-001 — Orquestração era "fora de escopo v3.0" ✅ FECHADO (2026-05-14)

`specs/SPEC.md` v3.0 linha 254 listava explicitamente "Orquestração automática entre agentes especializados" como fora de escopo. Coordenação multi-agente acontecia via prompts manuais e convenções de pasta.

**Resolução:** graduado para escopo aprovado em v3.1. Nova feature `specs/features/multi-agent-orchestration/SPEC.md` cobre: workflows como tipo de asset universal de primeira classe, CLI `dadaia orchestrate {list, show, run, status, resume}`, run state em `.dadaia/runs/<run-id>/`, 3 Protocols (`workflow_store`, `run_state_store`, `agent_dispatcher`), 3 módulos de feature (`service.py`, `runner.py`, `resolver.py`), 4 implementações em `infrastructure/`, mapeamento universal Claude (native) / OpenCode (best-effort) / Codex (unsupported), 2 workflows seed (`spec-refinement`, `tdd-cycle`), Input Contract obrigatório por agente, Handoff Schema v1. Sem framework externo. Decisões registradas em ADR-ORCH-001 a 006. SPEC sai como `Em revisão` aguardando aprovação humana.

### GAP-CICD-001 — Ausência total de `.github/workflows/` ✅ FECHADO (2026-05-14)

O repositório não tinha CI/CD. PRs entravam em `main` sem validação. Não havia caminho automatizado para publicar no PyPI. Nome `dadaia-workspace` no PyPI ainda **não reservado**.

**Resolução:** nova feature `specs/features/release-pipeline/SPEC.md` cobre: gitflow + branch protection + CODEOWNERS, `.github/workflows/ci.yml` (lint/typecheck/test + pr-title; Python 3.12 single; ubuntu-latest single; coverage gate ≥80%), `.github/workflows/release.yml` (validate → build → publish OIDC trusted publishing → smoke-test), CHANGELOG.md (Keep a Changelog), RELEASING.md (passo a passo). Right-sizing explícito: zero matrix multi-OS/multi-Python; zero Trivy/Codecov/Renovate/semantic-release/Sentry em v0.1. Pré-condições operacionais (pending publisher PyPI, environment, branch protection) documentadas em `release-pipeline/SPEC.md` "Pré-Condições Operacionais". SPEC sai como `Em revisão`.

### GAP-INPUT-001 — Agentes sem Input Contract obrigatório ✅ FECHADO (2026-05-14)

Antes desta rodada, os 6 agentes em `public/agents/` declaravam `name`, `description`, `model`, `tools` no frontmatter mas não havia contrato declarado de entradas/saídas. Agentes invocados em sessões "frescas" inventavam contexto ou inferiam de prompt — origem da literatura v1 §1.2 / v2 §"Diagnóstico" como gap principal.

**Resolução:** `specs/features/agents/SPEC.md` atualizado com FR-018..023: bloco `input_contract` obrigatório no frontmatter de cada agente (`requires_inputs`, `produces_outputs`, `stop_if_missing`), referência a `handoff-schema-v1`. Reports inter-agente seguem header canônico padrão (Findings, Riscos, Decisões necessárias, Recomendações, Artefatos consultados, Próximo gate). Tasks T102–T107 em `TASKS.md` adicionam o bloco em cada um dos 6 agentes.

---

### GAP-013 — `ContextStore` Protocol: um arquivo ou dois? ✅ FECHADO

Resolvido em 2026-05-09: `foundation/SPEC.md` RF-ARCH-002 atualizado — `primary_context_store.py` adicionado a `core/protocols/` e `json_primary_context_store.py` adicionado a `infrastructure/`. `ContextStore` gerencia `spec_contexts.json`; `PrimaryContextStore` gerencia `primary_context.json`. Dois Protocols independentes, separados por responsabilidade.

### GAP-001 — `foundation/SPEC.md` RF-ARCH-006 não cobre `is_selected` ✅ FECHADO

Resolvido na v4.0: `is_selected` foi removido do modelo. O mecanismo equivalente é `is_primary` (flag booleana no `SpecContextProject`). RF-ARCH-006 foi atualizado para refletir o modelo v4.0 (apenas `inativo` e `ativo`, com `is_primary` como flag).

### GAP-002 — `deactivate` sem parâmetro: ambiguidade de assinatura CLI ✅ FECHADO

Resolvido na v4.0: `deactivate <name>` é a única forma suportada. Não há fallback sem parâmetro. O spec v4.0 (`specs/features/spec-context-project/SPEC.md` FR-015) e `specs/SPEC.md` FR-003 definem `deactivate` como subcomando com `<name>` obrigatório.

### GAP-003 — Escopo de instalação do `/spec-context` por bot ✅ FECHADO

Resolvido novamente em 2026-05-09: commands são projetados para diretórios nativos por runtime. Claude Code usa `.claude/commands/`; OpenCode usa `.opencode/commands/` quando suportado; runtimes sem command support recebem instrução equivalente via `AGENTS.md`/rules e são reportados como `unsupported` pelo doctor. Documentado em `spec-context-agent-command/SPEC.md` e `universal-agentic-assets/SPEC.md`.

### GAP-004 — Alias `/ctx` para `/spec-context` ✅ FECHADO

Decisão: a v1.0 distribui apenas `spec-context.md`. Alias pode ser adicionado pelo operador manualmente.

### GAP-005 — `activate` de contexto `inativo` via `/spec-context`: comportamento de timeout ✅ FECHADO

Resolvido na v4.0: o `/spec-context <nome>` command simplesmente executa `dadaia context activate <nome>` e aguarda a conclusão. O spec não impõe timeout — a responsabilidade de feedback de progresso é da CLI `dadaia`. O command exibe o resultado após a conclusão.

### GAP-006 — Inconsistência de scaffold timing entre specs ✅ FECHADO

Resolvido nesta rodada: `specs/SPEC.md` US-003 CA e FR-017, `specs/memory/architecture.md` e `specs/features/spec-context-project/SPEC.md` (tabela "o que mudou" e glossário) foram todos alinhados. O contrato canônico é: **scaffold acontece exclusivamente em `activate`, após o clone, se `repos/<slug>/specs/` não existir**. O comando `create` nunca clona nem cria scaffold.

### GAP-007 — `dadaia context show <name>` ausente de `specs/SPEC.md` ✅ FECHADO

Resolvido nesta rodada: FR-013 em `specs/SPEC.md` foi atualizado para incluir a variante `dadaia context show [<name>] [--json]`.

### GAP-008 — `dadaia_workspace/public/scaffold/` ausente de `foundation/SPEC.md` RF-ARCH-002 ✅ FECHADO

Resolvido nesta rodada: RF-ARCH-002 em `specs/foundation/SPEC.md` foi atualizado para incluir o diretório `scaffold/` com sua estrutura canônica dentro de `public/`.

### GAP-010 — Comportamento de `dadaia context show --json` com `DADAIA_CONTEXT` ✅ FECHADO

Resolvido em 2026-05-09: FR-034-B adicionado em `specs/features/spec-context-project/SPEC.md` — "`dadaia context show --json` shall always read from `spec_contexts.json` and `primary_context.json`, ignoring the `DADAIA_CONTEXT` environment variable. The env var is exclusive to `ctx-inject.sh`."

### GAP-011 — `dadaia init` sem tabela canônica única ✅ FECHADO

Resolvido em 2026-05-09: `specs/SPEC.md` FR-001 reescrito como tabela canônica de 12 linhas cobrindo todos os paths criados por `dadaia init`. FRs individuais das features referenciam FR-001 em vez de redefinir.

### GAP-012 — `dadaia academy modules` comportamento indefinido ✅ FECHADO

Resolvido em 2026-05-09: `specs/features/dadaia-academy/SPEC.md` FR-016 reescrito — listagem dinâmica via `importlib.resources`, output exibe número + nome da pasta, sem paths absolutos.
