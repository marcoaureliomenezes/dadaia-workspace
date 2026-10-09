---
name: dd-bug-registration
description: >
  Propose a bug the operator confirms before it becomes a record: rule out each NOT-a-bug case of specs/bugs/AGENTS.md §1, name the contract line violated and one reproducing command,
  redact, then append. Use the moment a tool breaks a contract it documents.
---

# dd-bug-registration

> Any agent runs this; the propose/confirm rule lives in `specs/bugs/AGENTS.md` §1. Fixing a registered bug is dd-bug-resolution's.

## 1. When

- A tool broke a contract it documents — `--help`, the law, a schema, a promised exit
  code — and you can reproduce it.
- Before the turn ends.

## 2. Propose

1. Open `specs/bugs/AGENTS.md` (the area's scoped law) and follow it.
2. Name the contract line violated: file and line, `--help` text, or schema key.
3. Give ONE command that reproduces it, already run, with its exit code and output.
4. Name which `specs/bugs/AGENTS.md` §1 NOT-a-bug cases you ruled out and the work-branch sha that reproduces it, so the operator can confirm the tool is at fault.
5. Severity: CRITICAL a stall or data loss; HIGH a contract broken on the default
   path; MEDIUM off the default path or with a documented workaround; LOW a message
   or cosmetic defect.
6. A subagent returns the proposal as a `bug-proposal:` finding (the reviewer: in its verdict's `findings`); the main thread puts it to the operator.

## 3. Register — after the operator confirms

1. Append the record:

   ```bash
   python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append --specs <specs-dir> \
     --bug-id <slug> --reported-by <agent> --title "…" --severity LOW\|MEDIUM\|HIGH\|CRITICAL \
     --surface … --component … --context … --symptom … --repro … --expected … --correlates <ids>\|none
   ```
2. The surface is the name of a directory tracked in the repo.
3. In a job or `backlog/<slug>` worktree (`worktrees/AGENTS.md`), stage `BUGS.jsonl`; commit `chore(bugs): report <id>` — shape 1 of `dd-gitflow-default` §3a.
4. A bug belongs to the context whose tooling broke: its own `specs/bugs/`, plus an
   upstream report when the broken tool is someone else's.
5. Hand the fix to `dd-bug-resolution` once the record exists.

## 4. Done when

- Either `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status --specs <specs-dir>` lists the id and `bugs.py check --specs <specs-dir>` exits 0, its commit staging `BUGS.jsonl` — or one `bug-proposal:` finding is in the session's handoff and `git diff -- specs/bugs/BUGS.jsonl` is empty.

## 5. References

- `dd-handoff-emitter` — emitting the handoff; the `bug-proposal:` finding: `specs/bugs/AGENTS.md` §1.
- `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append --help` — the full flag list.
