---
name: dd-bug-registration
description: >
  Register a genuine product bug hit while operating this tooling: classify first,
  redact, append the one-record-per-bug entry. Use the moment a tool violates a
  contract it promises — before the turn ends; the fix itself is dd-bug-resolution.
---

# dd-bug-registration

> ADDITIVE paths (`specs/bugs/**`) are always writable, in any mode — registration is
> never blocked and never waits. Any agent runs this.

## 1. When

- Any agent, the moment a tool violates a contract it already promises — projection,
  doctor, upgrade, scaffolding, hooks, the gate, presence, context, panel, reports,
  CLI.
- Before the turn ends.

## 2. Steps

1. Classify first: does the symptom violate a promised contract? Environment limits,
   invalid input, wrong usage and a designed validation are not bugs — stop here for
   those.
2. Redact every field — no absolute local path, IP, hostname, private name, or
   secret.
3. Register:
   `dadaia bugs append --bug-id <slug> --reported-by <agent> --title "…"
   --severity LOW|MEDIUM|HIGH|CRITICAL --surface … --component … --context …
   --symptom … --repro … --expected …`
4. Stage `BUGS.jsonl` alone; commit `chore(bugs): report <id>` — shape 1 of
   `dd-gitflow-default` §3a.
5. Route this workspace's own bugs to `repos/dadaia-workspace/specs/bugs/`; a
   consumer workspace's bugs go to its active context's `specs/bugs/` plus an
   upstream report.
6. Hand the fix to `dd-bug-resolution` once the record exists.

## 3. Done when

- One `BUGS.jsonl` record exists, `status: "open"`, fully redacted.
- The registration commit stages `BUGS.jsonl` alone.

## 4. References

- `dd-bug-resolution` — the diagnosing method and the fix, once a record exists.
- `dd-gitflow-default` §3a — the isolated-commit shape.
- `dadaia bugs append --help` — the full flag list.
