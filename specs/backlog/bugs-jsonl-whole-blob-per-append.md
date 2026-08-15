---
title: "bugs.jsonl republishes its whole file as a new blob on every append — the dominant scan-cost and content-resurfacing driver"
status: idea
opened: 2026-08-14
description: >-
  v0.9.0 CLOSURE "Backlog returns" idea (routed to the ideas lane at the PE's
  judgement), reinforced twice by the ship security review. Because git stores a
  whole blob per file version, every `dadaia bugs append` republishes the entire
  ~900 KB specs/bugs/bugs.jsonl as a NEW blob in the pushed range. Two measured
  costs: (1) performance — one such blob appended twice inside v0.9.0's local
  range dominated the push-range scan (~2.7-3.4 s wall over 247 objects / 66
  blobs) and is the reason the A7.3 2 s budget was recorded as partially missed
  (V14: cause is data, not mechanism); (2) content resurfacing — every append
  makes ALL long-published lines of the file "new" range content again, which is
  how the security review's wider-set probe surfaced two historical hits on
  bugs.jsonl:353 (a since-DEAD context name resident since v0.1.x). Candidate
  shapes to weigh at grill time: per-bug or per-period sharding of the ledger
  (e.g. bugs/<year>/ or bugs/<bug-id>.jsonl), an append-only segment scheme, or
  accepting the cost and letting prior-published-term-amnesty neutralize the
  resurfacing half. Constraints: the never-delete law (events are kept forever),
  the ADDITIVE gate classification of specs/bugs/**, the jsonl append contract
  used by dadaia bugs append/status/stats, and existing bugs.jsonl consumers
  (panel, doctor, release pick precedence).
---

# bugs.jsonl whole-blob-per-append

## Description

See frontmatter. Sources, deduplicated into this single entry:

- `specs/_archive/releases/v0.9.0/CLOSURE.md` §"Backlog returns" (ideas routing)
  and §V14 — the A7.3 miss attribution ("dominated by one ~900 KB
  specs/bugs/bugs.jsonl blob appended twice inside this local range … whole-file
  blob per append").
- Security-reviewer ship handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`
  — the FR3 coverage-gap finding's supporting analysis: "bugs.jsonl republishes
  its whole file as a new blob on every append, which is why long-published lines
  resurface in a new object at all — a cost already recorded in ## Backlog
  returns".

## Motivation

One file's storage shape is simultaneously the gate's main perf tax on ordinary
ranges and its main source of resurfaced historical content. An idea rather than
a candidate because the right shape is genuinely open (sharding vs segments vs
accept-with-amnesty) and touches the bug-ledger contract — grill before binding
intents.

## Ownership

Needs `software-architect` input on the ledger shape before promotion to
candidate; cross-references `closure-v14-perf-figure-correction`,
`registry-derived-foreign-name-set`, `prior-published-term-amnesty`.
