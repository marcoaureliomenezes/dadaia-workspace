---
slug: spec-context-project
title: spec-context-project
category: product
tldr: The keystone concept — one canonical specs folder + one repo, session-bindable, enabling safe parallel multi-project work (constitution §0).
summary: Defines the Spec Context Project — the central organizing unit of dadaia-workspace.
  One canonical specs folder bound to one repository. Session binding triggers the
  bind→inject→enforce→parallel-multi-project value chain that lets a generic agent
  fleet build real projects safely and concurrently. Constitution §0 is the single
  source of truth for this concept.
tags:
- spec-context
- sdd
- lifecycle
- concurrency
agent_tier: self-pull
token_estimate: 900
last_updated: '2026-07-02'
release_origin: v0.1.48
---

## Purpose

The **Spec Context Project** is the central concept of dadaia-workspace. Constitution §0 defines it as the single unit through which the workspace's purpose is delivered. Everything else in the constitution — the lock model (§8), the agent roster (§14), the lifecycle gate sequence (§7), the coordinator + sub-agent topology (§9) — is machinery in service of this concept.

A Spec Context Project is **one canonical specs folder bound to one repository**. The specs folder follows a fixed pattern (`backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, plus `constitution.md` and `AGENTS.md`); the repository is the code the specs govern.

## Usage flow

Binding a Spec Context Project to a terminal session triggers the value chain:

1. **Bind** — the session attaches to a Spec Context Project. The operator runs `dadaia context bind <name>`, which persists context/mode into the session record, updates the incumbent pointer, and writes the bind-epoch marker (`.dadaia/states/bind_epoch/<ctx>`) — the ONLY trigger of context-memory injection. `--print-env` is the back-compat escape for the `eval $(...)` flow with `DADAIA_*` exports.

2. **Inject** — the binding injects the context's memory by **lazy product-feature consumption**: a bounded digest of `tech-stack.md` + the tldr-digest of `catalog.json` load up front; individual feature atoms are pulled on demand by the agent as relevant to the task. `constitution.md` is NOT injected — it is read from disk. No session pays for the whole catalog up front.

3. **Enforce** — the SDD lifecycle (constitution §7) is enforced for every production write under that context: no production change without an approved release and a reserved task. The single PreToolUse entrypoint (`python -m dadaia_workspace.hooks.pre_gate`) deterministically enforces path-class × lease × phase × mode on every write, and the git chokepoints (pre-commit lease gate + pre-push security-verdict gate) gate commit/push independently of harness hooks. `[-]` markers and spec approvals are agent/PM discipline, not gate mechanism.

4. **Parallel multi-project** — because each context carries exactly one MUTATING lease (§8), multiple Spec Context Projects can be worked on concurrently in different sessions. ADDITIVE work (backlog, bugs, research, audit, review) inside any context runs in parallel — with no collision, because the lock contract makes it structurally impossible to have more than one MUTATING writer per context at a time.

## Typical trigger

When the operator or the project-manager starts work on a project: `dadaia context bind <name>` in a new terminal. Each active project runs in its own terminal — binding is the act of declaring "this session works on this context". For ADDITIVE work (reports, handoffs, audits), binding is optional; the gate allows those writes unconditionally.

## Differentiator

Without the Spec Context Project as the central unit, a generic agent fleet would have to re-derive how to work every session, would have no persistent product memory, would have no lifecycle enforcement, and would collide on parallel projects. The Spec Context Project is what turns a generic fleet into a disciplined, parallel, multi-project software team:

- **Context engineering without re-derivation:** the context's memory digest is injected automatically on bind; agents never start blind.
- **Mechanical SDD enforcement:** the gate blocks out-of-scope writes — it is not a convention, it is a PreToolUse hook.
- **Safe parallelism:** the single-lease-per-context invariant (§8) guarantees structural exclusivity for MUTATING writers; ADDITIVE writers run concurrently by design.

## Runtime state touched

  * `.dadaia/states/spec_contexts.json` — registry of all Spec Context Projects (`schema_version: "2"`; state ALIVE/DEAD).
  * `.dadaia/states/ctx_locks/<ctx>.lock.json` — single-record JSON TTL-lease for the context (acquired on the session's first MUTATING write).
  * `.dadaia/sessions/runtime/<ctx>.ptr` — stable-session-identity pointer (D1 soul-fold).
  * `specs/memory/**` — the context's canonical memory (architecture.md, tech-stack.md, product/).
  * `specs/releases/ACTIVE.md` — the context's active release.

## Dependencies

  * [[context-management]] — manages the ALIVE/DEAD lifecycle and session binding.
  * [[sdd-gate-v3]] — enforces the SDD contract on every production write.
  * [[agent-orchestration]] — coordinates the agents working inside the context.
  * [[public-asset-distribution]] — projects the canonical surface to all runtimes serving the context.
  * Constitution §0 is the single source of truth for this concept's definition and philosophy — this atom cites, does not duplicate.
