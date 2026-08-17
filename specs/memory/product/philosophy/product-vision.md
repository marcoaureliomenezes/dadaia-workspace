---
slug: product-vision
title: product-vision
category: product
tldr: A strict, portable SDD workspace that gives agents current context, a document-governed lifecycle, visible concurrency, and strong anti-slop boundaries.
summary: >-
  Defines dadaia-workspace as a local-first environment for context-bound agent work.
  It combines canonical specs and memory, deterministic safety gates, a document-governed
  ordered lifecycle, cross-harness projections, auditable evidence, and explicit
  workspace/repository hygiene.
tags:
- vision
- philosophy
- identity
- lifecycle
- anti-slop
last_updated: '2026-08-07'
release_origin: v0.3.0
---

## Purpose

dadaia-workspace is the operating environment around repositories developed with AI
agents. It is not a general project-management suite and not a collection of loosely
related commands. Its unit is the Spec Context Project: one repository, one canonical
specs tree, current memory, and auditable lifecycle evidence.

## Design Pillars

1. **Current context** - agents bind explicitly and receive only the relevant project,
   memory, release, and task state.
2. **Documents are the lifecycle** - backlog, SPEC, PLAN, TASKS, CLOSURE and the bug
   ledger carry the ordered flow; agents are dispatched against them. The workspace
   ships no runtime that drives agents through steps.
3. **Deterministic boundaries** - path, phase, caller mode, root hygiene, and Git push
   gates are mechanical. What cannot be mechanical is written as law and upheld.
4. **Visible concurrency** - sessions may race; presence warnings and Git expose overlap.
   The workspace never freezes because another session holds a lock.
5. **No mechanism without a demand** - a capability exists only while it earns its
   maintenance cost; deleted surface is preferred to accreted surface.
6. **No slop** - runtime state, reports, handoffs, caches, generated projections, and
   temporary files have canonical homes and never leak into repositories.

## Harness Model

Claude Code, Codex, and Kimi Code are Layer-1 entry harnesses. Public assets
originate once under `dadaia_workspace/public/`, stage under `.dadaia/agentic/`, and
project to the runtime-specific roots.

## Evidence Model

Agents communicate through validated handoff JSON; human-readable HTML is optional.
Reviews, task markers, commands, and artifacts provide evidence; success is never
inferred from prose alone.

## Security And Credentials

Workspace credential material belongs only in the operator-managed root `.env` and is
passed minimally at runtime. Repositories, mounts, images, reports, handoffs, caches, and
generated configuration must not contain secrets.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[architecture]],
[[public-asset-distribution]].
