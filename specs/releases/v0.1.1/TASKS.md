# Tasks: Hotfix Release — v0.1.1

> **Status:** Aprovado
> **Release ID:** v0.1.1
> **Patches release:** dadaia-workspace-panel-v1
> **Owner:** product-engineer
> **Created:** 2026-05-17

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## T-DSR-01 — Centralized workspace resolver (core module + tests)

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** branch `hotfix/dev-server-registry-v0.1.1` criado, PR #9 mergeado em `main` (ou rebase posterior).
- **Files modified:**
  - `dadaia_workspace/core/workspace_resolver.py` (novo)
  - `tests/unit/core/test_workspace_resolver.py` (novo)
- **Mudanças:** Criar `resolve_workspace_root(cwd: Path | None = None) -> Path` que anda para cima procurando o **primeiro diretório que contém `.dadaia/states/spec_contexts.json`** (não apenas `.dadaia/`). Levanta `WorkspaceNotInitializedError` com mensagem citando cwd + candidatos inspecionados se não encontrar. Test-first: cwd em sub-repo com `.dadaia/`, cwd na raiz, cwd fora, cwd em workspace parcial.
- **Aceite:** Testes passam; ≥90% coverage do novo módulo.

## T-DSR-02 — Substituir _resolve_workspace duplicates por import

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** T-DSR-01 done.
- **Files modified:**
  - `dadaia_workspace/cli/commands/server.py` (linhas 26-30 removidas)
  - `dadaia_workspace/cli/commands/panel.py` (linhas 24-29 removidas)
  - + qualquer outra cópia descoberta via `grep -rn "_resolve_workspace\|def _resolve_workspace" dadaia_workspace/`
- **Mudanças:** Importar `from dadaia_workspace.core.workspace_resolver import resolve_workspace_root` em cada CLI. Substituir chamadas a `_resolve_workspace()` por `resolve_workspace_root()`.
- **Aceite:** Smoke from `cd repos/dadaia-bots && dadaia server list` retorna registry global, não "Workspace not initialized". Smoke from `cd repos/tauan-games && dadaia server list` idem. doctor green.

## T-DSR-03 — Skip-and-log JSON store resilience

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** T-DSR-02 done (resolver fix lands first, isolada).
- **Files modified:** `dadaia_workspace/infrastructure/json_server_registry_store.py`
- **Mudanças:** `_load()` catch `JSONDecodeError` → log warning + return empty registry. `_from_dict()` catch `KeyError`/`TypeError`/`ValueError` per-entry → log warning + skip (não raise). Manter forward-compat para chaves extras desconhecidas. Logs estruturados: `"registry_entry_malformed"` com `port` e `reason`.
- **Aceite:** Registry com 1 entry malformado + 2 válidas → list retorna 2 entries + 1 warning logged.

## T-DSR-04 — Tests for store resilience

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** T-DSR-03 done.
- **Files modified:** `tests/unit/infrastructure/test_json_server_registry_store_resilience.py` (novo)
- **Mudanças:** Cobrir 4 cenários: (1) JSON inválido → empty + warning + no raise; (2) entry sem `expires_at` → skipped, outras retornadas; (3) entry com tipo errado em `port` (string) → skipped; (4) entry com chave extra desconhecida → aceito (forward-compat).
- **Aceite:** ≥4 testes verdes.

## T-DSR-05 — Probe permission semantics fix

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** T-DSR-04 done.
- **Files modified:** `dadaia_workspace/core/protocols/process_probe.py`
- **Mudanças:** `OsProcessProbe.is_pid_alive`: `ProcessLookupError` → False; `PermissionError` → True (alive but unprobable, documentar); `OSError` outro → True + warning log. Atualizar docstring com tabela de exit conditions.
- **Aceite:** Testes self-PID alive, missing-PID dead, root-PID alive.

## T-DSR-06 — Tests for probe semantics

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** T-DSR-05 done.
- **Files modified:** `tests/unit/core/test_process_probe.py` (novo)
- **Mudanças:** Cobrir 3 PIDs: atual (alive), 99999999 (dead), PID 1 init (alive via PermissionError → True). Documentar comportamento de PID 0 (kernel) como xfail/skip.
- **Aceite:** ≥3 testes verdes.

## T-DSR-07 — Scan command core logic

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** T-DSR-06 done.
- **Files modified:**
  - `dadaia_workspace/features/server_registry/scan.py` (novo)
  - `dadaia_workspace/core/models/server_registry.py` (append `UnregisteredListener` dataclass)
- **Mudanças:** `scan_unregistered_listeners(registry_entries: list[PortEntry]) -> list[UnregisteredListener]`. Subprocess `ss -tlnp`, filtra por uid do user atual, skip portas `<1024` e ports já no registry. Para cada listener: `port`, `bind`, `pid`, `cmdline` (via `/proc/<pid>/cmdline`), `cwd` (via `/proc/<pid>/cwd`), `lan_exposed = bind == "0.0.0.0"`. Robusto a `ss` ausente (retorna empty + warning).
- **Aceite:** Smoke detecta orphan criado de propósito; tests com mocked `ss` output verdes.

## T-DSR-08 — `dadaia server scan` CLI subcommand

- [ ] **Status:** OPEN
- **Owner:** software-engineer
- **Precondições:** T-DSR-07 done.
- **Files modified:**
  - `dadaia_workspace/cli/commands/server.py` (novo subcomando)
  - `tests/unit/features/server_registry/test_scan.py` (novo)
- **Mudanças:** `dadaia server scan` (opção `--json`). Output table: Port | Bind | PID | Cmd | CWD | LAN-exposed. Exit 0 sempre (informativo). Tests com fixture de `ss -tlnp` mockado e registry de 1 entry retornando 2 unregistered.
- **Aceite:** `dadaia server scan` retorna 0 e lista um orphan controlado. `--json` retorna JSON parseable.

## T-DSR-09 — Panel "Unregistered" section UI

- [ ] **Status:** OPEN
- **Owner:** frontend-engineer
- **Precondições:** T-DSR-08 done.
- **Files modified:**
  - `dadaia_workspace/features/panel/service.py` (novo método `list_unregistered_listeners()`)
  - `dadaia_workspace/features/panel/views/api.py` (`/api/servers` payload + `unregistered`)
  - `dadaia_workspace/features/panel/views/_assets.py` (PANEL_CSS, PANEL_HTML, PANEL_JS)
  - `tests/unit/features/panel/test_unregistered_section.py` (novo)
- **Mudanças:** Lazy/on-request (cadência 5s herdada). Nova seção `role="region"` com `aria-label="Unregistered listeners"`, tabela com `<caption>`. Badge LAN-exposed usa `var(--color-alert)` do brand-identity-v1. Snapshot test do HTML renderizado.
- **Aceite:** Smoke visual via `dadaia panel`; seção mostra orphans com badge amarelo para `lan_exposed: true`.

## T-DSR-10 — Acceptance + PR

- [ ] **Status:** OPEN
- **Owner:** product-engineer (claude-main)
- **Precondições:** T-DSR-01..09 done.
- **Files modified:**
  - `.dadaia/reports/dadaia-workspace/product-engineer/<UTC-ts>-dev-server-registry-hotfix-acceptance.html`
  - `.dadaia/reports/dadaia-workspace/product-engineer/<UTC-ts>-dev-server-registry-hotfix-acceptance.handoff.json`
- **Mudanças:** Smoke end-to-end: spawn orphan controlado (`python -m http.server 9999 --bind 127.0.0.1 &`) → scan lista → painel mostra → register → move para Servers → kill → marcado stale. Emit HTML + handoff sidecar. Validar `dadaia reports validate`. PR cria `gh pr create --base main --head hotfix/dev-server-registry-v0.1.1`.
- **Aceite:** PR URL retornada ao operador; todos os 12 critérios SPEC §Acceptance verdes.
