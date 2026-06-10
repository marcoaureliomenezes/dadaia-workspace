---
name: workspace-protocol
description: Shared SDD protocol for all dadaia-workspace agents — gate, context discovery, task lifecycle, report emission, memory atomicity.
always_on: true
---

# Workspace Protocol

All dadaia-workspace agents follow this shared protocol. Do not duplicate these rules inline.

## 1. SDD gate
**What the hook enforces (deterministic, file-write tools only).** The
`dadaia_workspace.hooks.sdd_gate` PreToolUse hook evaluates each `Edit`/`Write`-family
tool call as path-class × lease × phase × mode: ADDITIVE paths (`specs/bugs|backlog|audits/`,
`.dadaia/reports|handoff|tmp/` — root or in-repo) always pass; MEMORY (`specs/memory/`)
passes only in DEFINITION/CLOSURE phase; FROZEN (`specs/_archive/`) and PROTECTED
(`.dadaia/sessions/`) block; MUTATING acquires the single per-context lease. Liveness is
TTL + pid veto: a holder whose pid is still running is never stolen, and the heartbeat
renews on every PostToolUse (harness-native session id from the hook stdin payload). A
session bound `--mode read` is non-acquiring — MUTATING writes block before any lease
call. `Bash`-tool writes are outside this envelope (Decision D-2); doctor coherence
checks are the backstop.

**What you uphold as discipline (the hook reads no SDD artifacts).** Before editing any
production file:
1. Confirm a `[-]` task marker is active in the release's TASKS.md for your task.
2. Flip `[ ]` → `[-]` BEFORE writing. Flip `[-]` → `[x]` AFTER completing.
3. At most one `[-]` per owner at a time (unless disjoint write sets are declared in TASKS.md).
4. SPEC/PLAN/TASKS carry `**Status:** Aprovado` (see §3) and the edit stays inside the
   task's declared write set.

## 2. Context discovery
Resolve specs_dir in priority order:
1. `DADAIA_CONTEXT` env var → `repos/<slug>/specs/`
2. `.dadaia/states/spec_contexts.json` — find the first ALIVE entry and derive `repos/<slug>/specs/`
3. `dadaia context show --json`

Context resolves automatically — the same fallback the SDD gate and `ctx-inject`
use. **Never halt the flow to ask the operator to bind or rebind a context.** A
`context bind` is optional convenience for pinning a non-default context; it is
never a precondition for doing work. If step 2 finds an ALIVE context, use it and
proceed. Only when the workspace has *no* ALIVE context at all should you tell the
operator there is nothing to work on.

## 3. Task lifecycle
1. Read ACTIVE.md → confirm release + phase.
2. Read SPEC.md, PLAN.md, TASKS.md — all must have `**Status:** Aprovado`.
3. Reserve your task: flip `[ ]` → `[-]`.
4. Complete the work.
5. Flip `[-]` → `[x]`. Commit with `conventional-commit(task-id): description`.

## 4. Report emission
- Default: emit JSON handoff (`<UTC>-<agent>-<slug>.handoff.json`) only.
- HTML report: only when operator explicitly requests it OR `next_handoff.agent == "human"`.
- Report path: `.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html`.
- Handoff path: `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json`.
- Reports > 30 KB: split into multi-HTML with `index.html` entry point.

## 5. Memory atomicity
`specs/memory/**/*.md` files are write-locked for all agents EXCEPT `product-engineer`, who may write in the DEFINITION and CLOSURE phases per `constitution.md §13`. No other agent edits memory atoms in any phase. The gate enforces the phase half deterministically (MEMORY path class, root and in-repo); the who half is agent discipline.

## 6. Write-allowlist convention
Each agent declares `paths.write_allowlist` in its frontmatter. Do not touch files outside your allowlist. This is an **agent-instruction convention**, not gate-enforced — no hook reads persona frontmatter, and no harness can assert persona identity to a hook (the RULE-D allowlist check was removed from the SDD gate in 0.1.7 rc-3 for exactly that reason). The only deterministic lock is the single-session lease (§1).
