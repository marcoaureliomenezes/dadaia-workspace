# Tasks: Release — dadaia-workspace-panel-v1

> **Status:** Em revisão
> **Release ID:** dadaia-workspace-panel-v1
> **Owner:** product-engineer (CLOSURE tasks); software-engineer + qa-engineer (implementation + E2E)
> **SPEC:** `specs/releases/dadaia-workspace-panel-v1/SPEC.md`
> **PLAN:** `specs/releases/dadaia-workspace-panel-v1/PLAN.md`

---

## Convenções

| Marker | Estado |
|---|---|
| `[ ]` | OPEN |
| `[-]` | IN PROGRESS |
| `[x]` | DONE |

- Only one `[-]` at a time per `TASKS.md` (`dadaia-task-manager` invariant).
- `[parallel: yes/no]` flags whether the task may run concurrently with another `[-]`
  task of the same phase in a separate session (disjoint write-sets).
- ID naming: `T-<phase>.<seq>`.
- Implementation only starts after `SPEC.md` AND `PLAN.md` reach `**Status:** Aprovado`
  AND `specs/releases/ACTIVE.md` flips to this release (after `agent-sdd-alignment-v1`
  reaches CLOSURE).

---

## Phase 1 — PanelService + container wiring

- [ ] T-1.1 `[parallel: no]` Create `dadaia_workspace/features/panel/__init__.py` and `dadaia_workspace/features/panel/service.py` with `PanelService` class. Constructor takes `ServerRegistryService` and `SpecContextService` (DI). Exposes `list_servers_grouped()` returning a `list[ServerGroup]` dataclass (group_label, context_name_or_None, rows) and `list_active_contexts()` returning a `list[PanelContext]` dataclass (slug, name, repo_path, branch, is_primary). Dataclasses live in `service.py`. **Files:** `dadaia_workspace/features/panel/__init__.py`, `dadaia_workspace/features/panel/service.py`. **Owner:** software-engineer. **Acceptance:** module imports clean; `ruff check`, `mypy --strict` green.

- [ ] T-1.2 `[parallel: no]` Implement best-effort grouping in `PanelService.list_servers_grouped()`: `project.lower() == repo_slug.lower()` against active contexts (D1.A from architect report). Unmatched entries fall under group `"Outros"`. Active-only filter (state == `ativo`) on contexts before matching. **Files:** `dadaia_workspace/features/panel/service.py`. **Owner:** software-engineer. **Acceptance:** unit test T-1.4 green for both matched and unmatched cases.

- [ ] T-1.3 `[parallel: no]` Add `build_panel_service(workspace_root: Path) -> PanelService` to `dadaia_workspace/container.py`. Composes `build_server_registry_service(workspace_root)` and `build_spec_context_service(workspace_root)` and injects both. **Files:** `dadaia_workspace/container.py`. **Owner:** software-engineer. **Acceptance:** factory callable from CLI command; existing container tests still green.

- [ ] T-1.4 `[parallel: yes]` Add unit tests for `PanelService` in `tests/unit/features/panel/test_service.py`: (a) best-effort matcher casing — `project="DadaiA-WorkSpace"` matches `repo_slug="dadaia-workspace"`; (b) unmatched falls into `"Outros"`; (c) `inativo` contexts filtered out; (d) empty registry returns empty groups list; (e) no active context returns empty contexts list. **Files:** `tests/unit/features/panel/test_service.py`. **Owner:** software-engineer. **Acceptance:** 5 tests green; coverage for `service.py` ≥ 80%.

---

## Phase 2 — HTTP layer + handler dispatch

- [ ] T-2.1 `[parallel: yes]` Create `dadaia_workspace/features/panel/server.py` exposing `build_panel_http_server(host, port, handler_factory) -> ThreadingHTTPServer` and `serve_blocking(server)` that installs SIGINT/SIGTERM handlers calling `server.shutdown()` from a daemon thread (stdlib idiom) so Ctrl+C frees the port within 2s. **Files:** `dadaia_workspace/features/panel/server.py`. **Owner:** software-engineer. **Acceptance:** server can be constructed in a test, started in a thread, `serve_blocking` shuts down clean on SIGINT; coverage ≥ 80%.

- [ ] T-2.2 `[parallel: yes]` Create `dadaia_workspace/features/panel/handler.py` with `PanelHandler(BaseHTTPRequestHandler)`. Carries the compiled regex `ROUTES` table (architect D3) — pure URL→view dispatch, ≤ 80 lines including imports. Each handler reads `self.path`, walks the route table, calls the matching view function with named groups, writes status + content-type + body. No rendering logic inside this file. **Files:** `dadaia_workspace/features/panel/handler.py`. **Owner:** software-engineer. **Acceptance:** handler instantiable; `ruff check` line-count check stays ≤ 100 lines.

- [ ] T-2.3 `[parallel: no]` Implement 404 fall-through in `PanelHandler` for unmatched paths: return HTTP 404 with a minimal HTML body whose copy follows the constitution's error contract (capability + context + next step) — e.g. `"Route not found. The panel exposes / /api/servers /api/contexts /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>. Open / for the index."`. **Files:** `dadaia_workspace/features/panel/handler.py`. **Owner:** software-engineer. **Acceptance:** integration test T-2.4 covers the 404 path.

- [ ] T-2.4 `[parallel: yes]` Add integration test `tests/integration/features/panel/test_http.py`: spin a `ThreadingHTTPServer` on an ephemeral port using the real `PanelService` wired against fake stores. Hit `/`, `/api/servers`, `/api/contexts`, `/memory/<slug>/architecture.html`, `/memory-view/<slug>/architecture.html`, `/unknown` via `urllib.request`. Assert status, content-type, and byte-identity against `tests/fixtures/memory/architecture.html`. **Files:** `tests/integration/features/panel/test_http.py`, `tests/fixtures/memory/architecture.html`. **Owner:** software-engineer. **Acceptance:** 6 routes asserted; integration suite green; teardown shuts the server within 2s.

---

## Phase 3 — View modules + frontend assets

- [ ] T-3.1 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/__init__.py` and `dadaia_workspace/features/panel/views/index.py` with `render_index(service: PanelService) -> bytes` returning the full panel HTML (3 sections: Servers active + Memories + Agents placeholder card with copy "Em breve — Release-2"). Inline JS link to `/static/panel.js`; inline CSS link to `/static/panel.css`. Module ≤ 100 lines. Primary context appears **first-position in the auto-fill grid** (resolution to frontend Q-2). **Files:** `dadaia_workspace/features/panel/views/__init__.py`, `dadaia_workspace/features/panel/views/index.py`. **Owner:** software-engineer. **Acceptance:** unit test T-3.8 green; rendered HTML contains the 3 section headers and the placeholder card copy verbatim.

- [ ] T-3.2 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/api.py` exposing `api_servers(service) -> bytes` (JSON of grouped servers — same shape as `PanelService.list_servers_grouped()` flattened to JSON-ready dicts) and `api_contexts(service) -> bytes` (JSON of active contexts). Each writes content-type `application/json; charset=utf-8`. Module ≤ 100 lines. **Files:** `dadaia_workspace/features/panel/views/api.py`. **Owner:** software-engineer. **Acceptance:** unit test T-3.9 green; JSON parses; field names stable.

- [ ] T-3.3 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/memory.py` with `serve_memory(workspace_root, slug, path) -> tuple[bytes, str]` returning `(file.read_bytes(), content_type)`. Content-type sniffed by extension only (`.html` → `text/html; charset=utf-8`, `.png` → `image/png`, `.svg` → `image/svg+xml`, fallback `application/octet-stream`). No template, no head injection, no body mutation. Module docstring explicitly names SPEC-DOC-008 + NFR-2 + architect's R3 (layer-bypass exception is intentional). Path traversal guard: reject any normalized path that escapes `repos/<slug>/specs/`. **Files:** `dadaia_workspace/features/panel/views/memory.py`. **Owner:** software-engineer. **Acceptance:** byte-identity canary test T-3.5 green; traversal guard test included; coverage ≥ 80%.

- [ ] T-3.4 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/wrapper.py` with `render_memory_wrapper(slug, file) -> bytes`. Returns a small HTML document: 40px top bar (`position: fixed`) with `← Voltar ao Painel` linking to `/`, plus `<iframe src="/memory/<slug>/<file>" sandbox="allow-scripts allow-same-origin">` sized to `width: 100vw; height: calc(100vh - 40px); border: 0;`. Module ≤ 100 lines. **Files:** `dadaia_workspace/features/panel/views/wrapper.py`. **Owner:** software-engineer. **Acceptance:** unit test T-3.10 green; output contains both back-bar and iframe with correct src.

- [ ] T-3.5 `[parallel: yes]` **BYTE-IDENTITY CANARY TEST** — add `tests/unit/features/panel/test_views_memory.py` with `test_serve_memory_byte_identity`: read fixture `tests/fixtures/memory/architecture.html` raw; call `serve_memory(workspace_root, slug, "architecture.html")`; assert returned bytes are **exactly equal** to `Path.read_bytes()` of the fixture. Test docstring explicitly names `SPEC-DOC-008` and `NFR-2`. Also test the traversal guard rejects `../../etc/passwd`. **Files:** `tests/unit/features/panel/test_views_memory.py`, `tests/fixtures/memory/architecture.html`. **Owner:** software-engineer. **Acceptance:** test green; fails fast if anyone ever adds string mutation to `views/memory.py`.

- [ ] T-3.6 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/static.py` with `serve_static(name) -> tuple[bytes, str]` reading `dadaia_workspace/features/panel/assets/<name>` and returning bytes + content-type (`text/css` or `application/javascript`). Reject any `name` containing `/` or `..`. **Files:** `dadaia_workspace/features/panel/views/static.py`. **Owner:** software-engineer. **Acceptance:** unit test green; traversal guard tested.

- [ ] T-3.7 `[parallel: yes]` Create `dadaia_workspace/features/panel/assets/panel.css` with the token block from PLAN.md `Visual contract` baked in as CSS custom properties. Copy structural rules from the mockup files (`index.html`, `memories.html`, `memory-view.html`) verbatim — grid layout for memory cards, table layout for servers, left-border accent + `#f0faff` tinted bg for primary card, status pill colors, hover row. **Body-text links MUST use `var(--color-accent-dark)` = `#2d7d9a`** (resolution to frontend Q-1); `#7ec8e3` is decorative accent only. **Files:** `dadaia_workspace/features/panel/assets/panel.css`. **Owner:** software-engineer (copy from mockup, do not invent). **Acceptance:** visual diff against the 3 mockup files is "same visual feel" — colors, spacing, typography identical.

- [ ] T-3.8 `[parallel: yes]` Create `dadaia_workspace/features/panel/assets/panel.js` (~30 lines): `setInterval(fetchServers, 5000)` where `fetchServers` does `fetch('/api/servers')`, parses JSON, swaps the `tbody` of each grouped table without full-page reload (frontend D-8). Tab switching between Servers / Memories / Agents toggles `aria-selected` + `hidden` on sections — no router. **TTL rendering helper**: client-side formats the registry's expiry timestamp into relative duration like `"6h 42m"` (resolution to frontend Q-4). **Files:** `dadaia_workspace/features/panel/assets/panel.js`. **Owner:** software-engineer. **Acceptance:** mockup `index.html` JS snippet is the reference; tab toggle works; status dot pulses on fetch.

- [ ] T-3.9 `[parallel: yes]` Add unit tests `tests/unit/features/panel/test_views_index.py` and `test_views_api.py`: index contains 3 section headers, placeholder card copy, primary-context first; api JSON has stable field names. **Files:** `tests/unit/features/panel/test_views_index.py`, `tests/unit/features/panel/test_views_api.py`. **Owner:** software-engineer. **Acceptance:** all tests green.

- [ ] T-3.10 `[parallel: yes]` Add unit test `tests/unit/features/panel/test_views_wrapper.py`: wrapper contains back-bar text "← Voltar ao Painel", href `/`, and iframe `src="/memory/<slug>/<file>"`. **Files:** `tests/unit/features/panel/test_views_wrapper.py`. **Owner:** software-engineer. **Acceptance:** test green.

---

## Phase 4 — CLI command + dashboard deprecation + bind fix

- [ ] T-4.1 `[parallel: no]` Create `dadaia_workspace/cli/commands/panel.py` with `dadaia panel [--port 4999] [--no-open] [--bind 127.0.0.1]`. `--bind` validates against `{"127.0.0.1"}` only — any other value exits with `"Release-1 supports loopback bind only"`. Builds `PanelService` from container, instantiates `ThreadingHTTPServer`, prints `Panel running at http://127.0.0.1:<port>/`, calls `webbrowser.open()` unless `--no-open`, then blocks via `serve_blocking()`. Catches `OSError` (port in use) and exits with constitution-compliant error message naming `lsof -i :<port>`. **Files:** `dadaia_workspace/cli/commands/panel.py`. **Owner:** software-engineer. **Acceptance:** command callable; `--help` lists all 3 flags; integration test T-4.4 green.

- [ ] T-4.2 `[parallel: yes]` Register `panel` subcommand in `dadaia_workspace/cli/main.py` so `dadaia panel` resolves. **Files:** `dadaia_workspace/cli/main.py`. **Owner:** software-engineer. **Acceptance:** `dadaia --help` lists `panel`; `dadaia panel --help` works.

- [ ] T-4.3 `[parallel: no]` Patch `dadaia_workspace/cli/commands/server.py::dashboard()`: (a) emit deprecation warning to stderr verbatim: `"[deprecation] 'dadaia server dashboard' will be removed in a future release. Use 'dadaia panel' instead."`; (b) bind `127.0.0.1` instead of stdlib default `0.0.0.0` (FR-7 security fix — in-scope per Q7 grill resolution); (c) switch the internal `HTTPServer` to `ThreadingHTTPServer` for consistency with the panel (architect R5); (d) update Typer docstring + `--help` to flag deprecation. **Files:** `dadaia_workspace/cli/commands/server.py`, possibly `dadaia_workspace/features/server_registry/dashboard.py`. **Owner:** software-engineer. **Acceptance:** dashboard still serves the legacy page; stderr contains the deprecation line; `nc -z <LAN-ip> <port>` fails after fix.

- [ ] T-4.4 `[parallel: yes]` Integration test `tests/integration/cli/test_panel_command.py`: spawn `dadaia panel --no-open --port <ephemeral>` as a subprocess via `subprocess.Popen`; wait for "Panel running at" line on stdout; send SIGINT; assert exit 0 within 2s; assert port is free via socket bind. **Files:** `tests/integration/cli/test_panel_command.py`. **Owner:** software-engineer. **Acceptance:** test green; no orphan process.

---

## Phase 5 — E2E (qa-engineer)

- [ ] T-5.1 `[parallel: yes]` E2E test `tests/e2e/features/test_panel.py::test_panel_renders_all_sections`: spawn `dadaia panel --no-open --port <ephemeral>`; use `urllib` to fetch `/`, assert 3 section markers in HTML; fetch `/api/servers` and `/api/contexts`, assert JSON parses; SIGINT teardown. **Files:** `tests/e2e/features/test_panel.py`. **Owner:** qa-engineer. **Acceptance:** test green.

- [ ] T-5.2 `[parallel: yes]` E2E test `test_panel_bind_loopback_only`: spawn panel on ephemeral port; assert `nc -z 127.0.0.1 <port>` returns 0; assert `nc -z <non-loopback-ip> <port>` returns non-zero. Skip the non-loopback assertion if no non-loopback IP available (CI). **Files:** `tests/e2e/features/test_panel.py`. **Owner:** qa-engineer. **Acceptance:** test green; AC-3 satisfied.

- [ ] T-5.3 `[parallel: yes]` E2E test `test_memory_view_iframe_loads`: fetch `/memory-view/dadaia-workspace/architecture.html`, assert response contains `<iframe src="/memory/dadaia-workspace/architecture.html"`; fetch `/memory/dadaia-workspace/architecture.html` and assert bytes match `repos/dadaia-workspace/specs/memory/architecture.html` on disk (AC-10 / NFR-2 end-to-end canary). **Files:** `tests/e2e/features/test_panel.py`. **Owner:** qa-engineer. **Acceptance:** test green; byte-identity holds across the full HTTP path.

- [ ] T-5.4 `[parallel: yes]` E2E test `test_dashboard_deprecation_warning_visible`: spawn `dadaia server dashboard --port <ephemeral>` as a subprocess, capture stderr, assert it contains `[deprecation]` line per FR-6. Tear down. **Files:** `tests/e2e/features/test_panel.py`. **Owner:** qa-engineer. **Acceptance:** test green; AC-6 satisfied.

- [ ] T-5.5 `[parallel: yes]` E2E test `test_panel_clean_shutdown_within_2s`: spawn panel, send SIGINT, assert `process.wait(timeout=2)` exits 0, assert socket bind to same port succeeds immediately after (NFR-4 / AC-9). **Files:** `tests/e2e/features/test_panel.py`. **Owner:** qa-engineer. **Acceptance:** test green.

---

## Phase 6 — CLOSURE prep (DO NOT EXECUTE NOW — queued for CLOSURE phase)

Per the release lifecycle, these tasks run only after Phases 1–5 are all `[x]` and the
release transitions to `phase: CLOSURE`. They are owned by `product-engineer` because
they touch `specs/memory/` (gate v3 allows memory writes only during CLOSURE).

- [ ] T-6.1 `[parallel: no]` Update `specs/memory/product/index.html` adding a "Panel" feature link pointing at the new `panel.html` (T-6.2). **Files:** `specs/memory/product/index.html`. **Owner:** product-engineer (CLOSURE). **Acceptance:** doctor green; new link renders.

- [ ] T-6.2 `[parallel: no]` Create `specs/memory/product/panel.html` describing the Panel feature for memory atomicity (one self-contained HTML, inline CSS, same tokens as other product memories). **Files:** `specs/memory/product/panel.html`. **Owner:** product-engineer (CLOSURE). **Acceptance:** `dadaia specs doctor` reports `0 errors` including SPEC-DOC-008 atomicity for the new file.

- [ ] T-6.3 `[parallel: no]` Write `specs/releases/dadaia-workspace-panel-v1/CLOSURE.md` with the 4 mandatory sections (Resumo / Evidências / Drifts / Próximos passos) and evidence triples for each AC-1…AC-11 (command + expected + actual output). **Files:** `specs/releases/dadaia-workspace-panel-v1/CLOSURE.md`. **Owner:** product-engineer (CLOSURE). **Acceptance:** every AC has a verifiable evidence triple; CLOSURE.md status reaches `Aprovado`.

- [ ] T-6.4 `[parallel: yes]` Add Release-2 candidate entry to `specs/backlog/candidates.md`: `- dadaia-workspace-panel-r2-agents — Surface installed agents and multi-agent workflows in the panel (owner: product-engineer, contexto: releases/dadaia-workspace-panel-v1/SPEC.md)`. **Files:** `specs/backlog/candidates.md`. **Owner:** product-engineer (CLOSURE). **Acceptance:** doctor `_check_backlog_schema` (SPEC-DOC-012) green; AC-11 satisfied.

- [ ] T-6.5 `[parallel: no]` Move release dir to `specs/_archive/releases/dadaia-workspace-panel-v1/` after CLOSURE is signed. Flip `specs/releases/ACTIVE.md` to next release or to the lifecycle-defined idle state. **Files:** `specs/releases/dadaia-workspace-panel-v1/` → `specs/_archive/releases/dadaia-workspace-panel-v1/`, `specs/releases/ACTIVE.md`. **Owner:** product-engineer (CLOSURE). **Acceptance:** doctor green; no stale ACTIVE.md pointer.

---

## Cross-phase gates

Before any commit on this release:

1. `pytest tests/ -x` — green.
2. `ruff format --check && ruff check && mypy --strict` — clean.
3. `dadaia specs doctor` — `0 errors`; warnings must not regress from baseline `0 errors, 0 warnings`.
4. Task marker is `[-]` for the task being worked, single `[-]` per `TASKS.md`.

Closing commit pattern (per `dadaia-task-manager`):

```
chore(tasks): start T-<id>      # before the work
feat(panel): <summary> (T-<id>) # after the work, includes [x] marker flip
```
