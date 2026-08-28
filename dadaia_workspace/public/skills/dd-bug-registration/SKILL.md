---
name: dd-bug-registration
description: >
  Use when: registering a genuine product bug you hit while operating this tooling —
  classify-first, redact, append the one-record-per-bug entry (`status: open`). The
  opening move of Arm B only; the fix itself belongs to `dd-bug-resolution`. Any agent
  may invoke it.
tldr: "Classify first, redact, then `dadaia bugs append` — one record, no `--event`. Fix belongs to dd-bug-resolution."
applyTo: "specs/bugs/*.jsonl"
---

# dd-bug-registration

> ADDITIVE paths (`specs/bugs/**`) are always writable, in any mode — discipline, not gate enforcement. Any agent runs this; not owned by one role.

## 1. When

- Any agent, the moment a tool violates a contract it already promises.
- Covers: projection, doctor, upgrade, scaffolding, hooks, the gate, presence, context, panel, reports, CLI.
- Before the turn ends — ADDITIVE writes never block, so nothing is gained by waiting.

## 2. Steps

1. Classify first: does the symptom violate a contract the tool already promises?
2. Register (step 3) only if yes; environment limits, invalid input, or a designed validation are not bugs.
3. Redact every field — never write an absolute local path, IP, hostname, private name, or secret.
4. Run `dadaia bugs append --bug-id <slug> --reported-by <agent> --title "…" --severity LOW|MEDIUM|HIGH|CRITICAL …`.
5. Include `--surface`, `--component`, `--context`, `--symptom`, `--repro`, `--expected` in that call.
6. Never pass `--event` — no such flag exists.
7. Stage `BUGS.jsonl` alone; commit `chore(bugs): report <id>` — shape 1 of `dd-gitflow-default` §3a.
8. Route this workspace's own bugs to `repos/dadaia-workspace/specs/bugs/`.
9. Route a consumer workspace's bugs to its active context's `specs/bugs/` plus an upstream report.
10. Hand off the fix to `dd-bug-resolution` once the record exists — never fix the bug from this skill.

## 3. Done when

- One `BUGS.jsonl` record exists, `status: "open"`, fully redacted.
- The registration commit stages `BUGS.jsonl` alone.
- Every reviewer verdict on this feature also states the bug-surface delta (FR24), evidenced by `dadaia bugs stats`.

## 4. References

- `dd-bug-resolution` — the fix, once a record exists.
- `dd-gitflow-default` §3a shape 1 — the isolated-commit shape.
- `entities/behavior-map.json` `declared_overlaps` — precedence vs `dd-bug-resolution`'s broader glob.
- `dadaia bugs append --help` / `dd-cli-library` — full CLI reference.
