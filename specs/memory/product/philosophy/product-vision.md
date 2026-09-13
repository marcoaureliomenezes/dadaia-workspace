---
slug: product-vision
title: product-vision
tldr: A local-first, spec-driven workspace that gives AI agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.
summary: dadaia-workspace is a local-first environment for context-bound agent work — canonical specs and memory, deterministic gates, a document-governed lifecycle and auditable evidence.
tags: [vision, philosophy, identity, lifecycle, anti-slop]
---

## Identity and pillars

- dadaia-workspace is the operating environment around repositories developed with AI agents, its unit being the context — a Spec Context Project ([[spec-context-project]]).
- Current context — agents bind explicitly and receive only the relevant project, memory, release and task state.
- Documents are the lifecycle — backlog, SPEC, PLAN, TASKS, `_RELEASE.json` and the bug record store `BUGS.jsonl` carry ordered work, and the workspace ships no runtime driving agents through steps.
- Deterministic boundaries — path class, bind scope, root hygiene, venv-rooting and the git push gate are mechanical, each refusal carrying its own runnable fix; what cannot be mechanical is written as law ([[sdd-gate-v3]]).
- Visible concurrency — sessions may race, presence warnings and git expose overlap, and nothing freezes waiting on a lock.
- No mechanism without a demand — a capability exists only while it earns its maintenance cost, and deleted surface beats accreted surface.
- No slop — runtime state, reports, handoffs, caches, projections and temporary files have canonical homes and never leak into repositories.
- Claude Code, Codex and Kimi Code are Layer-1 entry harnesses, and public assets originate once, stage once and project to each runtime root ([[public-asset-distribution]]).
- Success is evidenced by reviews, task markers, commands and artifacts, never inferred from prose.

## Two usage paths

- A human installs it from PyPI and drives it from a shell: `dadaia init` provisions a workspace, `context create`/`alive`/`bind` registers and scopes a context, `dadaia doctor` scores compliance with a runnable fix under every refusal, `dadaia panel` is the loopback-only view; `README.md` is that path, derived from memory ([[pypi-distribution]], [[workspace-init]], [[workspace-doctor]], [[panel]]).
- An agent reads `DADAIA.md` — one always-on law file, projected into every harness root — and works inside the gate, the record verbs and the handoff contract; `llms.txt` at the repository root is its index, every line linking to a derived document, the law, the CLI reference or the memory catalog ([[sdd-gate-v3]], [[agent-comms]]).
- Both paths read one truth: every human- and agent-facing document derives from a named memory atom under its content hash ([[QUALITY]] P-29).

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[ARCHITECTURE]], [[public-asset-distribution]], [[pypi-distribution]], [[QUALITY]].
