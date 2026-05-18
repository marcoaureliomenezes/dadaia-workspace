# Closure: Hotfix Release — v0.1.1

> **Status:** Aprovado
> **Release ID:** v0.1.1
> **Patches release:** dadaia-workspace-panel-v1
> **Severity:** HIGH
> **Owner:** product-engineer
> **Closed:** 2026-05-17
> **Spec:** `specs/releases/v0.1.1/SPEC.md`
> **Tasks:** `specs/releases/v0.1.1/TASKS.md`

---

## Summary

Hotfix release `v0.1.1` (alias `dev-server-registry-hotfix-v1`) corrige três bugs
silenciosos no ciclo de vida do server registry e fecha uma lacuna estrutural
(observabilidade de listeners não-registrados). Origem documentada em
`specs/backlog/candidates.md § Hotfixes pendentes` com post-mortem read-only em
`.dadaia/reports/dadaia-workspace/software-engineer/2026-05-17T200000Z-dev-server-registry-rca.html`.

Cinco entregáveis atômicos:

1. **Resolver de workspace centralizado** — `dadaia_workspace/core/workspace_resolver.py`
   exige `.dadaia/states/spec_contexts.json` (não apenas `.dadaia/`), eliminando o
   walk-up que parava em sub-repos com projeção agentic. Substitui duas cópias locais
   (`cli/commands/server.py` e `cli/commands/panel.py`) por import único.
2. **Resilience do JSON store** — `JsonServerRegistryStore._load()` e `_from_dict()`
   ganham try/except per-entry com warning estruturado (`registry_entry_malformed`);
   um entry inválido não derruba mais o `list_all()` inteiro.
3. **Semântica correta do probe** — `OsProcessProbe.is_pid_alive` distingue
   `ProcessLookupError` (False) de `PermissionError` (True, "alive but unprobable").
   PIDs root-owned (e.g. docker-proxy de containers) deixam de ser auto-swept.
4. **Reconciliação `dadaia server scan`** — novo subcomando read-only + módulo
   `features/server_registry/scan.py` que faz parse de `ss -tlnp` filtrado por uid,
   detecta orphans (listeners sem entry no registry) e marca `lan_exposed` para
   binds `0.0.0.0`. Dataclass `UnregisteredListener` no core models.
5. **Painel "Unregistered listeners"** — nova seção no `Servers` tab via
   `PanelService.list_unregistered_listeners()` + extensão de `/api/servers` (chave
   `"unregistered"`, forward-compat) + UI com badge LAN-exposed `var(--color-alert)`.

Cobertura adicionada: 4 cenários de resilience do store, 3 cenários de probe semantics
(self/missing/root-PID), unit tests do scan com `ss` mockado, snapshot test do HTML
renderizado da nova seção. Rollback por cherry-revert (T-DSR-01..09 são commits
isolados por bug).

10 tasks executadas serialmente em 6 waves (T-DSR-01..10) por `software-engineer-p1..p4`,
`frontend-engineer-p5` (T-DSR-09 UI), e `product-engineer claude-main-p6` (T-DSR-10
acceptance).

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-DSR-01 | Centralized workspace resolver (core module + tests) | `f8d8c6c` |
| T-DSR-02 | Substituir `_resolve_workspace` duplicates por import | `f8d8c6c` |
| T-DSR-03 | Skip-and-log JSON store resilience | `859764b` |
| T-DSR-04 | Tests for store resilience | `859764b` |
| T-DSR-05 | Probe permission semantics fix | `5aa08aa` |
| T-DSR-06 | Tests for probe semantics | `5aa08aa` |
| T-DSR-07 | Scan command core logic + `UnregisteredListener` dataclass | `3ba7610` |
| T-DSR-08 | `dadaia server scan` CLI subcommand | `3ba7610` |
| T-DSR-09 | Panel "Unregistered" section UI | `d29e82c` |
| T-DSR-10 | Acceptance + PR | `aae2e5a` |

---

## Drifts

### Drift #1 — Bug fixes paired into composite commits

**Description:** PLAN/TASKS sugerem 10 tasks com 10 commits separados (cherry-revert
granular). Em execução, tasks foram combinadas em 5 commits compostos por bug:
T-DSR-01+02 em `f8d8c6c` (resolver + import substitution), T-DSR-03+04 em `859764b`
(store fix + tests), T-DSR-05+06 em `5aa08aa` (probe + tests), T-DSR-07+08 em
`3ba7610` (scan core + CLI), T-DSR-09 isolado em `d29e82c`. Comum em hotfix —
fix+test no mesmo commit é prática padrão.

**Resolution:** Granularidade de revert preservada por bug (Bug A → `f8d8c6c`, Bug B →
`859764b`, Bug C → `5aa08aa`, Gap D core → `3ba7610`, Gap D UI → `d29e82c`). Cinco
pontos de revert atendem o rollback plan do SPEC sem perda funcional.

**Memory updates:** nenhuma (drift puramente de execução).

### Drift #2 — Hotfix promoted from backlog before formal SDD hotfix-track release

**Description:** Hotfix v0.1.1 foi aberto em 2026-05-17 antes da release
`sdd-hotfix-track-v1` ter pousado como referência canônica. A spec usou
o template adhoc deste hotfix; após `sdd-hotfix-track-v1` consolidar o template
`release_hotfix.md.j2`, releases futuras seguirão o template canonical.

**Resolution:** SPEC do hotfix v0.1.1 já contém todas as 6 seções mandatórias
(Incident summary, Affected memory, Root cause, Fix scope, Rollback plan, Acceptance);
o conteúdo é forward-compat com o template canonical. Próximo hotfix usará
`release_hotfix.md.j2` literalmente.

**Memory updates:** documentado em `sdd-hotfix-track.html` (já presente no catálogo).

---

## Validations

Evidence triples para os 12 critérios de SPEC § Acceptance + smoke test.

| # | Description | Command | Evidence |
|---|-------------|---------|----------|
| A1 | `cd repos/redacted-slug && dadaia server list` retorna registry global | `cd repos/redacted-slug && /home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia server list` | Lista entries globais; sem `WorkspaceNotInitializedError`. Coberto pelo commit `f8d8c6c` (resolver fix). |
| A2 | Registry com JSON inválido → warning + entries válidas | `pytest tests/unit/infrastructure/test_json_server_registry_store_resilience.py -q` | Commit `859764b`: 4 cenários verdes (invalid JSON, missing key, wrong type, unknown extra key). |
| A3 | Entry root-owned (docker-proxy) permanece `active` em `server list` | `pytest tests/unit/core/test_process_probe.py -q` | Commit `5aa08aa`: 3 cenários verdes (self alive, missing dead, PID 1 init alive via PermissionError). |
| A4 | `dadaia server scan` lista orphan bind 127.0.0.1 | `python -m http.server 9999 --bind 127.0.0.1 &; dadaia server scan` | Smoke registrado em report acceptance `T-DSR-10` (commit `aae2e5a`). Orphan listado com `lan_exposed=false`. |
| A5 | Orphan bind `0.0.0.0` retorna `lan_exposed: true` | `python -m http.server 9999 --bind 0.0.0.0 &; dadaia server scan` | Smoke registrado em report acceptance `T-DSR-10`. Badge LAN-exposed acionado. |
| A6 | Panel Servers tab mostra seção "Unregistered" com badge amarelo | `dadaia panel` + smoke visual com orphan ativo | Commit `d29e82c`: seção `role="region"` aria-label="Unregistered listeners" + badge `var(--color-alert)`. |
| A7 | `dadaia server register --port 9999` move orphan para Servers | `dadaia server register --port 9999 --project test --pid <pid>; refetch /api/servers` | Smoke acceptance `T-DSR-10`; listener desaparece de `unregistered[]` e aparece em `groups[*].entries[]`. |
| A8 | Pytest target paths green | `pytest tests/unit/core tests/unit/infrastructure tests/unit/features/server_registry tests/unit/features/panel -q` | Commit `aae2e5a` acceptance pass; suite green. |
| A9 | `dadaia specs doctor` 0 errors | `/home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia specs doctor --specs-dir specs` | `[ok] /home/marco/workspace/dadaia/repos/dadaia-workspace/specs — 0 errors, 0 warnings.` (pre-PR3 baseline). |
| A10 | `ruff format --check`, `ruff check`, `mypy --strict` green | `ruff format --check . && ruff check . && mypy --strict dadaia_workspace/` | Commit `aae2e5a` acceptance pass; all green. |
| A11 | `/api/servers` JSON contém `"unregistered": [...]` sem quebrar clientes antigos | `curl -s http://127.0.0.1:4999/api/servers \| jq '.unregistered \| type'` | Commit `d29e82c`: chave `unregistered` adicionada como extensão; clientes que ignoram chaves desconhecidas continuam funcionando. |
| A12 | Acceptance report HTML + handoff sidecar `VALID` | `dadaia reports validate .dadaia/reports/dadaia-workspace/product-engineer/<ts>-dev-server-registry-hotfix-acceptance.handoff.json` | Commit `aae2e5a`: handoff sidecar emitido pelo skill `dadaia-handoff-emitter`; validator exit 0. |

---

## Memory updates

- `specs/memory/product/server-registry.html` — **updated**: Estado runtime tocado
  documenta agora (a) que o sweep distingue `PermissionError` de `ProcessLookupError`
  (root-owned PIDs preservados), (b) que o store é resiliente a entries malformados
  (skip-and-log), e (c) que a feature ganhou a CLI `dadaia server scan` (read-only,
  detecção de orphans via `ss -tlnp`). Catálogo de portas continua sendo
  `.dadaia/states/server_registry.json`.
- `specs/memory/product/panel.html` — **updated**: Servers tab agora expõe seção
  "Unregistered listeners" com badge `var(--color-alert)` para `lan_exposed: true`.
  `/api/servers` payload extendido com chave `"unregistered"` (forward-compat).
- `specs/memory/product/index.html` — **no change**: catálogo já lista `server-registry`
  e `panel`; ordem inalterada (relevância no dia-a-dia do operador idêntica).
- `specs/memory/architecture.html` — **no change**: hotfix corrige defeitos em módulos
  existentes; nenhum novo módulo nem mudança de layer-rules.
- `specs/memory/tech-stack.html` — **no change**: zero novas dependências (stdlib
  apenas — `subprocess` para `ss`, `pathlib`, `dataclasses`).

---

## Backlog returns

Nenhum item promovido — hotfix endereçou exatamente o item `dev-server-registry`
do `## Hotfixes pendentes` (sera movido a `## Histórico` na finalização do CLOSURE).

Backlog atualizado:

- `backlog/candidates.md § Histórico` ← `dev-server-registry → release v0.1.1`
  (promovido 2026-05-17; SPEC em `_archive/releases/v0.1.1/SPEC.md`).

---

## Archive decision

**MOVE** — directory `specs/releases/v0.1.1/` é relocado para
`specs/_archive/releases/v0.1.1/` via `git mv` após este CLOSURE.md, as atualizações
de memory pousarem, e o backlog ser atualizado. Post-archive, `specs/releases/ACTIVE.md`
é re-apontado para a próxima release (`agent-monitoring-v1 / CLOSURE` em sequência).
