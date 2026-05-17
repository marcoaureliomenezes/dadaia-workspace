# Spec: Release — dadaia-workspace-panel-v1

> **Status:** Em revisão
> **Release ID:** dadaia-workspace-panel-v1
> **Phase:** SPEC (not yet ACTIVE — see "Lifecycle placement" below)
> **Owner:** product-engineer
> **Created:** 2026-05-16
> **Source SPEC:** input prose `specs/backlog/dadaia-workspace-panel.md` (promoted, file deleted on SPEC approval); parent feature `_archive/legacy-features/dev-server-registry/SPEC.md`
> **Grill source-of-truth:** `~/.claude/plans/feature-dadaia-parsed-flame.md` (Q1–Q7 resolved)

---

## Lifecycle placement (Option A)

Decision recorded by product-engineer at SPEC time:

- The dadaia SDD lifecycle accepts **one ACTIVE release at a time**. The currently
  active release is `agent-sdd-alignment-v1` in `phase: TASKS`. Implementation of that
  release is in progress and must not be interrupted.
- This SPEC is written **now**, in `Em revisão` status, so that the downstream specialist
  agents (software-architect, frontend-engineer) can produce their reports in parallel.
- `specs/releases/ACTIVE.md` is **not touched** by this SPEC. It will flip to
  `release: dadaia-workspace-panel-v1 / phase: SPEC` only after `agent-sdd-alignment-v1`
  reaches `CLOSURE` (per the lifecycle constraint).
- `PLAN.md` and `TASKS.md` for this release are **not** created in this pass. They are
  produced by product-engineer after the architect + frontend reports land.

This obeys the constitution rule "NUNCA implemente uma feature sem SPEC.md aprovado" and
the release-lifecycle rule "one active release at a time" simultaneously — the directory
exists in `specs/releases/` but is not announced as ACTIVE.

---

## Problem statement

dadaia-workspace today is a Python CLI plus an agentic asset system: `dadaia` Typer
commands, manifest-projected agents/skills/workflows, JSON state files. The product
surface is invisible without reading markdown or running CLI commands. New operators
and even the operator himself lose context across the 8 active Spec Context Projects;
the existing `dadaia server dashboard` at `http://localhost:4999` is a single utility
page, not a workspace identity.

The operator framed this release as **identity-defining**, not a side feature. The
Dadaia Workspace Panel is the unified local UI that gives the workspace a visible face
and surfaces the three pillars of the product: running dev servers across projects,
the current state of each active Spec Context Project (architecture, tech-stack,
product features served as memory HTML), and — in Release-2, with only a placeholder
in this release — the catalog of installed agents and multi-agent workflows.

Release-1 is intentionally narrow: it ships the panel shell, the Servers section
(evolving the existing `server dashboard`), the Memories section (reverse-proxy
serving of memory HTML with a CSS-injected back button), and a placeholder card for
Agents & Workflows. The visual identity is inherited verbatim from
`specs/memory/architecture.html` so the panel feels coherent with the content it
serves. Stdlib-only (no FastAPI/Flask/JS framework) — the panel must remain trivial
to maintain.

---

## Glossary

| Termo | Definição |
|---|---|
| **Panel** | Local single-page web UI at `http://127.0.0.1:4999/` started by `dadaia panel`. Identity-defining surface of the workspace. Foreground process, Ctrl+C shutdown. |
| **Section** | One of the 3 top-level areas of the panel: `Servers`, `Memories`, `Agents & Workflows`. Release-1 ships Servers + Memories functional; Agents & Workflows is a placeholder card. |
| **Memory rendering (reverse proxy + full-page)** | The panel reads memory HTML files (`specs/memory/architecture.html`, `specs/memory/tech-stack.html`, `specs/memory/product/*.html`) from each active Spec Context Project's repo on disk and serves them verbatim at `/memory/<context-slug>/<path>`. A "← Voltar ao Painel" header is injected as a `position: fixed` CSS overlay — the `<body>` of the memory HTML is never mutated, preserving the atomicity invariant enforced by SPEC-DOC-008. |
| **Active Context surface** | The list of Spec Context Projects with `state: ativo` in `.dadaia/states/spec_contexts.json`. The panel surfaces all of them; the one with `is_primary=True` is visually highlighted. Contexts in `inativo` are filtered out. |
| **Server Registry surface** | The Servers section of the panel reads `.dadaia/states/server_registry.json` (the existing store from the archived `dev-server-registry` feature), groups entries by `project`, and auto-refreshes every 5 seconds. |

---

## In-scope (Release-1)

The Release-1 surface is exactly three sections, in this order, behind the
`dadaia panel` command:

1. **Servers** — functional. Evolves the existing `dadaia server dashboard` page. Reads
   `.dadaia/states/server_registry.json`, groups by `project`, shows port / project /
   URL (clickable) / status / TTL remaining / PID. Auto-refreshes every 5s. Empty
   state shows guidance to register a server.
2. **Memories** — functional. One card per active Spec Context Project, primary
   highlighted. Each card links to `architecture.html`, `tech-stack.html`,
   `product/index.html` of that context. Clicking a link opens the memory HTML
   full-page at `/memory/<context-slug>/<file>` with a CSS-injected back button.
   The body of the memory HTML is served verbatim (no mutation).
3. **Agents & Workflows (placeholder)** — a single card with the copy
   `"Em breve — Release-2"`. The placeholder card IS in-scope for Release-1; the
   functional content (agent catalog, workflow invocation surface) is Release-2.

CLI surface (in-scope):

- New: `dadaia panel [--port 4999] [--no-open] [--bind 127.0.0.1]`
- Modified: `dadaia server dashboard` — emits deprecation warning pointing at
  `dadaia panel`, behavior preserved for one release. Bind fix applied (loopback only).

---

## Out-of-scope (Release-1)

- Functional Agents & Workflows section content (catalog, invocation surface). Goes
  to Release-2.
- Daemon / background process mode. Panel is foreground only in Release-1.
- LAN bind (`--bind 0.0.0.0`) and token auth. Future opt-in if multi-machine access
  is ever needed. Release-1 is 100% loopback.
- Visual brand exploration beyond the tokens inherited from
  `specs/memory/architecture.html`. No new design system; no logo; no marketing
  surface.
- Removal of `dadaia server dashboard`. Release-1 only deprecates with a warning.
  Actual removal lands in a later release.
- Registration of the panel process itself in `server_registry.json`. The registry
  is for project dev servers, not workspace tooling.
- Multi-process / multi-instance panel. Single foreground process per workspace.
- Any change to memory HTML content, to `dadaia specs doctor`, or to the gate v3
  fase-gated write rules. Release-1 only **reads** memory files.

---

## Functional Requirements

Each FR is anchored to the grill decision (Q1–Q7) that justifies it.

- **FR-1 (Q2, Q4, Q7):** The system shall expose a new CLI command
  `dadaia panel [--port 4999] [--no-open] [--bind 127.0.0.1]`. The command starts an
  HTTP server in the foreground, prints the URL, opens the user's browser unless
  `--no-open` is passed, and blocks until Ctrl+C. On Ctrl+C, the server shuts down
  cleanly without leaving the port reserved.

- **FR-2 (Q3, Q4, Q5):** The HTTP server shall route exactly these endpoints:

  | Route | Response |
  |---|---|
  | `GET /` | The panel index page (HTML, 3 sections, embedded auto-refresh JS) |
  | `GET /api/servers` | JSON snapshot of `.dadaia/states/server_registry.json` entries |
  | `GET /api/contexts` | JSON list of active Spec Context Projects (slug, name, repo path, branch, `is_primary`) |
  | `GET /memory/<slug>/<path>` | Memory HTML or asset from `repos/<slug>/specs/memory/<path>` (or `specs/assets/...` for images); HTML is served verbatim with a CSS-injected back-button overlay |
  | `GET /static/<file>` | Panel CSS / JS assets (light, ~150 total lines) |

  Any unknown route returns HTTP 404 with a minimal HTML body.

- **FR-3 (Q1, Q5):** The Servers section shall:
  - Show one row per entry in `server_registry.json`, with columns Port, Project,
    URL (clickable, `target="_blank"`), Status (`active` / `stale`), TTL remaining,
    PID.
  - Group rows visually by `project`. Best-effort match: if `project` equals the
    `repo_slug` of an active context, that context's name labels the group;
    otherwise rows fall into an "Outros" group.
  - Auto-refresh client-side every 5 seconds by fetching `/api/servers` (no
    full-page meta-refresh — smoother UX than the legacy dashboard).
  - Show the empty-state hint `"Nenhum servidor rodando. Rode 'dadaia server register --port X --project Y'."` when the registry has zero entries.

- **FR-4 (Q1, Q3, Q5, Q6):** The Memories section shall:
  - Render one card per active Spec Context Project (state = `ativo`). The primary
    context (`is_primary=True`) is visually highlighted (border accent + "primary"
    label).
  - Each card shows: context name, `repo_slug`, current branch (best-effort via
    `git rev-parse --abbrev-ref HEAD`, no failure if git not available), and three
    links: `architecture.html`, `tech-stack.html`, `product/index.html`.
  - Clicking a link navigates to `/memory/<slug>/<file>` as a full-page view (not
    an iframe, not a modal — bookmarkable URLs).
  - The memory HTML body is served **verbatim**; the back button is overlaid via a
    CSS `position: fixed` block injected before `</head>` (style + a snippet that
    creates the anchor via DOM after `DOMContentLoaded`, OR a wrapping `<header>` is
    inserted **outside** any body content that would be considered part of the
    atomic content — implementation chooses the least invasive approach that
    keeps `dadaia specs doctor` passing). The contract this FR commits to: the
    raw file on disk is unchanged AND every check inside `_check_memory_atomicity`
    continues to return 0 issues for every memory HTML in every active context's
    `specs/memory/` tree.
  - Relative `<img src="...">` references inside the memory HTML must resolve. The
    server maps `specs/assets/<scope>/<id>.png` requests under the same context
    slug — i.e. an image referenced as `../assets/foo/bar.png` from
    `memory/architecture.html` resolves to `repos/<slug>/specs/assets/foo/bar.png`.

- **FR-5 (Q1):** The Agents & Workflows section shall render exactly one card with
  the copy `"Em breve — Release-2"` and a muted style indicating "not yet
  available". No links, no JS interaction. The placeholder establishes the
  navigation layout for Release-2 without committing to Release-2 design now.

- **FR-6 (Q2):** The existing `dadaia server dashboard` command shall:
  - Continue to run and serve the legacy dashboard at the chosen port (behavior
    preserved for one release).
  - Print a deprecation warning to stderr on every invocation:
    `"[deprecation] 'dadaia server dashboard' will be removed in a future release. Use 'dadaia panel' instead."`
  - Be marked deprecated in `--help` text and in the Typer command docstring.

- **FR-7 (Q7):** Both `dadaia panel` and `dadaia server dashboard` shall bind the
  HTTP server explicitly to `127.0.0.1`, not to the stdlib default of `0.0.0.0`.
  This is a **security fix** to the existing dashboard (footgun in the current
  `http.server.HTTPServer` instantiation) and a **hard requirement** for the new
  panel. The `--bind` flag of `dadaia panel` accepts only `127.0.0.1` in Release-1;
  any other value rejects with `"Release-1 supports loopback bind only"`.

---

## Non-Functional Requirements

- **NFR-1 (stdlib only):** No new runtime dependencies. The panel uses
  `http.server` from stdlib, `pathlib`, `json`. No FastAPI, Flask, Starlette, Jinja
  (the HTML is rendered via Python f-strings or `string.Template`). No JS
  framework, no npm. The only external resource permitted is the Mermaid CDN that
  the served memory HTML already references — and that resource is loaded by the
  served HTML, not by the panel itself.

- **NFR-2 (memory atomicity preserved):** After Release-1 ships and runs in
  production, `dadaia specs doctor` shall continue to return `0 errors`. Specifically
  the `_check_memory_atomicity` check (SPEC-DOC-008) shall remain green for every
  HTML under every active context's `specs/memory/` tree. The panel reads memory
  HTML files; it never writes to them.

- **NFR-3 (coverage):** Coverage for new code under `dadaia_workspace/features/panel/`
  shall meet or exceed the project minimum of 80% (per constitution §"Qualidade de
  Código"). Tests live under `tests/unit/features/panel/` and
  `tests/e2e/features/test_panel.py`.

- **NFR-4 (foreground, clean shutdown):** The `dadaia panel` process runs in the
  foreground and shuts down cleanly on SIGINT / SIGTERM within 2 seconds, freeing
  the port. No background mode, no daemonization, no PID file in Release-1. The
  process is **not** registered in `server_registry.json`.

- **NFR-5 (visual identity):** The panel CSS adopts visual tokens (palette,
  typography, spacing) inherited from `specs/memory/architecture.html`. The
  resulting page must look continuous with the memory pages a user navigates to.
  The frontend-engineer report decides exact tokens; the constraint is: when the
  operator clicks from the panel into a memory HTML and back, the visual feel is
  continuous — no jarring style change.

- **NFR-6 (quality gates):** All new code shall pass `ruff format`, `ruff check`,
  `mypy --strict` per constitution §"Qualidade de Código". CLI errors follow the
  constitution's error message contract (capability + context + next safe step).

- **NFR-7 (4-layer architecture):** The panel feature respects the existing 4-layer
  rule (CLI → features → core ← infrastructure, all wired in `container.py`). The
  software-architect report (next agent in the dispatch sequence) defines the
  exact module boundaries and any new Protocols in `core/`.

---

## Acceptance criteria

Reproduced verbatim from the grill plan §"Verificação end-to-end". Each item is
verifiable; CLOSURE evidence will be captured per item.

- [ ] `cd repos/dadaia-workspace && dadaia specs doctor` → `0 errors` (warnings
      acceptable as long as count does not regress from baseline at SPEC time:
      currently `0 errors, 0 warnings`).
- [ ] `dadaia panel --port 4999` opens the browser at `http://127.0.0.1:4999/`,
      page renders the 3 sections, primary context is visually highlighted in
      Memories.
- [ ] `nc -z 127.0.0.1 4999` → succeeds; `nc -z <LAN-ip> 4999` → fails. Same check
      passes for `dadaia server dashboard` after the bind fix.
- [ ] Clicking `architecture.html` in a context card navigates to
      `http://127.0.0.1:4999/memory/<slug>/architecture.html`. The "← Voltar ao
      Painel" overlay is visible. Mermaid diagrams render (CDN). Relative images
      load (resolved under `repos/<slug>/specs/assets/`).
- [ ] `dadaia server register --port 3000 --project <some-slug>` followed by
      observing the panel within 5 seconds: the new entry appears in the Servers
      section grouped under the matching context (or under "Outros").
- [ ] `dadaia server dashboard` prints the deprecation warning to stderr and
      still serves the legacy dashboard correctly bound to `127.0.0.1`.
- [ ] `pytest tests/` → all green; coverage for `features/panel/` ≥ 80%.
- [ ] No new entries in `pyproject.toml`'s `[tool.poetry.dependencies]` block.
- [ ] On Ctrl+C during `dadaia panel`, the process exits with code 0 and port 4999
      is free within 2 seconds (verified via `lsof -i :4999`).
- [ ] The raw bytes of `repos/<slug>/specs/memory/architecture.html` are byte-for-byte
      identical before and after a request to `/memory/<slug>/architecture.html`
      (no body mutation — invariant required by NFR-2).
- [ ] `specs/backlog/dadaia-workspace-panel.md` is removed (promoted into this
      SPEC); `specs/backlog/candidates.md` records the Release-2 follow-up
      (Agents & Workflows section) — to be added at CLOSURE of Release-1, not now.

---

## Open Questions (resolved)

All seven grill questions are RESOLVED. Source-of-truth for full reasoning:
`~/.claude/plans/feature-dadaia-parsed-flame.md`.

| # | Theme | Resolution |
|---|---|---|
| Q1 | Scope & phasing of Release-1 | Release-1 = Servers + Memories functional, Agents & Workflows as a placeholder card. Release-2 ships the functional Agents & Workflows. |
| Q2 | Naming & continuity vs `dadaia server dashboard` | New command `dadaia panel` is the single entry point. The Servers section evolves the legacy dashboard. `dadaia server dashboard` emits a deprecation warning for one release and is removed in a later release. |
| Q3 | Memory rendering mode | Reverse proxy + full-page. Memory HTML served verbatim at `/memory/<slug>/<path>`; back button injected via CSS overlay only — the served body is byte-identical to the file on disk (NFR-2). |
| Q4 | Running model | Foreground, blocking, port 4999 by default. `--no-open` skips browser launch. Not registered in `server_registry.json`. |
| Q5 | Multi-context surface | The panel surfaces ALL contexts in `ativo` state. The `is_primary=True` context is highlighted. `inativo` contexts are filtered out. |
| Q6 | Visual identity authority | Inherit palette and typography from `specs/memory/architecture.html`. No brand exploration. Coherent visual feel between panel and memory pages. |
| Q7 | Security boundary | Bind `127.0.0.1` only, no auth. Loopback closes 100% of LAN surface. Same fix applied to `dadaia server dashboard` in this release. `--bind 0.0.0.0 --token X` is a future opt-in, not a Release-1 feature. |

---

## Dependencies

- **Hard dependency on `agent-sdd-alignment-v1`:** that release is currently
  ACTIVE in `phase: TASKS`. This release cannot become ACTIVE until
  `agent-sdd-alignment-v1` reaches CLOSURE (lifecycle constraint: one ACTIVE
  release at a time). The two releases do not touch overlapping files
  (`agent-sdd-alignment-v1` modifies agents/skills/workflows + `doctor.py`; this
  release adds `features/panel/` + modifies CLI), so parallel SPEC-time work is
  safe.
- **Parent feature (archived):** `_archive/legacy-features/dev-server-registry/SPEC.md`
  is the original Draft for the server registry. The Servers section of this
  panel evolves the surface that feature produced. The archived spec is cited as
  historical context; it is not promoted to Aprovado.
- **Memory contract dependency:** the panel depends on the memory HTML contract
  documented in `specs/memory/architecture.html` and enforced by
  `dadaia specs doctor` (SPEC-DOC-008, SPEC-DOC-010). If that contract changes
  (e.g. memory HTMLs gain dynamic includes), the panel's reverse-proxy serving
  logic may need adjustment.
- **No new runtime deps**; no new infrastructure; no CI changes in Release-1.
- **Reports required before PLAN.md is written** (per the grill plan dispatch
  sequence):
  1. `software-architect` — architectural placement of `features/panel/`,
     contract server↔context for the FR-3 grouping, request-flow diagram.
  2. `frontend-engineer` — static HTML mockup of the 3 sections using tokens
     inherited from `specs/memory/architecture.html`.

---

## Risks

| Risk | Mitigation |
|---|---|
| Back-button injection accidentally mutates memory HTML body and breaks SPEC-DOC-008 atomicity | NFR-2 commits to byte-identical serving; acceptance criterion explicitly tests it; software-engineer task includes a unit test that snapshots the served bytes vs the file bytes. |
| Best-effort `project` ↔ `repo_slug` match in FR-3 leads to confusing "Outros" groupings | software-architect report (next dispatch step) chooses between best-effort (Release-1) and enforced validation (future release with deprecation path). Decision documented in PLAN.md. |
| Stdlib `http.server` cannot serve concurrent requests well | Single-user, single-machine, single-tab usage profile. `ThreadingHTTPServer` from stdlib is acceptable if needed; still stdlib-only. |
| Mermaid CDN being offline breaks memory rendering | Out-of-scope for Release-1 (operator accepted the existing memory HTML contract); same risk exists today. |
| Bind fix to `dadaia server dashboard` regresses a workflow that relied on LAN access | Operator confirmed (Q7) that LAN access was never desired — current default is a footgun. Acceptance criterion verifies LAN closed; if anyone notices, they file a bug and use future opt-in `--bind 0.0.0.0`. |

---

## References

- **Grill plan (source-of-truth for Q1–Q7 resolutions):**
  `~/.claude/plans/feature-dadaia-parsed-flame.md`
- **Constitution:** `specs/constitution.md`
- **Memory contract:** `specs/memory/architecture.html`, `specs/memory/tech-stack.html`,
  `specs/memory/product/index.html`
- **Doctor invariants (esp. SPEC-DOC-008 atomicity, SPEC-DOC-010 image links):**
  `dadaia_workspace/features/specs/doctor.py:604` and `:628`
- **Parent feature (archived):** `specs/_archive/legacy-features/dev-server-registry/SPEC.md`
- **Existing dashboard being subsumed:**
  `dadaia_workspace/features/server_registry/dashboard.py`
- **Existing dashboard CLI being deprecated:**
  `dadaia_workspace/cli/commands/server.py` (`dashboard` subcommand)
- **Previous release (currently ACTIVE):**
  `specs/releases/agent-sdd-alignment-v1/SPEC.md`
- **Lifecycle model:** `specs/releases/sdd-release-lifecycle-v1/SPEC.md`
- **Backlog input (will be deleted at SPEC approval):**
  `specs/backlog/dadaia-workspace-panel.md`
