# Feature Spec: Cross-Tool Parity

**Feature ID:** cross-tool-parity
**Status:** Em revisão
**Owner:** dadaia Labs
**Version:** 2.1
**Data:** 2026-05-14
**Consolidado por:** `specs/features/universal-agentic-assets/SPEC.md`

---

## Contexto e Motivação

O workspace dadaia Labs é operado por Claude Code, OpenCode e Codex. Paridade não significa que todos tenham os mesmos mecanismos técnicos; significa que todos recebem as mesmas regras SDD, o mesmo contrato de descoberta de contexto e as mesmas personas de agente dentro das capacidades nativas de cada runtime.

**Objetivo:** garantir que Claude Code, OpenCode e Codex sejam intercambiáveis como ferramentas de trabalho, usando `dadaia_workspace/public/` como fonte canônica, `.dadaia/agentic/` como staging gerado e projeções para `.agents/`, `.claude/`, `.codex/`, `.opencode/`, `opencode.json` e `AGENTS.md`.

---

## Canal de Leitura por Ferramenta (ADR-CTP-001)

| Ferramenta | Carrega automaticamente |
|---|---|
| Claude Code | `.claude/rules/`, `.claude/agents/`, `.claude/skills/`, `.claude/settings.json`, `AGENTS.md` |
| OpenCode | `AGENTS.md`, `opencode.json`, `.opencode/commands/`, `.opencode/skills/`, `.opencode/agents/` |
| Codex | `AGENTS.md`, `.codex/rules/`, `.codex/hooks.json`, `.codex/config.toml`, `.agents/skills/` |

`AGENTS.md` é o documento universal mínimo. Diretórios runtime-specific são projeções geradas, nunca fonte canônica.

---

## User Stories

**US-CTP-001:** Como operador, quando alterno entre Claude Code, OpenCode e Codex, quero preservar as mesmas regras SDD e o mesmo procedimento de descoberta de contexto.

**US-CTP-002:** Como operador, quero usar o @architect-agent, @product-engineer-agent, @soft-engineer-agent e @product-auditor-agent em qualquer runtime que suporte personas/agentes, sem falsa paridade nos runtimes que não suportam.

**US-CTP-003:** Como operador, ao inicializar um novo workspace com `dadaia init`, quero que
`AGENTS.md`, `.agents/skills/`, `.claude/`, `.codex/`, `.opencode/` e configs relacionadas sejam geradas por projeção.

---

## Functional Requirements

**FR-CTP-001 — AGENTS.md universal:**
`AGENTS.md` no workspace root deve conter: identidade/tom, SDD enforcement completo,
Spec Context discovery, dadaia CLI reference, venv policy, regras de segurança, contexto
do projeto, 4 agentes com personas, checklist pré-código.

**FR-CTP-002 — opencode.json inclui AGENTS.md:**
`opencode.json` e `.opencode/` devem ser gerados como projeção nativa do OpenCode, sem depender de `.claude/` como fonte primária.

**FR-CTP-003 — Codex nativo:**
`.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/` e `.agents/skills/` devem ser gerados como projeção nativa do Codex.

**FR-CTP-004 — dadaia init gera AGENTS.md:**
O template de `AGENTS.md` deve viver em `dadaia_workspace/public/` e ser staged em `.dadaia/agentic/` antes da instalação.

**FR-CTP-005 — Init multi-runtime:**
`dadaia init` deve criar o scaffold multi-runtime chamando o mesmo fluxo de staging/projeção usado por `dadaia public install --target all`.

**FR-CTP-006 — Sem falsa paridade:**
Quando uma ferramenta não suportar hooks, sub-agentes, commands ou skills em determinado formato, a projeção deve omitir a capacidade e `dadaia public doctor` deve reportar `unsupported`.

---

## Non-Functional Requirements

**NFR-CTP-001:** `AGENTS.md` deve ser legível sem contexto adicional — qualquer modelo AI
que o leia deve conseguir operar o workspace seguindo as regras.

**NFR-CTP-002:** Projeções runtime-specific devem ser recriáveis a partir de `.dadaia/agentic/`.

**NFR-CTP-003:** `dadaia init` e `dadaia public install` não devem sobrescrever arquivos existentes sem `--force`.

---

## Acceptance Criteria

- [ ] `AGENTS.md` começa com `# dadaia Labs — AI Coding Assistant` (não `Workspace Assistant`)
- [ ] `AGENTS.md` contém seção SDD com pipeline e HARD STOP template
- [ ] `AGENTS.md` contém seção `dadaia context list` para Spec Context discovery
- [ ] `AGENTS.md` contém seção de agentes com os 6 personas (`software-architect`, `product-engineer`, `software-engineer`, `qa-engineer`, `devops-engineer`, `game-developer`)
- [ ] `.agents/skills/` contém skills universais
- [ ] `.claude/`, `.codex/` e `.opencode/` são gerados por `dadaia public install --target all`
- [ ] `dadaia public doctor` reporta `ok`, `missing`, `drift`, `partial` ou `unsupported`
- [ ] Nenhuma spec exige hook parity para OpenCode

---

## Paridade de Orquestração (adicionado por `multi-agent-orchestration`)

A partir desta evolução, a matriz de paridade inclui as capacidades de orquestração multi-agente. Cada linha lista o suporte declarado de cada runtime.

| Capacidade | Claude Code | OpenCode | Codex | Mecanismo |
|---|---|---|---|---|
| **workflows declarados** | full | full | full | `.../workflows/*.workflow.md` é projetado em todos os runtimes como referência human-readable |
| **`dadaia orchestrate {list, show, run, status, resume}`** | full | full | full | CLI universal; não depende do runtime |
| **`parallel_group` em workflows** | full (`mode=native`) | partial (`mode=best-effort-sequential`) | unsupported (`mode=unsupported`) | host agent dispara N `Agent` numa msg (Claude); OpenCode executa sequencial; Codex rejeita |
| **gates `operator-approval`** | full | full | full | Gate é gravado em `events.jsonl`; resolução via CLI `dadaia orchestrate resume <run-id>` (universal) |
| **run-state em `.dadaia/runs/`** | full | full | full | CLI universal; arquivos atômicos `manifest.json` + `events.jsonl` |
| **dispatcher selection (`DADAIA_AGENT_RUNTIME`)** | claude | opencode | codex | env var + flag `--runtime` |

**FR-CTP-007 — Orquestração honesta por runtime:**
`dadaia public doctor` shall classify each workflow per runtime using `ok | partial | unsupported | missing | drift`. The CLI surface `dadaia orchestrate` is identical across runtimes; only the dispatcher implementation differs. Tentativas de uso fora da capacidade do runtime devem falhar cedo com mensagem orientada (RF-QA-007), não simular paridade.

---

## Out of Scope

- Implementar capabilities inexistentes em runtimes.
- Usar `.claude/` como fonte primária para OpenCode ou Codex.
- Sincronização automática fora do fluxo `stage` → `install`.
