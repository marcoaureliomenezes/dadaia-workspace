---
title: "Bug-event redaction rule is on-demand only — add one always-on reinforcement line in law §6"
status: candidate
opened: 2026-08-15
description: >-
  The v0.10.0 dehydration moved the bug-event redaction rule (no absolute local paths,
  IPs, hostnames, private names or secrets in any bug-event field) from the always-on
  law into the on-demand dd-bug-registration skill (§3). An agent that registers a bug
  without invoking the skill — bug paths are ADDITIVE and registration is deliberately
  frictionless — no longer sees the rule at the moment it writes the event. Fix shape
  named by the reviewer: ONE always-on reinforcement line in DADAIA.md §6's
  register-every-bug paragraph pointing at the redaction rule, keeping the full rule
  on-demand in the skill (no rehydration of the dehydrated block). Distinct from live
  entry #23 refusal-path-redaction: that is the push-refusal renderer printing blob
  paths; this is the bug-event field rule's always-on visibility — different surface,
  no dedupe (dedupe record in intake report #2).
intents:
  - subject:
      kind: catalog
      ref: public-asset-distribution
    change: >-
      public/data/DADAIA.md §6 (Register every bug) gains one always-on line
      reinforcing the redaction rule by reference to dd-bug-registration §3; projected
      law files re-installed; no second full statement of the rule enters the law.
---

# Bug-event redaction rule — always-on reinforcement line

## Description

See frontmatter. Source: security-reviewer v0.10.0 ship handoff
`.dadaia/handoff/dadaia-workspace/2026-08-15T151005Z-security-reviewer-v0.10.0-ship.handoff.json`
(LOW). The law's §6 already routes to `dd-bug-registration` for "command, redaction rule
and context routing" — the reviewer's point is that the *existence* of a redaction
obligation should be visible before the skill is opened, because registration is the one
flow designed to happen without ceremony.

## Acceptance criteria

- `DADAIA.md` §6 carries exactly one reinforcement line naming the redaction obligation;
  the full rule remains only in `dd-bug-registration` §3 (proxy-2 clean — no duplicated
  block).
- Projections re-installed; `dadaia public doctor` green including `[ok] public-privacy`.

## Provenance

Intake report #2 item 2-4 — APPROVED. Trace: operator-delegated adjudication, 2026-08-15
(goal directive), verdicts per PM recommendation
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`).

## Ownership

`ai-engineer` (law text is a public/data asset; human-operator projection caveat applies —
the change lands at the source and re-projects). Priority P3.
