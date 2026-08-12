---
title: "Test stewardship — lifecycle law, dadaia-test-stewardship skill, tiered enforcement"
status: candidate
opened: 2026-08-12
description: >-
  Operator ruling (2026-08-12): agents create tests well and curate them badly — the
  workspace must make every agent build, maintain and prune tests against an explicit
  lifecycle. Source: the 30-statement test-stewardship report (groups A-H: intent
  taxonomy CONTRACT/SENTINEL/SCAFFOLD/QUARANTINE, admission filter, Google size tiers
  with enforced timeouts, demotion-at-closure, deletion criteria incl. the tombstone
  ban, flaky quarantine pipeline, artifact hygiene, health metrics + mutation testing).
  dadaia-workspace defines the abstract concept; every harness receives it via the
  projected skill + law. Decisions: skill named dadaia-test-stewardship; steward is
  verdict-only (qa-engineer sentences with S-16 evidence, software-engineer executes);
  approved parameter package (LARGE cap, flake ceiling, quarantine caps, pytest-timeout
  tiers, frozen wall-clock baseline, mutation 1x/release); law lands as a minimal
  5-point DADAIA.md §6 increment plus a new numbered Disciplina de Testes article in
  the scaffold constitution plus a public tests/AGENTS.md template.
intents:
  - subject:
      kind: doc
      ref: quality-assurance.md#Layers
    change: >-
      The doctrine itself: intent taxonomy, size tiers, admission filter, deletion
      criteria (tombstone ban extended in place in tests/AGENTS.md — it already exists
      there), demotion-at-closure block in dadaia-release-closure, flake quarantine
      pipeline (new memory h2 + heading allowlist), health metrics + mutation cadence —
      each concept placed in its single recommended home per the research dossier; the
      13 mapped conflicts (coverage doctrine 4-way split, qa-engineer allowlist
      contradiction, tests/README duplication, closed marker set, evidence forms,
      push-green carve-out) resolved by EDITING existing text, never appending
      duplicates.
  - subject:
      kind: catalog
      ref: public-asset-distribution
    change: >-
      New universal skill public/skills/dadaia-test-stewardship/SKILL.md (groups A-H as
      operational protocol; §10 parameters as declared adjustable defaults); public
      template of tests/AGENTS.md; new numbered article in scaffold/constitution.md so
      the doctrine reaches consumer workspaces at law level; DADAIA.md §6 five-point
      increment (intent+size mandatory; demotion is a closure step; implementer never
      prunes — curation is a qa-engineer verdict executed by software-engineer;
      tombstone and expired-SCAFFOLD are slop; test artifacts failure-gated and out of
      the repo) with the never-delete-law scoping sentence (bugs/backlog only — tests
      are prunable under the criteria).
  - subject:
      kind: doc
      ref: quality-assurance.md#CI
    change: >-
      Mechanical wiring: pytest-timeout dependency with tiered defaults (unit 10s /
      contract 30s / integration 60s / e2e 120s); flaky/quarantine markers added to the
      closed marker set (pyproject + conftest _PATH_MARKERS + tests/AGENTS.md +
      tech-stack.md + CI -m selectors together); Playwright flaky-status recording so
      pass-on-retry stops vanishing; --durations on unit/contract jobs + wall-clock
      budget ratchet frozen at the current baseline; retire the dead
      --ignore=tests/performance in ci_preflight; stale memory facts refreshed
      (test count, xdist/randomly in tech-stack).
---

# Test stewardship — lifecycle law, skill, tiered enforcement

## Description

See frontmatter. Research record: the v2 statements report (30 statements, LIT/NOSSO
honesty tags) plus three read-only scans of this repo's own suite executed 2026-08-12
(tautology/tombstone census: <10% of files affected, worst offenders named;
lifecycle-mechanics verdicts: ownership RED 0/26 LARGE files owned, flaky infra RED,
timeouts absent; full QA-surface inventory: 13 conflicts, single-home map). Dossier:
`.dadaia/tmp/software-engineer/20260812/stewardship-research-dossier.md`.

## Motivation

The operator's hardest recurring problem with AI agents is test quality: agents pile
up, duplicate, generate tautologies, leave eternal scaffolds and tombstone tests, and
couple tests to implementation — destroying the suite's signal. The suite must validate
the product, never accumulate slop, in every project of every consumer workspace.

## Acceptance criteria

- Every concept has exactly one home; the A2.3-style relocation grep for test doctrine
  comes back clean; no fact stated twice (constitution §12.3).
- dadaia-test-stewardship projected to all harnesses; consumer scaffold carries the
  constitution article + tests/AGENTS.md template.
- Mechanical: pytest-timeout active per tier; quarantine marker excluded from gating
  runs with bug-id required; Playwright flaky runs recorded and surfaced; budget
  ratchet in place; doctors + full suite green.
- The suite-remediation work is NOT this release: it is the companion backlog entry
  test-suite-remediation-stewardship, executed after the doctrine ships.
