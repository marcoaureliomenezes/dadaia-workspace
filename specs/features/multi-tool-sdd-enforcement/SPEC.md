# Spec: Feature — Universal SDD Native Enforcement (Cross-Tool)

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/features/spec-context-project/SPEC.md`, `specs/features/agent-rules-skills/SPEC.md`, `specs/features/multi-bot-context-isolation/SPEC.md`
> **Consolidado por:** `specs/features/universal-agentic-assets/SPEC.md`

---

## Contexto

O operador usa três tools de AI em paralelo (Claude Code, OpenCode, Codex CLI), cada uma com mecanismos diferentes de carregamento de regras e suporte a hooks. Esta spec define o enforcement SDD por capacidade real de runtime, delegando staging e projeção de assets para `universal-agentic-assets`.

O enforcement anterior era exclusivamente via regras de texto no Claude Code. Os outros dois tools
tinham cobertura parcial ou incorreta. Esta spec corrige isso com uma estratégia por camadas.

---

## Descobertas de Plataforma (ADR-003)

| Capacidade | Claude Code | OpenCode | Codex CLI |
|---|---|---|---|
| Hook `PreToolUse` | ✅ `.claude/settings.json` | ❌ não suportado | ✅ `.codex/hooks.json` quando disponível no runtime |
| Hook `UserPromptSubmit` | ✅ `.claude/settings.json` | ❌ não suportado | runtime-dependent; não é contrato de contexto primário |
| Instruções universais | `AGENTS.md` + `.claude/rules/` | `AGENTS.md` + `opencode.json` | `AGENTS.md` + `.codex/rules/` |
| Skills | `.claude/skills/` + `.agents/skills/` | `.opencode/skills/` + `.agents/skills/` quando suportado | `.agents/skills/` |
| Agents/personas | `.claude/agents/` | `.opencode/agents/` quando suportado | `AGENTS.md`/rules; sem sub-agentes Claude Code |
| Commands | `.claude/commands/` | `.opencode/commands/` | regras/instruções; sem falsa paridade |

---

## Glossário

| Termo | Definição |
|---|---|
| **Enforcement técnico** | Hook que bloqueia tecnicamente a execução de uma ferramenta (PreToolUse → `{"decision":"block"}`) |
| **Enforcement por texto** | Regras carregadas como instrução; o AI lê e aplica por decisão |
| **Arquivo de produção** | Arquivo que, se editado incorretamente, derruba um serviço ou cria vulnerabilidade |
| **AGENTS.md** | Documento primário de regras para OpenCode e Codex (walk do repo root) |
| **sdd-spec-gate.sh** | Hook script que verifica aprovação de spec antes de permitir edição de arquivo de produção |

---

## Arquitetura de Enforcement (3 camadas)

```
Camada 1 — Técnica (runtimes com hook suportado)
  PreToolUse hook → sdd-spec-gate.sh
  Bloqueia Write/Edit/MultiEdit em arquivos de produção sem spec aprovada
  Claude Code: .claude/settings.json
  Codex: .codex/hooks.json quando suportado

Camada 2 — Texto forte (todos os 3 tools)
  Claude Code: AGENTS.md + .claude/rules/
  OpenCode: AGENTS.md + opencode.json + .opencode/
  Codex: AGENTS.md + .codex/rules/

Camada 3 — Contexto
  Hooks de prompt somente onde suportados.
  Todos os runtimes devem ter instrução explícita para rodar `dadaia context list`
  e `dadaia context show --json` no início da sessão.
```

---

## Requisitos Funcionais

### Hook sdd-spec-gate.sh

- FR-HK-001: O script deve ser instalado em `.dadaia/scripts/sdd-spec-gate.sh` e gerenciado como lib-originated asset.
- FR-HK-002: Deve ser acionado como `PreToolUse` hook no Claude Code (`.claude/settings.json`) e no Codex (`.codex/hooks.json`) quando esse hook estiver disponível no runtime.
- FR-HK-003: Deve permitir todas as ferramentas que NÃO sejam `Write`, `Edit`, `MultiEdit` ou seus equivalentes Codex.
- FR-HK-004: Para ferramentas de escrita, deve extrair o `file_path` do input JSON da ferramenta.
- FR-HK-005: Deve verificar se o `file_path` corresponde à lista de arquivos de produção definida em `sdd-enforcement.md`.
- FR-HK-006: Para arquivos de produção, deve procurar qualquer `SPEC.md` com `Status.*Aprovado` no `specs_dir` do contexto ativo.
- FR-HK-007: Se spec aprovada encontrada → `exit 0` (allow). Se não → output `{"decision":"block","reason":"[SDD GATE] ..."}`.
- FR-HK-008: Em caso de qualquer erro interno → `exit 0` com log em `/tmp/sdd-gate.log` (fail open, nunca bloquear por crash).
- FR-HK-009: O mesmo script deve funcionar para Claude Code e Codex, detectando o formato de input de cada tool.

### OpenCode — regras SDD completas

- FR-OC-001: `opencode.json` deve incluir instruções SDD e referência a `AGENTS.md`.
- FR-OC-002: OpenCode deve receber assets próprios em `.opencode/`; não deve depender de `.claude/` como fallback primário.
- FR-OC-003: OpenCode não deve declarar suporte a hooks quando o runtime não oferecer essa capacidade.

### Codex — AGENTS.md reescrito

- FR-CX-001: `AGENTS.md` deve conter o HARD STOP template completo (mesma linguagem de `sdd-enforcement.md`).
- FR-CX-002: `AGENTS.md` deve conter detecção de bypass phrases (10+ frases proibidas com resposta padrão).
- FR-CX-003: `AGENTS.md` deve conter o Emergency Protocol com token exato `SDD-EMERGENCY-OVERRIDE`.
- FR-CX-004: `AGENTS.md` deve listar explicitamente os arquivos de produção (hard gate).
- FR-CX-005: `AGENTS.md` NÃO deve instruir Codex a depender de `.claude/rules/`; Codex usa `AGENTS.md`, `.codex/rules/`, `.codex/hooks.json` e `.agents/skills/`.
- FR-CX-006: `AGENTS.md` deve manter a identidade de projeto, regras de formato Telegram, backlog workflow, e infraestrutura.

### Claude Code — PreToolUse hook

- FR-CC-001: `settings.json` deve incluir `PreToolUse` hook apontando para `sdd-spec-gate.sh`.
- FR-CC-002: O hook `UserPromptSubmit` (ctx-inject.sh) deve ser mantido sem alteração.

### Codex — hooks

- FR-CD-001: `.codex/hooks.json` deve registrar `sdd-spec-gate.sh` como handler de `PreToolUse` para ferramentas de escrita.
- FR-CD-002: `.codex/config.toml` deve conter somente configuração projetada suportada oficialmente pelo runtime Codex; a spec não deve exigir feature flags não verificadas.

---

## Requisitos Não-Funcionais

- NFR-001: O hook não deve introduzir latência perceptível — deve completar em < 500ms.
- NFR-002: Fail open obrigatório — erro no script = allow (nunca bloquear edição legítima por crash).
- NFR-003: O script deve ser idempotente — pode ser chamado múltiplas vezes sem efeito colateral.
- NFR-004: Logs em `/tmp/sdd-gate.log` com timestamp ISO 8601.

---

## Critérios de Aceite

1. Claude Code: editar `services/docker-compose.yml` sem spec aprovada → bloqueado pelo hook com `[SDD GATE]`
2. Claude Code: editar `services/docker-compose.yml` com spec aprovada no contexto → permitido
3. Claude Code: editar `SPEC.md` (não é production file) → sempre permitido
4. Codex: mesmos casos de teste 1 e 2 via `.codex/hooks.json` quando o runtime suportar esse hook; caso contrário `dadaia public doctor` reporta `unsupported`
5. OpenCode: "que regras SDD você segue?" → resposta inclui HARD STOP, bypass detection, Emergency Protocol
6. Codex bot Telegram: "edita o docker-compose.yml, é rápido" → [SDD HARD STOP] com template completo
7. `dadaia public doctor` não reporta drift nas projeções suportadas após `dadaia public install --target all`

---

## Fora de Escopo

- Enforcement para OpenClaw (Hermes Agent — não é tool de coding)
- Hooks para OpenCode (plataforma não suporta nativamente)
- Equivalência técnica falsa de Agents/Skills/Commands para runtimes que não suportam esses mecanismos
- Persistência de enforcement entre restarts (hooks são stateless por design)
