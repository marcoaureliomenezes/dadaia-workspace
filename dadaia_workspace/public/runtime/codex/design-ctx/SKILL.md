---
name: design-ctx
description: Codex-only context injection adapter for design-specialist sessions, resolving active context, latest design evidence, QA screenshots, and active release.
---

# design-ctx — Codex Context Injection Adapter (design-specialist)

Inject read-only workspace context at the start of a Codex session for `design-specialist`,
providing situational awareness before any design work begins.

---

## Purpose

This adapter enriches the Codex runtime with the four pieces of context that
`design-specialist` needs at session start:

1. Active workspace context and `specs_dir`
2. Latest design report path
3. Latest QA screenshot report path
4. Active release identifier

It supplements the canonical `design-specialist` persona — it does NOT duplicate it.

---

## Protocol

Follow these steps in order at the beginning of every Codex session where
`design-specialist` is the active agent. Produce a context summary block before
beginning any design work.

### Step 1 — Resolve workspace context

Read `.dadaia/states/spec_contexts.json` and find the first entry with `state: alive`:
- `slug` — the active context name (`repo_slug` field).
- `specs_dir` — derived as `repos/<slug>/specs/` from the alive entry.

```
Read: .dadaia/states/spec_contexts.json
Find: first entry where state == "alive"
Derive: slug = entry.repo_slug, specs_dir = repos/<slug>/specs/
```

### Step 2 — Find the latest design report

Using the `slug` from Step 1, locate the most recent design-specialist report:

```
ls .dadaia/reports/<slug>/design-specialist/ | sort -r | head -1
```

Record the full path: `.dadaia/reports/<slug>/design-specialist/<filename>`.

### Step 3 — Find the latest QA screenshot report

Using the same `slug`, locate the most recent QA engineer report:

```
ls .dadaia/reports/<slug>/qa-engineer/ | sort -r | head -1
```

Record the full path: `.dadaia/reports/<slug>/qa-engineer/<filename>`.

If the directory does not exist, record: `[no QA screenshot report found]`.

### Step 4 — Read the active release

```
Read: <specs_dir>/releases/ACTIVE.md
Extract: release id, phase
```

### Step 5 — Emit context summary

Before beginning any design work, output a context block in this format:

```
=== design-ctx: Session Context ===
Workspace slug    : <slug>
Specs dir         : <specs_dir>
Active release    : <release-id> (phase: <phase>)
Latest design rpt : .dadaia/reports/<slug>/design-specialist/<filename>
Latest QA rpt     : .dadaia/reports/<slug>/qa-engineer/<filename>
===================================
```

---

## Guardrails

| Rule | Detail |
|------|--------|
| Read-only context phase | No Write, Edit, or Bash calls beyond the four read commands above. |
| No Playwright | Do not invoke Playwright or any browser capture tool during context gathering. |
| No raster generation | Do not generate images, screenshots, or raster assets at any point. |
| No production code | Do not write HTML, CSS, JS, TS, or TSX during context gathering or at all. |
| No persona duplication | This adapter supplements `design-specialist`; it does not replace or restate the canonical persona. |
| Reference whitelist | For reference research, always use the `design-reference-research` shared skill. |

---

## Codex runtime note

This file lives at `public/runtime/codex/design-ctx/SKILL.md` and is projected to
`.codex/skills/design-ctx/SKILL.md` by `dadaia public install --target codex`.

It does NOT appear in `.claude/skills/` or `.opencode/skills/`.

Source path is governed by ADR-CX-001.
