---
name: dd-bug-fix
description: "Use when: executing Arm B end-to-end on an already-registered bug — reproduce, RED, root-cause fix, GREEN, resolved event, commit — on the live feature branch. The single procedural source of the bug-fix flow. Any agent may invoke it once a bug carries a reported event."
applyTo: "specs/bugs/**"
---

# dd-bug-fix — Arm B End-to-End

> **Not a hook-enforced mechanism.** No engine advances Arm B or reads bug state.
> Any agent runs this protocol directly once a bug is `reported`; the git chokepoints
> (`DADAIA.md` §3) are the only mechanical backstop.

## 1. When to invoke

The bug already carries a `reported` event — `dd-bug-registration`'s only output. This
skill never registers a bug and never classifies one; it starts from an already-open bug
and runs Arm B through to close.

The broader `specs/bugs/**` glob is deliberate: this skill owns the whole bug lifecycle
(including the `resolved` event on the same ledger file `dd-bug-registration` narrows
to). Declared subset, activation precedence: `declared_overlaps` in
`entities/rules-skills-map.json` (canonical home, FR9/D4).

## 2. Branch and concurrency

Run on the live `feature/{M.m.p}` branch — no separate branch, no ceremony. Branch
contract: `DADAIA.md` §4 Gitflow; operations: `dd-gitflow-default`.

**Concurrency (ADR #10/E-4 — advisory presence only).** Races are surfaced, never blocked
(NO-LOCKS DOCTRINE): the SDD gate's presence heartbeat only names a live session working
the same context. Announce intent with `dadaia bugs append --bug-id <slug> --event
picked` (v0.4.3, FR14) — a non-terminal annotation that appends your agent to the bug's
`picked_by` list without changing its status; it never blocks a concurrent picker, it
only makes the pick observable.

## 3. Reproduce on the executed path

Reproduce the failure exactly as it occurred — the real command, the real environment,
the real path. A failure you cannot reproduce on the executed path is not yet ready for
a RED test.

## 4. RED test

Write the test that fails for the real reason. Intent and size classification at birth:
`dadaia-test-stewardship` §A — referenced, not restated.

## 5. Root-cause fix

Fix the cause, not the symptom (`DADAIA.md` §7 (Quality) "Root cause, always" —
referenced, not restated). Workarounds and symptom patches are not acceptable outcomes.

## 6. GREEN + `resolved` event + evidence

Prove the fix green, then append `resolved` with `--resolution-evidence` (reproducing
test, fix, suite result). What counts as closing the loop — the staging discipline for
the commit that follows — is the law's close-in-same-session rule (`DADAIA.md` §7
(Quality)): consult it, do not restate it here.

## 7. No separate release ceremony

The bug fix lands on the live `feature/{M.m.p}` branch with the rest of the release —
no separate SPEC, PLAN, TASKS, or `specs/releases/<id>/` directory, and no standalone
version mint for the bug alone (that ceremony belonged to the now-retired `hotfix/*`
path; branch contract: `DADAIA.md` §4 Gitflow; operations: `dd-gitflow-default`). The
bug ledger's `resolved` event is the durable record.

## 8. Checklist

- [ ] Bug carries a `reported` event before this skill starts.
- [ ] Branch is the live `feature/{M.m.p}` — no separate branch.
- [ ] Failure reproduced on the executed path.
- [ ] RED test written, intent/size declared (`dadaia-test-stewardship` §A).
- [ ] Root cause fixed — no workaround, no symptom patch.
- [ ] GREEN proven; `resolved` event appended with evidence; committed same session.
- [ ] No separate release ceremony opened for the bug; `resolved` event is the record.
