---
name: dd-release-definition
description: "Use when: turning bugs and/or backlog items into a release. product-engineer (dispatched by project-manager) picks a pre-sanitized set and refines it into a SPEC. Enforces bug-always-solved (unless subsumed) and a MANDATORY dadaia-grill-me session before the SPEC is written. Invoke at the start of release definition."
applyTo: "specs/backlog/**"
---

# dd-release-definition

> **Not a hook-enforced mechanism.** There is no workflow engine that assembles
> per-step prompts or advances gates. `product-engineer` (dispatched by
> `project-manager`) drives every step of this protocol directly, from picking the set
> through authoring SPEC → PLAN → TASKS, with reviews per the segment/release cadence.
> This skill is the authoritative protocol for that flow.

## When to invoke

When the operator asks for a new release built from bugs and/or backlog (e.g.
"cut a release from the backlog", "turn these bugs into a release"). `product-engineer`
runs this protocol after `project-manager` dispatches it; the output is an
approved SPEC for the release. Do **not** start authoring SPEC/PLAN/TASKS until
steps 1–3 below are complete.

## Inputs

- `specs/bugs/*.jsonl` — event-sourced bug records, inspected through `dadaia bugs`.
- Sanitized, deduplicated candidates: `specs/backlog/BACKLOG.md` `## ACTIVE`
  (see `dd-backlog-definition` §2) — the single-source document, no per-entry files.
- The operator's intent for the release (theme, urgency).

Sanitizing and deduplicating those inputs is `dd-backlog-definition`'s job, run
continuously by `project-manager` — this skill consumes an already-clean set and does
not re-triage it.

## Protocol

### 1. Pick the set

> **Pick-time priority** (`DADAIA.md` §5 Releases): "At pick time, open bugs and
> undispositioned audits outrank fresh backlog."

Select the bugs + backlog items this release will address. This is discovery
**within** `specs/bugs/` + `specs/backlog/` — not wide-codebase discovery (that
stays out of product-engineer's lane). Record the picked set; it becomes the
SPEC's scope.

### 2. Apply the bug-always-solved rule
Every **picked bug must be solved in the release**, with exactly one exception:
- If a **picked backlog item supersedes the bug** with a more complete solution,
  record the subsumption:
  - `dadaia bugs append --bug-id <slug> --event superseded --superseded-by <backlog-slug>`
    (the JSONL ledger, not frontmatter — bugs carry no `.md` file),
  - note it in the release SPEC,
  - ensure the backlog item's TASKS cover the bug's acceptance criteria.
- A bug is **never silently dropped**. If it's neither fixed nor subsumed, it is
  not "picked" — leave it open (`dd-backlog-definition` sanitizes it on its own cadence).

### 3. MANDATORY grill
Run a `dadaia-grill-me` session on the picked set. This is **obligatory** — it
resolves inconsistencies, scope gaps, ambiguous acceptance, and stale assumptions
**before** the SPEC exists. Do not skip it even when the scope "looks obvious".

### 4. Author the SPEC
Only now write the release SPEC (Draft), with:
- the picked bug + backlog set and their acceptance,
- every `superseded_by` link from step 2.

Definition runs on `feature/{M.m.p}`. Once SPEC + PLAN + TASKS are all `Aprovado`, that
is **milestone (a)**: merge `feature/{M.m.p}` into local `develop`, run the diff-based
security review, and push `develop` — a mandatory obligation, not optional cleanup (the
branch/commit/push mechanics are the `dadaia-gitflow` skill's contract).

Then continue the normal SDD flow (PLAN → TASKS → implementation), with reviews
per the segment/release cadence (alpha = qa-only; rc-ship = qa + code + security).

### 5. Declare consumed backlog (`**Consumes:**`)
If this release **fully consumes** one or more backlog items, declare them in a
machine-readable bold-key line in the SPEC, alongside `**Status:**` / `**Release ID:**`:

```
**Consumes:** slug-a, slug-b
```

`**Consumes:**` is SPEC provenance, not a producer call site — no library or CLI verb
reads this line. Two mechanisms actually execute consumption, at two different points:

| When | Executor | What it does |
|---|---|---|
| At definition, same commit as the SPEC | `project-manager`'s purge-on-pick (`dd-backlog-definition` §2) | Removes each declared slug from `## ACTIVE`, recording provenance in the SPEC |
| At closure | `dd-release-closure`'s Disposition sweep | Adds a `## LEDGER` line and drops the `## ACTIVE` subsection for each fully-consumed slug (terminal disposition token vocabulary: `dd-backlog-definition` §2) |

Two mechanical backstops catch a slug that falls through either step: `backlog doctor`'s
BL-STALE (an `ACTIVE` item already consumed/dispositioned) and `specs doctor`'s
SPEC-DOC-031 (FR14 semantics — an archived SPEC's `**Consumes:**` declaration or an
archived CLOSURE's `## Dispositions` rows naming a still-non-terminal `ACTIVE` slug). Rules that still describe something that runs:
- **Full-slug granularity:** a declared slug is treated as *fully* consumed (all its bound
  anchors shipped). A partially-shipped item must NOT be declared — leave it in the
  backlog and rewrite it to its residual by hand.
- **Fail-loud:** an unknown slug aborts step 1 (purge-on-pick) — fix the slug before it
  lands in the SPEC.
- Omit the line entirely when a release consumes no backlog item.

## Authority & dispatch

`product-engineer` owns picking and SPEC authorship; `project-manager` dispatches
this work and owns the mandatory-grill gate (it must not let a release-from-backlog
proceed to SPEC without the grill). See the `project-orchestration` skill's
release-definition playbook and the `DADAIA.md` §5 (Releases).

## Checklist

- [ ] Picked set recorded (from `dd-backlog-definition`'s already-sanitized `ACTIVE`).
- [ ] Every picked bug fixed-in-release OR `superseded_by` a picked backlog item.
- [ ] `dadaia-grill-me` session completed (report emitted).
- [ ] SPEC authored from the refined, picked set.
- [ ] `**Consumes:**` line declared for any fully-consumed backlog item (or omitted if none).
