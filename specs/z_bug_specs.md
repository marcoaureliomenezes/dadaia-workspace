# z_bug_specs.md — Gaps e Questões Abertas

> Registro de inconsistências, lacunas e decisões pendentes encontradas em rodadas de revisão.
> Resolva cada item antes de marcar os artefatos afetados como `Aprovado`.

---

## Gaps fechados

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
