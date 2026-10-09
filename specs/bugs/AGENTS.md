# specs/bugs/ — Bug Ledger Rules

Scope: this file governs only `specs/bugs/`.

- This directory holds the bug ledger: `BUGS.jsonl`, one JSON record per bug, appended once.
- No event stream, no fold. Schema: `bug-record-v1` (`.dadaia/agentic/schemas/bugs/bug-record-v1.schema.json`).
- The ledger's ONE writer and validator — `bugs.py` below — is `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py <verb> --specs <specs-dir>` — the worktree's `specs/` for a write (`dd-bug-registration` §3), `repos/<slug>/specs` for a read.

## 1. What a bug is

- A bug is a merged change that reproducibly breaks a documented contract — `--help`, the workspace law, a schema, a promised exit code.
- The agent proposes and the operator confirms (`dd-bug-registration` §2).
- `bugs.py append` runs only after that confirmation; with no operator, the proposal is a handoff finding whose `message` starts `bug-proposal:` — never a record.
- NOT a bug: a failure inside an unmerged worktree (rework), your own mistake, wrong usage, an environment limit, a designed validation (every `fix:` line), a law ambiguity, a missing feature.
- A law ambiguity goes to `dd-grill-me`; a missing feature goes to the backlog intake.
- Redact local paths, IPs, hostnames, private names and secrets from every field, and from every command, output and artifact of the arc.

## 2. Resolution

- The block list, closed: (1) the work branch's `verify:` line is red; (2) a Stall; (3) the running task cannot deliver its AC;
  (4) a security finding; (5) data loss or corruption.
- A block-list bug is a hotfix: a hotfix job (`worktrees/AGENTS.md` §3), landing before any
  other job merge; its fix body names `block: <item>`; no SPEC amendment.
- Every other confirmed bug becomes explicit candidate scope. Ship refuses an open bug unless
  the operator authorizes that exact id; the authorization is recorded verbatim and the bug remains open for the next candidate.
- Any fix whose `caused_by` is not `none`, a bug's fix or a feature task, is a REBUILD of the unit, keeping its tests.
- The next rc's `## Bug window review` judges those fixes (KEEP or REBUILD); its Job 1 executes the verdicts.
- Close with the fix: `bugs.py resolve`, with the flags `dd-bug-resolution` Phase 6 names.
- Check prior resolutions on the same component first using `dd-bug-resolution/LINEAGE.md`; inspect each persisted `fix_sha` with `git show`. `caused_by: X` means bug or task X wrote the lines this fix corrects; use `none` only when blame offers no candidate.
- Commit exactly what the fix touched, never a blanket `-A`; a net-positive diff is judged by `dd-code-review` §6's Architecture lens at review.

## 3. Field classes

- Each field's class is its `x-mutability` in `bug-record-v1`; this law lists no fields.
- `immutable-core`: never rewritten once appended.
- `write-once`: absent at registration; settable once, then immutable.
- `mutable-governance`: rewritten in place, atomic refuse-stale.

## 4. Authoring rules

- Register a new bug with `bugs.py append --bug-id <slug> --title ... --severity ...` and the remaining required flags.
- Every record change is one governance verb: `bugs.py append|update|resolve|supersede|reject|archive`.
- `status` and `closed_at` change only through the three terminal transitions (`resolve`, `supersede`, `reject`), never through `--set`.

## 5. Duties this ledger carries, and where each lives

- Diagnosing method, lineage first: `dd-bug-resolution` — window, cap, diff-trust rule, stated once there.
- Commit shapes for a registration and a resolution: `dd-gitflow-default`.
- CLI reference for filing: `dd-bug-registration`.
- The rest of Arm B (branch, concurrency, the `resolved` write): `dd-bug-resolution`.
