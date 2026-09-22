---
specs_pattern_version: 6
constitution_version: 6.0.0
---

# Constitution — dadaia-workspace

Permanent product law, stated **once**. Every rule already stated in `DADAIA.md` lives there
alone; this file carries only what no other file states.

## 1. Identity

`dadaia-workspace` is a multi-AI-harness, multi-project, SDD-oriented, multi-agent
development workspace. Its product is workspace-level context-engineering: it orients a
generic agent fleet to build many projects safely, in parallel, without re-deriving how to
work and without colliding.

Definitions are pointers, not rules — each term is defined once, in the atom named.

| Term | Defined once in |
|---|---|
| Vision · layout and module map | [[product-vision]] · [[architecture]] |
| **Spec Context Project** — one canonical specs folder bound to one repository | [[spec-context-project]] |
| **Entry harness** — the coding harness a human launches, and the roster of them | [[tech-stack]] Part 2 › Snapshot |
| **Harness isolation** — a workspace installed for any subset of the roster | the `specs/memory/product/harness/` atoms |
| **Agentic entity** — Persona, Deterministic Behavior, Abstract Rule, universal surface | [[agentic-entities]], registry `dadaia_workspace/public/entities/registry.json` |

The harness roster is enumerated in exactly one memory atom, set-equal to
`dadaia_workspace/core/harness_registry.py`; this constitution never enumerates it.

## 2. The Operational-Change Lane

The only sanctioned lane with no live release: version-metadata bumps, documentation-only
changes, CI-infrastructure fixes and dependency bumps — each on explicit operator order,
through the sha-keyed security-APPROVE push gate, with green CI.

**The memory-bearing test:** any change that alters agent or product behavior, or that would
require a `specs/memory/**` edit for memory to stay true, requires a release; an ungated span
that creates memory drift obligates the next release to carry a memory-truth pass.

This lane is judgment-enforced, at human PR review.

## 3. Dispatcher Purity

Only the main thread (the operator's session) dispatches sub-agents; every persona is a
worker that surfaces needs to the main thread and never spawns agents.

The scaffolded roster is **closed** — the library ships no plugin agent — and an operator's
own agents are never scaffolded by it and never derived from the registry. A persona is a
generic implementation specialized only in its SDD role: project-domain knowledge lives in
the bound context's `specs/`, never in a persona.

## 4. Versioning This File

`constitution_version` is semver: MAJOR for a changed or removed article, MINOR for a new
article or substantive clarification, PATCH for wording. An amendment lands with the accepted
decision that decided it, in the same commit; amendment history lives in git and in the
amending release's `_RELEASE.json` `log`, never inline.

<!-- dadaia:fixed slop-law -->
## Slop — workspace law (fixed)
- Slop is what passes the deletion test without loss: removed, no behavior changes and no decision loses its record.
- A SPEC declares scope, observable criteria and decisions in domain names; it fits the byte ceiling of `specs/releases/AGENTS.md`.
- A concept takes a glossary name; a numbered code exists only where a mechanical index reads it (FR, AC, T-).
- Every file has a canonical home and a GC path; summaries, backups, notes and scratch live in `.dadaia/tmp/` or do not exist.
- A branch dies at merge; a candidate exists only with scope that changes behavior.
- Measured by `dadaia doctor` (FIXED-1/2) and the slop ratchets; detection signals: `dd-code-review` SLOP.md.
<!-- /dadaia:fixed slop-law -->
