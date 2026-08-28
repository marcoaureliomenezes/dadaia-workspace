---
slug: product-vision
title: product-vision
category: product
tldr: A local-first, strictly bounded SDD workspace giving agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.
summary: dadaia-workspace is a local-first environment for context-bound agent work — canonical specs and memory, deterministic gates, a document-governed lifecycle and auditable evidence.
tags: [vision, philosophy, identity, lifecycle, anti-slop]
---

## Identity and pillars

- dadaia-workspace is the operating environment around repositories developed with AI agents, its unit being the Spec Context Project ([[spec-context-project]]).
- Current context — agents bind explicitly and receive only the relevant project, memory, release and task state.
- Documents are the lifecycle — backlog, SPEC, PLAN, TASKS, `RELEASE.json` and the bug ledger carry ordered work, and the workspace ships no runtime driving agents through steps.
- Deterministic boundaries — path, phase, caller mode, root hygiene and the git push gate are mechanical; what cannot be mechanical is written as law ([[sdd-gate-v3]]).
- Visible concurrency — sessions may race, presence warnings and git expose overlap, and nothing freezes waiting on a lock.
- No mechanism without a demand — a capability exists only while it earns its maintenance cost, and deleted surface beats accreted surface.
- No slop — runtime state, reports, handoffs, caches, projections and temporary files have canonical homes and never leak into repositories.
- Claude Code, Codex and Kimi Code are Layer-1 entry harnesses, and public assets originate once, stage once and project to each runtime root ([[public-asset-distribution]]).
- Success is evidenced by reviews, task markers, commands and artifacts, never inferred from prose.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[architecture]], [[public-asset-distribution]].
