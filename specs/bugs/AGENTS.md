# specs/bugs/ — Bug Ledger Rules

Scope: this file governs only `specs/bugs/`. It replaces the retired `bugs/README.md`
(v6 canon, FR1) — its content lives here now.

This directory holds this Spec Context Project's bug ledger: `BUGS.jsonl`, **one JSON
record per bug, appended once** — no event stream, no fold (v0.5.0 FR2/D11). Schema:
`bug-record-v1` (`dadaia_workspace/public/schemas/bugs/bug-record-v1.schema.json`).
There is no per-bug Markdown file and no session-lock gate on filing.

## Field classes (D11)

Every property carries its own mutability, declared once in the schema — this file
never re-states the field-by-field split, only the three classes:

| Class | Meaning | Examples |
|---|---|---|
| `immutable-core` | Never rewritten once appended | `id`, `ts`, `title`, `severity`, `surface`, `component`, `symptom`, `repro`, `expected` |
| `write-once` | Legitimately absent at registration; settable exactly once, then immutable | `root_cause`, `solution`, `evidence_loop`, `evidence_seam`, `evidence_diff`, `diff_direction` |
| `mutable-governance` | Rewritten in place through the atomic, refuse-stale update seam | `status`, `cause`, `caused_by`, `lineage_source`, `registration_commit`, `resolved_commit`, `resolution_granularity`, `resolved_release`, `audited` |

## Authoring rules

- Register a new bug with `dadaia bugs append --bug-id <slug> --title … --severity …
  --surface … --component … --context … --symptom … --repro … --expected …`
  (`dd-bug-registration`) — this appends the record **once**; do NOT hand-edit
  `BUGS.jsonl` to keep every entry schema-valid.
- Change a governance or write-once field on an existing record with `dadaia bugs
  update <id> --set <field>=<value>` — the one governance-write seam (AS-16): atomic,
  refuse-stale, redacted, and refused at the seam for any `immutable-core` field or a
  differing re-set of a `write-once` field.
- `status` has no `picked` value — a pick is the bundled release-definition commit
  (`DADAIA.md` §6), never a ledger write.
- Bug reports are **not** specs. They do not authorise implementation changes on their
  own. A bug may be addressed in a dedicated release or fixed on the spot (Arm B).
- Never hand-delete a record once appended. `dadaia bugs archive` is the only retiring
  path, and it is idempotent.

## Duties this ledger carries, and where each lives

- **The diagnosing method, lineage first.** Before any fix, phase 0 reads this ledger
  for prior fixes to the same `surface`/`component` and declares `caused_by` on the new
  record: `dd-diagnose` — the full window, cap, and diff-trust rule live there,
  stated once, never restated here.
- **Commit shapes** — the isolated commit a registration and a resolution each take:
  `dd-gitflow-default` — stated there, never restated here.
- **Redaction, classification and the CLI reference** for filing a new bug:
  `dd-bug-registration`.
- **The rest of Arm B** — branch, concurrency, the `resolved` write and its evidence
  triple: `dd-bug-resolution` (`dd-bug-fix` until its T-050-21 rename).

## Relationship to Sessions

There is no session-lock gate on filing a bug (NO-LOCKS DOCTRINE): `bugs append` never
blocks on session state. `reported_by` records the agent/runtime that registered the
record; concurrent sessions racing to file or resolve the same bug are surfaced, never
prevented — `dadaia bugs status`/`stats` read the ledger as it stands.
