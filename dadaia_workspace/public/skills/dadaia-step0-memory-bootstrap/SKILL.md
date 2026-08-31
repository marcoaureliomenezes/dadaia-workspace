---
name: dadaia-step0-memory-bootstrap
description: >
  Mandatory memory bootstrap protocol for every agent, executed before any
  implementation, review, or report. Grounds the session in the tech-stack digest and
  feature catalog (injected by the ctx-inject hook, or self-pulled), then reads the
  1-3 most relevant feature atoms — plain-Markdown files under
  specs/memory/product/<area>/ whose [[slug]] wikilinks resolve to sibling atoms —
  and ARCHITECTURE.md whenever the work is structural.
tldr: "Ground in tech-stack + catalog (hook-injected), self-pull 1-3 relevant feature atoms, self-pull ARCHITECTURE.md when structural."
applyTo: "**"
---

# dadaia-step0-memory-bootstrap

## 1. When

- Once per session, as the very first action, before reading any source file or writing any output.
- Before any implementation, review, or report task.

## 2. Steps

1. Rely on the ctx-inject hook (`dadaia_workspace.hooks.ctx_inject`) for the bootstrap prefix (tech-stack + `catalog.json`).
2. Expect the hook to fire once per bind, and again on every re-bind.
3. If running standalone with no ctx-inject prefix, self-pull `specs/memory/product/catalog.json` directly.
4. Scan the catalog's `tldr`/`summary` fields; pick the 1-3 features most relevant to the task.
5. Self-pull each chosen atom: `specs/memory/product/<area>/<slug>.md` — plain Markdown, read directly.
6. Resolve any `[[slug]]` wikilink by recursive lookup for `<slug>.md` under `specs/memory/`.
7. Fall back to `specs/memory/product/index.md` if `catalog.json` is absent (migration).
8. Self-pull `specs/memory/ARCHITECTURE.md` when the decision touches layer boundaries or dependency rules.
9. Self-pull `specs/memory/ARCHITECTURE.md` when the decision touches agent topology, dispatch graphs, or schema contracts.
10. Skip the architecture read when the task is self-contained within one well-understood component.

## 3. Done when

- The 1-3 relevant feature atoms are read before any implementation, review, or report begins.
- `ARCHITECTURE.md` is read whenever the task is structural, skipped otherwise.
- No memory atom is edited unless this session is `product-engineer` in DEFINITION or CLOSURE phase.

## 4. References

- `dadaia_workspace.hooks.ctx_inject` — the deterministic load sequence.
- `DADAIA.md` §6 — memory ownership and phase-gated writes.
- Atom files are `.md`, never `.html` — treat any `.html` atom reference as stale.
