# Plan: Release — dadaia-workspace-panel-v1

> **Status:** Em revisão
> **Release ID:** dadaia-workspace-panel-v1
> **Phase:** PLAN (release directory exists; `specs/releases/ACTIVE.md` still points at `agent-sdd-alignment-v1` / `phase: TASKS` — this release becomes ACTIVE only after that one reaches CLOSURE)
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **SPEC:** `specs/releases/dadaia-workspace-panel-v1/SPEC.md` (Status: Em revisão)

---

## Goal

Ship the **Dadaia Workspace Panel**: a local single-page UI at `http://127.0.0.1:4999/`
that gives the workspace a visible identity. It surfaces, in three navigation areas,
the running dev servers across projects (evolving the legacy `dadaia server dashboard`),
the current state of each active Spec Context Project (memory HTML served verbatim with
a CSS-overlay back button), and a placeholder card reserving room for the Release-2
Agents & Workflows surface. The panel boots via `dadaia panel`, blocks the terminal,
binds loopback only, and adds zero runtime dependencies — stdlib `http.server` is the
entire web tier.

---

## Architecture summary

Per the software-architect report (D1–D5, see `References`), the panel lives entirely
inside the existing 4-layer architecture without introducing new `core/` Protocols or
`infrastructure/` adapters:

```
cli/commands/panel.py  ──►  features/panel/  ──►  features/server_registry/  ──►  core/  ◄──  infrastructure/json_*_store
                                            └─►  features/spec_context/      ──►  core/  ◄──/
features/panel/views/memory.py  ─ direct pathlib.Path.read_bytes() of repos/<slug>/specs/memory/*  (HTTP-layer concern, not domain leak)
container.py: add build_panel_service(workspace_root) composing the two existing services.
```

Routing model (D3): `PanelHandler` carries a compiled regex dispatch table; each route
points at a small `views/*.py` module (each ≤ 100 lines, single-responsibility, unit
testable without `HTTPServer`). `handler.py` itself stays ~60 lines.

Memory serving (D4): **two routes**. `/memory/<slug>/<file>` returns `Path.read_bytes()`
verbatim — NFR-2 byte-identity preserved **by construction** (no template, no mutation,
no head injection). `/memory-view/<slug>/<file>` returns a separate wrapper page (40px
top bar with "← Voltar ao Painel" + full-viewport `<iframe src="/memory/<slug>/<file>">`).
The Memories cards link to `/memory-view/...`; the iframe loads `/memory/...`. Same
origin, Mermaid CDN works inside the iframe as it does today.

Architect's full report:
`.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T211602Z-panel-architecture.html`

---

## Module layout

New / changed files (everything else untouched):

```
dadaia_workspace/features/panel/                    # NEW package
├── __init__.py                                     # docstring naming R3 layer-bypass exception
├── service.py                                      # PanelService — read-only orchestrator
├── server.py                                       # ThreadingHTTPServer factory + signal/Ctrl+C
├── handler.py                                      # PanelHandler — regex dispatch only (~60 lines)
├── views/
│   ├── __init__.py
│   ├── index.py                                    # render_index(model) → HTML (3 sections)
│   ├── memory.py                                   # serve_memory(slug, path) verbatim bytes
│   ├── wrapper.py                                  # render_memory_wrapper(slug, file) iframe host
│   ├── api.py                                      # api_servers(model), api_contexts(model) → JSON
│   └── static.py                                   # serve_static(name) → CSS/JS bytes
└── assets/
    ├── panel.css                                   # tokens lifted from architecture.html
    └── panel.js                                    # fetch /api/servers every 5s + tab toggle

dadaia_workspace/cli/commands/panel.py              # NEW Typer command `dadaia panel`
dadaia_workspace/cli/main.py                        # PATCH: register `panel` subcommand
dadaia_workspace/cli/commands/server.py             # PATCH: dashboard() emits deprecation + binds 127.0.0.1, switches to ThreadingHTTPServer
dadaia_workspace/container.py                       # PATCH: add build_panel_service(workspace_root)
```

Tests:

```
tests/unit/features/panel/test_service.py
tests/unit/features/panel/test_views_index.py
tests/unit/features/panel/test_views_memory.py        # BYTE-IDENTITY CANARY — SPEC-DOC-008 / NFR-2
tests/unit/features/panel/test_views_wrapper.py
tests/unit/features/panel/test_views_api.py
tests/integration/features/panel/test_http.py
tests/e2e/features/test_panel.py                       # owned by qa-engineer
tests/fixtures/memory/architecture.html                # minimal fixture for byte-identity assertion
```

---

## Implementation phases

Sequential. Each phase ends green (`pytest` + `ruff` + `mypy --strict` + `dadaia specs doctor`).

### Phase 1 — PanelService + container wiring

Pure domain assembly, no HTTP yet. Read-only orchestrator that fans out to
`ServerRegistryService` and `SpecContextService`, returns dataclasses ready for
rendering. Best-effort `project.lower() == repo_slug.lower()` grouping (D1.A); unmatched
entries fall under group `"Outros"`. Active-context filtering (state == `ativo`) inside
the service, not the view. Unit tests use fakes for both injected services.

**Exit criteria:** `PanelService.list_servers_grouped()` and `list_active_contexts()`
return correctly shaped dataclasses; `build_panel_service()` composes them in
`container.py`; unit suite green; coverage ≥ 80% for `service.py`.

### Phase 2 — HTTP layer + handler dispatch

`features/panel/server.py` constructs a `ThreadingHTTPServer` (stdlib, NFR-1) bound to
`127.0.0.1` on the requested port, installs `SIGINT`/`SIGTERM` handlers that call
`server.shutdown()` from a thread (stdlib pattern) so Ctrl+C frees the port within 2s
(NFR-4). `features/panel/handler.py` carries the regex dispatch table from D3 — pure
URL→view fan-out, zero rendering logic. Unknown route returns HTTP 404 with a minimal
HTML body and the constitution's error contract phrasing (capability + context + next
step). Integration tests spin up `ThreadingHTTPServer` on an ephemeral port and exercise
each route end-to-end with `urllib.request`.

**Exit criteria:** integration suite green; all 6 routes return correct status +
content-type; 404 path covered; clean shutdown verified in test teardown.

### Phase 3 — View modules + frontend assets

Each `views/*.py` is < 100 lines and unit-tested in isolation (no HTTPServer instance
required). `views/memory.py` does **only** `Path.read_bytes()` and a content-type sniff
on extension — its unit test is the canary that protects SPEC-DOC-008 and NFR-2 (read a
fixture file, call the view, assert returned bytes == file bytes byte-for-byte). CSS and
JS are static assets under `features/panel/assets/`, served by `views/static.py`. The
CSS tokens are lifted verbatim from `specs/memory/architecture.html` per the frontend
mockup (see `Visual contract` below); the JS is ~30 lines for `fetch('/api/servers')` on
a 5s `setInterval` plus tab switching.

**Frontend resolutions baked in (do not re-ask):**

- **Body-text links use `#2d7d9a`** (passes WCAG AA ~5:1 on `#fafafa`). The lighter
  `#7ec8e3` is **decorative accent only** — left-border on primary card, hover glow,
  status pill background. Never as link text on light background.
- **Primary context card is first-position in the auto-fill grid** (no separate
  full-width row). Visual differentiation comes from the left-border accent
  (`#7ec8e3`, 4px) + tinted background (`#f0faff`) + "primary" badge.
- **Memory view = iframe-in-wrapper** (architect D4.A, frontend D-6). Confirmed.
- **TTL column shows relative duration** (e.g. `6h 42m`), formatted client-side from
  the registry's expiry timestamp. No absolute clock value in Release-1.

**Exit criteria:** unit suite green for every view module; byte-identity canary green
with explicit comment naming SPEC-DOC-008 and NFR-2; visual output matches the three
mockup files (`index.html`, `memories.html`, `memory-view.html`).

### Phase 4 — CLI command + dashboard deprecation + bind fix

`cli/commands/panel.py` exposes `dadaia panel [--port 4999] [--no-open] [--bind 127.0.0.1]`.
`--bind` accepts only `127.0.0.1` in Release-1 (FR-7); other values reject with
`"Release-1 supports loopback bind only"`. The command builds `PanelService` from the
container, instantiates the HTTP server, prints the URL on stdout, calls
`webbrowser.open()` unless `--no-open`, then blocks until SIGINT.

In the **same release**, `cli/commands/server.py::dashboard()` is patched to (a) print
the deprecation warning to stderr exactly per FR-6, (b) bind `127.0.0.1` instead of
the stdlib default `0.0.0.0` (FR-7 hardening — operator confirmed Q7 footgun), and
(c) switch its internal `HTTPServer` to `ThreadingHTTPServer` to match the panel's
concurrency model (R5). Behavior is otherwise preserved for one release.

**Exit criteria:** `dadaia panel --no-open --port <free>` boots and shuts down clean;
`dadaia server dashboard` still serves the legacy page and prints the deprecation line.
`--help` reflects the deprecation marker.

### Phase 5 — E2E (qa-engineer)

End-to-end happy paths under `tests/e2e/features/test_panel.py`. Spawns
`dadaia panel --no-open --port <ephemeral>` as a subprocess. Validates: loopback bind
(`nc -z 127.0.0.1 <port>` succeeds, `nc -z <LAN-ip> <port>` fails), each section
renders, click-through from `/memories` to `/memory-view/<slug>/architecture.html`
loads the wrapper with iframe, dashboard deprecation warning visible on stderr, port
freed within 2s of SIGINT.

**Exit criteria:** E2E suite green; CLOSURE evidence captured in T-6.3 below.

---

## Tests strategy (per architect D5)

| Layer | File | Scope |
|---|---|---|
| Unit | `tests/unit/features/panel/test_service.py` | `PanelService` with fake injected services; best-effort matcher; "Outros" group; active-only filter; empty registry |
| Unit | `tests/unit/features/panel/test_views_index.py` | `render_index(model)` HTML output assertions |
| Unit | `tests/unit/features/panel/test_views_memory.py` | **BYTE-IDENTITY CANARY** — assert `serve_memory()` returns bytes equal to `Path.read_bytes()` of the fixture; comment naming SPEC-DOC-008 + NFR-2 |
| Unit | `tests/unit/features/panel/test_views_wrapper.py` | wrapper page contains 40px back-bar + iframe pointing at `/memory/<slug>/<file>` |
| Unit | `tests/unit/features/panel/test_views_api.py` | `api_servers`/`api_contexts` serialize to expected JSON shape |
| Integration | `tests/integration/features/panel/test_http.py` | `ThreadingHTTPServer` on ephemeral port; `urllib` requests to `/`, `/api/servers`, `/api/contexts`, `/memory/<slug>/architecture.html`, `/memory-view/<slug>/architecture.html`, `/unknown` (404); content-type and byte-identity asserted against `tests/fixtures/memory/architecture.html` |
| E2E (qa-engineer) | `tests/e2e/features/test_panel.py` | Subprocess `dadaia panel --no-open --port <ephemeral>`; loopback-bind verification; 2s clean shutdown; deprecation warning visible from `dadaia server dashboard` |

Coverage gate (NFR-3, 80%) honored by unit + integration. The byte-identity test is
the suite's canary — if it regresses, SPEC-DOC-008 will break downstream.

---

## Visual contract

Tokens lifted verbatim from `specs/memory/architecture.html` and the frontend mockup
(`.dadaia/reports/dadaia-workspace/frontend-engineer/2026-05-16T211621Z-panel-mockup.html`).
Implementation copies these into `dadaia_workspace/features/panel/assets/panel.css`
without invention.

```css
/* Colors */
--color-bg:            #fafafa;
--color-surface:       #ffffff;
--color-text:          #222222;
--color-heading:       #111111;
--color-muted:         #666666;
--color-border:        #dddddd;
--color-border-strong: #333333;
--color-accent:        #7ec8e3;   /* decorative accent only — never link text on light bg */
--color-accent-dark:   #2d7d9a;   /* WCAG AA ~5:1 — body-text links (overrides mockup #4aa8c8) */
--color-code-bg:       #f0f0f0;
--color-th-bg:         #eeeeee;
--color-primary-ring:  #7ec8e3;
--color-primary-bg:    #f0faff;
--color-active-dot:    #3aaa6e;
--color-stale-dot:     #cc7700;
--color-row-hover:     #f5f5f5;

/* Typography */
--font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
--font-mono:  ui-monospace, "SFMono-Regular", Consolas, monospace;

/* Geometry */
--radius:      4px;
--radius-card: 6px;
```

**Visual ground truth (binding contract for QA):**

- `…/2026-05-16T211621Z-panel-mockup/index.html` — Servers tab active, grouped table, Agents placeholder card
- `…/2026-05-16T211621Z-panel-mockup/memories.html` — 2-col auto-fill grid, primary card highlighted (left-border + tinted bg)
- `…/2026-05-16T211621Z-panel-mockup/memory-view.html` — 40px back-bar + iframe loading the real memory HTML

---

## Acceptance criteria (CHECKLIST — sourced verbatim from SPEC)

- [ ] AC-1 — `cd repos/dadaia-workspace && dadaia specs doctor` → `0 errors` (warnings must not regress from baseline `0 errors, 0 warnings`).
- [ ] AC-2 — `dadaia panel --port 4999` opens browser at `http://127.0.0.1:4999/`, 3 sections render, primary context highlighted in Memories.
- [ ] AC-3 — `nc -z 127.0.0.1 4999` succeeds; `nc -z <LAN-ip> 4999` fails. Same passes for `dadaia server dashboard` after the bind fix.
- [ ] AC-4 — Clicking `architecture.html` in a context card navigates to `/memory-view/<slug>/architecture.html`. Back-bar visible. Mermaid diagrams render. Relative images load.
- [ ] AC-5 — `dadaia server register --port 3000 --project <slug>` then observing the panel within 5s: new entry appears grouped under matching context (or "Outros").
- [ ] AC-6 — `dadaia server dashboard` prints the deprecation warning to stderr and serves the legacy dashboard bound to `127.0.0.1`.
- [ ] AC-7 — `pytest tests/` → all green; coverage for `features/panel/` ≥ 80%.
- [ ] AC-8 — No new entries in `pyproject.toml [tool.poetry.dependencies]`.
- [ ] AC-9 — Ctrl+C during `dadaia panel` exits 0 and frees port 4999 within 2s (`lsof -i :4999`).
- [ ] AC-10 — Raw bytes of `repos/<slug>/specs/memory/architecture.html` byte-identical before/after request to `/memory/<slug>/architecture.html` (NFR-2 canary).
- [ ] AC-11 — `specs/backlog/dadaia-workspace-panel.md` removed (promoted into SPEC); `specs/backlog/candidates.md` records the Release-2 follow-up at CLOSURE.

---

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-NFR2 | Future temptation to inject HTML into the `/memory/` response breaks SPEC-DOC-008 atomicity | Two-route split (D4) is the structural defense. Byte-identity canary unit test (T-3.5) names SPEC-DOC-008 + NFR-2 in its docstring — any change to `views/memory.py` flips the test red |
| R-PORT | Port 4999 already in use when operator runs `dadaia panel` | CLI must catch `OSError` from bind and emit constitution-compliant error: "Port 4999 already in use. Free it (`lsof -i :4999`) or pass `--port <free>`." |
| R-DOC | Regression of `dadaia specs doctor` due to image/path drift introduced by panel docs | Run `dadaia specs doctor` before every commit on this release; baseline is `0 errors, 0 warnings`; any new warning is investigated, not committed-around |
| R-CONCUR | Stdlib `HTTPServer` single-threaded; iframe load races wrapper request | Use `ThreadingHTTPServer` (stdlib) on both the panel and the patched dashboard (R5 in architect report) |
| R-BIND | Bind fix on `dadaia server dashboard` regresses an undocumented LAN workflow | Operator confirmed at Q7 that LAN was never desired — current `0.0.0.0` is a footgun. AC-6 explicitly verifies loopback-only after fix |
| R1-ASSETS | `panel.css`/`panel.js` packaging gap in installed wheels | Static assets are Python string constants in `views/_assets.py` (R1 resolution) — no `importlib.resources`, no `pyproject.toml` package-data. If assets ever need to be edited outside the codebase (e.g. live tweaks by ops), this needs a refactor; acceptable for Release-1 (~150 total LoC of CSS+JS) |
| R4-BRANCH | Branch staleness in Memories cards | The `current_branch` field shown per context is whatever `SpecContextService` has cached (last `dadaia context show/activate` invocation). If the operator switches branches in a repo without re-activating the context, the panel will show stale info. Accepted for Release-1 due to per-request subprocess cost (8 contexts × every-5s auto-refresh). Mitigation: a future release can add a manual "refresh contexts" button or a per-request `git rev-parse` with a TTL cache |

---

## Dependencies & sequencing

- **Blocked on `agent-sdd-alignment-v1` reaching CLOSURE before `ACTIVE.md` flips to `dadaia-workspace-panel-v1`** (currently `phase: TASKS`). Disjoint write-sets (alignment touches agents + `doctor.py`; this release adds `features/panel/` + edits `cli/commands/server.py` + `container.py`) so parallel SPEC/PLAN work is safe — but only one ACTIVE release at a time per lifecycle constraint.
- **Reports already in:** software-architect (D1–D5) and frontend-engineer (mockup + tokens). **Pre-implementation review:** software-engineer (P0/P1 action items already folded into TASKS — see R1/R2/R3/R4 acceptance criteria deltas).
- **No new runtime deps; no CI changes; no infra changes** for Release-1.
- **Memory contract dependency:** SPEC-DOC-008 / SPEC-DOC-010 in `dadaia_workspace/features/specs/doctor.py`. If that contract changes mid-release, re-evaluate `views/memory.py`.

---

## References

- **SPEC:** `specs/releases/dadaia-workspace-panel-v1/SPEC.md`
- **Architect report:** `.dadaia/reports/dadaia-workspace/software-architect/2026-05-16T211602Z-panel-architecture.html`
- **Frontend mockup report:** `.dadaia/reports/dadaia-workspace/frontend-engineer/2026-05-16T211621Z-panel-mockup.html`
- **Mockup files (visual ground truth):** `.dadaia/reports/dadaia-workspace/frontend-engineer/2026-05-16T211621Z-panel-mockup/{index,memories,memory-view}.html`
- **Alignment plan (Q1–Q7 source-of-truth):** `~/.claude/plans/feature-dadaia-parsed-flame.md`
- **Constitution:** `specs/constitution.md`
- **Memory contract:** `specs/memory/architecture.html`, `specs/memory/tech-stack.html`, `specs/memory/product/index.html`
- **Doctor invariants:** `dadaia_workspace/features/specs/doctor.py` (SPEC-DOC-008 atomicity at `:604`, SPEC-DOC-010 image links at `:628`)
- **Legacy dashboard being subsumed:** `dadaia_workspace/features/server_registry/dashboard.py`, `dadaia_workspace/cli/commands/server.py` (`dashboard` subcommand)
- **Currently ACTIVE release:** `specs/releases/agent-sdd-alignment-v1/`
