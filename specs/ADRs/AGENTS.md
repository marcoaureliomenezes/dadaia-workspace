# specs/ADRs/ — Architecture Decision Record Rules

Scope: this file governs only `specs/ADRs/`. Decision records for every principle-level
choice this codebase's architecture, quality and tech-stack memory depend on (FR19/D12).

## Shape — Nygard + MADR fields, one decision per file

One file per decision: `NNNN-<slug>.md`, four digits, monotonic, gap-free, **never
reused** even for a rejected or superseded ADR. Every file carries, in order:

```markdown
# ADR NNNN — <title>

Status: proposed
Date: YYYY-MM-DD
Supersedes: — · Amends: — · Amended by: —

## Context
What forces make this decision necessary — the problem, not the solution.

## Decision
"We will …" — the choice, stated as a commitment, not a discussion.

## Consequences
+ benefits
- costs / trade-offs accepted

## Confirmation
Measured by: <the existing mechanical check that proves this decision holds — an
import-linter contract, a contract test node id, a doctor check code, a ratchet
script>.
```

An ADR with no `## Confirmation` / `Measured by:` line cannot be accepted — a decision
nobody can measure is not a principle, it is prose (FR18's own admission rule).

## Status vocabulary — closed set, exactly these tokens

`proposed` | `accepted` | `rejected` | `superseded by NNNN`

## The operator-only acceptance law

**Any agent may author an ADR with `Status: proposed`. ONLY the operator flips a
`Status` line to `accepted`, appending `Accepted by: operator, <date>` on its own
line.** An agent that writes `Status: accepted` has violated this law, whatever its
reasoning — the acceptance line is a physical marker, not a permission the writer grants
itself. **`accepted` is then immutable**: an accepted ADR is never edited in place again
except to add `Amended by: NNNN`/`Superseded by: NNNN` cross-references when a *later*
ADR reverses or narrows it — a reversal is always a **new** ADR, never a rewrite of the
old one's `Decision`/`Consequences` text.

## Commit shapes (FR8 shape 2, extended)

| Act | Commit | Stages |
|---|---|---|
| Propose | `docs(adr): propose NNNN-<slug>` | the new `specs/ADRs/NNNN-<slug>.md` file, alone |
| Accept | `docs(adr): accept NNNN-<slug>` | the ADR's `Status`/`Accepted by:` flip **plus** the Part-1 memory hunk (`ARCHITECTURE.md`/`QUALITY.md`/`TECHSTACK.md`) it admits — the two travel together, in the same commit, so pillar 3's "Part 1 changed without an accepted ADR" check (`dd-audit-project`'s `PILLAR-MEMORY.md`) always finds a pairing |

Never a third shape: rejecting an ADR is a `Status: rejected` edit by the operator,
staged alone; superseding is a **new** ADR proposal plus, once accepted, the superseded
ADR's own `Superseded by: NNNN` line updated by the operator in the accept commit of the
new one.

## Index — the 28 ADRs at T-050-30

Discover the live set with `ls specs/ADRs/*.md` — this table is a snapshot, not the
source of truth; a contract test (`tests/contract/test_adr_canon.py`) discovers the real
inventory by glob and enforces monotonic, gap-free, duplicate-free numbering.

| # | Title | Status |
|---|---|---|
| 0001 | Features depend on ports, not adapters | proposed |
| 0002 | Features never spawn a subprocess | proposed |
| 0003 | `core` is OS-primitive free | proposed |
| 0004 | `core` is the bottom ring | proposed |
| 0005 | `infrastructure` depends only on `core` | proposed |
| 0006 | `core.kernel_tunables` is a pure-constant leaf | proposed |
| 0007 | Features are mutually independent | proposed |
| 0008 | The CLI composes via the container | proposed |
| 0009 | One context-resolution authority | proposed |
| 0010 | Suppressed layering edges are capped and ratchet down | proposed |
| 0011 | File I/O enters `core` only through an authorized set | proposed |
| 0012 | Hooks never import the composition root | proposed |
| 0013 | Architecture diagrams derive from live code | proposed |
| 0014 | The release-event fold never writes | proposed |
| 0015 | The release-record envelope is closed | proposed |
| 0016 | Stored provenance equals derived provenance | proposed |
| 0017 | Every behavior surface maps to exactly one law section | proposed |
| 0018 | Module-size ceilings ratchet down | proposed |
| 0019 | Complexity ceilings ratchet down | proposed |
| 0020 | `specs upgrade` and `specs doctor` do not grow | proposed |
| 0021 | Every test carries a size tier with an enforced timeout | proposed |
| 0022 | Quarantine requires a registered bug | proposed |
| 0023 | Private-symbol imports in tests ratchet down | proposed |
| 0024 | Test intent is declared at birth | proposed |
| 0025 | SCAFFOLD tests expire | proposed |
| 0026 | One number per parameter | proposed |
| 0027 | The pyramid shape is measured every run, reported not gated | proposed |
| 0028 | The pytest marker set is closed and single-sourced | proposed |

## Relationship to memory and audits

A Part-1 principle in `specs/memory/{ARCHITECTURE,QUALITY,TECHSTACK}.md` carries
`Accepted by: ADR NNNN` naming the ADR that admitted it — never the reverse; the memory
atom points at the ADR, the ADR does not point back into memory beyond its own
`## Confirmation` line. `dd-audit-project`'s pillar 3 (`PILLAR-MEMORY.md`) is the sole
mechanical check that a Part-1 hunk and an `accept` commit travel together — no CLI verb
and no `specs doctor` rule are added for this (A19.4).
