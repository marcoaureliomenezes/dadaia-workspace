---
name: dadaia-step0-memory-bootstrap
description: >
  Mandatory memory bootstrap protocol for every agent, executed before any
  implementation, review, or report. Loads the tech-stack + feature catalog
  (injected by the ctx-inject hook or self-pulled) and ensures the agent reads the
  1-3 most relevant feature atoms and the architecture atom before starting work.
  Updated for the markdown source world: atoms are .md files read directly
  (no strip pass needed); catalog.json is generated from frontmatter; [[slug]]
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

## Protocol

### Precondition — Is the bootstrap already injected?

A lean bootstrap (tech-stack + catalog) is injected once per session by the
ctx-inject hook (`dadaia_workspace.hooks.ctx_inject`, wired on all harnesses). If it is
present in your context, skip the self-pull step below and go directly to Step 1.

If you are running standalone, or in any environment where the ctx-inject hook has
not run, self-pull manually:

```
Read: specs/memory/tech-stack.md          # verbatim; no strip pass needed
Read: specs/memory/product/catalog.json   # machine index generated from frontmatter
```

### Step 1 — Scan the catalog and identify relevant features

Read `specs/memory/product/catalog.json`. For each entry, the `tldr` field
provides a one-sentence first-pass scan. Use `summary` to decide whether a
feature warrants a full self-pull.

Identify the **1 to 3 features** most relevant to your current task. Note their
`slug` values — you will self-pull the corresponding atom in Step 3.

If `catalog.json` is absent (e.g. during migration), fall back to reading
`specs/memory/product/index.md` verbatim.

### Step 2 — Self-pull architecture before any architectural decision

`architecture.md` is NOT injected by the ctx-inject hook (it is large). You MUST
read it before any decision that touches:

- Layer boundaries or cross-layer dependency rules
- Agent topology or dispatch graphs
- Schema contracts between components
- Any structural or design decision

```
Read: specs/memory/architecture.md
```

Skip this step only if your task is entirely self-contained within a single
well-understood component and makes no cross-layer or design decisions.

### Step 3 — Self-pull the relevant feature atoms

For each slug identified in Step 1:

```
Read: specs/memory/product/<slug>.md
```

Atoms are plain Markdown with YAML frontmatter. Read them directly — no HTML
stripping, no conversion needed. `[[slug]]` wikilinks in atom bodies are
plain text; resolve them by reading `specs/memory/<slug>.md` if needed.

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
  `product-engineer` during the DEFINITION and CLOSURE phases (constitution §13).
