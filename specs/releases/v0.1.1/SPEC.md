# Spec: Hotfix Release — v0.1.1

> **Status:** Aprovado
> **Release ID:** v0.1.1
> **Patches release:** dadaia-workspace-panel-v1
> **Severity:** HIGH
> **Owner:** product-engineer
> **Created:** 2026-05-17
> **Slug alias:** dev-server-registry-hotfix-v1 (referenced in plan)

---

## Incident summary

Operador rodou um dev server para o projeto `dadaia-bots` e tentou registrá-lo via `dadaia server register`. Apesar de "ações drásticas" (re-execuções, registros manuais), o servidor nunca apareceu em `dadaia server list` nem no panel — somente o `portifolio` registrado por outro agente ficou visível. Investigação read-only identificou 3 bugs silenciosos no ciclo de vida do registry + lacuna estrutural (sem reconciliação de listeners não-registrados). Referente: backlog/candidates.md `2026-05-17T200000Z HIGH dev-server-registry`.

---

## Affected memory features

- `server-registry.html` — comportamento de discovery + sweep + grouping muda (orphan listeners agora detectáveis via `dadaia server scan` + panel "Unregistered" section).
- `panel.html` — Servers tab ganha seção "Unregistered listeners" com warning amarelo para bind `0.0.0.0` (LAN-exposed).

---

## Root cause

**Bug A — Resolver walks wrong direction (BLOCKER).** `_resolve_workspace()` em `dadaia_workspace/cli/commands/server.py:26-30` (e cópia em `cli/commands/panel.py:24-29`) anda para cima de `cwd` e retorna o primeiro diretório que contém um `.dadaia/`. Mas 4 sub-repos do workspace (`repos/dadaia-bots`, `repos/tauan-games`, `repos/dadaia-workspace`, `repos/workflow-tools`) têm seu próprio `.dadaia/` (sem `states/`). Cwd dentro de qualquer sub-repo → resolver retorna o sub-repo → `_guard_initialized` falha porque `.dadaia/states/spec_contexts.json` não existe → `WorkspaceNotInitializedError` exibida na stderr. Operador não notou no ruído de outros logs.

**Bug B — Corrupt-JSON cascade (HIGH).** `JsonServerRegistryStore._load()` (em `dadaia_workspace/infrastructure/json_server_registry_store.py:13-17`) chama `json.load(f)` sem try/except. `_from_dict(d)` exige 4 chaves obrigatórias sem fallback. Um único entry malformado em `server_registry.json` quebra `list_all()` inteiro → registry vira inacessível → `/api/servers` retorna `{"groups": []}` mesmo com entries válidas no disco.

**Bug C — Probe semantics confunde "morto" com "inacessível" (HIGH).** `OsProcessProbe.is_pid_alive` em `dadaia_workspace/core/protocols/process_probe.py:14-19` trata `PermissionError` igual a `ProcessLookupError` — ambos retornam `False`. PIDs root-owned (e.g. docker-proxy do portifolio-dev container) ficam marcados stale e são deletados pelo `_sweep()` na próxima chamada de `register()` por qualquer projeto.

**Gap estrutural D (MEDIUM).** Registry é push-only: agentes que sobem `python -m http.server` sem chamar `dadaia server register` produzem orphans invisíveis ao panel. Nenhum mecanismo de reconciliação existe — `dadaia server clean` só limpa entries stale registradas, não detecta listeners não-registrados.

---

## Fix scope

**PLAN.md:** Not required — fix scope cabe em 1 página neste SPEC. Cada bug fica em um arquivo dedicado; a unica decisão arquitetural (centralizar resolver) já está justificada acima.

### Mudanças

| Arquivo | Mudança | Bug |
|---|---|---|
| `dadaia_workspace/core/workspace_resolver.py` *(novo)* | `resolve_workspace_root(cwd: Path | None = None) -> Path` exigindo `.dadaia/states/spec_contexts.json` (não apenas `.dadaia/`). Sub-repos com `.dadaia/` parcial são ignorados. | A |
| `dadaia_workspace/cli/commands/server.py`, `panel.py` | Importar `resolve_workspace_root` em vez de definir `_resolve_workspace` local. Grep workspace inteiro para outras cópias. | A |
| `dadaia_workspace/infrastructure/json_server_registry_store.py` | `_load()` catch `JSONDecodeError` → log warning + return empty registry. `_from_dict()` catch `KeyError`/`TypeError`/`ValueError` per-entry → log + skip. Nunca raise. | B |
| `dadaia_workspace/core/protocols/process_probe.py` | `is_pid_alive`: `ProcessLookupError` → False, `PermissionError` → True (alive but unprobable), outros `OSError` → True + warning. | C |
| `dadaia_workspace/features/server_registry/scan.py` *(novo)* | `scan_unregistered_listeners(registry_entries)` — parsing `ss -tlnp` filtrado por uid, skip `<1024` e portas no registry. | D |
| `dadaia_workspace/cli/commands/server.py` | `dadaia server scan` subcomando (read-only; `--json` opcional; exit code 0 sempre). | D |
| `dadaia_workspace/core/models/server_registry.py` | `UnregisteredListener` dataclass append. | D |
| `dadaia_workspace/features/panel/service.py` | `list_unregistered_listeners()` que chama scan. | D (UI) |
| `dadaia_workspace/features/panel/views/api.py` | `/api/servers` payload extendido com chave `"unregistered": [...]` (backwards-compat). | D (UI) |
| `dadaia_workspace/features/panel/views/_assets.py` | PANEL_CSS + PANEL_HTML + PANEL_JS para nova seção "Unregistered" com badge `var(--color-alert)` para `lan_exposed: true`. | D (UI) |

Cobertura de testes nova: unit tests para cada arquivo novo + resilience tests para o store + probe tests para semântica `PermissionError`.

---

## Rollback plan

- Se a hotfix introduzir regressão na resolução de workspace: `git revert <merge-sha>` no main; usuários que tiverem o workspace inicializado corretamente não são afetados (mudança é backward-compat — `.dadaia/states/spec_contexts.json` existe nesses casos).
- Se o scan command der falsos positivos: `dadaia server scan` é read-only, não auto-mata nem auto-registra. Operador ignora a UI; nada se quebra.
- Painel "Unregistered" section é opt-out via tab navigation; clientes antigos que fazem `GET /api/servers` ignoram a chave extra `unregistered`.
- Para reverter parcialmente sem reverter tudo: cherry-revert individual commit (T-DSR-01..09 são commits separados por bug).

---

## Acceptance + smoke test

- [ ] **A1** — `cd repos/dadaia-bots && /home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia server list` não erra "Workspace not initialized"; lista o registry global da workspace root.
- [ ] **A2** — Corromper temporariamente `.dadaia/states/server_registry.json` com JSON inválido; `dadaia server list` mostra warning + entries válidas (não cresha).
- [ ] **A3** — Entry com PID root-owned (e.g. docker-proxy) permanece `active` em `dadaia server list` rodando como user não-root; `_sweep` não a deleta.
- [ ] **A4** — `dadaia server scan` lista um orphan controlado (criado via `python -m http.server 9999 --bind 127.0.0.1`) com port/pid/cmd/bind/lan_exposed=false.
- [ ] **A5** — Mesmo cenário com bind `0.0.0.0`: `dadaia server scan` retorna `lan_exposed: true`.
- [ ] **A6** — Panel Servers tab mostra seção "Unregistered listeners" com badge amarelo `var(--color-alert)` para o listener bind `0.0.0.0`.
- [ ] **A7** — `dadaia server register --port 9999 --project test --pid <pid>` move o listener da seção "Unregistered" para a tabela "Servers" no painel.
- [ ] **A8** — Pytest `tests/unit/core tests/unit/infrastructure tests/unit/features/server_registry tests/unit/features/panel` all green.
- [ ] **A9** — `dadaia specs doctor` retorna `[ok] 0 errors`.
- [ ] **A10** — `ruff format --check`, `ruff check`, `mypy --strict` all green.
- [ ] **A11** — `/api/servers` JSON retorna chave `"unregistered": [...]` adicional sem quebrar clientes antigos (forward-compat).
- [ ] **A12** — Acceptance report HTML + handoff sidecar `VALID` em `.dadaia/reports/`.

Evidence triples vão em CLOSURE.md `## Validations` após implementação.
