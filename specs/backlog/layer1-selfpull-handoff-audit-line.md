---
name: layer1-selfpull-handoff-audit-line
status: candidate
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.57 closure backlog return (FR4 Ruling A — Layer-1 injection ratified self-pull; the mechanical verifiability was deferred)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/hooks/ctx_inject.py#main" }
    change: "make Layer-1 self-pull mechanically verifiable: v0.1.57 Ruling A ratified self-pull for constitution/architecture/quality-assurance (ctx_inject byte-identical — the bounded tech-stack + lean catalog digest is the ONLY Layer-1 injection, and those atoms reach agents only via step0 self-pull discipline). Add a schema-level 'prove the atoms were read' audit line to agent handoffs — an InjectedContext/self-pull ref field in handoff-v1.1 that records which Layer-1 self-pull atoms a session actually loaded — plus a validator that checks it, turning the L1 self-pull DISCIPLINE into a checkable contract (symmetric with the Layer-2 mechanical proof R9 already ships: the role→atom map records refs in InjectedContext.refs and fragment_coherence_doctor FRAG-COH-4 asserts coverage). Requires a handoff-v1.1 schema bump + all-agent adoption + a reports-validation check."
---

# BACKLOG — Layer-1 self-pull handoff audit line

**Priority:** HIGH. v0.1.57 (R9 "Injection canon") settled the Layer-1 injection question by
**ratifying self-pull** (Ruling A, operator-overridable): constitution/architecture/quality-assurance
are never injected on Layer-1 — `ctx_inject.py#_build_memory` stays byte-identical (bounded
tech-stack digest + lean catalog digest), preserving the deliberate v0.1.30 dehydration and avoiding
unbounded Layer-1 context growth. What R9 delivered mechanically is the **Layer-2** half: the
role→memory-atom map records each resolved atom in `InjectedContext.refs`, and the coherence doctor
(`FRAG-COH-4`) asserts every model-driven step's role-mapped atom appears in its injected refs.

The **Layer-1** half was deliberately deferred rather than ballooning R9's surface. Today an agent's
Layer-1 self-pull of the deep atoms (via the step0 memory-bootstrap skill) is **discipline, not a
checkable contract** — nothing proves a session actually read the constitution / architecture /
quality-assurance atoms it was supposed to self-pull. This entry tracks closing that gap with a
**handoff audit line**: a schema-level field in agent handoffs that records which Layer-1 self-pull
atoms were loaded, plus a validator that enforces it. It needs a handoff-v1.1 schema bump, all-agent
adoption, and a `dadaia reports validate` check — a bounded, cross-cutting change worth its own pick.

**Override:** if the operator prefers **bounded phase-aware Layer-1 digests** injected at
`ctx_inject` instead of a self-pull audit line, FR4/Ruling A reopens and this entry is superseded by
that redesign.
