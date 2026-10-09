---
name: dd-spec-navigator
description: >
  Ground a session and load the specs in canonical order: resolve the context,
  bootstrap memory (tech digest, catalog, 1-3 feature atoms, ARCHITECTURE.md, QUALITY.md),
  resolve the live release via _RELEASE.json, read SPEC, PLAN and job files and verify Approved. Use as the first act of any implementation,
  review, planning or closure task.
---

# dd-spec-navigator

The one session-grounding protocol: three phases, in order, before any source file is
read or any output written.

## Phase 1 — resolve the context

1. Open `specs/AGENTS.md` (the area's scoped law) and follow it.
2. Resolve the spec context: `.dadaia/.venv/bin/dadaia context show --json` (order: `.dadaia/AGENTS.md` §2).
3. Nothing resolves: a subagent stops and reports; the main thread binds (`.dadaia/AGENTS.md` §2).

## Phase 2 — memory bootstrap

1. The ctx-inject hook injects the bootstrap prefix (`ARCHITECTURE.md`'s `## Tech Stack` section + `catalog.json` digest) once per bind and on every re-bind; running standalone with no prefix, read `specs/memory/product/catalog.json`.
2. Read `<specs-dir>/constitution.md`, `<specs-dir>/memory/ARCHITECTURE.md` (its `## Tech Stack` included) and `<specs-dir>/memory/QUALITY.md`.
3. Scan the catalog's `tldr`/`summary` fields; pick and read the 1-3 feature atoms most relevant to the task — `specs/memory/product/<area>/<slug>.md`, plain Markdown; resolve a `[[slug]]` wikilink by lookup for `<slug>.md` under `specs/memory/`.
4. Re-read `ARCHITECTURE.md` deliberately when the decision touches layer boundaries, dependency rules, agent topology or schema contracts; a task self-contained in one well-understood component skips that re-read.
5. Read memory only, since atoms change at closure from the code diff; its writers: `specs/memory/AGENTS.md`.

## Phase 3 — resolve the live release and its candidate

1. Read `<specs-dir>/releases/<release-id>/_RELEASE.json` — read its `phase`; the live candidate is the highest `rc-<N>/` beside it (`ls -d <specs-dir>/releases/[0-9]*/rc-* | sort -V | tail -1`).
2. No `_RELEASE.json` under `<specs-dir>/releases/`: stop before implementation and inform the operator.
3. Read the SPEC; add the PLAN when planning or implementing and every job file when implementing; read `_RELEASE.json`'s `log` when `phase` is `CLOSURE`.
4. Before any implementation, the precondition is `specs/AGENTS.md` §3; stop and name the missing item otherwise.

## Done when

- `.dadaia/.venv/bin/dadaia context show --json` names the context, and the live `rc-<N>/` is named.
- The handoff's `self_pull.refs` lists `constitution.md`, `ARCHITECTURE.md`, `QUALITY.md` and the 1-3 atoms read (`.dadaia/handoff/AGENTS.md` §1).
- The `specs/AGENTS.md` §3 precondition holds, or the gap was reported first.

## References

- `python3 .agents/skills/dd-spec-navigator/scripts/memory.py check --specs <specs-dir>` — run before trusting the catalog digest; `catalog generate` and `drift` are closure verbs (`dd-release-implementation`'s `MEMORY-UPDATE.md`).
- `specs/AGENTS.md` — canon and status tokens; `.dadaia/AGENTS.md` — context resolution order.
