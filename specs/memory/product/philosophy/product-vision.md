---
slug: product-vision
title: product-vision
tldr: One workspace keeps project repositories inside it and governance outside; each context spans one main repository and any associated repositories.
summary: The product paradigm, evidence and coupling principles, and the human and agent paths through one current product truth.
tags: [vision, paradigm, pillars]
sources:
  - AGENTS.md
  - dadaia_workspace/public/data/AGENTS.md
  - specs/constitution.md
---

## Paradigm

- An agent session starts at the workspace root. Product repositories live under `repos/<slug>/`; governance, projections, skills and runtime state live outside them.
- A context is one main repository, where `specs/` lives, plus associated repositories. A workspace holds many contexts and a context may span many repositories; this is not a monorepo ([[context-management]]).
- Repository changes land from canonical worktrees. Audits are the sole direct specs exception ([[worktrees]]).
- The same authored law reaches every registered harness through native files or projections ([[agentic-entities]]).

## Product principles

- Simplicity and lightness are the first law: the lightest solution that works wins, and a heavier one is chosen only when a lighter one was tried and failed. A requirement applied to every task, job or deletion, the `verify:` line and the merge checks are gates: each states its measured cost per run, that cost never exceeds one run of the job's `verify:` gate, and changing one needs the operator's ruling; no step reruns a check the merge runs, a heavier gate is never the recommended option, and a new gate names the heavier one it deletes.
- Context is explicit: a bind scopes the session to one context's repository set and injects its constitution and memory.
- Documents are the lifecycle: backlog, approved definition, job files, release state and record stores carry progress; no workflow engine advances them.
- Mechanical boundaries cover path class, bind scope, root hygiene and push publication. Each refusal carries one fix line: a runnable command, an `Agent action:` an agent performs, or an `Operator action:` only for an act the law reserves to the operator ([[sdd-gate-v3]]).
- Concurrency remains visible through git; no lock hides overlap.
- Evidence is produced by the mechanism that judged the artifact and binds to the judged sha.
- Features and fixes spend future options when they add coupling. Delivery alternates with deletion, simplification or decoupling that restores options.
- Mechanisms without a current demand are removed, and runtime state, reports, handoffs, caches and projections stay in their canonical homes.
- A test, or an existing assert, leaves a suite only on the operator's order; a bug fix hardens the contract test in that contract's one home.

## Two entry paths

- A human initializes the workspace, creates or adopts a context, initializes its specs, completes the first memory pass and publishes the project. `doctor` reports the next real-state step and one fix line ([[workspace-init]], [[workspace-doctor]]).
- An agent reads the root map, the scoped law for the area, the relevant memory and the approved release artifacts, then works through the owning ledger scripts and worktree gates.
- A repository declares one tracked `verify:` command. The job, rc and hotfix merges run it and refuse a repository that declares none; task merges enforce RED/implementation separation without a second repository command ([[worktrees]]).
- Human documents and agent-facing indices are reconciled from current product memory. The CLI reference is generated from the live command tree; text identity is not a product-truth mechanism.

## Dependencies

[[spec-context-project]], [[context-management]], [[sdd-gate-v3]], [[release-lifecycle]], [[worktrees]], [[public-asset-distribution]], [[workspace-init]], [[workspace-doctor]], [[agentic-entities]].
