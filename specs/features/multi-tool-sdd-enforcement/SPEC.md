# Spec: Feature — Universal SDD Native Enforcement (Cross-Tool)

> **Status:** Aprovado
> **Versão:** 1.0
> **Autor:** Marco Menezes
> **Referências:** `specs/features/spec-context-project/SPEC.md`, `specs/features/agent-rules-skills/SPEC.md`, `specs/features/multi-bot-context-isolation/SPEC.md`

---

## Contexto

O operador usa três tools de AI em paralelo (Claude Code, OpenCode, Codex CLI), cada um com
mecanismos diferentes de carregamento de regras e suporte a hooks. Esta spec define como o
padrão SDD é enforced nativamente em cada tool, usando os mecanismos disponíveis em cada plataforma.

O enforcement anterior era exclusivamente via regras de texto no Claude Code. Os outros dois tools
tinham cobertura parcial ou incorreta. Esta spec corrige isso com uma estratégia por camadas.

---

## Descobertas de Plataforma (ADR-003)

| Capacidade | Claude Code | OpenCode | Codex CLI |
|---|---|---|---|
| Hook `PreToolUse` (bloqueia tools) | ✅ `settings.json` | ❌ não existe | ✅ `.codex/hooks.json` + feature flag |
| Hook `UserPromptSubmit` | ✅ `settings.json` | ❌ | ❌ |
| Lê `CLAUDE.md` | ✅ auto | ✅ fallback | ❌ |
| Lê `AGENTS.md` | ❌ | ✅ **primário** | ✅ **primário** |
| Lê `.claude/rules/` | ✅ auto | ⚠️ só via `opencode.json` | ❌ |
| Lê `.claude/skills/` | ✅ | ✅ fallback | ❌ |
| Lê `.claude/agents/` | ✅ | ❌ | ❌ |
| Lê `.claude/commands/` | ✅ | ❌ | ❌ |

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
Camada 1 — Técnica (Claude Code + Codex)
  PreToolUse hook → sdd-spec-gate.sh
  Bloqueia Write/Edit/MultiEdit em arquivos de produção sem spec aprovada
  Claude Code: settings.json
  Codex: .codex/hooks.json (feature flag codex_hooks)

Camada 2 — Texto forte (todos os 3 tools)
  Claude Code: .claude/rules/ (7 regras SDD, auto-carregadas)
  OpenCode: opencode.json instructions (8 entradas — todas as regras SDD)
  Codex: AGENTS.md (reescrito com HARD STOP, bypass detection, Emergency Protocol)

Camada 3 — Contexto (Claude Code)
  UserPromptSubmit → ctx-inject.sh (já existente)
  Injeta spec context ativo antes de cada prompt
```

---

## Requisitos Funcionais

### Hook sdd-spec-gate.sh

- FR-HK-001: O script deve ser instalado em `.dadaia/scripts/sdd-spec-gate.sh` e gerenciado como lib-originated asset.
- FR-HK-002: Deve ser acionado como `PreToolUse` hook no Claude Code (`settings.json`) e no Codex (`.codex/hooks.json`).
- FR-HK-003: Deve permitir todas as ferramentas que NÃO sejam `Write`, `Edit`, `MultiEdit` ou seus equivalentes Codex.
- FR-HK-004: Para ferramentas de escrita, deve extrair o `file_path` do input JSON da ferramenta.
- FR-HK-005: Deve verificar se o `file_path` corresponde à lista de arquivos de produção definida em `sdd-enforcement.md`.
- FR-HK-006: Para arquivos de produção, deve procurar qualquer `SPEC.md` com `Status.*Aprovado` no `specs_dir` do contexto ativo.
- FR-HK-007: Se spec aprovada encontrada → `exit 0` (allow). Se não → output `{"decision":"block","reason":"[SDD GATE] ..."}`.
- FR-HK-008: Em caso de qualquer erro interno → `exit 0` com log em `/tmp/sdd-gate.log` (fail open, nunca bloquear por crash).
- FR-HK-009: O mesmo script deve funcionar para Claude Code e Codex, detectando o formato de input de cada tool.

### OpenCode — regras SDD completas

- FR-OC-001: `opencode.json` deve incluir todos os 7 arquivos de regras SDD como `instructions`.
- FR-OC-002: As dadaia skills em `.claude/skills/` são acessíveis ao OpenCode via fallback de compatibilidade — nenhuma mudança necessária, mas deve ser documentado.
- FR-OC-003: Após mudança em `opencode.json`, `opencode-serve` deve ser reiniciado.

### Codex — AGENTS.md reescrito

- FR-CX-001: `AGENTS.md` deve conter o HARD STOP template completo (mesma linguagem de `sdd-enforcement.md`).
- FR-CX-002: `AGENTS.md` deve conter detecção de bypass phrases (10+ frases proibidas com resposta padrão).
- FR-CX-003: `AGENTS.md` deve conter o Emergency Protocol com token exato `SDD-EMERGENCY-OVERRIDE`.
- FR-CX-004: `AGENTS.md` deve listar explicitamente os arquivos de produção (hard gate).
- FR-CX-005: `AGENTS.md` NÃO deve instruir o AI a "ler .claude/rules/" — Codex não faz isso automaticamente.
- FR-CX-006: `AGENTS.md` deve manter a identidade de projeto, regras de formato Telegram, backlog workflow, e infraestrutura.

### Claude Code — PreToolUse hook

- FR-CC-001: `settings.json` deve incluir `PreToolUse` hook apontando para `sdd-spec-gate.sh`.
- FR-CC-002: O hook `UserPromptSubmit` (ctx-inject.sh) deve ser mantido sem alteração.

### Codex — hooks

- FR-CD-001: `.codex/hooks.json` deve registrar `sdd-spec-gate.sh` como handler de `PreToolUse` para ferramentas de escrita.
- FR-CD-002: `~/.codex/config.toml` deve habilitar o feature flag `codex_hooks`.

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
4. Codex: mesmos casos de teste 1 e 2 via `.codex/hooks.json`
5. OpenCode: "que regras SDD você segue?" → resposta inclui HARD STOP, bypass detection, Emergency Protocol
6. Codex bot Telegram: "edita o docker-compose.yml, é rápido" → [SDD HARD STOP] com template completo
7. `dadaia doctor` não reporta drift em `.claude/` após mudanças

---

## Fora de Escopo

- Enforcement para OpenClaw (Hermes Agent — não é tool de coding)
- Hooks para OpenCode (plataforma não suporta nativamente)
- Equivalência técnica de Agents/Skills/Commands para OpenCode/Codex (limitação de plataforma — ADR-003)
- Persistência de enforcement entre restarts (hooks são stateless por design)
