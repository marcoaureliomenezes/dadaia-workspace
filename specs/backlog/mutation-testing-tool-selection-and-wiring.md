---
title: "Mutation-testing tool selection and wiring (1×/release, off the push path)"
status: candidate
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE
  claimed this routing but it never happened). CLOSURE text: "Mutation-testing tool
  selection and wiring. The cadence (1×/release, off the push path) is declared in the
  skill and in memory; choosing between mutmut / cosmic-ray / another and wiring it is
  its own task (SPEC §4 non-goal)." Verified at HEAD 2026-08-14: no mutation tool is
  wired (no mutmut/cosmic-ray in pyproject.toml or .github/workflows/) — the declared
  cadence still has no executor.
intents:
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#Layers
    change: >-
      Select the mutation-testing tool (mutmut vs cosmic-ray vs other), wire it at the
      declared cadence (once per release, never on the push path), and record the
      chosen tool + invocation in the QA memory so the cadence claim is backed by a
      runnable command.
---

# Mutation-testing tool selection and wiring

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", first item (destination `backlog/candidates.md`).

## Acceptance criteria

A mutation run is executable from the repo with one documented command; it runs
1×/release off the push path; its baseline score is recorded; the push gate is
untouched.
