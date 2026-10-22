# Concepts

Seven terms, one section each. Their glossary entries live in
[`CONTEXT.md`](../CONTEXT.md); each rule a section names is stated once, by its owner.
The walkthrough is [getting started](getting-started.md).

## Context

A *context* is one canonical `specs/` tree owned by one main repository: the unit for
memory, backlog, bugs, releases, reports and handoffs. Associated repositories own
production source only. Resolution, scope and races: `dadaia_workspace/public/data/dadaia-AGENTS.md`,
heading *Context, scope and races*.

## Release and candidate

A *release* is one SemVer line under `specs/releases/<M.m.p>/`, and its *candidates*
(`rc-<N>/`) are closed-scope steps through it; the highest candidate is live. The release
state is owned by
`dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`; the SPEC `Origin` line
and the release ids by `dadaia_workspace/public/scaffold/releases/AGENTS.md` (Authoring rules).

## The flow

Every demand takes one of two arms, Arm A (feature) or Arm B (bug). The steps of each arm
are the root map's, `dadaia_workspace/public/data/AGENTS.md`, heading *The flow*. Documents
record the flow; there is no in-repository flow engine. The review gates of a merge are in
`dadaia_workspace/public/data/worktrees-AGENTS.md`, heading *Merges, gates, review*.

## The gate

The pre-tool gate and the git chokepoints refuse what the root map's heading *What is
enforced* lists. Every refusal carries one executable `fix:` line or one operator act.

## Memory

*Memory* is current product truth: the product atoms, `ARCHITECTURE.md` and `QUALITY.md`.
A bound session receives the constitution, technical bootstrap and catalog digest. Its
writing rules are the memory law, `dadaia_workspace/public/scaffold/memory/AGENTS.md`.

## Bugs and backlog

A bug is one record in `specs/bugs/BUGS.jsonl`; its statuses, fields, lanes and writer are
the bug law, `dadaia_workspace/public/scaffold/bugs/AGENTS.md`, and `bugs.py --help`. The
window review judges each resolved fix KEEP or REBUILD and schedules no work: a fix judged
REBUILD is proposed as a bug and, once confirmed, rebuilt in its own lane. The rule is
`dadaia_workspace/public/skills/dd-release-definition/SKILL.md`, heading *Pick the set*.

The backlog is the operator's active demand queue; its law is
`dadaia_workspace/public/scaffold/backlog/AGENTS.md`, and `backlog.py --help` names its verbs.

## Audits

An *audit* is the full-tree inspection lane. Its law, its three pillars and its one
remediation release are in `dadaia_workspace/public/scaffold/audits/AGENTS.md`. The bug
pillar's forensic metrics are in `dadaia_workspace/public/skills/dd-audit-project/PILLAR-BUGS.md`,
heading *The nine forensic metrics*.
