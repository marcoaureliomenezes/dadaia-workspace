---
name: dd-bug-resolution
description: >
  Use when: closing out Arm B on an already-registered bug — branch, concurrency, the
  `resolved` record write, commit, no separate ceremony. The diagnosing method itself
  (lineage, red loop, hypotheses, instrument, seam test, cleanup) is `dd-diagnose`,
  called from here. Granted to `software-engineer` and `ai-engineer` once a bug
  carries a record in `BUGS.jsonl`. Renamed from `dd-bug-fix` at v0.5.0 T-050-21
  (FR12) — the diagnosing phases moved out to `dd-diagnose` (FR7); this skill keeps
  only the bug-lifecycle rump.
tldr: "Once dd-diagnose is GREEN: write the resolved record via `dadaia bugs update`, one commit, no separate release."
applyTo: "specs/bugs/**"
---

# dd-bug-resolution — Arm B, the Lifecycle Rump

> Not hook-enforced. `software-engineer`/`ai-engineer` run this directly once a bug carries a record.
> Git chokepoints (`DADAIA.md` §3) are the only mechanical backstop.

## 1. When

- A record already exists in `specs/bugs/BUGS.jsonl` (`status: "open"`) — `dd-bug-registration`'s only output.
- Never to register or classify a bug — that is `dd-bug-registration`'s job alone.

## 2. Steps

1. Call `dd-diagnose` now for phase 0 (lineage) through phase 6 (cleanup) — never restate the diagnosing method here.
2. Work on the live `feature/{M.m.p}` branch — no separate branch, no ceremony (`DADAIA.md` §4 / `dd-gitflow-default`).
3. Under the NO-LOCKS DOCTRINE, let races surface: two fixers resolve by whichever `dadaia bugs update` lands first.
4. A losing write fails non-zero — re-read and retry, never block a human.
5. Once `dd-diagnose` phase 6 is GREEN, write the resolution with `dadaia bugs update <bug-id> --set status=resolved …`.
6. Include in that update: `cause`, `resolved_release`, `evidence_loop`, `evidence_seam`, `evidence_diff`, `diff_direction`.
7. Never use `--event` — the event-stream shape was retired.
8. Leave `caused_by`/`lineage_source` untouched — `dd-diagnose` phase 0 already set them.
9. Route a `net-positive` diff to `software-architect` before the commit.
10. Stage code + regression test + the `BUGS.jsonl` line together, one commit, no second.
11. Use shape 3 of `dd-gitflow-default` §3a for that commit.
12. Leave `resolved_commit` as `null` at resolve time — a commit cannot contain its own sha.
13. Open no SPEC/PLAN/TASKS, no `specs/releases/<id>/`, no standalone version mint for the fix.

## 3. Done when

- `dd-diagnose` reached GREEN, lineage declared.
- `dadaia bugs update` carries the FR23 evidence triple plus `diff_direction` and `resolved_release`.
- A `net-positive` diff was routed to `software-architect` before committing.
- One isolated commit exists; no separate ceremony opened; worktree clean.

## 4. References

- `dd-diagnose` — the diagnosing method (lineage, red loop, hypotheses, seam test).
- `dd-gitflow-default` §3a shape 3 — the exact commit shape.
- `DADAIA.md` §4 (Gitflow), §7 (Quality) — branch contract, net-positive routing.
- `entities/behavior-map.json` — `declared_overlaps` for the shared `specs/bugs/**` glob.
