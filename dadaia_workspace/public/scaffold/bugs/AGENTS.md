# specs/bugs/ — Bug Ledger Rules

Scope: this file governs only `specs/bugs/`.

- This directory holds the bug ledger: `BUGS.jsonl`, one JSON record per bug, appended once.
- No event stream, no fold. Schema: `bug-record-v1` (`schemas/bugs/bug-record-v1.schema.json`).
- The ledger's ONE writer and validator — `bugs.py` below — is `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py <verb> --specs repos/<context>/specs` from the workspace root.
- `bugs.py` never creates a specs tree: a `--specs` that does not exist refuses, and its `fix:` names the bound context's tree.

## 1. What a bug is

- A bug is a merged change that reproducibly breaks a documented contract — `--help`, the workspace law, a schema, a promised exit code.
- NOT a bug: a failure inside an unmerged worktree (rework), your own mistake, wrong usage, an environment limit, a designed validation (every `fix:` line), a law ambiguity, a missing feature.
- A law ambiguity goes to `dd-grill-me`; a missing feature goes to the backlog intake.
- The agent proposes and the operator confirms: name the contract line violated, one reproducing command already run, and why it is not agent error.
- `bugs.py append` runs only after that confirmation; with no operator, the proposal is a handoff finding whose `message` starts `bug-proposal:` — never a record.
- Redact local paths, IPs, hostnames, private names and secrets from every field, and from every command, output and artifact of the arc.

## 2. Resolution

- The block list, closed: (1) the work branch's CI is red; (2) a Stall; (3) the running task cannot deliver its AC;
  (4) a security finding or an open dependency-vulnerability alert; (5) data loss or corruption.
- A block-list bug is a hotfix: registered with `caused_by`, its own job, job gate and one review, landing before any
  other job merge; its fix body names `block: <item>`; no SPEC amendment.
- Every other bug is only registered, `found_in` its rc; the next rc's `## Bug window review` reads it and its Job 1 resolves it, a
  fix-induced one as a REBUILD.
- Close with the fix: `bugs.py resolve`, with the flags `dd-bug-resolution` Phase 6 names.
- Check prior resolutions on the same component first; `caused_by: X` means the fix of X wrote the lines this fix corrects, picked from `bugs.py resolve`'s blame candidates, `none` only when there are none or with `--lineage-reason`.
- Commit exactly what the fix touched, never a blanket `-A`; a net-positive diff passes the architecture lens first.

## 3. Field classes (D11)

- Each field's class is its `x-mutability` in `bug-record-v1`; this law lists no fields.
- `immutable-core`: never rewritten once appended.
- `write-once`: absent at registration; settable once, then immutable.
- `mutable-governance`: rewritten in place, atomic refuse-stale.

## 4. Authoring rules

- Register a new bug with `bugs.py append --bug-id <slug> --title ... --severity ...` and the remaining required flags.
- Never hand-edit `BUGS.jsonl` to keep every entry schema-valid.
- Every record change is one governance verb: `bugs.py append|update|resolve|supersede|defer|reject|archive`.
- That seam is atomic, refuse-stale, refuses a value the push would refuse, and refuses any `immutable-core` field or a differing re-set of a `write-once` field.
- `status` and `closed_at` change only through the four terminal transitions, never through `--set`.
- Never hand-delete a record — `bugs.py archive --adr <id>`, naming an accepted ADR, is the only retiring path.

## 5. Duties this ledger carries, and where each lives

- Diagnosing method, lineage first: `dd-bug-resolution` — window, cap, diff-trust rule, stated once there.
- Commit shapes for a registration and a resolution: `dd-gitflow-default`.
- CLI reference for filing: `dd-bug-registration`.
- The rest of Arm B (branch, concurrency, the `resolved` write): `dd-bug-resolution`.

## 6. Relationship to sessions

- No session-lock gate on filing a bug (NO-LOCKS DOCTRINE) — `bugs.py append` never blocks on session state.
- `reported_by` records the agent/runtime that registered the record.
- Concurrent sessions racing to file or resolve the same bug are surfaced, never prevented.
- `bugs.py status`/`stats` read the ledger as it stands.
