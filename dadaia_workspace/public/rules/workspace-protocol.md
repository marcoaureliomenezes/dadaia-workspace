---
name: workspace-protocol
description: Shared SDD protocol for all dadaia-workspace agents — gate, context discovery, task lifecycle, report emission, memory atomicity.
always_on: true
---

# Workspace Protocol

All dadaia-workspace agents follow this shared protocol. Do not duplicate these rules inline.

## 1. SDD gate
**What the hooks enforce (deterministic).** A single merged PreToolUse entrypoint —
`dadaia_workspace.hooks.pre_gate` — reads each tool payload once and evaluates three
policies in fixed order, **first-block-wins**:
1. **root-whitelist** — blocks any file-tool write that would create a new top-level
   workspace-root entry outside the whitelist.
2. **venv-guard** — Bash-only, fixed leading-token patterns (no general shell parsing):
   `dadaia`, `pip`, and `python -m dadaia_workspace` invocations must be rooted in
   `.dadaia/.venv/bin/`; the block message carries the corrected command.
3. **SDD gate** — evaluates each `Edit`/`Write`-family call as path-class × lease ×
   phase × mode: ADDITIVE paths (`specs/bugs|backlog|audits/`,
   `.dadaia/reports|handoff|tmp/` — root or in-repo) always pass; MEMORY
   (`specs/memory/`) passes only in DEFINITION/CLOSURE phase; FROZEN (`specs/_archive/`)
   and PROTECTED (`.dadaia/sessions/`) block; MUTATING acquires the single per-context
   lease. Liveness is TTL + pid veto: the lease records the long-lived harness pid (hook
   payload pid when present, else the hook's parent process) — a holder whose recorded
   pid is still running is never stolen — and the heartbeat renews on every PostToolUse
   (match-all on both harnesses; harness-native session id from the hook stdin payload).
   A session whose mode resolves READ (env → session record → the context's incumbent
   pointer, which `bind` refreshes → IMPLEMENTATION default) is non-acquiring — MUTATING
   writes block before any lease call.

**Chokepoints close the Bash hole at the git boundaries.** Arbitrary `Bash`-tool file
writes are not classified by the PreToolUse gate (no shell parsing); instead, two
deterministic git-hook chokepoints gate the exits — they run as git hooks and do not
depend on any harness hook firing:
- **pre-commit lease gate** — a `git commit` into a Spec Context repo from a session
  that does not hold the context's live MUTATING lease is blocked with an actionable
  message. The holder's commits flow, and commits flow when no lease exists at all
  (ADDITIVE work commits freely). When holder identity is indeterminate (the ancestry
  probe is unavailable, or the holder pid is dead) the gate **ALLOWs with a logged
  WARN** — zero-false-block dominates; the chokepoint degrades to advisory on that
  platform.
- **pre-push security-verdict gate** — a `git push` is blocked unless an APPROVED
  `security-reviewer` handoff whose `metrics.commit_sha` equals each pushed ref sha
  exists. Branch deletions and tag-only pushes pass. Commits are never review-blocked —
  only pushes.

An **advisory working-tree reconciler** (PostToolUse) flags out-of-lease dirty MUTATING
paths in the bound context's repo (log event / report line); it NEVER blocks. Doctor
coherence checks remain the after-the-fact backstop.

**What you uphold as discipline (the hook reads no SDD artifacts).** Before editing any
production file:
1. Confirm a `[-]` task marker is active in the release's TASKS.md for your task.
2. Flip `[ ]` → `[-]` BEFORE writing. Flip `[-]` → `[x]` AFTER completing.
3. At most one `[-]` per owner at a time (unless disjoint write sets are declared in TASKS.md).
4. SPEC/PLAN/TASKS carry `**Status:** Aprovado` (see §3) and the edit stays inside the
   task's declared write set.

## 2. Context discovery and injection
When you need to resolve specs_dir yourself, use this priority order:
1. `DADAIA_CONTEXT` env var → `repos/<slug>/specs/`
2. `.dadaia/states/spec_contexts.json` — find the first ALIVE entry and derive `repos/<slug>/specs/`
3. `dadaia context show --json`

(The first-ALIVE fallback above is agent-side discovery discipline; the SDD gate's
lease-context resolution also uses it. It is NOT how injection works.)

**Injection is bind-driven.** `dadaia context bind` writes a bind-epoch marker
(`.dadaia/states/bind_epoch/<ctx>`) and is the **sole trigger** for context-memory
injection: the ctx-inject hook re-injects a context's memory only when a bind-epoch
marker is newer than this session's **existing** sentinel (or the session's own bound
context changed). A fresh unbound session gets generic preflight only — dispatcher
preflight plus the list of ALIVE contexts, NO context memory — and a pre-existing
marker never binds a fresh session. There is no first-ALIVE injection fallback.

**Bind stays non-blocking.** **Never halt the flow to ask the operator to bind or
rebind a context.** ADDITIVE work (bugs, backlog, audits, reports, handoffs) needs no
bind at all. A `context bind` selects which context's memory is injected and refreshes
the incumbent pointer; it is never a precondition for doing work. Only when the
workspace has *no* ALIVE context at all should you tell the operator there is nothing
to work on.

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
- A push-cycle `security-reviewer` APPROVE handoff carries `metrics.commit_sha` — the
  exact pushed ref sha. The pre-push security-verdict chokepoint (§1) keys on it.

## 5. Memory atomicity
`specs/memory/**/*.md` files are write-locked for all agents EXCEPT `product-engineer`, who may write in the DEFINITION and CLOSURE phases per `constitution.md §13`. No other agent edits memory atoms in any phase. The gate enforces the phase half deterministically (MEMORY path class, root and in-repo); the who half is agent discipline.

## 6. Write-allowlist convention
Each agent declares `paths.write_allowlist` in its frontmatter. Do not touch files outside your allowlist. This is an **agent-instruction convention**, not gate-enforced — no hook reads persona frontmatter, and no harness can assert persona identity to a hook (the RULE-D allowlist check was removed from the SDD gate in 0.1.7 rc-3 for exactly that reason). The only deterministic lock is the single-session lease (§1).
