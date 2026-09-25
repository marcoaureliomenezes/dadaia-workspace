# SPEC — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-09-25
**Origin:** operator-demand

---

## 1. Problem and context

Candidate 2 — "definition reviews the as-is before it adds". Operator demand 2026-09-25 (verbatim):

> "esse fator de analisar o que temos implementado, o que deve ser deletado, o que deve ser atualizado /
> reconstruido / refeito é um papel fundamental e acontece na etapa em que se constroi as release, SPECS,
> PLAN e TASKS a partir de uma demanda, ou backlog ou mesmo bugs... O que jamais pode ser feito: declarar
> uma nova release onde só se empilha novas coisas. A release em si, ao ser definida, deve olhar
> obrigatoriamente como aquela parte do projeto está implementada... quais são as classes, métodos, o que
> cada coisa faz. E confrontar com o que está vindo para ser definido... o dadaia-workspace, na etapa de
> definição de releases deve ter critérios claros de revisão do código as-is contra a nova demanda,
> orientado a ver nessa sequência o que precisa ser deletado, o que precisa ser atualizado / reconstruído /
> refeito, o que precisa ser adicionado. E isso deve estar nas nossas skills canônicas... precisamos parar
> de empilhar feature em cima de features podres."

Grill 2026-09-25, Q1–Q5 accepted (ADR 0041, handoff `2026-09-25T040500Z-main-thread-asis-review-grill`).
The operator's one concern (Q2): keep it SIMPLE, robust, resilient — the mechanical check is STRUCTURE
ONLY; trigger judgement stays with the engineer and the reviewer; no automated bug counting, no code
analysis.

- As-is (grill inspection): `dd-release-definition` goes from picking the set (§1) straight to the grill
  (§2) and the trio (§3); one sentence (§3.4, "PLAN names the seams the work will cut … what each FR grows
  or deletes") is the whole of the as-is duty, with no procedure, no table, no check.
- Evidence of stacking (ADR 0041 context): 9 fix-line bugs patched per call site, 8 hard-coded-branch bugs
  patched per literal, the baseline's convergent branch — new behaviour built on units that should have
  been rebuilt.
- `dd-bug-resolution` Phase 0 already reads the lineage window and Phase 6 already requires a non-growing
  diff; what is missing is the rule that a repeated fix site is rebuilt, not patched again.
- Bug history of mechanical PLAN gates (retired lifecycle engine, all resolved by deletion):
  `plan-dependency-gate-rejects-numbered-heading`, `scaffold-artifacts-fail-own-workflow-gates`,
  `plan-review-approves-a-plan-missing-its-contract-bindings`,
  `release-definition-approves-plan-with-unbound-public-api-contract`,
  `tasks-implementability-review-does-not-converge-on-a-real-release`,
  `release-definition-allows-validation-dependency-inversion`. Content-judging gates looped; this candidate's
  one gate judges structure only, accepts a numbered heading, and is proven against its own taught skeleton.
- `release.py phase IMPLEMENTATION` (`_release_phase.py`) carries 0 ledger bugs; `release.py new` carries
  1 (`release-new-refuses-the-stacked-candidate-the-law-requires`, resolved).
- Q5: this candidate lands before the onboarding foundation (c3) and docs (c4); their inventories
  (`.dadaia/tmp/claude/20260925/`) are the first as-is reviews under the new rule.

## 2. Objective

Every candidate definition starts by reviewing the as-is units the demand touches — DELETE, REBUILD,
UPDATE, KEEP, then a justified ADD — recorded as PLAN §1, echoed as the SPEC's `Replaces`, ordered first in
TASKS, refused by `release.py` only when the table is structurally absent, checked against the diff by the
reviewer; and a bug fix on a twice-fixed unit is a rebuild.

## 3. Decided design (ADR 0041, grill Q1–Q5)

- D1 (Q1) Definition step 2, between picking the set and the grill: `dd-software-engineer` reviews the
  as-is code the demand touches, read-only; its table travels in its handoff to the main thread, which
  carries it into the grill; it lands as PLAN §1.
- D2 (Q2) PLAN §1 `As-is review` is one Markdown table `unit | today | bugs | verdict | why`; verdicts
  `DELETE | REBUILD | UPDATE | KEEP`, then ADD rows (verdict `ADD`, `today` = `—`) only for what no existing
  unit can carry, each justified in `why`.
- D3 (Q2) REBUILD is mandatory when the unit carries ≥ 2 bugs; the demand changes its fundamental
  behaviour; the change would need a flag, branch, special case or second path; or its contract contradicts
  the demand. Judged by the engineer and the reviewer — never computed.
- D4 (Q1) SPEC gains `Replaces`: the current behaviours that stop existing.
- D5 TASKS order DELETE/REBUILD (expand–contract) before ADD.
- D6 (Q3) `release.py phase IMPLEMENTATION` refuses a PLAN without the table or with a verdict outside the
  vocabulary — structure only, one `fix:` line naming the skill section.
- D7 (Q3) `dd-code-review` spec axis: a DELETE/REBUILD unit left unchanged is HIGH; a KEEP unit that grew
  is a finding.
- D8 (Q4) Arm B: ≥ 2 prior fixes on the same unit in the Phase 0 window ⇒ the fix is a REBUILD of that
  unit, stated in the commit body and `--solution`.
- D9 Root map Arm A flow names the step; `dd-product-engineer` and `dd-software-engineer` gain one line each;
  law files stay statements.
- Decided by inspection: no PLAN stub — `release.py new` keeps deleting the closed PLAN/TASKS (a stale
  Approved pair must not pass); the skill's skeleton is the PLAN shape. ADD shares the one table (one parse).

## 4. Terms (enter `CONTEXT.md` with the implementation)

- **As-is review** — definition step 2: the read-only reading of every unit a picked set touches, its bug
  history included, ending in one As-is verdict per unit. _Avoid_: audit (the three-pillar review),
  inventory, survey (`dd-architecture-survey`).
- **As-is verdict** — one of `DELETE REBUILD UPDATE KEEP ADD` on one row of PLAN §1; always written
  qualified. _Avoid_: verdict (bare — the PR approval record), finding verdict (the doctor's).
- **As-is unit** — the row subject: a module (`dd-codebase-design`) or a law/skill/doc section with a
  today-behaviour. Never `memory.py drift`'s code unit (a directory holding code files).
- **Replaces** — the SPEC section naming current behaviours the candidate removes; the prose mirror of the
  DELETE/REBUILD rows.

## 5. Functional requirements

`RELEASE_PY` = `python3 .agents/skills/dd-release-implementation/scripts/release.py`. Every file named
below is the library source under `dadaia_workspace/public/`; projections follow by `public install`.

### FR1 — Definition step 2: the as-is review (`dd-release-definition`)

- AC1.1 The skill's sections read, in order: Pick the set → As-is review → The mandatory grill → Author
  the trio → TASKS as tracer bullets → Declaring consumption → Done when → References; `dd-grill-me`'s two
  `dd-release-definition` §-pointers name the grill's new number.
- AC1.2 The As-is review section states D1: run by `dd-software-engineer`, dispatched by the main thread
  after the set is picked and before the grill; read-only (no write to code, specs or tests); reads each
  touched unit and its ledger slice (`bugs.py status`/`stats`, `git log` on the unit); returns the table in
  its handoff.
- AC1.3 It states D2: the five columns in order, one row per touched unit, consideration order DELETE →
  REBUILD → UPDATE → KEEP, then ADD rows with `today` `—` and a `why` saying why no existing unit can
  carry it.
- AC1.4 It lists D3's four mandatory-REBUILD triggers and one statement that the engineer and the reviewer
  judge them; no script counts bugs or reads code for them.
- AC1.5 It shows the PLAN §1 skeleton once: a `## 1. As-is review` heading and the table with one example
  row carrying a valid As-is verdict.
- AC1.6 Author the trio: PLAN opens with §1 As-is review; SPEC carries `Replaces` (one bullet per current
  behaviour a DELETE/REBUILD row removes, or `none` with its reason); the §3.4 sentence "PLAN names the
  seams the work will cut …" is deleted (Replaces R1).
- AC1.7 TASKS as tracer bullets: tasks realizing DELETE/REBUILD rows precede tasks realizing ADD rows; the
  existing demolition bullet is rewritten to cover every DELETE/REBUILD row (expand–contract), not
  duplicated beside it.
- AC1.8 Done when gains one bullet: PLAN §1 names every unit the picked set touches; SPEC `Replaces` present.
- AC1.9 The SPEC stub `RELEASE_PY new` writes (birth and stacked alike) carries a `Replaces` section
  between Scope and Out of scope; `new` writes no PLAN and still deletes the closed PLAN/TASKS.

### FR2 — `release.py phase IMPLEMENTATION` refuses a PLAN without the as-is table

- AC2.1 Pass: the trio Approved and `PLAN.md` holding a level-2 heading whose text, after an optional
  `N.` prefix, is `As-is review` (case-insensitive), followed before the next level-2 heading by a Markdown
  table whose header cells are `unit | today | bugs | verdict | why` (trimmed, case-insensitive) and ≥ 1
  data row, each row's verdict cell — trimmed of whitespace, `` ` `` and `*` — one of `DELETE REBUILD UPDATE
  KEEP ADD` (case-insensitive) ⇒ the phase moves exactly as today (exit 0, `defined` stamped, one note).
- AC2.2 Refusal — heading missing, heading with no table, a header other than the five columns, or zero
  data rows: exit non-zero, `_RELEASE.json` byte-identical, the message names `PLAN.md` and the missing
  structure, exactly one `fix:` line pointing at `dd-release-definition`'s As-is review section.
- AC2.3 Refusal — a row whose verdict is outside the vocabulary: same exit and `fix:`; the message names
  that row's unit and verdict.
- AC2.4 Structure only: an all-ADD table passes; empty `bugs` and `why` cells pass; the check never
  counts bugs, resolves a unit, reads SPEC `Replaces`, TASKS order or any code. No other new refusal
  anywhere: `phase CLOSURE`, `new`, `memory`, `check` and `dadaia doctor` behave as today.
- AC2.5 The check runs inside the trio admission `phase IMPLEMENTATION` already performs, after the
  Approved check (an unapproved trio refuses first, message unchanged); no flag, no verb, no new file
  under `scripts/`.
- AC2.6 `tests/contract/test_release_script.py` (ADR 0041 `measured_by`) holds, RED before the check:
  the pass case; each AC2.2/AC2.3 refusal; numbered and unnumbered headings; a lowercase verdict; and the
  AC1.5 skeleton extracted from the skill's source text passing the check — the teaching and the gate
  cannot drift (`scaffold-artifacts-fail-own-workflow-gates`).

### FR3 — Review: the spec axis confronts the as-is verdicts with the diff (`dd-code-review`)

- AC3.1 Axis 2 reads PLAN §1 beside SPEC/TASKS; a DELETE or REBUILD unit the reviewed range leaves
  unchanged is a HIGH finding; a KEEP unit the range grew is a finding.
- AC3.2 Axis 2 grows by at most two bullets; the other axes and the six lenses are untouched.

### FR4 — Arm B: a twice-fixed unit is rebuilt (`dd-bug-resolution`)

- AC4.1 `LINEAGE.md` (Phase 0's canonical text) states D8: when the window holds ≥ 2 prior fixes on the
  unit the bug lands in, the fix is a REBUILD of that unit; the commit-body echo block gains
  `rebuild: <unit> — prior fixes <id>, <id>` and `--solution` opens with `REBUILD <unit>:`.
- AC4.2 `SKILL.md` Phase 0 carries one clause pointing at that rule, and its Done-when names the rebuild
  decision (`rebuild` or `none`).
- AC4.3 `bugs.py` is unchanged — no flag, no count, no field.

### FR5 — Law and personas name the step

- AC5.1 Root map (`data/AGENTS.md`) §1 Arm A reads `demand -> backlog -> as-is review -> release
  candidate (SPEC/PLAN/TASKS) -> …`; the §2 `dd-software-engineer` row names the as-is review; no bullet
  is added.
- AC5.2 `scaffold/releases/AGENTS.md`'s lifecycle-order line starts `as-is review -> grill -> SPEC.md
  (Draft) -> …`; this repo's `specs/releases/AGENTS.md` equals its reprojection.
- AC5.3 `agents/dd-software-engineer.md` gains one line: a definition demand runs the as-is review
  read-only per `dd-release-definition` and returns the table in its handoff.
  `agents/dd-product-engineer.md` gains one line: the SPEC's `Replaces` names every behaviour the as-is
  review marks DELETE or REBUILD.
- AC5.4 Every touched law, skill and persona line is a statement (`dd-ai-eng-knowhow` AUTHORING);
  `public stage`, `public install`, `public doctor` and `dadaia doctor` exit 0; `CONTEXT-MAP.md` byte
  columns match and `tests/contract/test_context_map.py` is green.

### FR6 — Terms, dogfood and memory

- AC6.1 `CONTEXT.md` carries §4's four terms, each with its _Avoid_ list; the As-is verdict entry names
  the PR verdict and the finding verdict it must not be confused with.
- AC6.2 This candidate's own PLAN opens with `## 1. As-is review` over the units FR1–FR5 touch and passes
  the FR2 check as built (asserted once by the reviewer at the develop PR).
- AC6.3 The closure memory pass rewrites `release-lifecycle` (the definition arc names the as-is review;
  `phase IMPLEMENTATION`'s new refusal) and reconciles every other atom `memory.py drift` lists;
  `memory.py check` exit 0.

### FR7 — Simplicity (operator standing rule)

- AC7.1 No new file under `dadaia_workspace/` (tests excepted), no new schema, state file, CLI verb,
  flag or doctor code.
- AC7.2 Python growth is confined to the `phase IMPLEMENTATION` trio admission; PLAN §1 justifies it as the
  UPDATE of that unit.
- AC7.3 Every behaviour in §6 is gone in the same change that replaces it: `grep` finds no "PLAN names the
  seams" and no lifecycle-order line starting at `grill`.

## 6. Replaces

- R1 `dd-release-definition` §3.4 "PLAN names the seams the work will cut … what each FR grows or
  deletes" — replaced by the As-is review section and PLAN §1.
- R2 The definition order pick → grill → trio (skill §1→§2→§3, releases law lifecycle line, root map Arm
  A) — replaced by pick → as-is review → grill → trio.
- R3 `phase IMPLEMENTATION` admitting any Approved PLAN whatever its structure — replaced by FR2.
- R4 The demolition-only expand–contract bullet — replaced by the DELETE/REBUILD-before-ADD rule (AC1.7).
- R5 Phase 0 ending at the `caused_by` link — replaced by link plus rebuild decision (FR4).
- R6 The SPEC stub without `Replaces` (AC1.9).
- R7 `dd-grill-me`'s pointers to `dd-release-definition` §2 (AC1.1).

## 7. Acceptance gate

- AC2.6 green; CI green on the develop PR (every job); `dd-code-reviewer` APPROVED with FR3 applied to
  this candidate's own PLAN §1.
- Live instance: `public stage` + `public install` + `public doctor` + `dadaia doctor` exit 0 after every
  library change.

## 8. Out of scope (non-goals)

- Automated bug counting, code analysis, trigger detection, unit resolution.
- A new file, schema, state, verb, flag or doctor rule; any check of SPEC `Replaces`, TASKS order or
  `why` content; gating anything outside `release.py`'s own documents.
- A PLAN stub; retrofitting closed candidates' PLANs; `dd-manager-orchestration` text; any CI job.

## 9. Risks and dependencies

- The instance's projected `release.py` changes only at `public install`: this candidate's own
  `phase IMPLEMENTATION` runs the pre-change script; AC6.2 is verified by the reviewer, not by that run.
- ADR 0041 `measured_by` names `tests/contract/test_release_script.py`, a path that does not exist yet;
  AC2.6 creates it. The existing `tests/unit/skills/test_release_implementation_release_script.py` keeps
  its cases.
- A content-judging creep in the check reopens the lifecycle-gate bug loop (§1); AC2.4 is the fence.
- c3 and c4 are defined after this candidate closes and are the first to pass the new check.

## 10. Traceability

| FR | Decisions / replaces | Surface |
|---|---|---|
| FR1 | D1 D2 D3 D4 D5 · R1 R2 R4 R6 R7 | `dd-release-definition`, `dd-grill-me`, `_release_new.py` stub |
| FR2 | D6 · R3 | `_release_phase.py` trio admission, `tests/contract/` |
| FR3 | D7 | `dd-code-review` Axis 2 |
| FR4 | D8 · R5 | `dd-bug-resolution` `LINEAGE.md`, `SKILL.md` |
| FR5 | D9 · R2 | `data/AGENTS.md`, `scaffold/releases/AGENTS.md`, two personas |
| FR6 | terms, dogfood, closure | `CONTEXT.md`, PLAN §1, `release-lifecycle` atom |
| FR7 | standing rule | all |
