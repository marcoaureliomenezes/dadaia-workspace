---
title: "dd-audit-project: pin the third-party scan-tool installs (unpinned pip/npx guidance)"
status: candidate
opened: 2026-08-15
description: >-
  Pre-existing supply-chain guidance carried through the v0.10.0 rename: the audit skill
  (dd-audit-project, formerly the audit skill under its old name) instructs installing
  third-party scanning tools via unpinned `pip install <tool>` / `npx <tool>` — an
  unpinned install at audit time executes whatever the registry serves that day, inside
  the workspace venv. Fix: version-pin (or hash-pin) every tool invocation the skill
  prescribes, and state the rule once so future tool additions inherit it.
intents:
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#Dependencies
    change: >-
      The audit-lane tool-install guidance is pinned: dd-audit-project prescribes exact
      versions (or hashes) for every third-party scanner it instructs installing, and
      the dependency-hygiene doctrine records that audit tooling follows the same
      pinning rule as production dependencies.
---

# dd-audit-project — pinned scan-tool installs

## Description

See frontmatter. Source: security-reviewer v0.10.0 ship handoff
`.dadaia/handoff/dadaia-workspace/2026-08-15T151005Z-security-reviewer-v0.10.0-ship.handoff.json`
(INFO; pre-existing, rename-carried — outside every v0.10.0 write set).

## Acceptance criteria

- Zero unpinned `pip install` / `npx` invocations remain in `dd-audit-project/SKILL.md`;
  each names a version or hash.
- The pinning rule is stated once in the skill so future additions inherit it.

## Provenance

Intake report #2 item 2-5 — APPROVED. Trace: operator-delegated adjudication, 2026-08-15
(goal directive), verdicts per PM recommendation
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`).

## Ownership

`ai-engineer` (skill text); `security-reviewer` verifies at the covering push review.
Priority P3 — small hardening.
