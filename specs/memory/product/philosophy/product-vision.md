---
slug: product-vision
title: product-vision
category: product
tldr: A local-first, strictly bounded SDD workspace giving agents current context, a document-governed lifecycle, visible concurrency and anti-slop boundaries.
summary: dadaia-workspace is a local-first environment for context-bound agent work — canonical specs and memory, deterministic gates, a document-governed lifecycle, cross-harness projections and auditable evidence.
tags:
- vision
- philosophy
- identity
- lifecycle
- anti-slop
---

## Purpose

dadaia-workspace is the operating environment around repositories developed with AI
agents. Its unit is the Spec Context Project: one main repository, one canonical specs
tree, current memory, and auditable lifecycle evidence ([[spec-context-project]]).

## Design pillars

1. **Current context** — agents bind explicitly and receive only the relevant project,
   memory, release and task state.
2. **Documents are the lifecycle** — backlog, SPEC, PLAN, TASKS, the `RELEASE.jsonl` fold
   and the bug ledger carry ordered work; the workspace ships no runtime that drives
   agents through steps.
3. **Deterministic boundaries** — path, phase, caller mode, root hygiene and the git
   push gate are mechanical; what cannot be mechanical is written as law
   ([[sdd-gate-v3]]).
4. **Visible concurrency** — sessions may race; presence warnings and git expose overlap,
   and nothing freezes waiting on a lock.
5. **No mechanism without a demand** — a capability exists only while it earns its
   maintenance cost; deleted surface is preferred to accreted surface.
6. **No slop** — runtime state, reports, handoffs, caches, projections and temporary files
   have canonical homes and never leak into repositories.

## Harness and evidence model

Claude Code, Codex and Kimi Code are Layer-1 entry harnesses; public assets originate once
under `dadaia_workspace/public/`, stage under `.dadaia/agentic/`, and project to each
runtime root ([[public-asset-distribution]]). Agents communicate through validated handoff
JSON, with HTML optional; success is evidenced by reviews, task markers, commands and
artifacts, never inferred from prose.

## Credentials

Credential material lives only in the operator-managed root `.env` and is passed minimally
at runtime. Repositories, mounts, images, reports, handoffs, caches and generated
configuration carry no secrets.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[architecture]],
[[public-asset-distribution]].
