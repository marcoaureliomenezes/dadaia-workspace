---
name: memory-ctx
description: Universal Codex memory bootstrap adapter. Fires before all role-specific adapters (design-ctx, frontend-ctx). Injects architecture, tech-stack, and feature catalog into every Codex session.
---

# memory-ctx — Universal Memory Bootstrap Adapter (Codex)

Inject the workspace memory context at the start of every Codex session — regardless of
the active agent role — providing architecture rules, tech-stack constraints, and the
feature catalog before any work begins.

This adapter fires **before** role-specific adapters (`design-ctx`, `frontend-ctx`).
Those adapters add role-specific context (release, task, reports). This adapter provides
the universal product foundation that all roles require.

---

## Purpose

The equivalent of `ctx-inject.sh`'s memory bootstrap payload for Claude Code and
OpenCode sessions — delivered here for Codex sessions where the hook does not fire.
Every Codex session receives:

1. Architecture rules and agent topology (`architecture.html`)
2. Approved toolchain and constraints (`tech-stack.html`)
3. Feature catalog for task-scoped self-pull (`catalog.json` or `product/index.html`)

It supplements the canonical agent persona — it does NOT duplicate it.

---

## Protocol

Follow these steps in order at the beginning of every Codex session, before any
role-specific adapter and before any implementation work.

### Step 1 — Resolve `specs_dir`

Resolve in priority order:

1. Environment variable `DADAIA_CONTEXT` is set: use `repos/<DADAIA_CONTEXT>/specs/`.
2. Otherwise: read `.dadaia/states/primary_context.json` and extract `specs_dir`.

If neither resolves, stop and ask the operator to run `dadaia context activate <name>`.

```
DADAIA_CONTEXT env var → repos/<slug>/specs/
OR
Read: .dadaia/states/primary_context.json → extract: specs_dir
```

### Step 2 — Read and strip `architecture.html`

Read `<specs_dir>/memory/architecture.html`. Strip boilerplate before use:
remove `<head>`, `<style>`, and Mermaid `<script>` blocks. Preserve all prose,
heading, ADR, and diagram content.

```
Read: <specs_dir>/memory/architecture.html
Strip: <head>, <style>, <script> (Mermaid) blocks
```

If the file is absent, record `[architecture.html not found]` and continue.

### Step 3 — Read and strip `tech-stack.html`

Read `<specs_dir>/memory/tech-stack.html`. Apply the same strip as Step 2.

```
Read: <specs_dir>/memory/tech-stack.html
Strip: <head>, <style>, <script> (Mermaid) blocks
```

If the file is absent, record `[tech-stack.html not found]` and continue.

### Step 4 — Read feature catalog

Check whether `<specs_dir>/memory/product/catalog.json` exists.

- **If present:** read it directly (JSON — no stripping needed). It contains all
  features with `slug`, `title`, `summary`, `path`, `tags`, and `depends_on` fields.
  Use `summary` and `tags` to identify the 1-3 features relevant to your task, then
  self-pull the corresponding `product/<slug>.html` files.
- **If absent:** fall back to reading `<specs_dir>/memory/product/index.html`
  (strip boilerplate as in Step 2) for the human-readable catalog.

```
Read: <specs_dir>/memory/product/catalog.json   (preferred)
OR fallback:
Read: <specs_dir>/memory/product/index.html     (stripped, if catalog.json absent)
```

### Step 5 — Emit memory context block

Emit the following context block before any role-specific adapter runs or any work begins:

```
=== workspace memory (arch + tech + catalog) ===
[stripped architecture.html content]

[stripped tech-stack.html content]

[catalog.json content OR stripped product/index.html content]
=== end memory bootstrap ===
```

After emitting this block, proceed to any role-specific adapter (`design-ctx`,
`frontend-ctx`, etc.) and then to the active task.

---

## Guardrails

| Rule | Detail |
|------|--------|
| Universal execution | This adapter runs for every Codex session, every agent role, without exception. |
| Fires first | Execute this adapter before `design-ctx`, `frontend-ctx`, or any other role adapter. |
| Read-only | No Write, Edit, or Bash calls beyond the four read operations above during context gathering. |
| No persona duplication | This adapter supplements the canonical agent persona — it does not replace or restate it. |
| Graceful degradation | If a memory file is missing, record the absence and continue — do not block the session. |
| Self-pull responsibility | Use the catalog to identify relevant features; self-pull only 1-3 `product/<slug>.html` files for your specific task to avoid context overload. |

---

## Codex runtime note

This file lives at `public/runtime/codex/memory-ctx/SKILL.md` and is projected to
`.codex/skills/memory-ctx/SKILL.md` by `dadaia public install --target codex`.

It is auto-discovered by `_install_codex_runtime_adapters` via directory iteration —
no `config.toml` entry is needed or exists for this purpose (ADR-CX-001).

It does NOT appear in `.claude/skills/` or `.opencode/skills/`.
