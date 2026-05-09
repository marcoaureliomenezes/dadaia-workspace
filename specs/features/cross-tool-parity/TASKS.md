# Tasks: Cross-Tool Parity

**Feature:** cross-tool-parity
**Status:** Aprovado
**PLAN:** `specs/features/cross-tool-parity/PLAN.md`
**Data:** 2026-05-09

---

## Pre-implementation checklist

- [x] SPEC.md com Status: Aprovado
- [x] PLAN.md com Status: Aprovado
- [x] AGENTS.md (workspace root) já reescrito como Fase 1
- [x] opencode.json já atualizado como Fase 1

---

## T01 — Criar `public/data/` e `public/data/AGENTS.md`

**Objetivo:** criar o diretório `public/data/` e copiar o conteúdo atual do `AGENTS.md`
do workspace root como template canônico.

**Ação:**
```bash
mkdir -p dadaia_workspace/public/data
cp /home/ubuntu/workspace/AGENTS.md dadaia_workspace/public/data/AGENTS.md
```

**Verificação:**
```bash
head -3 dadaia_workspace/public/data/AGENTS.md
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

## T06 — Atualizar `WorkspaceService.init()` para criar AGENTS.md

**Objetivo:** `dadaia init` deve criar `AGENTS.md` no workspace root a partir de `public/data/AGENTS.md`.

**Arquivo:** `dadaia_workspace/features/workspace/service.py`

**Padrão:** seguir exatamente o padrão de criação de outros arquivos do scaffold (create if absent).
Usar `importlib.resources` ou `Path(__file__).parent` para localizar `public/data/AGENTS.md`.

**Verificação:**
```bash
# Em um diretório limpo sem AGENTS.md
dadaia init /tmp/test-ws-ctp
ls /tmp/test-ws-ctp/AGENTS.md  # deve existir
head -3 /tmp/test-ws-ctp/AGENTS.md  # deve ser "# dadaia Labs — AI Coding Assistant"
rm -rf /tmp/test-ws-ctp
```

---

## T07 — Verificar/Atualizar `PublicAssetService.install()` para AGENTS.md

**Objetivo:** `dadaia public install --target .claude` deve também instalar `AGENTS.md`
no workspace root (um nível acima de `.claude/`).

**Arquivo:** `dadaia_workspace/features/public/service.py`

Verificar se `install()` já suporta arquivos em `public/data/` sendo instalados fora de `.claude/`.
Se não, adicionar lógica: arquivos em `public/data/` vão para `<workspace-root>/`, não para `<target>/`.

**Verificação:**
```bash
dadaia public install --target /tmp/test-install/.claude
ls /tmp/test-install/AGENTS.md  # deve existir no root, não em .claude/
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

# 3. Template canônico existe
ls $REPO/dadaia_workspace/public/data/AGENTS.md

# 4. Agentes atualizados
grep -l "dadaia context list" $REPO/dadaia_workspace/public/agents/*.md | wc -l
# → 4

# 5. dadaia init gera AGENTS.md (em workspace limpo)
TMPWS=$(mktemp -d)
$WS/.dadaia/.venv/bin/dadaia init "$TMPWS"
ls "$TMPWS/AGENTS.md" && head -2 "$TMPWS/AGENTS.md"
rm -rf "$TMPWS"
```
