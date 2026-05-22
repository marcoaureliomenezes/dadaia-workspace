---
name: frontend-ctx
description: Codex-only context injection adapter for frontend-engineer sessions, resolving active context, design handoff, QA evidence, and active implementation task.
---

# frontend-ctx — Codex Context Injection Adapter (frontend-engineer)

Inject read-only implementation context at the start of a Codex session for
`frontend-engineer`, providing the active release, active task, latest design
handoff, and dev-server state before any implementation work begins.

---

## Purpose

This adapter enriches the Codex runtime with the four pieces of context that
`frontend-engineer` needs at session start:

1. Active release and phase from `ACTIVE.md`
2. Active task assigned to `frontend-engineer` in the release's TASKS.md
3. Latest design report path (source of visual direction)
4. Dev-server registry state

It supplements the canonical `frontend-engineer` persona — it does NOT duplicate it.

---

## Protocol

Follow these steps in order at the beginning of every Codex session where
`frontend-engineer` is the active agent. Produce a context summary block before
beginning any implementation work.

### Step 1 — Read the active release

```
Read: specs/releases/ACTIVE.md
Extract: release-id, phase
```

If `ACTIVE.md` is missing or contains `release: none`, stop and inform the operator
that no active release is set.

### Step 2 — Identify the active frontend task

Read the TASKS.md for the active release:

```
Read: specs/releases/<release-id>/TASKS.md
```

Find the first task entry in state `[-]` (IN PROGRESS) or `[ ]` (OPEN) whose
**Owner** is `frontend-engineer`. Record the task ID and description.

If no such task exists, record: `[no frontend-engineer task found]`.

### Step 3 — Find the latest design report

Resolve `slug` from `.dadaia/states/primary_context.json`, then:

```
ls .dadaia/reports/<slug>/design-specialist/ | sort -r | head -1
```

Record the full path: `.dadaia/reports/<slug>/design-specialist/<filename>`.

If the directory does not exist, record: `[no design report found — request one from design-specialist]`.

### Step 4 — Read dev-server registry state

```
Read: .dadaia/states/server_registry.json   (if it exists)
```

Extract: registered servers (name, port, status). If the file does not exist,
record: `[server_registry.json not found]`.

### Step 5 — Emit context summary

Before beginning any implementation work, output a context block in this format:

```
=== frontend-ctx: Session Context ===
Active release    : <release-id> (phase: <phase>)
Active task       : <task-id> — <description>
Latest design rpt : .dadaia/reports/<slug>/design-specialist/<filename>
Dev server state  : <list of name:port entries, or "none registered">
=====================================
```

---

## Guardrails

| Rule | Detail |
|------|--------|
| Read-only context phase | No Write or Edit to source files during context gathering. |
| No UX/UI decisions | All visual direction comes from the design report. If the report is missing, request it from `design-specialist` before proceeding. |
| No E2E ownership | Playwright and browser evidence are owned by `qa-engineer`, not this adapter. |
| No design authority | Do not modify tokens, color palettes, spacing scales, or typography without a design report authorizing the change. |
| No persona duplication | This adapter supplements `frontend-engineer`; it does not replace or restate the canonical persona. |
| Handoff emitter | After completing implementation, use the `dadaia-handoff-emitter` shared skill to emit the sidecar. |

---

## Codex runtime note

This file lives at `public/runtime/codex/frontend-ctx/SKILL.md` and is projected to
`.codex/skills/frontend-ctx/SKILL.md` by `dadaia public install --target codex`.

It does NOT appear in `.claude/skills/` or `.opencode/skills/`.

Source path is governed by ADR-CX-001.
