# Plan: Hotfix Release — v0.1.1

> **Status:** Aprovado
> **Release ID:** v0.1.1
> **Patches release:** dadaia-workspace-panel-v1
> **Owner:** product-engineer
> **Created:** 2026-05-17

---

## Why this PLAN exists despite the hotfix template defaulting to "PLAN.md not required"

The hotfix template declares `**PLAN.md:** Not required — fix is self-contained`. That default holds for single-file fixes (e.g. a typo, a regex, a one-line patch). **This hotfix exceeds that scope**: it spans 11 file modifications across 4 layers (core resolver, infrastructure store, probe protocol, scan feature, panel views) plus a new `dadaia server scan` CLI subcommand and a new panel UI section. Per the hotfix-track contract, a hotfix touching > 2 files or introducing an architectural decision must ship a PLAN.

The SPEC.md `## Fix scope` table already enumerates every file. This PLAN orders the work into 6 sequential phases with TDD discipline, calls out the only architectural decision (centralize the workspace resolver), and lists invariants to honour.

---

## Phases (sequential, one fresh `software-engineer` per phase except P5 which is `frontend-engineer`)

### P1 — Bug A: centralized workspace resolver (T-DSR-01, T-DSR-02)

1. Test-first: write `tests/unit/core/test_workspace_resolver.py` covering cwd in sub-repo, cwd at workspace root, cwd outside, cwd in partial workspace.
2. Implement `dadaia_workspace/core/workspace_resolver.py::resolve_workspace_root(cwd)` requiring `.dadaia/states/spec_contexts.json`.
3. Replace `_resolve_workspace` in `cli/commands/server.py:26-30` and `cli/commands/panel.py:24-29`. Grep for other copies.
4. Smoke: `cd repos/redacted-slug && dadaia server list` returns the workspace-root registry, not "not initialized".
5. Commit: `fix(core): T-DSR-01/02 — resolver requires .dadaia/states/ (centralized)`.

### P2 — Bug B: corrupt-JSON guard (T-DSR-03, T-DSR-04)

1. Test-first: write `tests/unit/infrastructure/test_json_server_registry_store_resilience.py` covering invalid JSON, missing-key entry, wrong-type entry, extra-key entry.
2. Harden `_load()` and `_from_dict()` in `infrastructure/json_server_registry_store.py` — try/except per-entry, log warnings, never raise.
3. Smoke: corrupt a copy of `server_registry.json`, run `dadaia server list` — does not crash; emits warning + valid entries.
4. Commit: `fix(store): T-DSR-03/04 — skip-and-log malformed entries (no cascade)`.

### P3 — Bug C: probe semantics (T-DSR-05, T-DSR-06)

1. Test-first: `tests/unit/core/test_process_probe.py` covering self-PID (alive), missing-PID (dead), PID 1 init (alive via PermissionError).
2. Rewrite `OsProcessProbe.is_pid_alive` in `core/protocols/process_probe.py`: `ProcessLookupError → False`, `PermissionError → True (alive but unprobable)`, other `OSError → True + warning`.
3. Smoke: registered entry with docker-proxy root PID stays `active` under non-root user.
4. Commit: `fix(probe): T-DSR-05/06 — PermissionError treated as alive`.

### P4 — Bug D: scan command (T-DSR-07, T-DSR-08)

1. Test-first: `tests/unit/features/server_registry/test_scan.py` with mocked `ss -tlnp` output.
2. Add `UnregisteredListener` dataclass to `core/models/server_registry.py`.
3. Create `features/server_registry/scan.py::scan_unregistered_listeners(registry_entries)`.
4. Add `dadaia server scan` subcommand to `cli/commands/server.py` with `--json` flag, exit code 0 always.
5. Smoke: `dadaia server scan` lists a controlled orphan (e.g. `python -m http.server 9999 --bind 127.0.0.1`).
6. Commit: `feat(server): T-DSR-07/08 — server scan command (orphan detection)`.

### P5 — Unregistered section UI (T-DSR-09)

1. Test-first: `tests/unit/features/panel/test_unregistered_section.py` snapshot test.
2. Add `list_unregistered_listeners()` to `features/panel/service.py`.
3. Extend `/api/servers` payload in `features/panel/views/api.py` with `"unregistered": [...]` (backwards-compat — clients ignoring unknown keys keep working).
4. Add CSS + HTML + JS to `features/panel/views/_assets.py`: `<section role="region" aria-label="Unregistered listeners">` with table + badge using `var(--color-alert)` for `lan_exposed: true`.
5. Smoke visual: `dadaia panel` shows the section; LAN-exposed orphan gets yellow badge.
6. Commit: `feat(panel): T-DSR-09 — Unregistered section with LAN-exposed warning`.

### P6 — Acceptance + PR (T-DSR-10)

1. `dadaia doctor` and `pytest tests/unit/core tests/unit/infrastructure tests/unit/features/server_registry tests/unit/features/panel -q` — all green.
2. Smoke end-to-end:
   a. Spawn `python -m http.server 9999 --bind 127.0.0.1 &`.
   b. `dadaia server scan` lists port 9999.
   c. Panel shows it in "Unregistered" section.
   d. `dadaia server register --port 9999 --project test --pid <pid>` moves it to Servers.
   e. `kill <pid>` marks the registered entry stale.
3. Emit acceptance report HTML + handoff sidecar in `.dadaia/reports/dadaia-workspace/product-engineer/`.
4. Validate with `dadaia reports validate`.
5. Commit: `chore(release): T-DSR-10 — v0.1.1 acceptance pass`.
6. Push, open PR: `gh pr create --base main --head hotfix/dev-server-registry-v0.1.1 --title "fix(server-registry,panel): v0.1.1 — resolver + corrupt-JSON + probe + scan + UI"`.

---

## Architectural decision (single one)

**Centralize the workspace resolver in `core/workspace_resolver.py`.** The two `_resolve_workspace` copies in `cli/commands/server.py:26-30` and `cli/commands/panel.py:24-29` drift independently and are part of why bug A persists. The fix consolidates them into one module + one contract (must find `.dadaia/states/spec_contexts.json`, not just `.dadaia/`). All CLI commands import this single function. Future commands inherit the correct behaviour by default.

---

## Invariants to honour

- Zero new Python deps (no additions to `pyproject.toml`).
- Zero new npm deps.
- Panel binding stays `127.0.0.1` (no remote exposure).
- `dadaia server scan` is **read-only** — never auto-kills, never auto-registers.
- T1 privacy allowlist (`dadaia_workspace/features/telemetry/reader/allowlist.py`) not affected — scan emits no `content`/`text`/`prompt`/`response` keys.
- The resolver change is **backward-compat**: workspaces already resolved correctly stay resolved; only sub-repos with partial `.dadaia/` get the corrected behaviour.
- All test files MUST be ≤300 lines (PLAN-line-count discipline).

---

## Out of scope (registered as follow-ups)

- Port range validation in `register()` (the out-of-range silent accept — cosmetic; doesn't cause invisibility).
- `dadaia server adopt --port N` interactive registration of detected orphans.
- Auto-cleanup of orphans on workspace shutdown (signal handler).
- Auto-export of `DADAIA_CONTEXT` for Claude sessions (cross-feature with the spec-context-isolation hotfix candidate already registered).
- Cross-host visibility (registry shared via mDNS/CRDT).
