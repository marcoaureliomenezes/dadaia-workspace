---
name: dd-release-definition
description: >
  Use when: turning bugs and/or backlog items into a release. product-engineer (dispatched
  by project-manager) picks a pre-sanitized set and refines it into a SPEC. Enforces bug-
  always-solved (unless subsumed) and a MANDATORY dd-grill-me session before the SPEC is
  written. Invoke at the start of release definition.
tldr: "Pick set -> bug-always-solved -> mandatory dd-grill-me -> author SPEC -> declare **Consumes:**."
applyTo: "specs/releases/*/SPEC.md"
---

# dd-release-definition

> Not hook-enforced. `product-engineer` (dispatched by `project-manager`) drives every step directly.
> From picking the set through SPEC -> PLAN -> TASKS.

## 1. When

- The operator asks for a new release built from bugs and/or backlog.
- `product-engineer` runs this after `project-manager` dispatches it.
- Never start authoring SPEC/PLAN/TASKS until steps 1-3 (below) are complete.

## 2. Steps

1. Inspect `specs/bugs/BUGS.jsonl` via `dadaia bugs status`/`stats`.
2. Read `specs/backlog/BACKLOG.json`'s `active[]` — already sanitized/deduplicated by `dd-backlog-definition`.
3. Pick the set: open bugs and undispositioned audits outrank fresh backlog (`DADAIA.md` §6).
4. Keep picking scoped to `specs/bugs/`+`specs/backlog/` discovery — not wide-codebase discovery.
5. Record the picked set; it becomes the SPEC's scope.
6. Solve every picked bug in the release, with exactly one exception: subsumption by a picked backlog item.
7. On subsumption, run `dadaia bugs supersede <slug> --by <backlog-slug>` — never `update --set status=`.
8. Note the subsumption in the release SPEC; ensure the backlog item's TASKS cover the bug's acceptance criteria.
9. Never silently drop a bug — leave it `open` if neither fixed nor subsumed (`dd-backlog-definition` sanitizes it later).
10. Call the Skill tool with `dd-grill-me` on the picked set — mandatory, never skipped even when scope "looks obvious".
11. Author the release SPEC (Draft) only after the grill: the picked bug+backlog set, their acceptance, every `superseded_by` link.
12. Run definition on `feature/{M.m.p}`; open the definition PR once SPEC+PLAN+TASKS are all `Aprovado`.
13. Append the `defined` milestone in `RELEASE.json` at the promotion commit (`RELEASE-EVENTS.md`'s recipe).
14. Continue the normal SDD flow (PLAN -> TASKS -> implementation) with reviews per the segment/release cadence (`RC-FLOW.md`).
15. Declare fully-consumed backlog items in the SPEC: `**Consumes:** slug-a, slug-b`.
16. Treat `**Consumes:**` as SPEC provenance only — no library/CLI verb reads this line.
17. Let `project-manager`'s purge-on-pick (same commit as the SPEC) execute consumption at definition.
18. Let `dd-release-implement`'s disposition sweep (closure) rewrite that slug's histo record to its terminal token, in place.
19. Declare a slug only when fully consumed (all its bound anchors shipped) — never a partially-shipped item.
20. Abort on an unknown slug (fail-loud) — fix the slug before it lands in the SPEC.
21. Omit the `**Consumes:**` line entirely when the release consumes no backlog item.

## 3. Done when

- Picked set recorded (from `dd-backlog-definition`'s already-sanitized `ACTIVE`).
- Every picked bug fixed-in-release OR `superseded_by` a picked backlog item.
- `dd-grill-me` session completed (report emitted).
- SPEC authored from the refined, picked set.
- `**Consumes:**` declared for any fully-consumed backlog item, or omitted if none.

## 4. References

- `dd-backlog-definition` §2 — the sanitized-set source this skill consumes without re-triage.
- `dd-grill-me` — the mandatory pre-SPEC session.
- `dd-gitflow-default` §3a shape 5 — the release-definition commit shape.
- `dd-release-implement` (`RELEASE-EVENTS.md`, `RC-FLOW.md`) — milestone recipe, review cadence, disposition sweep.
- `specs/releases/AGENTS.md` — release-id format, `_ideas/`'s pre-approval role.
- Two mechanical backstops for a fallen-through slug: `backlog doctor`'s BL-STALE, `specs doctor`'s SPEC-DOC-031.
- `DADAIA.md` §4 Gitflow, §6 (Releases) — branch contract, pick-time priority.
- `entities/behavior-map.json` `declared_overlaps` — activation precedence for the fleet.
