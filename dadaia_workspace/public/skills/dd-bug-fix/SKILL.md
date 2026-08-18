---
name: dd-bug-fix
description: "Use when: executing Arm B end-to-end on an already-registered bug — reproduce, RED, root-cause fix, GREEN, resolved event, commit, PATCH mint — on hotfix/{M.m.p}. The single procedural source of the hotfix flow. Any agent may invoke it once a bug carries a reported event."
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
to). Declared subset, activation precedence: `dd-backlog-definition` §7 (canonical home).

## 2. Branch and concurrency

Run on `hotfix/{M.m.p}` at the next PATCH, cut from `develop` — full stage-contract row:
`dadaia-gitflow` (`bug-fix/hotfix`), referenced here, not restated.

**Concurrency (ADR #10/E-4 — advisory presence only).** No reservation marker exists for
bugs. Races are surfaced, never blocked (NO-LOCKS DOCTRINE): the SDD gate's presence
heartbeat only names a live session working the same context. The reservation primitive
is still being designed: `specs/backlog/bug-picked-ledger-event.md`. Invent no marker,
no lock, no lease here.

## 3. Reproduce on the executed path

Reproduce the failure exactly as it occurred — the real command, the real environment,
the real path. A failure you cannot reproduce on the executed path is not yet ready for
a RED test.

## 4. RED test

Write the test that fails for the real reason. Intent and size classification at birth:
`dadaia-test-stewardship` §A — referenced, not restated.

## 5. Root-cause fix

Fix the cause, not the symptom (`DADAIA.md` §6 "Root cause, always" — referenced, not
restated). Workarounds and symptom patches are not acceptable outcomes.

## 6. GREEN + `resolved` event + evidence

Prove the fix green, then append `resolved` with `--resolution-evidence` (reproducing
test, fix, suite result). What counts as closing the loop — the staging discipline for
the commit that follows — is the law's close-in-same-session rule (`DADAIA.md` §6):
consult it, do not restate it here.

## 7. PATCH mint + `CHANGELOG.md`, same commit, merge to `develop`

At merge into `develop`, in the **same commit**: bump `pyproject.toml`'s version to the
minted PATCH, and add the `CHANGELOG.md` entry. **No release ceremony** — no SPEC, no
PLAN, no TASKS, no `specs/releases/<id>/` directory. The bug ledger plus the
`CHANGELOG.md` entry are the record.

## 8. Checklist

- [ ] Bug carries a `reported` event before this skill starts.
- [ ] Branch is `hotfix/{M.m.p}` at the next PATCH, cut from `develop`.
- [ ] Failure reproduced on the executed path.
- [ ] RED test written, intent/size declared (`dadaia-test-stewardship` §A).
- [ ] Root cause fixed — no workaround, no symptom patch.
- [ ] GREEN proven; `resolved` event appended with evidence; committed same session.
- [ ] `pyproject.toml` PATCH bump + `CHANGELOG.md` entry, same commit, merged to `develop`.
