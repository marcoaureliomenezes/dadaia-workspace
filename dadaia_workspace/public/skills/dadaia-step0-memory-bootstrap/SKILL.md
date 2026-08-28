---
name: dadaia-step0-memory-bootstrap
description: >
  Mandatory memory bootstrap protocol for every agent, executed before any
  implementation, review, or report. Loads the tech-stack + feature catalog
  (injected by the ctx-inject hook or self-pulled) and ensures the agent reads the
  1-3 most relevant feature atoms and the architecture atom before starting work.
  Updated for the markdown source world: atoms are .md files, read as plain text;
  catalog.json is generated from frontmatter; [[slug]]
  wikilinks in atom bodies resolve to specs/memory/<slug>.md.
applyTo: "**"
---

# dadaia-step0-memory-bootstrap

## Purpose

Before any agent begins implementation, review, or report work, it must ground
itself in the current product state. This skill defines that grounding protocol
for the markdown-source memory world (`memory-markdown-source-v1` and later).

Execute this skill **once per session**, as the very first action, before reading
any source file or writing any output.

---

## Deterministic load sequence (the ctx-inject hook)

The lean bootstrap prefix (tech-stack verbatim + `catalog.json`) is injected once per
session by the ctx-inject hook (`dadaia_workspace.hooks.ctx_inject`), bind-driven: it
fires again only when the session record's bind timestamp is newer than the session's
own sentinel (so a re-bind — even to the same context — re-injects). When
present, that prefix is already in your context — no separate assembly step to run.

What this skill keeps is the **judgment** the hook cannot make for you: *read the
relevant atoms before acting.* The prefix gives you the catalog; choosing which atoms
the task actually needs, and reading them before deciding, is yours.

## The judgment — read the relevant atoms before acting

1. **Scan the catalog, pick 1-3 relevant atoms.** From
   `specs/memory/product/catalog.json` (in your context via the prefix; self-pull it if
   running standalone with no ctx-inject), use each entry's `tldr`/`summary` to identify
   the **1 to 3 features** most relevant to your current task. Self-pull each chosen
   atom: `specs/memory/product/<area>/<slug>.md`. Atoms are plain Markdown — read
   directly, no stripping. `[[slug]]` wikilinks resolve to any `<slug>.md` file found
   under `specs/memory/` (recursive lookup). If
   `catalog.json` is absent (migration), fall back to `specs/memory/product/index.md`.
2. **Self-pull architecture only when the decision needs it.** `architecture.md` is NOT
   in the prefix (it is large). Read `specs/memory/architecture.md` before any decision
   touching layer boundaries / cross-layer dependency rules, agent topology or dispatch
   graphs, schema contracts, or any structural design choice — and skip it when the task
   is self-contained within one well-understood component.

The discipline: do not begin implementation, review, or report until you have grounded
yourself in the atoms the task touches. Skipping the read means working from stale or
missing context.

---

## Guardrails

- Do NOT begin any implementation, review, or report until this protocol is
  complete. Skipping it means working from stale or missing context.
- Atom files are `.md` (not `.html`). Any reference to `.html` atom paths is
  stale and should be treated as `.md`.
- `catalog.json` is the machine index. Prefer it over reading all atom files
  individually for an initial scan.
- `architecture.md` is large. Self-pull it only when needed (Step 2 criteria
  above), not for every task.
- Never edit memory atoms. They are write-locked for all agents except
  `product-engineer` during the DEFINITION and CLOSURE phases (constitution, Memory Canon).
