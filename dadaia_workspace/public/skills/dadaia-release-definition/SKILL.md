---
name: dadaia-release-definition
description: "Use when: the operator wants to turn reported bugs and/or backlog items into a release. The protocol product-engineer follows (dispatched by project-manager) to pick, sanitize, and refine bugs + backlog into a SPEC. Enforces the `bug-hotfix-doctrine` rule (bugs are hotfixed, never released; supersession is the only release-side disposition), staleness sanitization, and a MANDATORY dadaia-grill-me session before the SPEC is written. Invoke at the start of release definition, before authoring SPEC/PLAN/TASKS."
applyTo: "specs/backlog/**"
---

# dadaia-release-definition

> **Not the lifecycle enforcement mechanism.** Ordered release-definition execution is
> owned by the **release-definition dadaia-workflow**
> (`dadaia lifecycle release-definition`) —
> a Python workflow body that assembles fragment-scoped per-step prompts
> (`release_scope → spec_create → spec_*_review → plan_create → … → definition_commit_gate`)
> and advances Python-validated gates. This skill is reference / manual-operator guidance
> only; it does not enforce the sequence. See **`dadaia panel` → 2º Agentic Layer**
> for the live workflow description.

## When to invoke

When the operator asks for a new release built from bugs and/or backlog (e.g.
"cut a release from the backlog", "turn these bugs into a release"). `product-engineer`
runs this protocol after `project-manager` dispatches it; the output is an
approved SPEC for the release. Do **not** start authoring SPEC/PLAN/TASKS until
steps 1–4 below are complete.

## Inputs

- `specs/bugs/*.jsonl` — event-sourced bug records, inspected through `dadaia bugs`.
- `specs/backlog/*.md` + `candidates.md` / `ideas.md` — backlog (read `specs/backlog/*.md` directly).
- The operator's intent for the release (theme, urgency).

## Protocol

### 1. Sanitize first
Before picking, triage every open bug and backlog item for staleness/validity:
- An item already solved, obsolete, or no longer valid → mark `status: rejected`
  (invalid) or `status: deferred` (valid but not now), **with a one-line reason**.
- **Never delete** a bug or backlog file (matches `specs/bugs|backlog/README`).
- Staleness signal: an open item with no `release:` past the cutoff (72h-style
  window for `## Hotfixes pendentes` bullets; tune for general items). When unsure,
  surface it in the grill (step 4) rather than guessing.

### 2. Pick the set
Select the bugs + backlog items this release will address. This is discovery
**within** `specs/bugs/` + `specs/backlog/` — not wide-codebase discovery (that
stays out of product-engineer's lane). Record the picked set; it becomes the
SPEC's scope.

### 3. Dispose any open bug per the `bug-hotfix-doctrine` rule
Bugs are **not release material**. A reported bug is fixed on the spot — register,
root-cause, RED test, fix, GREEN, `resolved` event, commit — never by opening a
release for it. The only bug disposition a release still makes is **supersession**:
- If a **picked backlog item supersedes an open bug** with a more complete solution,
  record the subsumption:
  - add `superseded_by: <backlog-slug>` to the bug's frontmatter,
  - note it in the release SPEC,
  - ensure the backlog item's TASKS cover the bug's acceptance criteria.
- A bug is **never silently dropped**. If it's neither fixed nor subsumed, it is
  not "picked" — leave it open (and sanitize/defer it explicitly if stale).

### 4. MANDATORY grill
Run a `dadaia-grill-me` session on the picked set. This is **obligatory** — it
resolves inconsistencies, scope gaps, ambiguous acceptance, and stale assumptions
**before** the SPEC exists. Do not skip it even when the scope "looks obvious".

### 5. Author the SPEC
Only now write the release SPEC (Draft), with:
- the picked bug + backlog set and their acceptance,
- every `superseded_by` link from step 3,
- the sanitization outcomes from step 1 (what was deferred/rejected and why).

**Every acceptance criterion states how it will be proven.** A criterion with no verification
path is a wish. For public behaviour, name the observable input/output/failure that proves
it. For an internal or negative constraint, name the controlled probe, fake, call-observation
test, or structural inspection that can prove it — *never* rely on equal end results to prove
which internal path produced them, because two paths that agree on the output prove nothing
about which one ran.

### 5b. PLAN — decide the contracts here, once

The PLAN carries the ordered workstreams and where each change lands. For **every new or
changed caller-facing surface**, it also carries the **contract binding**: the exact
module/export path, the public type/function/method name, the parameter and return
signature, and the field names with types.

Decide those bindings in the PLAN and nowhere else. TASKS copies them **verbatim** and is
forbidden to invent one you left out — anything omitted here becomes unfixable downstream,
because the implementer will invent a signature and the reviewer will reject it. Authoring
PLAN and TASKS apart, without this rule, guarantees drift.

The PLAN also carries a **validation dependency table**, one row per workstream, so the
release states how each piece is proven and what that proof waits on:

```
| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |
|---|---|---|---|---|
| WS-1 | … | … | None | None |
```

Use `None` for an empty cell — never leave one blank. A workstream may not depend on a
**later** one for its own validation: a forward dependency means the plan cannot be validated
in the order it is written. A shell command in the "Direct validation" cell may contain a
pipe; wrap it in a code span or escape it as `\|` so the table still parses.

### 5c. TASKS

One task per unit of work, each carrying: owner role, explicit write set, description,
validation command, preconditions by task id, and the `[ ]` marker (see the
`dadaia-task-manager` skill for marker discipline).

Then continue the normal SDD flow (implementation), with reviews per the segment/release
cadence (alpha = qa-only; rc-ship = qa + code + security).

### 6. Declare consumed backlog (`**Consumes:**`)
If this release **fully consumes** one or more backlog items, declare them in a
machine-readable bold-key line in the SPEC, alongside `**Status:**` / `**Release ID:**`:

```
**Consumes:** slug-a, slug-b
```

This is the producer half of removal-on-release. At `dadaia lifecycle release-definition`,
a guarded post-step parses this line, binds each declared slug's `intents[]` through the
canonical-subject registry → the verified **shipped-anchor set**, and writes
`specs/_archive/<release-id>/consumed_backlog.json`. At
`dadaia lifecycle implementation-reviews`, the
residual-aware removal hook reads that ledger and drops each fully-consumed item from the
live `specs/backlog/` SET (archiving a copy first), so `backlog doctor` reports zero
BL-STALE. Rules:
- **Full-slug granularity:** a declared slug is treated as *fully* consumed (all its bound
  anchors shipped). A partially-shipped item must NOT be declared — leave it in the
  backlog and rewrite it to its residual by hand.
- **Fail-loud:** an unknown slug, or one whose intents do not bind in the registry, aborts
  the define post-step (no silent skip) — fix the slug or the item's `intents[]`.
- Omit the line entirely when a release consumes no backlog item.

## Authority & dispatch

`product-engineer` owns picking and SPEC authorship; `project-manager` dispatches
this work and owns the mandatory-grill gate (it must not let a release-from-backlog
proceed to SPEC without the grill). See the `project-orchestration` skill's
release-definition playbook and the `release-governance` rule.

## Checklist

- [ ] Stale bugs/backlog sanitized (`deferred`/`rejected` + reason; nothing deleted).
- [ ] Picked set recorded.
- [ ] Every open bug hotfixed on the spot OR `superseded_by` a picked backlog item —
      never carried into the release as scope.
- [ ] `dadaia-grill-me` session completed (report emitted).
- [ ] SPEC authored from the refined, picked set.
- [ ] `**Consumes:**` line declared for any fully-consumed backlog item (or omitted if none).
