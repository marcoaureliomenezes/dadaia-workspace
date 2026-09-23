---
name: dd-bug-registration
description: >
  Propose a bug the operator confirms before it becomes a record: classify against the
  not-a-bug rubric, name the contract line violated and one reproducing command,
  redact, then append. Use the moment a tool breaks a contract it documents.
---

# dd-bug-registration

> The agent proposes; the operator confirms. `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append` runs after that
> confirmation, never on the agent's own judgement. Any agent runs this.

## 1. When

- A tool broke a contract it documents — `--help`, the law, a schema, a promised exit
  code — and you can reproduce it.
- Before the turn ends.

## 2. Propose

- What is and is not a bug, the propose/confirm rule and the redaction rule: `specs/bugs/AGENTS.md`.

1. Open `specs/bugs/AGENTS.md` (the area's scoped law) and follow it.
2. Name the contract line violated: file and line, `--help` text, or schema key.
3. Give ONE command that reproduces it, already run, with its exit code and output.
4. State why it is not agent error — which not-a-bug arm you ruled out and how.
5. Severity: CRITICAL a stall or data loss; HIGH a contract broken on the default
   path; MEDIUM off the default path or with a documented workaround; LOW a message
   or cosmetic defect.
6. Put the proposal to the operator and wait.
7. No operator in the session: emit it as one handoff finding whose `message` starts
   `bug-proposal:` and whose `fix_recommendation` is the exact `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append`
   line (`dd-handoff-emitter`). A proposal is never a record.

## 3. Register — after the operator confirms

1. `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append --bug-id <slug> --reported-by <agent> --title "…"
   --severity LOW|MEDIUM|HIGH|CRITICAL --surface … --component … --context …
   --symptom … --repro … --expected …`
2. `--surface unknown` is refused; name the real surface.
3. Stage `BUGS.jsonl` alone; commit `chore(bugs): report <id>` — shape 1 of
   `dd-gitflow-default` §3a.
4. A bug belongs to the context whose tooling broke: its own `specs/bugs/`, plus an
   upstream report when the broken tool is someone else's.
5. Hand the fix to `dd-bug-resolution` once the record exists.

## 4. Done when

- Either one confirmed `BUGS.jsonl` record exists, `status: "open"`, fully redacted,
  its commit staging `BUGS.jsonl` alone — or one `bug-proposal:` finding left the
  session and no record was written.

## 5. References

- `dd-bug-resolution` — the diagnosing method and the fix, once a record exists.
- `dd-handoff-emitter` — the `bug-proposal:` finding shape.
- `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py append --help` — the full flag list.
