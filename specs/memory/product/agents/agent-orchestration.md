---
slug: agent-orchestration
title: agent-orchestration
category: product
tldr: Twelve personas, two dispatchers, leaf workers everywhere else, and advisory-only concurrency — no role ever holds a lock.
summary: >-
  How the persona roster operates: who dispatches, what every worker does before starting,
  how tasks are reserved and released, and where review evidence gates a commit or a push.
  The persona definitions themselves live in the personas atom.
tags:
- orchestration
- agents
- dispatch
token_estimate: 0
last_updated: '2026-08-01'
release_origin: v0.2.9
---

## Purpose

The roster and its authorities live in [[personas]]. This atom records how those personas
**operate together**.

## Dispatch is a tree with two roots

Only `project-manager` and `project-auditor` dispatch. Every other persona is a leaf
worker: it surfaces a need to its dispatcher and never spawns another agent. A call graph
with a single shape is what makes a run auditable after the fact.

`project-manager` is the entry point for every non-trivial demand — it classifies,
dispatches, and synthesizes. `project-auditor` dispatches only the evidence specialists an
audit needs.

## What every worker does before starting

1. Resolve or bind the intended Spec Context.
2. Read the constitution, architecture, tech stack, product catalog, the relevant memory
   atoms, and the active release artifacts.
3. Reserve its task `[ ]` → `[-]`, work inside the declared write set, validate, then mark
   `[x]`.
4. Emit a machine-readable handoff; add an HTML report only for an explicit human target.

## Review evidence gates the exits, not the work

Reviews do not block a worker mid-flight; they gate the two exits. A commit follows QA and
code review; a push additionally requires an approved `security-reviewer` handoff whose
recorded commit sha equals the pushed ref. A rejection returns the work to its
implementing persona with the objection attached — never silently.

## Concurrency is advisory, always

Concurrent sessions are allowed. Presence is surfaced, never enforced: no persona
acquires, holds, hands off, releases, or steals a workspace lock. Task markers and
dispatch coordination reduce conflicting intent; genuine races stay visible as Git
conflicts rather than being prevented by waiting.

## Model governance

Persona sources are model-agnostic. A model tier and reasoning effort are attached at
projection time, when a harness scaffolds its own entity, from the selected template plus
the operator overlay. The panel's Agentic Layer manages that policy.

## Dependencies

[[personas]], [[agent-comms]], [[sdd-gate-v3]].
