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

- [ ] T-1.1 `[parallel: no]` Create `dadaia_workspace/features/panel/__init__.py` and `dadaia_workspace/features/panel/service.py` with `PanelService` class. Constructor takes `ServerRegistryService` and `SpecContextService` (DI). Exposes `list_servers_grouped()` returning a `list[ServerGroup]` dataclass (group_label, context_name_or_None, rows) and `list_active_contexts()` returning a `list[PanelContext]` dataclass (slug, name, repo_path, branch, is_primary). Dataclasses live in `service.py`. **Files:** `dadaia_workspace/features/panel/__init__.py`, `dadaia_workspace/features/panel/service.py`. **Owner:** software-engineer. **Acceptance:** module imports clean; `ruff check`, `mypy --strict` green. **R4 (branch freshness):** `list_active_contexts()` returns the `current_branch` field exactly as exposed by `SpecContextService` (cached at last `dadaia context activate/show` invocation). It does NOT invoke `git rev-parse` or any other git subprocess per request. `PanelContext.branch` is `str | None`; rendering displays `"(unknown)"` when `None`. This trade-off (potential staleness vs. per-request subprocess cost across 8 contexts every 5s) is documented in PLAN risks (R4).

- [ ] T-1.2 `[parallel: no]` Implement best-effort grouping in `PanelService.list_servers_grouped()`: `project.lower() == repo_slug.lower()` against active contexts (D1.A from architect report). Unmatched entries fall under group `"Outros"`. Active-only filter (state == `ativo`) on contexts before matching. **Files:** `dadaia_workspace/features/panel/service.py`. **Owner:** software-engineer. **Acceptance:** unit test T-1.4 green for both matched and unmatched cases.

- [ ] T-1.3 `[parallel: no]` Add `build_panel_service(workspace_root: Path) -> PanelService` to `dadaia_workspace/container.py`. Composes `build_server_registry_service(workspace_root)` and `build_spec_context_service(workspace_root)` and injects both. **Files:** `dadaia_workspace/container.py`. **Owner:** software-engineer. **Acceptance:** factory callable from CLI command; existing container tests still green.

- [ ] T-1.4 `[parallel: yes]` Add unit tests for `PanelService` in `tests/unit/features/panel/test_service.py`: (a) best-effort matcher casing — `project="DadaiA-WorkSpace"` matches `repo_slug="dadaia-workspace"`; (b) unmatched falls into `"Outros"`; (c) `inativo` contexts filtered out; (d) empty registry returns empty groups list; (e) no active context returns empty contexts list. **Files:** `tests/unit/features/panel/test_service.py`. **Owner:** software-engineer. **Acceptance:** 5 tests green; coverage for `service.py` ≥ 80%.

---

## Phase 2 — HTTP layer + handler dispatch

- [ ] T-2.1 `[parallel: yes]` Create `dadaia_workspace/features/panel/server.py` exposing `build_panel_http_server(host, port, handler_factory) -> ThreadingHTTPServer` and `serve_blocking(server)` that installs SIGINT/SIGTERM handlers calling `server.shutdown()` from a daemon thread (stdlib idiom) so Ctrl+C frees the port within 2s. **Files:** `dadaia_workspace/features/panel/server.py`. **Owner:** software-engineer. **Acceptance:** server can be constructed in a test, started in a thread, `serve_blocking` shuts down clean on SIGINT; coverage ≥ 80%. **R2 (signal handler deadlock pattern — locked):** (a) SIGINT and SIGTERM handlers MUST spawn a daemon thread that calls `server.shutdown()`; the handler frame itself MUST NOT call `shutdown()` directly (would deadlock the serving loop against the signal frame); (b) `signal.signal(...)` is installed ONLY when `serve_blocking()` runs on the main thread (Typer CLI command path) — integration tests use `serve_forever()` in a background thread and never install signal handlers; (c) clean shutdown completes within 2s (matches T-5.5 / NFR-4 / AC-9 acceptance).

- [ ] T-2.2 `[parallel: yes]` Create `dadaia_workspace/features/panel/handler.py` with `PanelHandler(BaseHTTPRequestHandler)`. Carries the compiled regex `ROUTES` table (architect D3) — pure URL→view dispatch, ≤ 80 lines including imports. Each handler reads `self.path`, walks the route table, calls the matching view function with named groups, writes status + content-type + body. No rendering logic inside this file. **Files:** `dadaia_workspace/features/panel/handler.py`. **Owner:** software-engineer. **Acceptance:** handler instantiable; `ruff check` line-count check stays ≤ 100 lines.

- [ ] T-2.3 `[parallel: no]` Implement 404 fall-through in `PanelHandler` for unmatched paths: return HTTP 404 with a minimal HTML body whose copy follows the constitution's error contract (capability + context + next step) — e.g. `"Route not found. The panel exposes / /api/servers /api/contexts /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>. Open / for the index."`. **Files:** `dadaia_workspace/features/panel/handler.py`. **Owner:** software-engineer. **Acceptance:** integration test T-2.4 covers the 404 path.

- [ ] T-2.4 `[parallel: yes]` Add integration test `tests/integration/features/panel/test_http.py`: spin a `ThreadingHTTPServer` on an ephemeral port using the real `PanelService` wired against fake stores. Hit `/`, `/api/servers`, `/api/contexts`, `/memory/<slug>/architecture.html`, `/memory-view/<slug>/architecture.html`, `/unknown` via `urllib.request`. Assert status, content-type, and byte-identity against `tests/fixtures/memory/architecture.html`. **Files:** `tests/integration/features/panel/test_http.py`, `tests/fixtures/memory/architecture.html`. **Owner:** software-engineer. **Acceptance:** 6 routes asserted; integration suite green; teardown shuts the server within 2s. **R2 (signal handler discipline):** test MUST start `ThreadingHTTPServer.serve_forever()` directly in a background thread; MUST NOT call `serve_blocking()` nor install any `signal.signal(...)` handlers (would conflict with pytest's own signal handling and would raise `ValueError: signal only works in main thread`); teardown calls `server.shutdown()` directly from the test thread.

---

## Phase 3 — View modules + frontend assets

- [ ] T-3.1 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/__init__.py` and `dadaia_workspace/features/panel/views/index.py` with `render_index(service: PanelService) -> bytes` returning the full panel HTML (3 sections: Servers active + Memories + Agents placeholder card with copy "Em breve — Release-2"). Inline JS link to `/static/panel.js`; inline CSS link to `/static/panel.css`. Module ≤ 100 lines. Primary context appears **first-position in the auto-fill grid** (resolution to frontend Q-2). **Files:** `dadaia_workspace/features/panel/views/__init__.py`, `dadaia_workspace/features/panel/views/index.py`. **Owner:** software-engineer. **Acceptance:** unit test T-3.9 green; rendered HTML contains the 3 section headers and the placeholder card copy verbatim. **R3-A (XSS / OWASP A03):** all operator-controlled strings — server `project`, `url`, `description` from `server_registry.json`; context `name`, `repo_slug`, `branch` from `spec_contexts.json` — are passed through `html.escape()` (stdlib) before insertion into the HTML template. Unit test covers a fixture with `<script>alert(1)</script>` in a `project` field and asserts the rendered output contains the escaped form `&lt;script&gt;` and never the raw `<script>` tag.

- [ ] T-3.2 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/api.py` exposing `api_servers(service) -> bytes` (JSON of grouped servers — same shape as `PanelService.list_servers_grouped()` flattened to JSON-ready dicts) and `api_contexts(service) -> bytes` (JSON of active contexts). Each writes content-type `application/json; charset=utf-8`. Module ≤ 100 lines. **Files:** `dadaia_workspace/features/panel/views/api.py`. **Owner:** software-engineer. **Acceptance:** unit test T-3.9 / T-3.9-bis green; JSON parses; field names stable. **R3-A (response headers):** both handlers MUST set `Content-Type: application/json; charset=utf-8`. No additional escaping of dynamic strings is needed — `json.dumps()` handles JSON-string escaping correctly. HTML-escaping is only required in HTML responses (T-3.1), not JSON.

- [ ] T-3.3 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/memory.py` with `serve_memory(workspace_root, slug, path) -> tuple[bytes, str]` returning `(file.read_bytes(), content_type)`. Content-type sniffed by extension only (`.html` → `text/html; charset=utf-8`, `.png` → `image/png`, `.svg` → `image/svg+xml`, fallback `application/octet-stream`). No template, no head injection, no body mutation. Module docstring explicitly names SPEC-DOC-008 + NFR-2 + architect's R3 (layer-bypass exception is intentional). Path traversal guard: reject any normalized path that escapes `repos/<slug>/specs/`. **Files:** `dadaia_workspace/features/panel/views/memory.py`. **Owner:** software-engineer. **Acceptance:** byte-identity canary test T-3.5 green; traversal guard test included; coverage ≥ 80%.

- [ ] T-3.4 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/wrapper.py` with `render_memory_wrapper(slug, file) -> bytes`. Returns a small HTML document: 40px top bar (`position: fixed`) with `← Voltar ao Painel` linking to `/`, plus `<iframe src="/memory/<slug>/<file>" sandbox="allow-scripts allow-same-origin">` sized to `width: 100vw; height: calc(100vh - 40px); border: 0;`. Module ≤ 100 lines. **Files:** `dadaia_workspace/features/panel/views/wrapper.py`. **Owner:** software-engineer. **Acceptance:** unit test T-3.10 green; output contains both back-bar and iframe with correct src.

- [ ] T-3.5 `[parallel: yes]` **BYTE-IDENTITY CANARY TEST** — add `tests/unit/features/panel/test_views_memory.py` with `test_serve_memory_byte_identity`: read fixture `tests/fixtures/memory/architecture.html` raw; call `serve_memory(workspace_root, slug, "architecture.html")`; assert returned bytes are **exactly equal** to `Path.read_bytes()` of the fixture. Test docstring explicitly names `SPEC-DOC-008` and `NFR-2`. Also test the traversal guard rejects `../../etc/passwd`. **Files:** `tests/unit/features/panel/test_views_memory.py`, `tests/fixtures/memory/architecture.html`. **Owner:** software-engineer. **Acceptance:** test green; fails fast if anyone ever adds string mutation to `views/memory.py`.

- [ ] T-3.6 `[parallel: yes]` Create `dadaia_workspace/features/panel/views/static.py` with `serve_static(name) -> tuple[bytes, str]` that returns the Python-string-constant CSS/JS body (NOT a filesystem read) + the explicit content-type from the map `{"panel.css": "text/css; charset=utf-8", "panel.js": "application/javascript; charset=utf-8"}`. Imports `PANEL_CSS` and `PANEL_JS` constants from `dadaia_workspace/features/panel/views/_assets.py` (created in T-3.7 / T-3.8). For any `name` not in the map → return 404 via raising a `KeyError` the handler maps to HTTP 404. **R1 (asset packaging — decision locked):** no `importlib.resources`, no `pyproject.toml` package-data declaration, no filesystem read — assets are Python string constants so they ship correctly in any installed wheel and require no traversal guard (a literal dict lookup is the entire validation surface). The route remains `/static/panel.css` and `/static/panel.js` for cleaner browser caching than embedding into every page render. **Files:** `dadaia_workspace/features/panel/views/static.py`. **Owner:** software-engineer. **Acceptance:** unit test green; `serve_static("panel.css")` returns the same bytes as `PANEL_CSS.encode("utf-8")` with content-type `text/css; charset=utf-8`; `serve_static("../etc/passwd")` raises `KeyError` (no traversal possible by construction).

- [ ] T-3.7 `[parallel: yes]` Embed `panel.css` as Python string constant matching frontend mockup tokens (`#fafafa` bg, `#222` text, `#2d7d9a` body-text links, `#7ec8e3` decorative accent only). Define `PANEL_CSS: str` in `dadaia_workspace/features/panel/views/_assets.py` (co-located with `views/static.py`). Content is the token block from PLAN.md `Visual contract` baked in as CSS custom properties plus structural rules copied verbatim from the mockup files (`index.html`, `memories.html`, `memory-view.html`) — grid layout for memory cards, table layout for servers, left-border accent + `#f0faff` tinted bg for primary card, status pill colors, hover row. **Body-text links MUST use `var(--color-accent-dark)` = `#2d7d9a`** (resolution to frontend Q-1); `#7ec8e3` is decorative accent only. **R1:** the CSS is a Python string constant — NOT a file under `assets/` — so it ships correctly in any installed wheel without `pyproject.toml` package-data. **Files:** `dadaia_workspace/features/panel/views/_assets.py`. **Owner:** software-engineer (copy from mockup, do not invent). **Acceptance:** visual diff against the 3 mockup files is "same visual feel" — colors, spacing, typography identical; `PANEL_CSS` is a non-empty `str`; importing the module costs zero filesystem reads.

- [ ] T-3.8 `[parallel: yes]` Embed `panel.js` as Python string constant — auto-refresh of `/api/servers` every 5s + tab switching. Define `PANEL_JS: str` in `dadaia_workspace/features/panel/views/_assets.py` (same module as `PANEL_CSS` from T-3.7). Content (~30 lines): `setInterval(fetchServers, 5000)` where `fetchServers` does `fetch('/api/servers')`, parses JSON, swaps the `tbody` of each grouped table without full-page reload (frontend D-8). Tab switching between Servers / Memories / Agents toggles `aria-selected` + `hidden` on sections — no router. **TTL rendering helper**: client-side formats the registry's expiry timestamp into relative duration like `"6h 42m"` (resolution to frontend Q-4). **R1:** the JS is a Python string constant — NOT a file under `assets/` — so it ships correctly in any installed wheel without `pyproject.toml` package-data. **Files:** `dadaia_workspace/features/panel/views/_assets.py`. **Owner:** software-engineer. **Acceptance:** mockup `index.html` JS snippet is the reference; tab toggle works; status dot pulses on fetch; `PANEL_JS` is a non-empty `str`.

- [ ] T-3.9 `[parallel: yes]` Contract test for `/api/servers` in `tests/unit/features/panel/test_views_api.py::test_api_servers_shape_contract`. Asserts the deserialized JSON response is an array; each element has named keys `port` (int), `project` (str), `url` (str), `status` (str — one of `"active"` or `"stale"`), `pid` (int or null), `ttl_remaining_human` (str — e.g. `"6h 42m"`). If keys are missing or renamed, test fails — this is the contract that protects `panel.js` from silent drift during Phase 1 refactoring (no mypy catch for JS). Also covers the existing assertions: `test_views_index.py` checks that the index contains the 3 section headers, the placeholder card copy "Em breve — Release-2", and primary-context-first ordering in the grid. **Files:** `tests/unit/features/panel/test_views_index.py`, `tests/unit/features/panel/test_views_api.py`. **Owner:** software-engineer. **Acceptance:** all tests green; the contract test's docstring explicitly states "if this fails, panel.js must be updated in lockstep".

- [ ] T-3.9-bis `[parallel: yes]` Contract test for `/api/contexts` in `tests/unit/features/panel/test_views_api.py::test_api_contexts_shape_contract`. Asserts the deserialized JSON response is an array; each element has named keys `name` (str), `repo_slug` (str), `current_branch` (str), `is_primary` (bool), `memory_files` (array of strings — e.g. `["architecture.html", "tech-stack.html", "product/index.html"]`). If keys are missing or renamed, test fails. **Files:** `tests/unit/features/panel/test_views_api.py`. **Owner:** software-engineer. **Acceptance:** test green; docstring explicitly states "if this fails, panel.js must be updated in lockstep".

- [ ] T-3.10 `[parallel: yes]` Add unit test `tests/unit/features/panel/test_views_wrapper.py`: wrapper contains back-bar text "← Voltar ao Painel", href `/`, and iframe `src="/memory/<slug>/<file>"`. **Files:** `tests/unit/features/panel/test_views_wrapper.py`. **Owner:** software-engineer. **Acceptance:** test green.

---

## Phase 4 — CLI command + dashboard deprecation + bind fix

- [ ] T-4.1 `[parallel: no]` Create `dadaia_workspace/cli/commands/panel.py` with `dadaia panel [--port 4999] [--no-open] [--bind 127.0.0.1]`. `--bind` validates against `{"127.0.0.1"}` only — any other value exits with `"Release-1 supports loopback bind only"`. Builds `PanelService` from container, instantiates `ThreadingHTTPServer`, prints `Panel running at http://127.0.0.1:<port>/`, calls `webbrowser.open()` unless `--no-open`, then blocks via `serve_blocking()`. Catches `OSError` (port in use) and exits with constitution-compliant error message naming `lsof -i :<port>`. **Files:** `dadaia_workspace/cli/commands/panel.py`. **Owner:** software-engineer. **Acceptance:** command callable; `--help` lists all 3 flags; integration test T-4.4 green.

- [ ] T-4.2 `[parallel: yes]` Register `panel` subcommand in `dadaia_workspace/cli/main.py` so `dadaia panel` resolves. **Files:** `dadaia_workspace/cli/main.py`. **Owner:** software-engineer. **Acceptance:** `dadaia --help` lists `panel`; `dadaia panel --help` works.

- [ ] T-4.3 `[parallel: no]` Patch `dadaia_workspace/cli/commands/server.py::dashboard()` and `dadaia_workspace/features/server_registry/dashboard.py`: (a) emit deprecation warning to stderr verbatim: `"[deprecation] 'dadaia server dashboard' will be removed in a future release. Use 'dadaia panel' instead."`; (b) bind `127.0.0.1` explicitly instead of the current `"localhost"` string (FR-7 security fix — in-scope per Q7 grill resolution). **Before/after for the bind fix:** the current line `server.py:257` reads `HTTPServer(("localhost", port), DashboardHandler)`; replace with `ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)`. "localhost" resolution is OS-dependent (can resolve to `::1` on IPv6-first systems); the explicit `"127.0.0.1"` string guarantees IPv4 loopback bind on Ubuntu 24.04 and matches the panel's bind invocation. (c) switch the internal `HTTPServer` to `ThreadingHTTPServer` for consistency with the panel (architect R5); (d) update Typer docstring + `--help` to flag deprecation. **R3-B (architect Q-C / DEPRECATED annotation):** (e) add a module-level docstring to `dadaia_workspace/features/server_registry/dashboard.py` exactly `"""DEPRECATED — removed in a future release. New code in features/panel/. See specs/releases/dadaia-workspace-panel-v1/."""` (matches architect's R7 / Q-C "mandatory annotation"); (f) at the top of the `dashboard()` CLI subcommand entry (in `cli/commands/server.py`), call `warnings.warn("'dadaia server dashboard' is deprecated. Use 'dadaia panel' instead. This command will be removed in the next release.", DeprecationWarning, stacklevel=2)` BEFORE the stderr deprecation line is printed (both must coexist — `warnings.warn` is for Python-level callers, the stderr line is for shell users). **Files:** `dadaia_workspace/cli/commands/server.py`, `dadaia_workspace/features/server_registry/dashboard.py`. **Owner:** software-engineer. **Acceptance:** dashboard still serves the legacy page; stderr contains the verbatim deprecation line; `nc -z <LAN-ip> <port>` fails after fix; `dashboard.py` module docstring starts with `DEPRECATED`; running `python -W error::DeprecationWarning -m dadaia_workspace server dashboard --port <free>` raises `DeprecationWarning`.

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
