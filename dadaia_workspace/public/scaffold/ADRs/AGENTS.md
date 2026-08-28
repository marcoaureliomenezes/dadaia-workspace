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

## Index

An ADR exists per DECISION — written when a Part-1 principle is created or changed —
never one file per principle that merely exists. Discover the live set with `ls
specs/ADRs/*.md`; a contract test (`tests/contract/test_adr_canon.py`) discovers the
real inventory by glob and enforces monotonic, gap-free, duplicate-free numbering. This
file carries no hand-kept table of the inventory.

## Relationship to memory and audits

A Part-1 principle in `specs/memory/{ARCHITECTURE,QUALITY,TECHSTACK}.md` carries
`Accepted by: ADR NNNN` naming the ADR that admitted it — never the reverse; the memory
atom points at the ADR, the ADR does not point back into memory beyond its own
`## Confirmation` line. `dd-audit-project`'s pillar 3 (`PILLAR-MEMORY.md`) is the sole
mechanical check that a Part-1 hunk and an `accept` commit travel together — no CLI verb
and no `specs doctor` rule are added for this (A19.4).

**The first-inventory case (bootstrap).** The pairing law above presupposes a Part 1
that already exists. It does not apply to the CREATING commit — the one that adds
`## Part 1 — Principles` to a memory trio file for the first time, with every one of
its principles' `ADR:` lines naming a `proposed` (not yet `accepted`) ADR: that commit
is the bootstrap shape, not drift. Pillar 3's pairing check (`PILLAR-MEMORY.md` §2)
grades it as a T-050-31-class operator finding — the operator's acceptance sitting has
not yet happened — never a HIGH drift finding, and never something an agent is expected
to clear, since flipping a `Status` line to `accepted` is operator-only (above). From
the first `docs(adr): accept NNNN-<slug>` commit onward — the first commit anywhere in
history that flips any ADR's `Status` to `accepted` — the pairing law applies
unconditionally: every later Part-1 hunk needs its own `accept` commit, same or
immediately preceding, no further exception.
