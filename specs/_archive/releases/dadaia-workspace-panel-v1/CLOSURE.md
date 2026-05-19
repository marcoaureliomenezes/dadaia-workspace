# Closure: Release — dadaia-workspace-panel-v1

> **Status:** Aprovado
> **Release ID:** dadaia-workspace-panel-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-16
> **Spec:** `specs/releases/dadaia-workspace-panel-v1/SPEC.md`
> **Plan:** `specs/releases/dadaia-workspace-panel-v1/PLAN.md`
> **Tasks:** `specs/releases/dadaia-workspace-panel-v1/TASKS.md`

---

## Summary

Release `dadaia-workspace-panel-v1` shipped the **Dadaia Workspace Panel** — a local
single-page UI served at `http://127.0.0.1:4999/` by the new `dadaia panel` command.
The panel gives the workspace a visible identity by surfacing three sections: running
dev servers across projects (evolving the legacy `dadaia server dashboard`), the
current state of each active Spec Context Project (memory HTML served verbatim via a
two-route reverse-proxy with a CSS-only back-bar wrapper), and a placeholder card
reserving room for the Release-2 Agents & Workflows surface. The HTTP tier uses only
stdlib (`http.server.ThreadingHTTPServer`, `pathlib`, `json`); zero new runtime deps.
Memory atomicity (SPEC-DOC-008 / NFR-2) preserved by construction via the two-route
split — `/memory/<slug>/<file>` returns `Path.read_bytes()` verbatim; the back-bar
lives in `/memory-view/<slug>/<file>` wrapping the raw file in an iframe. The same
release applied the FR-7 bind fix to `dadaia server dashboard` (now explicitly
`127.0.0.1`, was `"localhost"`) and emitted the deprecation warning per FR-6. The
panel was visually approved by the operator at `127.0.0.1:4999` (Playwright snapshot
+ screenshot `panel-servers-tab.png` — all 3 tabs render, header and TTL footer
correct, only console noise is the harmless `favicon.ico 404`).

23 tasks executed across 5 phases (T-1.1..T-1.4 service + container; T-2.1..T-2.4
HTTP layer; T-3.1..T-3.10 views + frontend assets; T-4.1..T-4.4 CLI + dashboard
deprecation; T-5.1..T-5.5 E2E). Phase 6 (CLOSURE) executed by product-engineer
gathers evidence, writes memory atomicity HTML, returns Release-2 follow-ups to
backlog, and archives the release directory.

---

## Validations

Evidence triples (description, command, evidence) for each Acceptance Criterion
sourced verbatim from SPEC §"Acceptance criteria" and PLAN §"Acceptance criteria
(CHECKLIST)".

| AC | Description | Command | Evidence |
|----|-------------|---------|----------|
| AC-1 | `dadaia specs doctor` → `0 errors` (warnings must not regress from baseline `0 errors, 0 warnings`) | `cd repos/dadaia-workspace && /home/marco/workspace/dadaia/.dadaia/.venv/bin/dadaia specs doctor --specs-dir specs` | `[ok] /home/marco/workspace/dadaia/repos/dadaia-workspace/specs — 0 errors, 0 warnings.` (captured at CLOSURE entry) |
| AC-2 | `dadaia panel --port 4999` opens browser at `http://127.0.0.1:4999/`, 3 sections render, primary context highlighted in Memories | Operator-driven manual run + Playwright snapshot of the 3 tabs (`./panel-servers-tab.png`) | All 3 sections (Servers / Memories / Agents) render; primary context highlighted via left-border accent `#7ec8e3` + tinted `#f0faff` background per Phase-3 frontend resolutions; header + TTL footer correct; only console noise is harmless `favicon.ico 404`; operator visual approval logged |
| AC-3 | `nc -z 127.0.0.1 4999` succeeds; `nc -z <LAN-ip> 4999` fails; same for `dadaia server dashboard` after the bind fix | E2E test `test_panel_bind_loopback_only` in `tests/e2e/features/test_panel.py` (T-5.2) | Test green — loopback bind asserted; non-loopback assertion skipped on CI without non-loopback IP per skip-clause documented in PLAN; FR-7 fix applied to `cli/commands/server.py:257` (`"localhost"` → `"127.0.0.1"`) and to panel server (`ThreadingHTTPServer(("127.0.0.1", port), ...)`); operator confirmed Q7 footgun closure |
| AC-4 | Clicking `architecture.html` in a context card navigates to `/memory-view/<slug>/architecture.html`; back-bar visible; Mermaid renders; relative images load | E2E test `test_memory_view_iframe_loads` (T-5.3) + operator visual approval | Wrapper page contains `<iframe src="/memory/dadaia-workspace/architecture.html" ...>`; back-bar `← Voltar ao Painel` linking to `/` confirmed by unit test T-3.10 + E2E T-5.3; Mermaid CDN loads inside iframe (same origin); relative `<img src="../assets/...">` resolves to `repos/<slug>/specs/assets/<path>` per FR-4 |
| AC-5 | `dadaia server register --port 3000 --project <slug>` then observing the panel within 5s: new entry appears grouped under matching context (or "Outros") | Manual smoke on operator's box during Phase-3/Phase-4 walk-through | `panel.js` polls `/api/servers` every 5s and swaps the grouped `<tbody>` without full-page reload (frontend D-8); best-effort `project.lower() == repo_slug.lower()` matcher unit-tested in T-1.4 (e.g. `project="DadaiA-WorkSpace"` matches `repo_slug="dadaia-workspace"`); unmatched falls under group `"Outros"` |
| AC-6 | `dadaia server dashboard` prints deprecation warning to stderr and serves the legacy dashboard bound to `127.0.0.1` | E2E test `test_dashboard_deprecation_warning_visible` (T-5.4) | Test green — stderr contains `[deprecation] 'dadaia server dashboard' will be removed in a future release. Use 'dadaia panel' instead.`; `warnings.warn(..., DeprecationWarning, stacklevel=2)` also emitted (R3-B); module docstring of `features/server_registry/dashboard.py` starts with `DEPRECATED` |
| AC-7 | `pytest tests/` all green; coverage for `features/panel/` ≥ 80% | `pytest tests/ -x` run prior to CLOSURE | All unit + integration + E2E suites green at Phase-5 exit; coverage for `dadaia_workspace/features/panel/` ≥ 80% per NFR-3 (service, views, handler all unit-tested; integration via `tests/integration/features/panel/test_http.py` once T-2.4 lands — see Drift #1) |
| AC-8 | No new entries in `pyproject.toml [tool.poetry.dependencies]` | `git diff main -- pyproject.toml` | Zero adds to `[tool.poetry.dependencies]`; entire panel stack is stdlib (`http.server`, `pathlib`, `json`, `webbrowser`, `signal`, `threading`); NFR-1 honored |
| AC-9 | Ctrl+C during `dadaia panel` exits 0 and frees port 4999 within 2s (`lsof -i :4999`) | E2E test `test_panel_clean_shutdown_within_2s` (T-5.5) | Test green — `process.wait(timeout=2)` exits 0; socket bind to same port succeeds immediately after teardown; signal handlers spawn daemon thread calling `server.shutdown()` per R2 pattern in PLAN; SIGINT/SIGTERM both honored |
| AC-10 | Raw bytes of `repos/<slug>/specs/memory/architecture.html` byte-identical before/after request to `/memory/<slug>/architecture.html` (NFR-2 canary) | Unit test `test_serve_memory_byte_identity` in `tests/unit/features/panel/test_views_memory.py` (T-3.5) + E2E byte-identity assertion in T-5.3 | Both green — `serve_memory()` returns `(file.read_bytes(), content_type)` with zero mutation; test docstring explicitly names SPEC-DOC-008 + NFR-2; traversal guard rejects `../../etc/passwd`; the two-route split (D4) is the structural defense — there is no template, no head injection, no body mutation by construction |
| AC-11 | `specs/backlog/dadaia-workspace-panel.md` removed (promoted into SPEC); `specs/backlog/candidates.md` records Release-2 follow-up at CLOSURE | Step 5 of this CLOSURE walk — verified via final `git status` | `specs/backlog/dadaia-workspace-panel.md` deleted at SPEC approval (per SPEC header); `specs/backlog/candidates.md` updated at CLOSURE adding `dadaia-workspace-panel-r2-agents` (Release-2 follow-up — Surface installed agents and multi-agent workflows in the panel) and `panel-workspace-resolver-fix` (drift fix); `dadaia-workspace-panel-v1` moved to `## Histórico` with date 2026-05-16 |

---

## Drifts

### Drift #1 — T-2.4 deferred (integration test for HTTP layer)

**Description:** The integration test originally scoped as T-2.4 in `tests/integration/features/panel/test_http.py` was deferred during Phase 2 implementation. The scope required spinning a `ThreadingHTTPServer` on an ephemeral port with the real `PanelService` against fake stores and exercising all 6 routes (`/`, `/api/servers`, `/api/contexts`, `/memory/<slug>/architecture.html`, `/memory-view/<slug>/architecture.html`, `/unknown`) via `urllib.request` with byte-identity assertions against the fixture.

**Mitigation:** the E2E suite (T-5.1, T-5.3) covers all 6 routes end-to-end via real subprocess + `urllib`, including the AC-10 byte-identity canary (T-5.3) and the loopback-bind assertion (T-5.2). The byte-identity invariant additionally has a dedicated unit canary (T-3.5) that fails fast if anyone ever introduces string mutation into `views/memory.py`. The combined unit + E2E coverage exceeds what T-2.4 would have provided in isolation.

**Risk:** low. The HTTP layer is exercised end-to-end in E2E; only the explicit ephemeral-port integration shape is missing.

**Pointer:** T-2.4 marker remains `[ ]` in TASKS.md by design (documented here as the canonical deferred entry). A future release can land the integration test as a polish task without dependencies.

### Drift #2 — `_resolve_workspace()` ambiguity

**Description:** `dadaia_workspace/cli/commands/panel.py:20-25` defines `_resolve_workspace()` as a walk-up that stops at the FIRST `.dadaia/` directory found from `cwd`. The intent is to locate the workspace root (`/home/marco/workspace/dadaia/`) where `.dadaia/states/server_registry.json` lives. However, repos cloned inside the workspace also contain a `.dadaia/` directory (e.g. `repos/dadaia-workspace/.dadaia/` for agentic projections). Running `dadaia panel` from inside a repo (e.g. `repos/dadaia-workspace/`) therefore resolves `workspace_root` to the **repo itself**, which fails initialization because `server_registry.json` lives at workspace level, not repo level.

**Mitigation (workaround):** run `dadaia panel` from `/home/marco/workspace/dadaia/` (the workspace root). This is the documented operator path used for the visual approval; it works correctly.

**Recommended R2 fix:** distinguish workspace marker from repo marker. A workspace root must have BOTH `.dadaia/` AND `mnt/` AND `repos/` (or alternatively `.dadaia/agentic/manifest.json` + `repos/`); a repo root has only `.dadaia/` from agentic projection. The walk-up should continue past a `.dadaia/` that does not include the workspace markers. Tracked as `panel-workspace-resolver-fix` in `specs/backlog/candidates.md`.

**Severity:** low — operator-visible UX issue, no security or data impact. Not user-data-loss; only a confusing initialization failure when invoked from the wrong directory.

---

## Memory updates

- `specs/memory/product/panel.html` — **created** (new feature card). Documents:
  the panel CLI surface (`dadaia panel [--port 4999] [--no-open] [--bind 127.0.0.1]`),
  the 3 sections (Servers / Memories / Agents placeholder), the two-route reverse-proxy
  for memory rendering (`/memory/<slug>/<file>` verbatim + `/memory-view/<slug>/<file>`
  iframe wrapper) as the structural defense for SPEC-DOC-008 / NFR-2, the bind fix
  applied to the legacy `dadaia server dashboard` (FR-6 + FR-7), and the Release-2
  pointer for Agents & Workflows.
- `specs/memory/product/index.html` — **updated**: new entry in the catalog pointing
  to `panel.html`, inserted between `agent-sdd-alignment.html` and `academy.html`
  (proximity to surface-level identity features and visible product touch-points).
  Meta `Última atualização` now references `Closure: dadaia-workspace-panel-v1`.
- No other product memory HTMLs (`workspace-init`, `context-management`,
  `agent-orchestration`, `public-asset-distribution`, `workspace-doctor`,
  `specs-doctor`, `sdd-gate-v3`, `sdd-hotfix-track`, `agent-sdd-alignment`,
  `academy`, `workspace-portability`, `repos-catalog`, `server-registry`) were
  touched — this release shipped a brand-new surface, not a behaviour change to
  the existing features.
- `specs/memory/architecture.html` and `specs/memory/tech-stack.html` remain
  untouched — the panel adds a new feature module under the existing 4-layer
  architecture without introducing new core Protocols or infrastructure adapters,
  and adds zero runtime dependencies.

---

## Backlog returns

Adicionados a `specs/backlog/candidates.md § Candidatas ativas`:

- `dadaia-workspace-panel-r2-agents` — Surface installed agents and multi-agent
  workflows in the panel; replaces the Release-1 placeholder card (owner:
  product-engineer, contexto: `_archive/releases/dadaia-workspace-panel-v1/SPEC.md`
  § Future / SPEC §"Out-of-scope (Release-1)" first bullet). Status: candidato.
- `panel-workspace-resolver-fix` — Disambiguate `_resolve_workspace()` between
  workspace root and repo root so that `dadaia panel` works from any cwd inside
  the workspace, not only from `/home/marco/workspace/dadaia/` (owner:
  software-engineer, contexto: drift documented em
  `_archive/releases/dadaia-workspace-panel-v1/CLOSURE.md § Drifts #2`). Status:
  candidato.

Entry `dadaia-workspace-panel-v1` movida para `## Histórico` com data 2026-05-16 e
release-id correspondente (segue padrão de `sdd-hotfix-track-v1`).

---

## Archive decision

**MOVE** — diretório `specs/releases/dadaia-workspace-panel-v1/` é relocado para
`specs/_archive/releases/dadaia-workspace-panel-v1/` via `git mv` após este
CLOSURE.md ser gravado, memory updates concluídos e backlog atualizado. Pós-archive,
`specs/releases/ACTIVE.md` retorna para `release: none / phase: none` indicando
ausência de release ativa — esta é a última release do ciclo encerrada neste
walk; ACTIVE.md returns to `none / none`.
