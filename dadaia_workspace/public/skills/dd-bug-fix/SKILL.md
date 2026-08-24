---
name: dd-bug-fix
description: "Use when: executing Arm B end-to-end on an already-registered bug — red loop, minimise, hypotheses, instrument, seam test, cleanup, resolved event, commit — on the live feature branch. The single procedural source of the bug-fix flow, granted to `software-engineer` and `ai-engineer` once a bug carries a `reported` event."
applyTo: "specs/bugs/**"
---

# dd-bug-fix — Arm B End-to-End

> **Not a hook-enforced mechanism.** No engine advances Arm B or reads bug state.
> `software-engineer` and `ai-engineer` run this protocol directly once a bug is
> `reported`; the git chokepoints (`DADAIA.md` §3) are the only mechanical backstop.

## 1. When to invoke

The bug already carries a `reported` event — `dd-bug-registration`'s only output; this
skill never registers or classifies one, it runs Arm B through on an already-open bug.
The broader `specs/bugs/**` glob is deliberate: this skill owns the whole lifecycle,
including `resolved` on the same ledger `dd-bug-registration` narrows to — declared
subset, `declared_overlaps` in `entities/rules-skills-map.json` (FR9/D4).

## 2. Branch and concurrency

Run on the live `feature/{M.m.p}` branch — no separate branch, no ceremony. Branch
contract: `DADAIA.md` §4 Gitflow; operations: `dd-gitflow-default`.

**Concurrency (ADR #10/E-4 — advisory presence only).** Races are surfaced, never
blocked (NO-LOCKS DOCTRINE). Announce intent with `dadaia bugs append --bug-id <slug>
--event picked` (v0.4.3, FR14) — appends your agent to `picked_by` without changing
status; it never blocks a concurrent picker, it only makes the pick observable.

## 3. The six-phase method

1. **Red loop before any hypothesis.** Reproduce the failure exactly as it occurred —
   real command, real environment, real path. *Done when:* the command and its red
   output are captured.
2. **Minimise until load-bearing.** Shrink the reproduction until every remaining
   element is necessary. *Done when:* removing any element makes it stop failing.
3. **3–5 falsifiable hypotheses.** Write them before touching code, each paired with
   the observation that would kill it. *Done when:* every hypothesis is killed by an
   observation or is the last one standing.
4. **Instrument, never read code for a theory.** Add probes/logs/asserts on the
   executed path that discriminate between the surviving hypotheses. *Done when:* the
   surviving hypothesis is confirmed by an observation, not by inference.
5. **Regression test at the correct seam.** Intent/size declared at birth:
   `dadaia-test-stewardship` §A. **No correct seam exists → register an architecture
   finding and dispatch `software-architect` before fixing** — the absence of a seam is
   itself the finding. *Done when:* the test fails at HEAD, passes after the fix.
6. **Cleanup.** Remove every probe from phase 4; the diff must leave the touched
   feature smaller or equal, never bigger (`DADAIA.md` §7 (Quality) "Root cause,
   always"). *Done when:* instrumentation is gone, worktree clean and GREEN.

## 4. GREEN, `resolved` event, commit

Append `resolved` carrying three independently-checked fields (FR23): `--evidence-loop`
(phase 1's red-loop command), `--evidence-seam` (phase 5's regression-test seam), and
`--evidence-diff` (phase 6's diff direction, prefixed `net-negative:`/`net-positive:`/
`net-neutral:` — `net-positive:` routes to `software-architect` before the commit).
Closing the loop — the staging discipline for the commit that follows — is the law's
close-in-same-session rule (`DADAIA.md` §7 (Quality)): consult it, do not restate it.

## 5. No separate release ceremony

The bug fix lands on the live `feature/{M.m.p}` branch with the rest of the release —
no separate SPEC/PLAN/TASKS, no `specs/releases/<id>/`, no standalone version mint
(retired `hotfix/*` path; `DADAIA.md` §4 Gitflow / `dd-gitflow-default`). The `resolved`
event is the durable record.

## 6. Checklist

- [ ] Bug carries a `reported` event; branch is the live `feature/{M.m.p}`.
- [ ] Red loop captured before any hypothesis; repro minimised to load-bearing.
- [ ] 3–5 falsifiable hypotheses written before touching code.
- [ ] Surviving hypothesis confirmed by instrumentation, not by reading code.
- [ ] Test lands at the correct seam, or an architecture finding is registered and
      `software-architect` dispatched first.
- [ ] Cleanup done (probes gone, diff smaller or equal); GREEN; `resolved` event
      carries evidence, committed same session; no separate ceremony opened.
