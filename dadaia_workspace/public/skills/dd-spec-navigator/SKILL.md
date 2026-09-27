---
name: dd-spec-navigator
description: >
  Ground a session and load the specs in canonical order: resolve the context,
  bootstrap memory (tech digest, catalog, 1-3 feature atoms, ARCHITECTURE.md when the
  work is structural), resolve the live release via _RELEASE.json, read
  SPEC/PLAN/TASKS and verify Approved. Use as the first act of any implementation,
  review, planning or closure task.
---

# dd-spec-navigator

The one session-grounding protocol: three phases, in order, before any source file is
read or any output written.

## Phase 1 — resolve the context

1. Open `specs/AGENTS.md` (the area's scoped law) and follow it.
2. Resolve the spec context: `DADAIA_CONTEXT` env var, else your session binding (`.dadaia/.venv/bin/dadaia context show --json`), else the repo containing your cwd.
3. Nothing resolves (unbound, cwd outside `repos/<slug>/`): bind with `.dadaia/.venv/bin/dadaia context bind <ctx>` — no ALIVE context is ever borrowed; zero ALIVE contexts: alert the operator.

## Phase 2 — memory bootstrap

1. The ctx-inject hook (`dadaia_workspace.hooks.ctx_inject`) injects the bootstrap prefix (`ARCHITECTURE.md`'s `## Tech Stack` section + `catalog.json` digest) once per bind and on every re-bind; running standalone with no prefix, self-pull `specs/memory/product/catalog.json`.
2. Read `<specs-dir>/constitution.md`, `<specs-dir>/memory/ARCHITECTURE.md` (its `## Tech Stack` included) and `<specs-dir>/memory/QUALITY.md`.
3. Scan the catalog's `tldr`/`summary` fields; pick and read the 1-3 feature atoms most relevant to the task — `specs/memory/product/<area>/<slug>.md`, plain Markdown; resolve a `[[slug]]` wikilink by lookup for `<slug>.md` under `specs/memory/`.
4. Re-read `ARCHITECTURE.md` deliberately when the decision touches layer boundaries, dependency rules, agent topology or schema contracts; a task self-contained in one well-understood component skips that re-read.
5. Memory is read-only here: atoms are written only by `dd-product-engineer` in DEFINITION/CLOSURE phase (`specs/memory/AGENTS.md`) — discipline the audit measures, never a gate block.

## Phase 3 — resolve the live release and its trio

1. Read `<specs-dir>/releases/<release-id>/_RELEASE.json` — its `phase` field is the resolver; the live candidate's trio is always flat at the release root.
2. No state-document-carrying release directory: stop before implementation and inform the operator.
3. Read the SPEC; add the PLAN when planning or implementing, the TASKS when implementing; read `_RELEASE.json`'s `log` when `phase` is `CLOSURE`/`ARCHIVED`.
4. Verify every loaded SPEC/PLAN/TASKS carries `**Status:** Approved` before any implementation; stop and name the unapproved artifact otherwise.

## Done when

- Context and live release are resolved and named.
- Constitution, ARCHITECTURE.md, QUALITY.md and the 1-3 relevant atoms are read.
- Every SPEC/PLAN/TASKS in scope carries `**Status:** Approved`, or the gap was
  reported first.

## References

- Script: `python3 .agents/skills/dd-spec-navigator/scripts/memory.py` — `catalog generate`, `check`, `drift --since <sha>`: the catalog's ONE writer.
- `specs/AGENTS.md` — canon and status tokens; `.dadaia/AGENTS.md` — context resolution order.
- `dd-release-implementation` (`RELEASE-EVENTS.md`) — `_RELEASE.json` shape.
- `_archive/` and `backlog/` are read-only history — never a source of approval.
