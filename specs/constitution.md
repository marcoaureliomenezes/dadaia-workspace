---
specs_pattern_version: 6
constitution_version: 5.1.0
---

# Constitution — dadaia-workspace

Permanent product law, stated **once** and by reference. Every article names where its rule
is measured or described; no article restates a mechanism that the memory trio
(`specs/memory/ARCHITECTURE.md`, `specs/memory/QUALITY.md`, `specs/memory/TECHSTACK.md`),
`specs/memory/product/**` or `DADAIA.md` already carries.

**How to read a reference.** `P-01…P-17` are the Part-1 principles of `ARCHITECTURE.md`,
`P-18…P-27` of `QUALITY.md`, `P-28` of `TECHSTACK.md`; each names the mechanical check that
measures it and the ADR that admitted it. **Every ADR cited below is `proposed`** — the ids
become final at the operator's acceptance sitting (release 0.5.0, T-050-31), and a rejected
ADR takes its principle and this file's reference to it with it. **`C-NN`** marks a clause no
principle measures yet: it is a `proposed`-ADR candidate carried to the operator in the
coverage table of the release that introduced it, and it carries no ADR number until the
operator rules on it.

## 0. Identity & Definitions

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

**Law.** The harness roster is enumerated in exactly one memory atom, set-equal to
`dadaia_workspace/core/harness_registry.py`; this constitution never enumerates it
(**C-01** — measured today by `dadaia specs doctor` SPEC-DOC-037).

## 1. SDD Is Binding

No production change lands without an approved release gate and a reserved task, and bypass
language never overrides that. The gate artifacts, the canonical status tokens and the
task-marker lifecycle are stated once in `DADAIA.md` §6 (**C-02**).

**Operational-change lane** — the only sanctioned lane with no live release: version-metadata
bumps, documentation-only changes, CI-infrastructure fixes and dependency bumps, each on
explicit operator order, through the sha-keyed security-APPROVE push gate, with green CI.
**The memory-bearing test:** any change that alters agent or product behavior, or that would
require a `specs/memory/**` edit for memory to stay true, requires a release; an ungated span
that creates memory drift obligates the next release to carry a memory-truth pass. This lane
is judgment-enforced, at human PR review (**C-03**).

Bugs never travel through a release — the register → root-cause → RED → fix → GREEN →
`resolved` arm is `DADAIA.md` §1 Arm B. Fix approval belongs to the operator and the
consumer-side validation agent; an internal gate never substitutes (**C-04**).

## 2. Public Defaults Must Be Generic

A publicly distributed asset must be safe for **any** consumer: it carries nothing private,
and consumer-specific domain knowledge belongs in an optional pack or a private overlay, never
in a default. What counts as private, the credential boundary and the push-path scan are
stated once in `DADAIA.md` §8 and §9 (**C-05** — measured today by `dadaia public doctor`'s
`public-privacy` check and the pre-push denylist scan).

## 3. Memory Is Repository Truth

A claim in memory the product does not honor is a defect of the same severity as failing
code — that is what makes memory binding rather than documentation. Memory's current-truth
posture is `DADAIA.md` §6; its canon shape and authorship are §13 (**C-06**).

## 4. Runtime Parity Must Be Honest

No projection, doctor line or document claims enforcement a runtime does not actually
perform, and harness-specific behavior is expressed in that harness's native terms. Each
runtime's real posture: the `specs/memory/product/harness/` atoms and [[architecture]]
Part 2 (**C-07**).

## 5. Source Repo Must Stay Clean

The source repository never tracks what a runtime generates — a checkout is source and its
own artifacts, nothing a tool produced. The exclusion list, the per-tool redirection recipes
and the workspace-root whitelist are stated once in `DADAIA.md` §5 (**C-08** — measured today
by `dadaia doctor`'s ROOT checks and `tests/contract/test_source_repo_hygiene.py`).

## 6. Layering

The ring shape of this codebase is described once, in [[architecture]] Part 2 › Overview.
Every **edge** of that shape is a measured principle, and this article adds nothing to them —
it exists to make them constitutional: ports over direct adapters
(`ARCHITECTURE.md` P-01, ADR 0001 proposed); no subprocess inside a feature (P-02, ADR 0002
proposed); a `core` free of OS primitives (P-03, ADR 0003 proposed) and file-I-O-pure outside
its authorized set (P-11, ADR 0011 proposed) that imports no upper ring (P-04, ADR 0004
proposed); `infrastructure` on `core` only (P-05, ADR 0005 proposed); a pure-constant
tunables leaf (P-06, ADR 0006 proposed); mutually independent features composing through the
container (P-07, ADR 0007 proposed); container-composed CLI verbs (P-08, ADR 0008 proposed);
one context-resolution authority with three sanctioned importers (P-09, ADR 0009 proposed);
hooks that never import the composition root (P-12, ADR 0012 proposed); and every suppressed
layering edge capped and ratcheting down only (P-10, ADR 0010 proposed).

## 7. Canonical Development Lifecycle

Every action belongs to exactly one of eight phases: backlog definition · bug filing ·
research · audit · release definition · implementation · review gates · closure. Which agent
owns each phase is stated once in `DADAIA.md` §2; the write class and concurrency posture of
each path is stated once in `DADAIA.md` §3. The phase vocabulary a release may record is
closed by the release-record envelope (`ARCHITECTURE.md` P-15, ADR 0015 proposed) and folded
read-only (P-14, ADR 0014 proposed), so the fold is the one answer to "what phase is this
release in".

The audit lane's own law — one audit, one remediation release, every finding dispositioned
before the audit archives — is stated once in `DADAIA.md` §6 (Audits) (**C-09**).

## 8. Concurrency Invariants

**The workspace never serializes its actors.** Every concurrency mechanism it may not have —
lock, lease, acquisition, adoption, steal — and every one it does have — advisory presence,
caller-local READ mode, fail-open presence I/O, the push boundary as a quality gate rather
than a lock — is stated once in `DADAIA.md` §3, and its embodiment in code is described in
[[architecture]] Part 2 › Concurrency and [[sdd-gate-v3]] (**C-10**).

## 9. Coordinator + Sub-Agent Architecture

**Dispatcher purity:** only `project-manager` and `project-auditor` dispatch sub-agents;
every other persona is a worker that surfaces needs to its dispatcher and never spawns
agents. Roles and their write scopes are stated once in `DADAIA.md` §2, and the map from each
persona and scoped `AGENTS.md` to the law section it owns is measured by `ARCHITECTURE.md`
P-17 (ADR 0017 proposed).

## 10. Backlog → Release

Stated once in `DADAIA.md` §6 (Backlog, Releases): who creates demand, who curates it, how an
entry enters and leaves, pick-time priority, the bug-always-solved rule and the mandatory
grill before the SPEC. This constitution adds nothing to it and keeps the article only so the
lane has a constitutional address (**C-11**).

## 11. Checkpoints, Gates, and the Three Channels

A **checkpoint** is PM-mediated discipline — an APPROVE handoff advances it. A **gate** is a
mechanical block. Checkpoints never block mechanically: commits always flow (§8) and only the
push boundary blocks. The review cadence and the sha-keyed push verdict are stated once in
`DADAIA.md` §7; the git chokepoints in §3.

**Exactly three** report and communication channels exist — no fourth is created — and each
has exactly one path. The channels and their paths: `DADAIA.md` §5 and §6 (**C-12**).

## 12. Anti-Slop Law

1. Slop is defined once, in `DADAIA.md` §7.6, and stated for the specs class in the fixed section "Slop — workspace law" below; this constitution never restates it (**C-14**).
2. Every agent, skill, rule and hook owns or gates a phase of §7; a phase-less artifact is removed. Measured by `ARCHITECTURE.md` P-17 (ADR 0017 proposed).
3. A fix that only adds carries the reason removal was impossible; the bug-surface axis of every verdict answers "reduced" or "increased" per `DADAIA.md` §7 (**C-15**).
4. Derivation law: no scaffolded core sub-agent, hook or rule file without its Persona, Deterministic Behavior or Abstract Rule in the agentic entity registry (§0); operator-created assets are exempt. Measured by `dadaia public doctor` `entities-derivation` and `tests/contract/test_agentic_entities_derivation.py` (**C-16**).

## 13. Memory Canon

Authoritative memory is the trio — `specs/memory/ARCHITECTURE.md`, `specs/memory/QUALITY.md`,
`specs/memory/TECHSTACK.md` — plus `specs/memory/product/**`. **`product-engineer` is the sole
memory author**, writing only in the DEFINITION and CLOSURE phases: this is the "who" half no
hook can verify, and `specs/memory/AGENTS.md` defers to this article for it. That same file is
the one home of everything else about memory — the two-tier shape, the Part-1 admission rule
and its ADR gate, the atom format, and the forbidden history sections — read there, never
restated here (**C-17**).

## 14. Agent Roster

The scaffolded roster is **closed** — the library ships no plugin agent — and an operator's
own agents are exempt from §12.5 and never scaffolded by it. Agents are generic
implementations specialized only in their SDD role: all project-domain knowledge lives in the
bound context's `specs/`, never in a persona. Roster membership, phase ownership and write
scope are stated once in `DADAIA.md` §2, and every persona-to-law-section mapping is measured
by `ARCHITECTURE.md` P-17 (ADR 0017 proposed) (**C-18**).

## 15. Governance

This constitution is versioned (`constitution_version`, semver): MAJOR for a changed or
removed article, MINOR for a new article or substantive clarification, PATCH for wording. An
amendment lands with the ADR that decided it (§13); amendment history lives in the amending
release's `RELEASE.json` notes and in `_archive/`, never inline. `dadaia specs doctor` holds
this law consistent with code and memory (**C-19**).

## 16. Rules Map to Skills

Every always-on rule of this workspace is a section of `DADAIA.md`; every core skill and every
scoped `AGENTS.md` maps to exactly one such section, and every section has at least one owner.
That relation is declared in exactly one controlled source,
`dadaia_workspace/public/entities/behavior-map.json`, and is measured by `ARCHITECTURE.md`
P-17 (ADR 0017 proposed). A second declaration of the same relation is deleted (§12).

<!-- dadaia:fixed slop-law -->
## Slop — workspace law (fixed)
- Slop is what passes the deletion test without loss: removed, no behavior changes and no decision loses its record (`DADAIA.md` §7.6).
- A SPEC declares scope, observable criteria and decisions in domain names; it fits the byte ceiling of `DADAIA.md` §6.7.
- A concept takes a glossary name; a numbered code exists only where a mechanical index reads it (FR, AC, T-).
- Every file has a canonical home and a GC path; summaries, backups, notes and scratch live in `.dadaia/tmp/` or do not exist.
- A branch dies at merge; a candidate exists only with scope that changes behavior.
- Measured by `dadaia specs doctor` (FIXED-1/2) and the slop ratchets; detection signals: `dd-code-review` SLOP.md.
<!-- /dadaia:fixed slop-law -->
