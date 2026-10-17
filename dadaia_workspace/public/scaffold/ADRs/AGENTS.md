# specs/ADRs/ — Architecture Decision Record Rules

Scope: this file governs only `specs/ADRs/`.

## 1. Shape

- JSONL, one record per line, `decisions.jsonl`, `decision-record-v1`.
- Fields: `id` (NNNN, zero-padded, monotonic, gap-free, never reused), `ts`, `title`, `status`.
- Fields (continued): `context`, `decision`, `options`, `consequences`, `measured_by`, `supersedes`, `amends`.
- `options`: at least two, each `{name, tradeoff, rejected_because}`.
- Threshold: a decision is an ADR only when all three legs hold: it is a one-way door, it is architecturally significant, and at least two genuine options exist; a decision failing a leg lives in its scoped law line or the SPEC.
- `status` values: `proposed` | `accepted` | `rejected` | `superseded`.
- `accepted` requires a non-empty `measured_by` naming the check; `.dadaia/.venv/bin/dadaia doctor` (`LEDGER-ADR-SCHEMA`) validates every record and the numbering.
- Schema: `.dadaia/agentic/schemas/ADRs/decision-record-v1.schema.json`.

## 2. Acceptance law (operator-only)

- Any agent may append a record with `status: "proposed"`.
- One decision per change set; never one per statement that merely exists.
- Only the operator accepts: the main thread writes `accepted` with `ruling: {date, words}` (his verbatim words, in the turn he rules; the question plus the chosen option, never only an answer id) and `measured_by` naming a check of a kind `specs/memory/AGENTS.md` §2 lists; never delegated, and no role agent writes `accepted` or `ruling`.
- `accepted` is then immutable: `context`/`decision`/`consequences` never rewritten again.
- A reversal is a new record naming the earlier `id` in `supersedes`/`amends`.
- The main thread writes `rejected` on the operator's ruling.
- Superseding is a new record proposal; once accepted, the superseded record stays in `decisions.jsonl` with `status: superseded` and the successor's `supersedes` naming it (one id, or comma-separated ids ascending).
- A superseded record keeps its `id` and its line.

## 3. Commit shapes

- The ADR commit shapes (propose, accept, repair): `dd-gitflow-default` §3a.
