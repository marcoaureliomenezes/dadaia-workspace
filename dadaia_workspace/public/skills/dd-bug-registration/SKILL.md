---
name: dd-bug-registration
description: "Use when: registering a genuine product bug you hit while operating this tooling — classify-first, redact, append the `reported` event. The opening move of Arm B only; the fix itself belongs to `dd-bug-fix`. Any agent may invoke it."
applyTo: "specs/bugs/*.jsonl"
---

# dd-bug-registration

> **Not a hook-enforced mechanism.** ADDITIVE paths (`specs/bugs/**`) are always
> writable, in any mode — this is discipline, not gate enforcement. Any agent runs this
> protocol; it is not owned by one role.

The narrower glob names the exact write target — the `reported` event append. It is a
declared subset of `dd-bug-fix`'s broader `specs/bugs/**` (activation precedence:
`declared_overlaps` in `entities/rules-skills-map.json`, canonical home, FR9/D4).

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

Absolute local paths, IPs, hostnames, private names and secrets never enter a record
field — redact before writing. Every `--symptom`/`--repro`/`--expected` value is
sanitized text, never a raw log dump.

## 4. `dadaia bugs append` command reference

Verified against `dadaia bugs append --help` — no `--event` flag exists (v0.5.0 FR2:
one record per bug, appended once, never an event stream). This append's isolated-commit
shape (staging only `BUGS.jsonl`) is stated once in `dd-gitflow-default` §3a shape 1 —
not restated here.

```bash
dadaia bugs append --bug-id <slug> --reported-by <agent> \
  --title "…" --severity LOW|MEDIUM|HIGH|CRITICAL --surface "…" --component "…" \
  --context <ctx> --symptom "… (redacted)" --repro "… (redacted)" --expected "… (redacted)"
```

## 5. Review-verdict bug-surface axis (FR24)

A reviewer's `APPROVE`/`REQUEST_CHANGES` (or REJECT) verdict also states whether the
change reduced or increased the bug surface of the touched feature, with evidence from
`specs/bugs/*.jsonl` (`dadaia bugs stats`). A verdict without this axis is incomplete —
tests green is insufficient on its own; check the bug surface separately.

## 6. Context routing (self-hosting vs consumer)

In this self-hosting workspace, bugs go to `repos/dadaia-workspace/specs/bugs/`. In a
consumer workspace, bugs go to the active context's `specs/bugs/` plus an upstream
report.

This skill's only output is the `reported` event — never the fix. Hand-off to the fix:
`dd-bug-fix` (picked up once a bug carries `reported`). Further CLI reference:
`dadaia bugs append --help` / `dd-cli-library`.
