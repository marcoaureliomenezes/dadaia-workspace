# specs/bugs/ — Bug Ledger Rules

Scope: this file governs only `specs/bugs/`.

- This directory holds the bug ledger: `BUGS.jsonl`, one JSON record per bug, appended once.
- No event stream, no fold. Schema: `bug-record-v1` (`schemas/bugs/bug-record-v1.schema.json`).
- There is no per-bug Markdown file and no session-lock gate on filing.

## 1. Field classes (D11)

| Class | Meaning |
|---|---|
| `immutable-core` | Never rewritten once appended |
| `write-once` | Absent at registration; settable once, then immutable |
| `mutable-governance` | Rewritten in place, atomic refuse-stale |

- `immutable-core` fields: `id`, `ts`, `title`, `severity`, `surface`, `component`, `symptom`, `repro`, `expected`.
- `write-once` fields: `root_cause`, `solution`, `evidence_loop`, `evidence_seam`, `evidence_diff`, `diff_direction` (derived from `evidence_diff`'s `net-*:` prefix).
- `mutable-governance` fields: `status`, `closed_at`, `cause`, `caused_by`, `resolved_release`, `audited`.

## 2. Authoring rules

- Register a new bug with `dadaia bugs append --bug-id <slug> --title ... --severity ...` and the remaining required flags.
- Full command reference: `dd-bug-registration`.
- Never hand-edit `BUGS.jsonl` to keep every entry schema-valid.
- Every record change is one governance verb: `dadaia bugs append|update|resolve|supersede|defer|reject|archive`; a hand edit surfaces as `LEDGER-BUGS-HANDEDIT`.
- That seam is atomic, refuse-stale, redacted, and refuses any `immutable-core` field or a differing re-set of a `write-once` field.
- `status` and `closed_at` change only through the four terminal transitions, never through `--set`; `dadaia bugs archive` ages by `closed_at`.
- `status` has no `picked` value — a pick is the bundled release-definition commit, never a ledger write.
- Bug reports are not specs — they do not authorize implementation changes on their own.
- Never hand-delete a record once appended — `dadaia bugs archive` is the only retiring path, and it is idempotent.

## 3. Duties this ledger carries, and where each lives

- Diagnosing method, lineage first: `dd-bug-resolution` — window, cap, diff-trust rule, stated once there.
- Commit shapes for a registration and a resolution: `dd-gitflow-default`.
- Redaction, classification, CLI reference for filing: `dd-bug-registration`.
- The rest of Arm B (branch, concurrency, the `resolved` write, evidence triple): `dd-bug-resolution`.

## 4. Relationship to sessions

- No session-lock gate on filing a bug (NO-LOCKS DOCTRINE) — `bugs append` never blocks on session state.
- `reported_by` records the agent/runtime that registered the record.
- Concurrent sessions racing to file or resolve the same bug are surfaced, never prevented.
- `dadaia bugs status`/`stats` read the ledger as it stands.
