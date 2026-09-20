# specs/ADRs/ — Architecture Decision Record Rules

Scope: this file governs only `specs/ADRs/`.

## 1. Shape

- JSONL, one record per line, `decisions.jsonl`, `decision-record-v1`.
- Fields: `id` (NNNN, zero-padded, monotonic, gap-free, never reused), `ts`, `title`, `status`.
- Fields (continued): `context`, `decision`, `consequences`, `measured_by`, `supersedes`, `amends`.
- `status` values: `proposed` | `accepted` | `rejected` | `superseded`.
- `accepted` requires a resolvable `measured_by` — a `pytest`/`lint-imports` invocation or a grep-able code (`SPEC-DOC-nnn`, `WS-*`, `BL-*`, `RELEASE-TREE-*`, `LEDGER-*`), never prose.
- Schema: `public/schemas/ADRs/decision-record-v1.schema.json`.

## 2. Acceptance law (operator-only)

- Any agent may append a record with `status: "proposed"`.
- One decision per change set, naming every Part-1 principle it creates or changes — never one per principle that merely exists.
- Only the operator flips `status` to `accepted` (in-place edit, `measured_by` set to a real check).
- A record born from an operator grill ruling is `accepted` at append, the ruling date in `context`.
- An agent that writes `status: "accepted"` has violated this law.
- `accepted` is then immutable: `context`/`decision`/`consequences` never rewritten again.
- A reversal is always a new record (`supersedes`/`amends` naming the earlier `id`), never an edit.

## 3. Commit shapes (FR8 shape 2, extended)

| Act | Commit | Stages |
|---|---|---|
| Propose | `docs(adr): propose <slug>` | the appended `decisions.jsonl` line, alone |
| Accept | `docs(adr): accept <slug>` | the record's `status`/`measured_by` flip + the paired Part-1 memory hunk, same commit |

- Never a third shape: rejecting is a `status: "rejected"` edit by the operator, staged alone.
- Superseding is a new record proposal; once accepted, the superseded record stays in `decisions.jsonl` with `status: superseded` and the successor's `supersedes` naming it.
- A superseded record's `id` is never reused, never re-numbered, and its line never moves.

## 4. Discovery

- `decisions.jsonl` is the complete, authored inventory — proposed, accepted, rejected and superseded alike.
- No hand-kept index table — `tests/contract/test_adr_canon.py` enforces monotonic, gap-free, duplicate-free numbering.
- The file may be legitimately empty.

## 5. Relationship to memory and audits

- A Part-1 principle carries `ADR: NNNN (proposed|accepted)` naming the decision record that admitted it.
- The commit touching a Part-1 principle carries its accepted decision; a pre-canon principle carries `ADR: none` until it is next touched.
- The memory atom points at the ADR, never the reverse.
- `dd-audit-project`'s pillar 3 (`PILLAR-MEMORY.md`) is the sole mechanical check that a Part-1 hunk and an accept commit pair.

### 5.1 The first-inventory case (bootstrap)

- The pairing law presupposes a Part 1 that already exists — it does not apply to the CREATING commit.
- A CREATING commit's principles name a `proposed` decision, or the literal `ADR: none` for a pre-canon principle.
- Pillar 3 grades that as an operator finding, never a HIGH drift finding, and never agent-clearable.
- From the first `docs(adr): accept <slug>` commit onward, the pairing law applies unconditionally.
