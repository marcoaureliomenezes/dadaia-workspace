---
title: "refusal-path-redaction: the push-gate refusal prints the offending blob path verbatim (CWE-532 residual)"
status: candidate
opened: 2026-08-14
description: >-
  v0.9.0 CLOSURE "Backlog returns" item (LOW, from the code-review round),
  independently re-confirmed by the ship security review. The refusal masks the
  matched term (first…last) and never echoes the matched line, but prints the
  offending blob path verbatim in "<local-ref> -> <remote-ref>: <path>:<line>
  (blob <sha12>)" — and a path such as specs/<private-name>/notes.md can itself
  carry the private name the gate is protecting. Meanwhile FR8a's --redact covers
  doctor/context-list/context-show only, while the new QA doctrine tells agents to
  transcribe diagnostics into authored documents; today only the by-hand masking
  branch exists. Two acceptable resolutions were named at routing: extend the
  redaction surface to the refusal renderer, or state in the doctrine that gate
  refusals must be hand-masked INCLUDING the path. Secondary, same class
  (recorded, likely accept): the short blob sha lets any holder of the local
  repository recover the full unmasked term via git show — local-only and inherent
  to naming the object at all.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/service.py#_compose_denylist_refusal
    change: >-
      Resolution A: mask private-name-bearing path segments in the refusal
      rendering (reusing the ContextRedactor/masking machinery), keeping the
      diagnostic satisfiable — the operator must still be able to locate the
      offending file.
  - subject:
      kind: code
      ref: dadaia_workspace/cli/redact.py#ContextRedactor
    change: >-
      If resolution A is chosen: extend the redaction surface to the refusal
      renderer so gate output joins the three FR8a verbs; render-boundary only,
      default output unchanged where no redaction applies.
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#Redaction At Authoring
    change: >-
      If resolution B (doctrine-only) is chosen instead: record in the
      redaction-at-authoring doctrine (memory atom + qa-engineer persona) that
      transcribed gate refusals must be hand-masked including the path, so the
      by-hand branch is at least stated rather than implicit. Either resolution
      closes the entry; pick one at grill time.
---

# refusal-path-redaction

## Description

See frontmatter. Sources, deduplicated into this single entry:

- `specs/_archive/releases/v0.9.0/CLOSURE.md` §"Backlog returns" —
  `refusal-path-redaction` (LOW, from the review), naming the two acceptable
  resolutions; also listed in the accepted-without-action ledger as "routed to
  backlog above, not fixed here".
- Security-reviewer ship handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`
  — LOW "CWE-532 residual (previously found, accepted, still open)":
  independently confirmed at `service.py:351`, with the interim rule that agents
  transcribing a refusal must mask the path as well as the term, and the demand
  that this backlog entry pick one of the two resolutions when picked.

## Motivation

The refusal is the one place the gate speaks at the exact moment it is protecting
a name; a path that carries the name defeats the masking. Low severity because the
audience is the pushing developer's own terminal — but the QA doctrine actively
encourages transcription into authored documents, which is the entry path both
historical incidents used.

## Acceptance criteria

- One of the two named resolutions implemented (renderer redaction) or ratified in
  doctrine (hand-mask including path), with the choice and reason recorded here.
- If renderer redaction: a unit test proves a private-name-bearing path is masked
  in the refusal while the diagnostic stays satisfiable; default (non-matching)
  output byte-identical.
- The interim by-hand rule stops being the only branch.

## Ownership

`software-engineer` (resolution A) or `ai-engineer` (resolution B, doctrine
surface); `security-reviewer` verifies closure.

## Intake adjudication (ADR #15 — report #1)

**APPROVED** — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts
per PM recommendation. Adjudicated via intake report #1
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T132600Z-intake.html`).
The entry remains a live pickable candidate.
