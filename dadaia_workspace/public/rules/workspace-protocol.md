---
name: workspace-protocol
description: Shared SDD protocol for all dadaia-workspace agents — gate, context discovery, task lifecycle, report emission, memory atomicity.
always_on: true
---

# Workspace Protocol

All dadaia-workspace agents follow this shared protocol. Do not duplicate these rules inline.

## 1. SDD gate
Before editing any production file:
1. Confirm a `[-]` task marker is active in the release's TASKS.md for your task.
2. Flip `[ ]` → `[-]` BEFORE writing. Flip `[-]` → `[x]` AFTER completing.
3. At most one `[-]` per owner at a time (unless disjoint write sets are declared in TASKS.md).

## 2. Context discovery
Resolve specs_dir in priority order:
1. `DADAIA_CONTEXT` env var → `repos/<slug>/specs/`
2. `.dadaia/states/primary_context.json` field `specs_dir`
3. `dadaia context show --json`
If none resolves: stop and ask operator to run `dadaia context activate <name>`.

## 3. Task lifecycle
1. Read ACTIVE.md → confirm release + phase.
2. Read SPEC.md, PLAN.md, TASKS.md — all must have `**Status:** Aprovado`.
3. Reserve your task: flip `[ ]` → `[-]`.
4. Complete the work.
5. Flip `[-]` → `[x]`. Commit with `conventional-commit(task-id): description`.

## 4. Report emission
- Default: emit JSON sidecar (`<UTC>-<slug>.handoff.json`) only.
- HTML report: only when operator explicitly requests it OR `next_handoff.agent == "human"`.
- Report path: `.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html` (HTML) / `.handoff.json` (sidecar, adjacent).
- Reports > 30 KB: split into multi-HTML with `index.html` entry point.

## 5. Memory atomicity
`specs/memory/**/*.md` files are write-locked for all agents EXCEPT `product-engineer` during CLOSURE phase. Never edit memory atoms in any earlier phase.

## 6. Write-allowlist enforcement
Each agent declares `paths.write_allowlist` in its frontmatter. Do not touch files outside your allowlist. The SDD gate enforces this at runtime.
