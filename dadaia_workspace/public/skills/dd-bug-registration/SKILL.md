---
name: dd-bug-registration
description: "Use when: registering a genuine product bug you hit while operating this tooling — classify-first, redact, append the `reported` event. The opening move of Arm B only, never the fix (that's `dd-bug-fix`). Any agent may invoke it."
applyTo: "specs/bugs/*.jsonl"
---

# dd-bug-registration

> **Not a hook-enforced mechanism.** ADDITIVE paths (`specs/bugs/**`) are always
> writable, in any mode — this is discipline, not gate enforcement. Any agent runs this
> protocol; it is not owned by one role.

The narrower glob names the exact write target — the `reported` event append. It is a
declared subset of `dd-bug-fix`'s broader `specs/bugs/**` (activation precedence:
`dd-backlog-definition` §7, canonical home).

## 1. When to invoke

Any agent, the moment a tool breaks its own contract while operating this tooling —
projection, doctor, upgrade, scaffolding, hooks, the gate, presence, context, panel,
reports, or the CLI itself. Append the `reported` event before the turn ends — the
ADDITIVE path class (`DADAIA.md` §3) never blocks this write, so nothing is gained by
waiting.

## 2. Classify-first decision table

| Symptom | Product bug? | Action |
|---|---|---|
| The tool violates a contract it already promises | Yes | Register (§4) |
| Environment limits (quota/rate limits, network, sandbox) | No | Diagnose, do not register |
| Invalid input / wrong usage | No | Fix the call, do not register |
| A validation the tool is designed to emit | No | Not a bug — the tool is working |

Classify **before** registering anything — diagnose first, register with evidence
second.

## 3. Redaction rule

Absolute local paths, IPs, hostnames, private names and secrets never enter an event
field — redact before writing. Every `--notes`/`--symptom`/`--repro` value is sanitized
text, never a raw log dump.

## 4. `dadaia bugs append` command reference

```bash
dadaia bugs append --bug-id <slug> --event reported --reported-by <agent> \
  --title "…" --severity LOW|MEDIUM|HIGH|CRITICAL --surface "…" --component "…" \
  --context <ctx> --tag <tag> --symptom "…" --repro "…" --expected "…" --notes "… (redacted)"
```

## 5. Context routing (self-hosting vs consumer)

In this self-hosting workspace, bugs go to `repos/dadaia-workspace/specs/bugs/`. In a
consumer workspace, bugs go to the active context's `specs/bugs/` plus an upstream
report.

## 6. Handoff to `dd-bug-fix` (non-goal, stated explicitly)

This skill's only output is the `reported` event. It never reproduces the failure,
never writes a RED test, never fixes the cause — that is entirely `dd-bug-fix`'s job,
picked up once a bug carries a `reported` event: reproduce on the executed path → RED →
root-cause fix → GREEN → `resolved` event → commit, on `hotfix/{M.m.p}`.

## 7. CLI reference

```bash
dadaia bugs status        # open bugs
dadaia bugs stats         # bug-ledger aggregate view
```
