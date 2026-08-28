---
name: memory-ctx
description: Universal Codex memory bootstrap adapter. Fires before all role-specific adapters (design-ctx, frontend-ctx). Injects tech-stack and feature catalog into every Codex session.
---

# memory-ctx — Universal Memory Bootstrap Adapter (Codex)

Inject the workspace memory context at the start of every Codex session — regardless of
the active agent role — providing tech-stack constraints and the feature catalog before
any work begins.

This adapter fires **before** role-specific adapters (`design-ctx`, `frontend-ctx`).
Those adapters add role-specific context (release, task, reports). This adapter provides
the universal product foundation that all roles require.

---

## Purpose

The equivalent of the ctx-inject hook's (`dadaia_workspace.hooks.ctx_inject`) memory
bootstrap payload for Claude Code sessions — delivered here for Codex
sessions where the hook does not fire.
Every Codex session receives:

1. Approved toolchain and constraints (`TECHSTACK.md`)
2. Feature catalog for task-scoped self-pull (`product/catalog.json` or `product/index.md`)

Architecture (`ARCHITECTURE.md`) is **not** injected here — it is large (~7.5K tokens)
and agents self-pull it before any architectural, cross-layer, or design decision.

It supplements the canonical agent persona — it does NOT duplicate it.

---

## Protocol

Follow these steps in order at the beginning of every Codex session, before any
role-specific adapter and before any implementation work.

### Step 1 — Resolve `specs_dir`

Resolve in priority order:

1. Environment variable `DADAIA_CONTEXT` is set: use `repos/<DADAIA_CONTEXT>/specs/`.
2. Otherwise: read `.dadaia/states/spec_contexts.json`, find the first entry with `state: alive`,
   and derive `repos/<slug>/specs/`.

Context resolves automatically from the registry — never halt to ask the operator to
bind or rebind. Binding is optional. Only if the workspace has no ALIVE context at all
is there nothing to load.

```
DADAIA_CONTEXT env var → repos/<slug>/specs/
OR
Read: .dadaia/states/spec_contexts.json → find first alive entry → derive: repos/<slug>/specs/
```

### Step 2 — Read `TECHSTACK.md`

Read `<specs_dir>/memory/TECHSTACK.md` directly. Preserve frontmatter and body
content; do not strip Markdown.

```
Read: <specs_dir>/memory/TECHSTACK.md
```

If the file is absent, record `[TECHSTACK.md not found]` and continue.

### Step 3 — Read feature catalog

Check whether `<specs_dir>/memory/product/catalog.json` exists.

- **If present:** read it directly (JSON — no stripping needed). It contains all
  features with `slug`, `title`, `summary`, `area`, `path`, `tags`, and `depends_on`
  fields. Use `summary` and `tags` to identify the 1-3 features relevant to your task,
  then self-pull each entry's `path` field (`product/<area>/<slug>.md`).
- **If absent:** fall back to reading `<specs_dir>/memory/product/index.md`
  for the human-readable catalog.

```
Read: <specs_dir>/memory/product/catalog.json   (preferred)
OR fallback:
Read: <specs_dir>/memory/product/index.md     (if catalog.json absent)
```

### Step 4 — Emit memory context block

Emit the following context block before any role-specific adapter runs or any work begins:

```
=== workspace memory (tech + catalog) ===
[TECHSTACK.md content]

[catalog.json content OR product/index.md content]
=== end memory bootstrap ===
```

After emitting this block, proceed to any role-specific adapter (`design-ctx`,
`frontend-ctx`, etc.) and then to the active task.

### Step 5 — Self-pull architecture before architectural work

Before any architectural, cross-layer, or design decision, self-pull:

```
Read: <specs_dir>/memory/ARCHITECTURE.md
```

Architecture is NOT part of the bootstrap payload (it is large). Pull it on demand,
not at session start.

---

## Guardrails

| Rule | Detail |
|------|--------|
| Universal execution | This adapter runs for every Codex session, every agent role, without exception. |
| Fires first | Execute this adapter before `design-ctx`, `frontend-ctx`, or any other role adapter. |
| Read-only | No Write, Edit, or Bash calls beyond the read operations above during context gathering. |
| No persona duplication | This adapter supplements the canonical agent persona — it does not replace or restate it. |
| Graceful degradation | If a memory file is missing, record the absence and continue — do not block the session. |
| Architecture is self-pull | Never inject ARCHITECTURE.md as part of bootstrap. Self-pull it only when making architectural or cross-layer decisions. |
| Self-pull responsibility | Use the catalog to identify relevant features; self-pull only 1-3 `product/<area>/<slug>.md` files (per each entry's `path` field) for your specific task to avoid context overload. |

---

## Codex runtime note

This file lives at `public/runtime/codex/memory-ctx/SKILL.md` and is projected to
`.codex/skills/memory-ctx/SKILL.md` by `dadaia public install --target codex`.

It is auto-discovered by `_install_codex_runtime_adapters` via directory iteration —
no `config.toml` entry is needed or exists for this purpose (ADR-CX-001).

It does NOT appear in `.claude/skills/`.
