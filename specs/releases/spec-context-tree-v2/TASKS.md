# TASKS — Release: spec-context-tree-v2

**Status:** Aprovado
**Release ID:** spec-context-tree-v2
**Owner:** product-engineer
**Opened:** 2026-05-30

> **Activation gate:** Implementation must NOT begin until `go-open-source` phase = ARCHIVED
> and SPEC.md + PLAN.md both have `**Status:** Aprovado`.

---

## T-1 — Remove `foundation/` from scaffold; service.py:119 fallback cleanup

**Owner:** [software-engineer-python]
**Depends on:** none (Wave 1 — independent)
**SPEC cluster:** §3 T-1

Delete `dadaia_workspace/public/scaffold/foundation/` and its contents. Remove the
`"foundation"` entry from the fallback subdirectory list at
`features/spec_context/service.py:119`. Doctor invariant TREE-1 is wired in T-9 (not
here). Migration behaviour (`dadaia migrate tree-v2` moves `foundation/` content to
`releases/legacy/foundation/`) is also implemented here as part of the `dadaia migrate
tree-v2` command — see SPEC §4 for the full migrate spec.

**Done criterion:** AC-T1-1 (scaffold has no `foundation/`), AC-T1-2 (service.py has no
`"foundation"` in fallback list), AC-T1-4 (`dadaia migrate tree-v2` idempotently moves
`foundation/` content). AC-T1-3 (doctor TREE-1) is verified in T-9.

[x] T-1

---

## T-2 — Scaffold memory as HTML; drop markdown memory files

**Owner:** [software-engineer-python]
**Depends on:** none (Wave 1 — independent; OQ-4 resolution confirmed before starting)
**SPEC cluster:** §3 T-2

Remove `dadaia_workspace/public/scaffold/memory/architecture.md`,
`memory/tech-stack.md`, and `memory/product.md`. Add
`scaffold/memory/architecture.html` and `scaffold/memory/tech-stack.html` as static
pre-rendered stubs (rendered from the canonical Jinja templates by `dadaia public stage`;
committed as static HTML). Confirm with the stage pipeline that the Jinja step handles
these new stubs cleanly (OQ-4 resolution).

**Done criterion:** AC-T2-1 (architecture.html and tech-stack.html exist as valid HTML
after scaffold), AC-T2-2 (no `*.md` under `specs/memory/` after scaffold). AC-T2-3
(doctor TREE-3 auto-fix) is verified in T-9.

[x] T-2

---

## T-4 — Scaffold `backlog/`, `bugs/`, `releases/` with README and `.gitkeep`

**Owner:** [software-engineer-python]
**Depends on:** none (Wave 1 — independent; T-3 and T-7 depend on this)
**SPEC cluster:** §3 T-4

Add to `dadaia_workspace/public/scaffold/`: `backlog/README.md` (authoring rules for
backlog entries), `backlog/.gitkeep`, `bugs/README.md` (authoring rules for bug reports),
`bugs/.gitkeep`, `releases/README.md` (authoring rules for release directories),
`releases/.gitkeep`. Doctor TREE-4 auto-fix (recreates missing directories) is wired in T-9.

**Done criterion:** AC-T4-1 (all three directories with README.md and .gitkeep present
after scaffold), AC-T4-3 (command does not recreate directories that already exist).
AC-T4-2 (doctor TREE-4) is verified in T-9.

[x] T-4

---

## T-6 — Deprecate root `specs/SPEC.md`; remove from scaffold; doctor warn + migrate auto-fix

**Owner:** [software-engineer-python]
**Depends on:** none (Wave 1 — independent)
**SPEC cluster:** §3 T-6

Remove `dadaia_workspace/public/scaffold/SPEC.md`. Implement the `dadaia migrate tree-v2`
action for root SPEC.md: move to `releases/legacy/SPEC.md` (or add timestamp suffix if
destination already exists), per SPEC §4. Doctor TREE-2 (warn-only, `fixable=False`) is
wired in T-9.

**Done criterion:** AC-T6-1 (root SPEC.md absent after scaffold), AC-T6-3 (TREE-2 is
warn-only; `doctor --fix` does NOT move the file), AC-T6-4 (`dadaia migrate tree-v2`
moves root SPEC.md to `releases/legacy/` atomically). AC-T6-2 (doctor TREE-2) is
verified in T-9.

[x] T-6

---

## T-8a — Gate cleanup: remove legacy root-TASKS.md fallback path

**Owner:** [software-engineer-python]
**Depends on:** none (Wave 1 — independent)
**SPEC cluster:** §3 T-8a

Remove any fallback in `dadaia_workspace/public/scripts/sdd-spec-gate.sh` that looks
for `TASKS.md` at the spec tree root (paths matching `$PRIMARY_SPECS/TASKS.md`). The
gate must only search in `$PRIMARY_SPECS/releases/<active-release-id>/TASKS.md`. Do NOT
change the gate's primary context resolution logic (still reads `primary_context.json`
— context resolution changes belong to T-13 in R2).

**Important cross-reference:** T-8a is the first half of the full per-release gate
(ADR D-9). T-13 in `spec-context-session-locks-v1` completes it by rewriting context
resolution to use the implementation lock. T-13 depends on T-8a having shipped.

**Done criterion:** AC-T8a-1 (gate contains no root-level TASKS.md path pattern),
AC-T8a-2 (existing gate integration tests pass), AC-T8a-3 (new test
`test_gate_resolves_active_release_tasks` passes), AC-T8a-4 (new test
`test_gate_blocks_when_active_release_has_no_task` passes).

[x] T-8a

---

## T-3 — Mandatory `memory/product/index.html`; `dadaia memory product add <slug>` CLI

**Owner:** [software-engineer-python]
**Depends on:** T-4 (scaffold `releases/` directory must exist before product catalog
scaffold is wired)
**SPEC cluster:** §3 T-3

Add `dadaia_workspace/public/scaffold/memory/product/index.html` rendered from
`memory-product-index.html.j2` (placeholder catalog, zero features). Remove the
monolithic `memory/product.md` if it still exists after T-2. Implement new CLI subcommand
`dadaia memory product add <slug>` that: (1) creates `specs/memory/product/<slug>.html`
from `memory-product-feature.html.j2`; (2) regenerates `specs/memory/product/index.html`
deterministically (lexicographic order; idempotent). Doctor TREE-3 auto-fix for
`product/index.html` is wired in T-9.

**Done criterion:** AC-T3-1 (index.html exists post-scaffold with empty catalog), AC-T3-2
(`dadaia memory product add payments` creates feature HTML and updates index), AC-T3-3
(idempotent index regeneration). AC-T3-4 (doctor TREE-3 auto-fix) is verified in T-9.

[x] T-3

---

## T-5 — New template `specs/AGENTS.md` (SDD workflow contract)

**Owner:** [software-engineer-python]
**Depends on:** none (Wave 2 — can proceed in parallel with T-3, T-7)
**SPEC cluster:** §3 T-5

Add `dadaia_workspace/public/templates/specs-AGENTS.md` — new canonical template
describing the SDD workflow contract for the spec tree. Add
`dadaia_workspace/public/scaffold/AGENTS.md` as the scaffolded version rendered from the
template. This file is DISTINCT from the repo-root `AGENTS.md` (which is lib-originated
and describes all agents). Doctor TREE-5 (drift detection, warn-only, no auto-overwrite)
is wired in T-9.

**Done criterion:** AC-T5-1 (specs/AGENTS.md exists post-scaffold with content matching
canonical template), AC-T5-5 (distinct from repo-root AGENTS.md). TREE-5 tests
(AC-T5-2..T5-4) are verified in T-9.

[x] T-5

---

## T-7 — New CLI: `dadaia release new`, `dadaia backlog new`, `dadaia bug new`

**Owner:** [software-engineer-python]
**Depends on:** T-4 (`backlog/`, `bugs/`, `releases/` directories must exist in scaffold
before CLI commands target them)
**SPEC cluster:** §3 T-7

Implement three new CLI subcommands: `dadaia release new <id>` creates
`specs/releases/<id>/SPEC.md` stub with canonical frontmatter (validates slug matches
`^[a-z][a-z0-9-]+$`; exits non-zero if directory exists); `dadaia backlog new <slug>`
creates `specs/backlog/<slug>.md` with canonical frontmatter stub; `dadaia bug new
<slug>` creates `specs/bugs/<slug>.md` with `session_id: null` (does NOT block on absent
`DADAIA_SESSION_ID` — that is R2). Also implement `dadaia memory product add` here if
it was not already delivered in T-3.

**Done criterion:** AC-T7-1..AC-T7-5 (all CLI acceptance criteria from SPEC §3 T-7).
AC-C-1..AC-C-7 from SPEC §7.3.

[x] T-7

---

## T-9 — Doctor TREE-1..TREE-7 invariants

**Owner:** [software-engineer-python]
**Depends on:** T-1, T-2, T-3, T-4, T-5, T-6, T-8a (all Wave 1 + Wave 2 tasks must be
committed before wiring invariants)
**SPEC cluster:** §3 T-9

Add `TreeDoctorService` (or extend `DoctorService`) implementing seven invariants per
the table in SPEC §3 T-9: TREE-1 (foundation/ warn-only), TREE-2 (root SPEC.md
warn-only), TREE-3 (missing memory HTML auto-fix), TREE-4 (missing backlog/bugs/releases
auto-fix), TREE-5 (AGENTS.md drift-detect warn-only), TREE-6 (release dir missing
mandatory SDD artifact no-fix), TREE-7 (bug slug missing session_id frontmatter no-fix).
Implement the loud migration guard for TREE-1 and TREE-2 (printed regardless of `--fix`
flag). All fix policies must match the table in SPEC §3 T-9.

**Done criterion:** AC-T9-1..AC-T9-16 (14 invariant tests + 2 integration tests). Also
confirms AC-D-15 (`dadaia doctor` exits 0 on fresh scaffold) and AC-D-16 (exits 0 on
dadaia-workspace repo itself).

[x] T-9

---

## T-QA — TREE invariant tests, gate tests, onboarding E2E

**Owner:** [qa-engineer]
**Depends on:** T-9 (all TREE invariants implemented), T-8a (gate change committed)
**SPEC cluster:** §7 (AC-D, AC-G, AC-O)

Write and run the full test suite per QA strategy (`.dadaia/reports/dadaia-workspace/
qa-engineer/2026-05-30T120000Z-test-strategy-spec-context-v2.html` §4.2 and §5):
14 TREE invariant tests (2 per invariant; violating fixture + expected post-fix state);
AC-G-1..G-8 gate integration tests; AC-O-1 onboarding end-to-end test (`dadaia init →
context create → context activate → dadaia specs doctor` exits 0). All tests must run on
real `tmp_path` filesystem (no mocks that hide tree shape). Report green CI run as
evidence.

**Done criterion:** `poetry run pytest` green, all AC-D-1..D-16, AC-G-1..G-8, AC-O-1
pass. Coverage unchanged or improved.

[ ] T-QA

---

## T-DEVOPS — Propagate scaffold and script changes

**Owner:** [devops-engineer]
**Depends on:** T-QA (must be green before propagation)
**SPEC cluster:** §10.1 (dependencies — `dadaia public stage`)

Run `dadaia public stage && dadaia public install --target all` after all Wave 1-3
tasks are committed and the test suite is green. Verify `dadaia public doctor` exits 0.
This propagates the updated scaffold, templates, and gate script to all runtime
projections (`.claude/`, `.codex/`, `.opencode/`).

**Done criterion:** `dadaia public doctor` exits 0. No `[drift]` or `[missing]` entries.

[ ] T-DEVOPS

---

## Cross-release note

**This release (R1) is a prerequisite for `spec-context-session-locks-v1` (R2).** R2
implementation must NOT begin until R1 phase = ARCHIVED. Both R1 and R2 wait for
`go-open-source` to close and `ACTIVE.md` to be freed before entering IMPLEMENTATION.
