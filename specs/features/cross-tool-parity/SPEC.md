# Feature Spec: Cross-Tool Parity

**Feature ID:** cross-tool-parity
**Status:** Aprovado
**Owner:** dadaia Labs
**Version:** 1.0
**Data:** 2026-05-09

---

## Contexto e Motivação

O workspace dadaia Labs é operado via Claude Code (ferramenta principal). Quando o contexto
do Claude esgota, o operador precisa trocar para OpenCode ou Codex e continuar com as **mesmas
regras, mesma consciência do projeto e os mesmos agentes**. Hoje essa troca quebra porque:

- `AGENTS.md` no workspace root continha conteúdo de bot Telegram (sem regras SDD)
- Codex lê apenas `AGENTS.md` + PreToolUse hook — sem regras chega ao modelo
- OpenCode lê as rules via `opencode.json` mas não tem agentes definidos
- `dadaia public install` não instala `AGENTS.md` — novos workspaces ficam sem cross-tool parity
- Agentes Claude Code (`.claude/agents/`) não documentam dadaia CLI, venv policy, nem academy

**Objetivo:** garantir que Claude Code, OpenCode e Codex sejam intercambiáveis como ferramentas
de trabalho neste workspace, cada uma com o contexto completo e agentes adequados.

---

## Canal de Leitura por Ferramenta (ADR-CTP-001)

| Ferramenta | Carrega automaticamente |
|---|---|
| Claude Code | `.claude/rules/*.md`, `.claude/agents/*.md`, `.claude/skills/`, CLAUDE.md |
| OpenCode | `AGENTS.md` (primário) + `opencode.json` instructions |
| Codex | `AGENTS.md` (primário) + `.codex/hooks.json` PreToolUse |

`AGENTS.md` é o documento universal — o único que precisa existir para garantir parity mínima
para OpenCode e Codex.

---

## User Stories

**US-CTP-001:** Como operador, quando o contexto do Claude esgota, quero abrir OpenCode e
continuar trabalhando com as mesmas regras SDD e conhecimento do projeto.

**US-CTP-002:** Como operador, quero usar o @architect-agent, @product-engineer-agent,
@soft-engineer-agent e @product-auditor-agent em qualquer uma das três ferramentas.

**US-CTP-003:** Como operador, ao inicializar um novo workspace com `dadaia init`, quero que
`AGENTS.md` seja gerado automaticamente com o conteúdo correto.

---

## Functional Requirements

**FR-CTP-001 — AGENTS.md universal:**
`AGENTS.md` no workspace root deve conter: identidade/tom, SDD enforcement completo,
Spec Context discovery, dadaia CLI reference, venv policy, regras de segurança, contexto
do projeto, 4 agentes com personas, checklist pré-código.

**FR-CTP-002 — opencode.json inclui AGENTS.md:**
`opencode.json` deve listar `"AGENTS.md"` como primeira entrada em `instructions`.

**FR-CTP-003 — Template canônico em public/:**
`dadaia_workspace/public/data/AGENTS.md` deve conter o template de `AGENTS.md` instalado
por `dadaia public install`.

**FR-CTP-004 — dadaia init gera AGENTS.md:**
`dadaia init` deve criar `AGENTS.md` no workspace root a partir do template em `public/data/`.
Se `AGENTS.md` já existe, não sobreescreva (comportamento idêntico ao de outros arquivos do scaffold).

**FR-CTP-005 — Agentes Claude Code atualizados:**
Os 4 agentes em `dadaia_workspace/public/agents/` devem incluir seções sobre:
dadaia CLI reference, venv policy, como descobrir o spec context ativo.

**FR-CTP-006 — dadaia public install inclui AGENTS.md:**
O comando `dadaia public install` deve copiar `public/data/AGENTS.md` para `<target>/AGENTS.md`
(um nível acima de `.claude/`, no workspace root).

---

## Non-Functional Requirements

**NFR-CTP-001:** `AGENTS.md` deve ser legível sem contexto adicional — qualquer modelo AI
que o leia deve conseguir operar o workspace seguindo as regras.

**NFR-CTP-002:** O template em `public/data/AGENTS.md` deve ser idêntico ao `AGENTS.md`
instalado — sem placeholders, sem variáveis de substituição.

**NFR-CTP-003:** `dadaia init` não deve falhar se `AGENTS.md` já existe — usar modo "create if absent".

---

## Acceptance Criteria

- [ ] `AGENTS.md` começa com `# dadaia Labs — AI Coding Assistant` (não `Workspace Assistant`)
- [ ] `AGENTS.md` contém seção SDD com pipeline e HARD STOP template
- [ ] `AGENTS.md` contém seção `dadaia context list` para Spec Context discovery
- [ ] `AGENTS.md` contém seção de agentes com os 4 personas
- [ ] `opencode.json` lista `"AGENTS.md"` como primeiro item de `instructions`
- [ ] `dadaia public install` cria/atualiza `AGENTS.md` no workspace root
- [ ] `dadaia init` cria `AGENTS.md` se não existir
- [ ] Agentes em `public/agents/` mencionam `dadaia CLI`, `venv policy`, `dadaia context list`

---

## Out of Scope

- Hooks automáticos para OpenCode/Codex equivalentes ao ctx-inject.sh do Claude Code
  (OpenCode e Codex não suportam UserPromptSubmit; instrução em AGENTS.md é suficiente)
- Sincronização automática de AGENTS.md com `.claude/rules/` (manutenção manual)
- Skills/commands para OpenCode ou Codex (sem mecanismo equivalente disponível)
