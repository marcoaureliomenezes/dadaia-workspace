# specs/ADRs/ — Architecture Decision Record Rules

Scope: this file governs only `specs/ADRs/`.

## 1. Shape

- JSONL, one record per line, `decisions.jsonl`, `decision-record-v1`.
- Fields: `id` (NNNN, zero-padded, monotonic, gap-free, never reused), `ts`, `title`, `status`.
- Fields (continued): `context`, `decision`, `consequences`, `measured_by`, `supersedes`, `amends`.
- `status` values: `proposed` | `accepted` | `rejected` | `superseded`.
- `accepted` requires a non-empty `measured_by` naming the check; `.dadaia/.venv/bin/dadaia doctor` (`LEDGER-ADR-SCHEMA`) validates every record and the numbering.
- Schema: `.dadaia/agentic/schemas/ADRs/decision-record-v1.schema.json`.

## 2. Acceptance law (operator-only)

- Any agent may append a record with `status: "proposed"`.
- One decision per change set, naming every canonical memory statement it creates or changes — never one per statement that merely exists.
- Only the operator accepts: the main thread writes `accepted` with `ruling: {date, words}` (his verbatim words or grill answer id, in the turn he rules) and `measured_by` naming a check of a kind `specs/memory/AGENTS.md` §2 lists; never delegated, and no role agent writes `accepted` or `ruling`.
- A canonical-memory commit that only states what the code is, outside a `### P-NN` principle, needs no ADR and names its code evidence.
- `accepted` is then immutable: `context`/`decision`/`consequences` never rewritten again.
- A reversal is a new record naming the earlier `id` in `supersedes`/`amends`.
- Rejecting is a `status: "rejected"` edit by the operator.
- Superseding is a new record proposal; once accepted, the superseded record stays in `decisions.jsonl` with `status: superseded` and the successor's `supersedes` naming it (one id, or comma-separated ids ascending).
- A superseded record keeps its `id` and its line.

## 3. Commit shapes

- The ADR commit shapes (propose, accept, repair): `dd-gitflow-default` §3a.

## 5. Relationship to memory and audits

- Canonical memory's `ADR:` line: `specs/memory/AGENTS.md` §2.
- `dd-audit-project`'s pillar 3 (`PILLAR-MEMORY.md`) is the audit check that a canonical hunk and an accept commit pair.

### 5.1 The first-inventory case (bootstrap)

- The pairing law presupposes a `## Principles` section that already exists — it does not apply to the CREATING commit.
- A CREATING commit's statements name a `proposed` decision, or the literal `ADR: none` for a pre-canon statement.
- Pillar 3 grades that as an operator finding, never a HIGH drift finding, and never agent-clearable.
- From the first `docs(adr): accept <slug>` commit onward, the pairing law applies unconditionally.
