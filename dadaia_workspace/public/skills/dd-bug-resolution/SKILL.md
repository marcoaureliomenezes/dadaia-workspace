---
name: dd-bug-resolution
description: "Use when: closing out Arm B on an already-registered bug — branch, concurrency, the `resolved` record write, commit, no separate ceremony. The diagnosing method itself (lineage, red loop, hypotheses, instrument, seam test, cleanup) is `dd-diagnose`, called from here. Granted to `software-engineer` and `ai-engineer` once a bug carries a record in `BUGS.jsonl`. Renamed from `dd-bug-fix` at v0.5.0 T-050-21 (FR12) — the diagnosing phases moved out to `dd-diagnose` (FR7); this skill keeps only the bug-lifecycle rump."
applyTo: "specs/bugs/**"
---

# dd-bug-resolution — Arm B, the Lifecycle Rump

> **Not a hook-enforced mechanism.** No engine advances Arm B or reads bug state.
> `software-engineer` and `ai-engineer` run this protocol directly once a bug carries a
> record; the git chokepoints (`DADAIA.md` §3) are the only mechanical backstop.

## 1. When to invoke

A record for this bug already exists in `specs/bugs/BUGS.jsonl` (`status: "open"`) —
`dd-bug-registration`'s only output; this skill never registers or classifies one, it
runs Arm B through on an already-open record. The broader `specs/bugs/**` glob is
deliberate: this skill owns the whole lifecycle, including the `resolved` write on the
same ledger `dd-bug-registration` narrows to — declared subset, `declared_overlaps` in
`entities/behavior-map.json` (canonical home, FR9/FR10/D4 — this map retired
`rules-skills-map.json` at T-050-19).

**The diagnosing method is not here.** Phase 0 (lineage) and phases 1–6 (red loop
through cleanup) are `dd-diagnose`'s — call it now, before reading further in this
skill. Return here only for the branch/concurrency setup (§2) and the closing write
(§4–§6).

## 2. Branch and concurrency

Run on the live `feature/{M.m.p}` branch — no separate branch, no ceremony. Branch
contract: `DADAIA.md` §4 Gitflow; operations: `dd-gitflow-default`.

**Concurrency (NO-LOCKS DOCTRINE, D15/AS-16).** Races are surfaced, never blocked. There
is no announce-intent write and no `picked` status (v0.5.0 FR2 dropped both — a record
is `open` or terminal, nothing in between). Two fixers racing the same bug are resolved
by whoever's `dadaia bugs update <id> --set status=resolved …` (§4) lands first through
the one governance-write seam (AS-16): atomic, refuse-stale. A losing racer's write
fails non-zero, naming the re-read-and-retry remedy — never a block on a human.

## 3. GREEN, then the `resolved` write, then commit

Once `dd-diagnose`'s phase 6 is GREEN, write the resolution through the one
governance-write seam — **`dadaia bugs update`, never `--event`** (v0.5.0 FR2 retired
the event-stream shape; there is no `dadaia bugs append --event …` verb):

```bash
dadaia bugs update <bug-id> \
  --set status=resolved \
  --set cause="<what caused the bug>" \
  --set resolved_release=<release-id> \
  --set evidence_loop="<phase 1's red-loop command>" \
  --set evidence_seam="<phase 5's regression-test file::node>" \
  --set evidence_diff="net-negative: <checkable rationale>" \
  --set diff_direction=net-negative
```

`caused_by`/`lineage_source` are already declared by `dd-diagnose` phase 0 — do not
re-set them here. `evidence_loop`/`evidence_seam`/`evidence_diff` are the FR23 evidence
triple (write-once — a differing re-set is refused at the seam); `evidence_diff` carries
the free-text rationale prefixed `net-negative:`/`net-positive:`/`net-neutral:`,
`diff_direction` carries the same verdict as a closed enum a metric can read without
parsing prose. `net-positive:`/`diff_direction=net-positive` routes to
`software-architect` **before** the commit (`dd-diagnose` §4, `DADAIA.md` §7 (Quality)).

**Commit shape.** One commit, no second — code + regression test + the `BUGS.jsonl`
line, staged together. The exact shape is stated once, at `dd-gitflow-default` §3a shape
3 — consult it, do not restate it; `resolved_commit` stays `null` at resolve time (a
commit cannot contain its own sha, AS-1) and is filled later, by an audit.

## 4. No separate release ceremony

The bug fix lands on the live `feature/{M.m.p}` branch with the rest of the release —
no separate SPEC/PLAN/TASKS, no `specs/releases/<id>/`, no standalone version mint
(retired `hotfix/*` path; `DADAIA.md` §4 Gitflow / `dd-gitflow-default`). The resolved
record, dated and evidenced, is the durable record.

## 5. Checklist

- [ ] A record for this bug exists (`status: "open"`) before starting; branch is the
      live `feature/{M.m.p}`.
- [ ] `dd-diagnose` run through to phase 6, GREEN — including its phase 0 lineage
      declaration (`caused_by`/`lineage_source`).
- [ ] `dadaia bugs update <id> --set status=resolved …` carries the FR23 evidence
      triple (`evidence_loop`/`evidence_seam`/`evidence_diff`) plus `diff_direction`
      and `resolved_release` — never `--event`.
- [ ] A `net-positive` diff routed to `software-architect` before the commit.
- [ ] One isolated commit (`dd-gitflow-default` §3a shape 3); no separate ceremony
      opened; worktree clean.
