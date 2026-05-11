# Tasks: Cross-Tool Parity

**Feature:** cross-tool-parity
**Status:** Aprovado
**PLAN:** `specs/features/cross-tool-parity/PLAN.md`
**Data:** 2026-05-09
**Consolidado por:** `specs/features/universal-agentic-assets/TASKS.md`

---

## Pre-implementation checklist

- [x] SPEC.md com Status: Aprovado
- [x] PLAN.md com Status: Aprovado
- [x] AGENTS.md (workspace root) já reescrito como Fase 1
- [x] opencode.json já atualizado como Fase 1

---

## T01 — Criar template universal de `AGENTS.md` em `public/`

**Objetivo:** criar o template universal de `AGENTS.md` dentro de `dadaia_workspace/public/`, para staging em `.dadaia/agentic/` e projeção no workspace root.

**Ação:**
```bash
dadaia public stage
```

**Verificação:**
```bash
head -3 .dadaia/agentic/templates/AGENTS.md
# deve mostrar: # dadaia Labs — AI Coding Assistant
```

---

## T02 — Atualizar `public/agents/architect-agent.md`

**Objetivo:** adicionar seções de dadaia CLI, venv policy e Spec Context ao agente.

**Adição após a seção `## Rules`:**
```markdown
## dadaia CLI

- Descubra o contexto ativo: `dadaia context list`
- Se há contexto ativo, carregue `specs/constitution.md` e `specs/SPEC.md` do repositório
- Para acionar outros recursos: `dadaia academy list`, `dadaia doctor`

## Python / venv

- Sempre use `.dadaia/.venv/bin/python` — nunca `python3` diretamente
- Scripts temporários: `.dadaia/tmp/python/`
```

**Verificação:** `grep -c "dadaia context list" dadaia_workspace/public/agents/architect-agent.md` → `1`

---

## T03 — Atualizar `public/agents/product-auditor-agent.md`

**Objetivo:** mesmas seções de T02 no agente product-auditor.

**Verificação:** `grep "dadaia context list" dadaia_workspace/public/agents/product-auditor-agent.md`

---

## T04 — Atualizar `public/agents/product-engineer-agent.md`

**Objetivo:** mesmas seções de T02 no agente product-engineer.

**Verificação:** `grep "dadaia context list" dadaia_workspace/public/agents/product-engineer-agent.md`

---

## T05 — Atualizar `public/agents/soft-engineer-agent.md`

**Objetivo:** mesmas seções de T02 no agente soft-engineer.

**Verificação:** `grep "dadaia context list" dadaia_workspace/public/agents/soft-engineer-agent.md`

---

## T06 — Atualizar `WorkspaceService.init()` para projeções multi-runtime

**Objetivo:** `dadaia init` deve executar staging e instalar projeções multi-runtime, incluindo `AGENTS.md`.

**Arquivo:** `dadaia_workspace/features/workspace/service.py`

**Padrão:** seguir exatamente o padrão de criação de outros arquivos do scaffold (create if absent).
Usar o mesmo fluxo de `dadaia public stage` e `dadaia public install --target all`.

**Verificação:**
```bash
# Em um diretório limpo sem AGENTS.md
dadaia init /tmp/test-ws-ctp
ls /tmp/test-ws-ctp/AGENTS.md
ls /tmp/test-ws-ctp/.agents/skills
ls /tmp/test-ws-ctp/.codex
ls /tmp/test-ws-ctp/.opencode
head -3 /tmp/test-ws-ctp/AGENTS.md  # deve ser "# dadaia Labs — AI Coding Assistant"
rm -rf /tmp/test-ws-ctp
```

---

## T07 — Verificar/Atualizar `PublicAssetService` para stage/install/doctor

**Objetivo:** `dadaia public stage`, `dadaia public install --target all|claude|codex|opencode|agents` e `dadaia public doctor` devem operar sobre package source, staging e projeções.

**Arquivo:** `dadaia_workspace/features/public/service.py`

Verificar que install gera staging se ausente, preserva arquivos sem `--force`, e reporta unsupported quando runtime não suporta uma capability.

**Verificação:**
```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
ls /tmp/test-install/AGENTS.md
rm -rf /tmp/test-install
```

---

## T08 — E2E: verificar parity completa

**Objetivo:** confirmar que todos os critérios de aceitação do SPEC estão atendidos.

```bash
WS=/home/ubuntu/workspace
REPO=$WS/repos/dadaia-workspace

# 1. AGENTS.md correto no workspace root
head -3 $WS/AGENTS.md
# → # dadaia Labs — AI Coding Assistant

# 2. opencode.json com AGENTS.md primeiro
python3 -c "import json; d=json.load(open('$WS/opencode.json')); print(d['instructions'][0])"
# → AGENTS.md

# 3. Staging canônico existe
ls $WS/.dadaia/agentic/manifest.json

# 4. Agentes atualizados
grep -l "dadaia context list" $REPO/dadaia_workspace/public/agents/*.md | wc -l
# → 4

# 5. dadaia init gera projeções multi-runtime (em workspace limpo)
TMPWS=$(mktemp -d)
$WS/.dadaia/.venv/bin/dadaia init "$TMPWS"
ls "$TMPWS/AGENTS.md" && head -2 "$TMPWS/AGENTS.md"
ls "$TMPWS/.agents/skills" "$TMPWS/.codex" "$TMPWS/.opencode" "$TMPWS/.claude"
rm -rf "$TMPWS"
```
