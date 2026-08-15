# PLAN — Release v0.10.0 — `dd-` lifecycle skills family and rule dehydration

**Status:** Aprovado
**Release ID:** v0.10.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.10.0/SPEC.md`
**Branch:** `feature/v0.10.0` (cut from `develop` at `0f66fb3f`; branch contract: `dadaia-gitflow`)
**Segment:** none — flat release, one implementation increment closed by a `qa-engineer` review

---

## 1. Strategy

This release moves **text between files**. Almost nothing executes differently afterwards;
what changes is which file a given sentence lives in, and therefore what every session
pays for it. That shapes the whole plan:

1. **Destinations before sources.** Every dehydration cut has a destination skill. Author
   the destination first, then cut the source. A cut whose destination does not yet exist
   is a deletion, and the intermediate commit would ship a law with a dangling pointer.
2. **The law last among the text edits.** `public/data/DADAIA.md` is the highest-stakes
   file in the tree and the one the operator personally eyeballs (ADR #7/E-1 guardrail c).
   Its edit lands after all six destination skills exist, so the diff can be read against
   a tree where every pointer already resolves.
3. **Wiring after content.** Frontmatter grants, the Codex prefix gate and the test
   goldens all name the final skill set. They move once, at the end, not seven times.
4. **Projection is a task, not a footnote.** v0.9.0's lesson: re-projection plus
   `dadaia public doctor` is an explicit task with its own done criterion. This release
   adds the orphan sweep to it, because `install` prunes nothing.
5. **One `[-]` at a time.** No sanctioned parallel pair. Ten of the nineteen tasks write
   into `dadaia_workspace/public/`, and the rename ripples cross those files; overlapping
   write sets would make a partial state unreadable.

**Ownership is the release's defining constraint.** `DADAIA.md` §2 gives the AI surface —
agents, skills, rules — to `ai-engineer` exclusively. Eleven tasks are `ai-engineer`'s.
Exactly one task (FR13) is `software-engineer`'s, and it exists only because the rename
would otherwise silently disable a doctor check. `product-engineer` authors text and never
implements; every git step is the dispatcher's or `software-engineer`'s.

---

## 2. Layers and surfaces affected

| Surface | Files | Owner |
|---|---|---|
| Skills — new | `public/skills/{dd-backlog-definition,dd-release-implement,dd-bug-registration,dd-bug-fix}/SKILL.md` | ai-engineer |
| Skills — renamed | `dadaia-release-definition` → `dd-release-definition`; `dadaia-release-closure` → `dd-release-closure`; `drift-detection` → `dd-audit-project` | ai-engineer |
| Skills — dehydrated | `dadaia-cli`, `dadaia-gitflow`, `project-orchestration` | ai-engineer |
| Skills — reference-only edits | `dadaia-grill-me`, `dadaia-test-stewardship`, `ai-harness-codex` | ai-engineer |
| Law source | `public/data/DADAIA.md` (§5 Backlog, §5 Hotfixes, §6 registration, §6 watch-CI, §9 skills row) | ai-engineer, under the ADR #7/E-1 guardrails |
| Agent personas | `public/agents/{ai-engineer,product-engineer,project-auditor,project-manager,qa-engineer,software-engineer}.md` | ai-engineer |
| Production code | `infrastructure/runtime_transforms/codex_assets.py` (one constant) | software-engineer |
| Tests | `tests/e2e/features/test_public_pipeline.py`, two `_golden/*.json`, one new contract test | software-engineer |
| Projections | `.dadaia/agentic/`, `.agents/`, `.claude/`, `.codex/`, `.kimi-code/` | ai-engineer (via the CLI chain) |
| Memory | four atoms + `catalog.json` (see SPEC §5) | product-engineer, CLOSURE only |

**Untouched by design:** `specs/_archive/**` (FROZEN), `CHANGELOG.md` history entries,
`public/scaffold/backlog/README.md`, every `features/backlog/*` module, and the
`dadaia backlog` CLI verbs (SPEC §4.5, §4.10).

---

## 3. Execution order and why

```
01 definition commit ─ 02 milestone (a): merge → security review → push
                              │
                        03 baseline census (the denominator for FR15)
                              │
   ┌── destinations ──────────┴────────────────────────────────────┐
   │ 04 dd-backlog-definition   (owns the vocabulary + intake gate) │
   │ 05 dd-release-definition   (consumes 04's sanitize reference)  │
   │ 06 dd-release-implement    (absorbs the E-3 cadence table)     │
   │ 07 dd-release-closure      (references 04; re-routes returns)  │
   │ 08 dd-audit-project        (merge+rename of drift-detection)   │
   │ 09 dd-bug-registration     (drains the cli duplicate)          │
   │ 10 dd-bug-fix              (drains the gitflow duplicate)      │
   └────────────────────────────┬───────────────────────────────────┘
                          11 law dehydration  ← every pointer now resolves
                                │
                 12 F-0 + rename ripple      13 ADR #15 external surfaces
                                │
                          14 software-engineer wiring (FR13)
                                │
                          15 re-projection + orphan sweep
                                │
                          16 qa-engineer review (flat alpha close)
                                │
                 17 memory (CLOSURE)  ─  18 CLOSURE + archive + bump
                                │
                          19 milestone (b): ship
```

Task 04 is first among the destinations because two other skills reference the vocabulary
it owns (ADR #13/E-7) and one references its intake gate (ADR #15). Task 11 is the hinge:
before it, the law still carries the procedure; after it, the law points and the skills
own. Tasks 12 and 13 are separated because they answer different questions — 12 is "does
any file still say the old name?", 13 is "does any file still describe the old flow?" —
and mixing them produces a diff nobody can review.

---

## 4. The three judgment calls this plan encodes

**(a) The E-3 table move is a move, not a copy.** `project-orchestration` keeps a one-line
named reference. If implementation finds the reference insufficient for a dispatcher, that
is a drift to record in CLOSURE, not a licence to leave a second copy — proxy 2 of the
style bar (SPEC A1.3) would fail it anyway.

**(b) The law's net size is a gate, not an aspiration.** FR9-C1 grows §5 (the BACKLOG.md
doctrine plus the intake rule) while C3/C5/C6 shrink §5/§6. A15.2 requires the post-release
word count not to exceed the measured baseline. If the arithmetic comes out negative at
task 11, the correct response is to tighten C1's wording — not to relax the criterion and
not to cut deeper into C2/C4, which are explicitly `KEEP`.

**(c) The style bar is verified, not asserted.** No linter is built (SPEC §4.6). The
proxy-2 shingle scan is a documented command that `qa-engineer` runs at task 16 and whose
output goes into CLOSURE. Building a linter for a one-off family would be a second
production surface in an AI-surface release.

---

## 5. Technical risks and their handling in this plan

| Risk (SPEC §6) | Where the plan absorbs it |
|---|---|
| R1 silent D-CX-7 degradation | task 14 pairs the constant edit with a new contract test that fails if the gate goes inert; the test is written **before** the tuple change (RED-first) |
| R2 orphan projections | task 15's done criterion includes an explicit absence check across five trees |
| R3 lost classification signal | task 11's checklist verifies C2/C4/§1/§2 byte-identity as a precondition of its own completion |
| R4 the law grows | task 03 captures the baseline; task 11 reports its own delta; task 16 verifies |
| R5 duplication reappears | tasks 04–10 each end with a proxy-2 self-check against the already-written family members |
| R7 privacy at push | standing rule in TASKS; the v0.9.0 range scan will refuse the push otherwise |
| R10 residual old flow | task 13 is a dedicated task with a grep-based done criterion, not a rider on task 12 |

---

## 6. RED-first, and where it applies

This release is overwhelmingly prose, where "RED first" has no meaning. It applies to
exactly one task:

- **Task 14** — the D-CX-7 contract test is written first and observed failing for the
  real reason (a projected persona citing `dd-nonexistent` produces no ERROR line because
  the prefix tuple does not yet contain `dd-`), then the tuple is fixed and the test goes
  green. Intent declared at birth: `Intent: CONTRACT — v0.10.0 A13.3`.

Every other task's verification is a documented command whose output is captured for
CLOSURE (`wc`, `grep`, `dadaia public doctor`, the e2e suite).

---

## 7. Validation plan

| # | What | Command | Gate |
|---|---|---|---|
| V1 | Family exists, budgets hold | `wc -l dadaia_workspace/public/skills/dd-*/SKILL.md` | A1.1, A1.2 |
| V2 | No duplicated law text | normalized 15-word shingle scan across the seven skills and `public/data/DADAIA.md` | A1.3 |
| V3 | Description listing tax | frontmatter `description` length per family skill | A1.4 |
| V4 | Zero stale skill names | `grep -rn "dadaia-release-definition\|dadaia-release-closure\|drift-detection"` excluding `specs/_archive/**` and `CHANGELOG.md` | A12.1 |
| V5 | Zero stale intake flow | `grep -rn "backlog/ideas.md\|backlog/candidates.md\|## Hotfixes pendentes" dadaia_workspace/public/` | A16.3 |
| V6 | Law fidelity | diff of `public/data/DADAIA.md` against SPEC FR9's verbatim text; C2/C4/§1/§2 byte-identical | A9.1–A9.3 |
| V7 | Law net size | `wc -w dadaia_workspace/public/data/DADAIA.md` vs the task-03 baseline | A15.2 |
| V8 | D-CX-7 live for the family | the new contract test | A13.3 |
| V9 | Skill set pinned | full `pytest` incl. `EXPECTED_SKILLS` and both goldens | A13.4 |
| V10 | Projection chain | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | A14.1 |
| V11 | No orphans | absence check in `.dadaia/agentic/skills/`, `.agents/skills/`, `.claude/skills/`, `.codex/`, `.kimi-code/` | A14.2 |
| V12 | Byte identity across trees | source ↔ staging ↔ `.agents` ↔ `.claude` for the seven skills | A14.3 |
| V13 | Push preflight | `dadaia ci preflight` (ruff format, ruff check, mypy --strict, pytest) | before each push |
| V14 | Token accounting | task-03 baseline vs post-release measurement, itemized | A15.1–A15.4 |
| V15 | Frontmatter grants | each `dd-` skill present in the frontmatter `skills:` list of every agent named in FR13(a) | A13.1 |

`qa-engineer` runs V1–V12 and V14–V15 at task 16 and returns an APPROVE/REQUEST_CHANGES
verdict enumerating every acceptance id. V13 runs before every push.

---

## 8. Definition-of-done for the release

1. Nineteen tasks `[x]`.
2. `qa-engineer` APPROVED on the increment (task 16).
3. `dadaia public doctor` green including `[ok] public-privacy`; full suite green.
4. Memory updated per SPEC §5, then `CLOSURE.md` written, then the release archived —
   in that order.
5. `CLOSURE.md` carries: the FR15 before/after token table with its commands, the V1–V3
   style-bar measurements, the V4/V5 zero-hit greps, the disposition of the picked
   candidate (`DELIVERED — v0.10.0`), the ADR #14 scope-split statement (A10.3), and the
   intake-candidate list under the new `## Intake candidates` heading — compiled for the
   PM's operator-facing intake report, never materialized as backlog entries.
6. `code-reviewer` + `security-reviewer` APPROVED at ship; PR `develop` → `main` merged;
   CI green.
