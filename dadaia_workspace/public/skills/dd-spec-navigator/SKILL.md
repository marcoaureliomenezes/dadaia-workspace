---
name: dd-spec-navigator
description: >
  Ground a session and load the specs in canonical order: resolve the context,
  bootstrap memory (tech digest, catalog, 1-3 feature atoms, ARCHITECTURE.md when the
  work is structural), resolve the live release via _RELEASE.json, read
  SPEC/PLAN/TASKS and verify Aprovado. Use as the first act of any implementation,
  review, planning or closure task.
---

# dd-spec-navigator

The one session-grounding protocol: three phases, in order, before any source file is
read or any output written.

## Phase 1 — resolve the context

1. Resolve the spec context: `DADAIA_CONTEXT` env var, else your session binding
   (`dadaia context show --json`), else the repo containing your cwd.
2. Binding is optional — only zero ALIVE contexts stops navigation; alert the
   operator then, and only then.

## Phase 2 — memory bootstrap

1. The ctx-inject hook (`dadaia_workspace.hooks.ctx_inject`) injects the bootstrap
   prefix (tech-stack digest + `catalog.json` digest) once per bind and on every
   re-bind; running standalone with no prefix, self-pull
   `specs/memory/product/catalog.json`.
2. Read `<specs-dir>/constitution.md`, `<specs-dir>/memory/ARCHITECTURE.md` and
   `<specs-dir>/memory/TECHSTACK.md`.
3. Scan the catalog's `tldr`/`summary` fields; pick and read the 1-3 feature atoms
   most relevant to the task — `specs/memory/product/<area>/<slug>.md`, plain
   Markdown; resolve a `[[slug]]` wikilink by lookup for `<slug>.md` under
   `specs/memory/`.
4. Re-read `ARCHITECTURE.md` deliberately when the decision touches layer boundaries,
   dependency rules, agent topology or schema contracts; a task self-contained in one
   well-understood component skips that re-read.
5. Memory is read-only here: atoms are written only by `product-engineer` in
   DEFINITION/CLOSURE phase (`DADAIA.md` §6).

## Phase 3 — resolve the live release and its trio

1. Read `<specs-dir>/releases/<release-id>/_RELEASE.json` — its `phase` field is the
   resolver; the live candidate's trio is always flat at the release root, `rc-N/`
   folders are archived candidates.
2. No state-document-carrying release directory: stop before implementation and
   inform the operator.
3. Read `SPEC.md`; add `PLAN.md` when planning or implementing; add `TASKS.md` when
   implementing; read `_RELEASE.json`'s `log` when `phase` is `CLOSURE`/`ARCHIVED`.
4. Verify every loaded SPEC/PLAN/TASKS carries `**Status:** Aprovado` before any
   implementation; stop and name the unapproved artifact otherwise.

## Done when

- Context and live release are resolved and named.
- Constitution, ARCHITECTURE.md, TECHSTACK.md and the 1-3 relevant atoms are read.
- Every SPEC/PLAN/TASKS in scope carries `**Status:** Aprovado`, or the gap was
  reported first.

## References

- `DADAIA.md` §3 — context resolution order; §6 — status tokens, memory ownership.
- `dd-release-implementation` (`RELEASE-EVENTS.md`) — `_RELEASE.json` shape.
- `_archive/` and `backlog/` are read-only history — never a source of approval.
