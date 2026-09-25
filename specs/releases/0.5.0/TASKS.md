# TASKS — Release: 0.5.0

**Status:** Approved
**Owner:** dd-software-engineer

Paths under `dadaia_workspace/public/` abbreviated `pub/`. DELETE/REBUILD rows (PLAN §1) land first.

## Candidate 2 — definition reviews the as-is before it adds

- [x] **T-050-01 — Rebuild `dd-release-definition`: the as-is review step.**
  Delete §3.4 (R1); sections become Pick the set → As-is review → The mandatory grill → Author the trio →
  TASKS as tracer bullets → Declaring consumption → Done when → References; As-is review states D1–D3 and
  the PLAN §1 skeleton once; §4 demolition bullet rewritten to DELETE/REBUILD-before-ADD (R4); Done when
  gains one bullet; `dd-grill-me` pointers name §3 (R7).
  `Write set:` `pub/skills/dd-release-definition/SKILL.md`, `pub/skills/dd-grill-me/SKILL.md`
  `blocked by:` none · `delivers:` FR1 AC1.1–AC1.8 — a definer reads the step and the skeleton

- [x] **T-050-02 — `phase IMPLEMENTATION` refuses a PLAN without the as-is table.**
  RED first: `tests/contract/test_release_script.py` — pass case, missing heading, heading without table,
  wrong header, zero rows, unknown verdict (names unit + verdict), numbered/unnumbered heading, lowercase
  verdict, all-ADD, unapproved trio refuses first, and the skeleton extracted from the skill's source text
  passing. Then one private check in `_refuse_unapproved_trio`'s admission.
  `RED:` every refusal case exits 0 before the check; skeleton case fails before T-050-01.
  `Write set:` `pub/skills/dd-release-implementation/scripts/_release_phase.py`,
  `tests/contract/test_release_script.py`, `tests/unit/skills/test_release_implementation_release_script.py` (fixture PLAN only)
  `blocked by:` T-050-01 · `delivers:` FR2 AC2.1–AC2.6 — a PLAN without §1 cannot enter IMPLEMENTATION

- [x] **T-050-03 — SPEC stub carries `Replaces`.**
  `SPEC_STUB` gains `## Replaces` between Scope and Out of scope; `new` still writes no PLAN and deletes
  the closed PLAN/TASKS.
  `RED:` a `new` stub test asserts the section order.
  `Write set:` `pub/skills/dd-release-implementation/scripts/_release_new.py`, `tests/contract/test_release_script.py`
  `blocked by:` T-050-02 · `delivers:` AC1.9 — a newborn SPEC asks for its Replaces

- [ ] **T-050-04 — Review and Arm B read the as-is.**
  `dd-code-review` Axis 2 gains two bullets (D7); `LINEAGE.md` states D8 with the `rebuild:` echo and
  `--solution` prefix; `dd-bug-resolution` Phase 0 clause + Done-when names `rebuild`/`none`. `bugs.py` untouched.
  `Write set:` `pub/skills/dd-code-review/SKILL.md`, `pub/skills/dd-bug-resolution/{SKILL,LINEAGE}.md`
  `blocked by:` none · `delivers:` FR3, FR4 — a reviewer and a fixer apply the verdicts

- [ ] **T-050-05 — Law, personas and terms name the step.**
  Root map Arm A + §2 engineer row; scaffold releases lifecycle line + `specs/releases/AGENTS.md`
  reprojection; one line per persona; `CONTEXT.md` four terms + Candidate arc.
  `Write set:` `pub/data/AGENTS.md`, `pub/scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md`,
  `pub/agents/dd-{software,product}-engineer.md`, `CONTEXT.md`, `CONTEXT-MAP.md`, recorded contract fixtures
  `blocked by:` T-050-01 · `delivers:` FR5, AC6.1 — every agent sees the step in its law

- [ ] **T-050-06 — Reproject and verify.**
  `public stage`/`install`/`doctor`, `dadaia doctor` exit 0; grep finds no "PLAN names the seams" and no
  lifecycle line starting at `grill` (AC7.3); `ci preflight --quick` green.
  `Write set:` recorded fixtures the suite demands (shipped hashes, behavior map, context map)
  `blocked by:` T-050-01..05 · `delivers:` AC5.4, AC7.1–AC7.3 — the live instance runs the new check
