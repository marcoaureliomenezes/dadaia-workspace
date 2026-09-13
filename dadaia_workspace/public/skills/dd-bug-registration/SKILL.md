---
name: dd-bug-registration
description: >
  Propose a bug the operator confirms before it becomes a record: classify against the
  not-a-bug rubric, name the contract line violated and one reproducing command,
  redact, then append. Use the moment a tool breaks a contract it documents.
---

# dd-bug-registration

> The agent proposes; the operator confirms. `dadaia bugs append` runs after that
> confirmation, never on the agent's own judgement. Any agent runs this.

## 1. When

- A tool broke a contract it documents — `--help`, the law, a schema, a promised exit
  code — and you can reproduce it.
- Before the turn ends.

## 2. Classify — what is NOT a bug

- Your own mistake: a wrong command, a wrong path, a wrong assumption.
- Wrong usage: a documented flag used for something it never promised.
- An environment limit: no network, no store, missing binary, permissions, disk.
- A designed validation: a refusal the tool documents, including every `fix:` line.
- A law ambiguity: two rules readable two ways — `dd-grill-me`, not a bug.
- A missing feature: behavior never promised — the operator-gated backlog intake
  (`dd-backlog-definition`), not a bug.

## 3. Propose

1. Name the contract line violated: file and line, `--help` text, or schema key.
2. Give ONE command that reproduces it, already run, with its exit code and output.
3. State why it is not agent error — which of §2's six arms you ruled out and how.
4. Severity: CRITICAL a stall or data loss; HIGH a contract broken on the default
   path; MEDIUM off the default path or with a documented workaround; LOW a message
   or cosmetic defect.
5. Redact every field — no absolute local path, IP, hostname, private name, secret.
6. Put the proposal to the operator and wait.
7. No operator in the session: emit it as one handoff finding whose `message` starts
   `bug-proposal:` and whose `fix_recommendation` is the exact `dadaia bugs append`
   line (`dd-handoff-emitter`). A proposal is never a record.

## 4. Register — after the operator confirms

1. `dadaia bugs append --bug-id <slug> --reported-by <agent> --title "…"
   --severity LOW|MEDIUM|HIGH|CRITICAL --surface … --component … --context …
   --symptom … --repro … --expected …`
2. `--surface unknown` is refused; name the real surface.
3. Stage `BUGS.jsonl` alone; commit `chore(bugs): report <id>` — shape 1 of
   `dd-gitflow-default` §3a.
4. A bug belongs to the context whose tooling broke: its own `specs/bugs/`, plus an
   upstream report when the broken tool is someone else's.
5. Hand the fix to `dd-bug-resolution` once the record exists.

## 5. Done when

- Either one confirmed `BUGS.jsonl` record exists, `status: "open"`, fully redacted,
  its commit staging `BUGS.jsonl` alone — or one `bug-proposal:` finding left the
  session and no record was written.

## 6. References

- `dd-bug-resolution` — the diagnosing method and the fix, once a record exists.
- `dd-handoff-emitter` — the `bug-proposal:` finding shape.
- `dadaia bugs append --help` — the full flag list.
