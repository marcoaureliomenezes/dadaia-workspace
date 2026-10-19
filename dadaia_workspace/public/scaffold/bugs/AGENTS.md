# specs/bugs/ — Bug Ledger Rules

Scope: this file governs only `specs/bugs/`.

- This directory holds the bug ledger: `BUGS.jsonl`, one JSON record per bug, appended once.
- Schema: `bug-record-v1` (`.agents/skills/dd-bug-resolution/scripts/schemas/bug-record-v1.schema.json`).
- The ledger's ONE writer and validator — `bugs.py` below — is `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py <verb> --specs <specs-dir>` — the worktree's `specs/` for a write (`dd-bug-registration` §3), `repos/<slug>/specs` for a read.

## 1. What a bug is

- A bug is a merged change that reproducibly breaks a documented contract — `--help`, the workspace law, a schema, a promised exit code.
- The agent proposes and the operator confirms (`dd-bug-registration` §2).
- `bugs.py append` runs only after that confirmation; with no operator, the proposal is a handoff finding whose `message` starts `bug-proposal:` — never a record.
- NOT a bug: a failure inside an unmerged worktree (rework), your own mistake, wrong usage, an environment limit, a designed validation whose `fix:` line runs, a law ambiguity, a missing feature.
- A law ambiguity goes to `dd-grill-me`; a missing feature goes to the backlog intake.
- Redact local paths, IPs, hostnames, private names and secrets from every field, and from every command, output and artifact of the arc.

## 2. Resolution

- The block list, closed: (1) the work branch's `verify:` line is red; (2) a Stall; (3) the running task cannot deliver its AC;
  (4) a security finding; (5) data loss or corruption.
- Any confirmed bug in code the work branch holds takes a `<v>/wt-hotfix-<bug-id>` lane (`worktrees/AGENTS.md` §1–2), in any phase, landing before any other merge, then `worktree sync`.
- After `release.py phase CLOSURE`, a fix to code that exists only on the `wt-rc` lands in that rc only for a block-list bug; any other confirmed bug there, REBUILD or operator demand is a job of the next rc, which opens at once. A block-list bug in that code takes the `wt-rc`: its registration, `test(` commit, fix, `bugs.py update` and `resolve` are commits there, under its merge's `verify:` and `APPROVED` verdict; its `test(` and fix commits name `block: <item>`, the only path that requires it; no SPEC amendment.
- Every other confirmed bug becomes explicit candidate scope. Ship refuses an open bug unless
  the operator authorizes that exact id; the authorization is recorded verbatim and the bug remains open for the next candidate.
- Any fix whose `caused_by` is not `none`, a bug's fix or a feature task, is a REBUILD of the unit, keeping its tests.
- The next rc's `## Bug window review` judges those fixes (KEEP or REBUILD); its Job 1 executes the verdicts.
- Close with the fix: `bugs.py resolve`, with the flags `dd-bug-resolution` Phase 6 names; a record's fix is the newest commit HEAD reaches whose message holds a line `fix(bugs): <id> — …` (a group lists its ids) or `refactor(bugs): <id> — …`, and `fix_sha` is its write-once hint.
- Lineage before any fix: `dd-bug-resolution/LINEAGE.md`.
- Commit exactly what the fix touched, never a blanket `-A`; a net-positive diff is judged by `dd-code-review` §6's Architecture lens at review.

## 3. Field classes

- Each field's class is its `x-mutability` in `bug-record-v1`; this law lists no fields.
- `immutable-core`: never rewritten once appended.
- `write-once`: settable once at closure, then immutable.
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
