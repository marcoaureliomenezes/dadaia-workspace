# specs/bugs/ — Bug Ledger Rules

Scope: this file governs only `specs/bugs/`.

- This directory holds the bug ledger: `BUGS.jsonl`, one JSON record per bug, appended once.
- No event stream, no fold. Schema: `bug-record-v1` (`schemas/bugs/bug-record-v1.schema.json`).
- There is no per-bug Markdown file and no session-lock gate on filing.
- The ledger's ONE writer and validator — `bugs.py` below — is `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py <verb> --specs specs`.

## 1. What a bug is

- A bug is a reproducible violation of a contract the tool documents — `--help`, the workspace law, a schema, a promised exit code.
- NOT a bug: your own mistake, wrong usage, an environment limit, a designed validation (including every `fix:` line), a law ambiguity, a missing feature.
- A law ambiguity goes to `dd-grill-me`; a missing feature goes to the backlog intake.
- The agent proposes and the operator confirms: name the contract line violated, one reproducing command already run, and why it is not agent error.
- `bugs.py append` runs only after that confirmation; with no operator, the proposal is a handoff finding whose `message` starts `bug-proposal:` — never a record.
- Redact local paths, IPs, hostnames, private names and secrets from every field, and from every command, output and artifact of the arc.

## 2. Resolution

- Close in the same session as the fix: `bugs.py resolve` carrying the red-loop command, the regression-test seam and the diff direction.
- Check prior resolutions on the same component first; declare `caused_by: <bug_id>|none`.
- Commit exactly what the fix touched, never a blanket `-A`; a net-positive diff passes the architecture lens first.

## 3. Field classes (D11)

| Class | Meaning |
|---|---|
| `immutable-core` | Never rewritten once appended |
| `write-once` | Absent at registration; settable once, then immutable |
| `mutable-governance` | Rewritten in place, atomic refuse-stale |

- `immutable-core` fields: `id`, `ts`, `title`, `severity`, `surface`, `component`, `symptom`, `repro`, `expected`.
- `write-once` fields: `solution`, `evidence_loop`, `evidence_seam`, `evidence_diff`, `diff_direction` (derived from `evidence_diff`'s `net-*:` prefix).
- `mutable-governance` fields: `status`, `closed_at`, `cause`, `caused_by`, `resolved_release`, `audited`.

## 4. Authoring rules

- Register a new bug with `bugs.py append --bug-id <slug> --title ... --severity ...` and the remaining required flags.
- Full command reference: `dd-bug-registration`.
- Never hand-edit `BUGS.jsonl` to keep every entry schema-valid.
- Every record change is one governance verb: `bugs.py append|update|resolve|supersede|defer|reject|archive`.
- That seam is atomic, refuse-stale, redacted, and refuses any `immutable-core` field or a differing re-set of a `write-once` field.
- `status` and `closed_at` change only through the four terminal transitions, never through `--set`; `bugs.py archive` ages by `closed_at`.
- `status` has no `picked` value — a pick is the bundled release-definition commit, never a ledger write.
- Bug reports are not specs — they do not authorize implementation changes on their own.
- Never hand-delete a record once appended — `bugs.py archive` is the only retiring path, and it is idempotent.

## 5. Duties this ledger carries, and where each lives

- Diagnosing method, lineage first: `dd-bug-resolution` — window, cap, diff-trust rule, stated once there.
- Commit shapes for a registration and a resolution: `dd-gitflow-default`.
- CLI reference for filing: `dd-bug-registration`.
- The rest of Arm B (branch, concurrency, the `resolved` write, evidence triple): `dd-bug-resolution`.

## 6. Relationship to sessions

- No session-lock gate on filing a bug (NO-LOCKS DOCTRINE) — `bugs.py append` never blocks on session state.
- `reported_by` records the agent/runtime that registered the record.
- Concurrent sessions racing to file or resolve the same bug are surfaced, never prevented.
- `bugs.py status`/`stats` read the ledger as it stands.
