# specs/ADRs/ — Architecture Decision Record Rules

Scope: this file governs only `specs/ADRs/`. Decision records for every principle-level
choice this codebase's architecture, quality and tech-stack memory depend on (FR19/D12).

## Shape — JSONL, one record per line (v0.5.0 specs-canon closure)

One line per decision in `decisions.jsonl` — a `decision-record-v1` object: `id`
(NNNN, zero-padded 4-digit, monotonic, gap-free, **never reused**), `ts`, `title`,
`status` (`proposed`|`accepted`|`rejected`|`superseded`), `context`, `decision`,
`consequences`, `measured_by`, `supersedes`, `amends`. `accepted` requires a
non-null `measured_by` — a decision nobody can measure is not a principle, it is
prose (FR18's own admission rule). Schema: `public/schemas/ADRs/decision-record-v1.schema.json`.

## The operator-only acceptance law

**Any agent may append a record with `status: "proposed"`. ONLY the operator flips a
`status` field to `accepted` (an in-place edit of that one line, `measured_by` set to
a real check).** An agent that writes `status: "accepted"` has violated this law,
whatever its reasoning — accepting is not a permission the writer grants itself.
**`accepted` is then immutable**: an accepted record's `context`/`decision`/
`consequences` are never rewritten again — a reversal is always a **new** record
(`supersedes`/`amends` naming the earlier `id`), never an edit of the old one's text.

## Commit shapes (FR8 shape 2, extended)

| Act | Commit | Stages |
|---|---|---|
| Propose | `docs(adr): propose <slug>` | the appended `specs/ADRs/decisions.jsonl` line, alone |
| Accept | `docs(adr): accept <slug>` | the record's `status`/`measured_by` in-place flip **plus** the Part-1 memory hunk (`ARCHITECTURE.md`/`QUALITY.md`/`TECHSTACK.md`) it admits — the two travel together, in the same commit, so pillar 3's "Part 1 changed without an accepted ADR" check (`dd-audit-project`'s `PILLAR-MEMORY.md`) always finds a pairing |

Never a third shape: rejecting a decision is a `status: "rejected"` edit by the
operator, staged alone; superseding is a **new** record proposal plus, once accepted,
the superseded record's whole line MOVED (never copied) from `decisions.jsonl` to
`_superseded/superseded.jsonl` with `status: "superseded"` — its `id` is never reused,
never re-numbered — in the accept commit of the new one.

## Discovery

`decisions.jsonl` + `_superseded/superseded.jsonl` together are the complete,
authored inventory — no hand-kept index table (a contract test,
`tests/contract/test_adr_canon.py`, enforces monotonic, gap-free, duplicate-free
numbering across both files). Either file may be legitimately empty.

## Relationship to memory and audits

A Part-1 principle in `specs/memory/{ARCHITECTURE,QUALITY,TECHSTACK}.md` carries
`ADR: NNNN (proposed|accepted)` naming the decision record that admitted it — never
the reverse; the memory atom points at the ADR, the ADR does not point back into
memory. `dd-audit-project`'s pillar 3 (`PILLAR-MEMORY.md`) is the sole mechanical
check that a Part-1 hunk and an `accept` commit travel together — no CLI verb and no
`specs doctor` rule are added for this (A19.4).

**The first-inventory case (bootstrap).** The pairing law above presupposes a Part 1
that already exists. It does not apply to the CREATING commit — the one that adds
`## Part 1 — Principles` to a memory trio file for the first time, with every one of
its principles' `ADR:` lines naming a `proposed` (not yet `accepted`) decision, or the
literal `ADR: none` for a pre-canon principle: that commit is the bootstrap shape, not
drift. Pillar 3's pairing check (`PILLAR-MEMORY.md` §2) grades it as an operator
finding — the operator's acceptance sitting has not yet happened — never a HIGH drift
finding, and never something an agent is expected to clear, since flipping `status` to
`accepted` is operator-only (above). From the first `docs(adr): accept <slug>` commit
onward — the first commit anywhere in history that flips any decision's `status` to
`accepted` — the pairing law applies unconditionally: every later Part-1 hunk needs its
own `accept` commit, same or immediately preceding, no further exception.
