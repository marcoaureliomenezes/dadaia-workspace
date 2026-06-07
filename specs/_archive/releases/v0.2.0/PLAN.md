# PLAN: v0.2.0 — Agentic Development Lifecycle

**Status:** Aprovado
**Release ID:** v0.2.0
**Owner:** product-engineer
**Created:** 2026-06-06

---

## Strategy

Five sequenced milestones on a single `feature/0.2.0` branch. Milestones v0.1.6–v0.1.9
are workspace-internal checkpoints (no PyPI publish, no tag). Only v0.2.0 deploys.
Each milestone is fully implemented, test-green, gate-reviewed (qa→commit,
security→push, code-review→PR where required), and operator-validated in the
instantiated workspace before the next milestone opens.

Order rationale:
- **v0.1.6 first** — the lock/gate is the only thing that can deadlock the toolchain.
  Fix it before touching any persona or surface file. Every later milestone depends
  on agents that must not deadlock.
- **v0.1.7 second (THE FREEZE)** — encode the lifecycle law and memory canon before
  writing a single persona line. This is cheap and eliminates the "build-then-change"
  thrash that caused three rewrites.
- **v0.1.8 third** — personas are authored exactly once, against frozen constitution.
  No rewrite possible because the law is already committed.
- **v0.1.9 fourth** — surface cleanup once roster is final. Deleting a workflow before
  its final referencing persona is known creates dangling references.
- **v0.2.0 last** — integration + drift-elimination + single deploy after the whole
  lifecycle is dogfooded end-to-end on this instance.

---

## Milestone v0.1.6 — State model (foundation)

**Objective:** Replace the four-store lock model with one cross-platform JSON TTL-lease
per context. Collapse `sdd-spec-gate.sh` from ~1050 to ~150 lines. Eliminate the
soft-deadlock root cause. Deliver the gate foundation every later milestone requires.

**Module-level change map:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/spec_context/lease.py` (NEW) | Single-record module: `acquire/heartbeat/release/is_held/read`; `O_EXCL` CAS on acquire; injectable clock; ~120 lines |
| `dadaia_workspace/core/` | `is_stale(data, *, clock, pid_probe, session_exists)` predicate; zero direct `datetime.now()` in hot path |
| `dadaia_workspace/features/spec_context/locking.py` | Delete Lock-3 functions (~346 lines); keep fcntl Lock-1/Lock-2 wrappers untouched |
| `dadaia_workspace/features/spec_context/semaphore.py` | Retire entirely; three good primitives migrated to `lease.py` / `core/` |
| `dadaia_workspace/features/spec_context/service.py` | Integrate lease acquisition on first MUTATING write; GC on `context show/list` |
| `dadaia_workspace/features/spec_context/doctor.py` | LOCK-2..LOCK-7 checks → single-record invariant; `--fix` actually deletes expired records + `.dadaia/sessions/` orphans |
| `dadaia_workspace/cli/commands/context.py` | Remove semaphore acquisition on `context bind`; add `dadaia lock steal <ctx>` command |
| `dadaia_workspace/public/scripts/sdd-spec-gate.sh` | Collapse to ≤175 lines; path-classifier (ADDITIVE/MEMORY/FROZEN/MUTATING); delete RULE E; demote RULE C to PostToolUse WARN; RULE D → pre-compiled `agents.index.json` lookup |
| `tests/unit/features/spec_context/test_lease*.py` (NEW) | ~35 unit tests: `is_stale` branch table, 8-row fail-safe property, activity-class exemption table |
| `tests/integration/` | ADDITIVE-while-MUTATING smoke test; doctor GC test |
| `tests/e2e/` | Exactly 1 real two-process denial (file-based rendezvous, `tmp_path`, no sleep); move existing threading.Barrier test out of `tests/unit/` |

**Dependency:** none — this is the foundation milestone.

**Test strategy:**
- Unit: injectable clock via `FakeClock`; `_before_write` hook for TOCTOU interleave
  simulation (sequential, no real threads); `FakeProcessProbe` for pid-probe seam.
- Integration: real `tmp_path`; doctor GC verifies stale record deleted; one hook smoke
  confirming ADDITIVE write allowed while MUTATING lease held by different session.
- E2E (exactly 1): real two-process denial; file-based rendezvous (not sleep, not
  repo-root); replaces the existing `threading.Barrier` test.
- Activity-class exemption table: each of MUTATING/ADDITIVE/MEMORY/FROZEN crossed with
  each lease-state (absent, live-mine, live-other, expired) — 16 combinations, all
  expected outcomes documented as test assertions.
- Fail-safe property: for every possible input state, the gate produces one of {allow,
  actionable-error, never-unhandled-exception} — no silent failure, no unblock-less block.
- fcntl Lock-1/Lock-2 existing tests must remain passing (zero regression).

**In-workspace validation (operator):**
Operator drives one full mutate→edit→commit cycle on the live instance. Operator then
forces a stale-lease condition (edit `heartbeat` field to expired timestamp) and runs
`dadaia lock steal dadaia-workspace` to confirm unblock. `dadaia doctor --fix` exits 0
and shows zero expired records afterward. The soft-deadlock scenario (two independent
sessions both attempt MUTATING write) is reproducible only with a live second session —
confirmed unreproducible in normal single-session use.

---

## Milestone v0.1.7 — Constitution v2 + lifecycle law + memory canon (THE FREEZE)

**Objective:** Encode the §3 matrix, §4 coordinator/sub-agent architecture, the anti-slop
law, the review-gate sequence, and the memory canon as binding constitutional law before
any persona or workflow is touched. Create `quality-assurance.md` memory atom (absorbing
`test-suite-architecture.md`). This milestone is document-only — no Python code.

**Module-level change map:**

| File | Change |
|------|--------|
| `specs/constitution.md` | Major revision: add §Anti-Slop, §Canonical Lifecycle (matrix verbatim), §Agent Roster (9 named), §Activity-Class Lock Contract, §Review-Gate Sequence, §Memory Canon; cross-harness honesty §4 updated |
| `specs/memory/product/quality-assurance.md` (NEW) | New memory atom: absorbs `test-suite-architecture.md`; all 6 required sections (Propósito, Fluxo de uso, Trigger típico, Diferencial, Estado runtime tocado, Dependências) |
| `specs/memory/product/index.md` | Add catalog entry for `quality-assurance.md` |
| `specs/memory/product/test-suite-architecture.md` | Stage for `git mv` to `specs/_archive/legacy-memory/<timestamp>/` (actual move at CLOSURE per gate rules) |

**Dependency:** v0.1.6 must be committed. Constitution cites the ratified lock model (OQ-1..4
from design proposal) as implemented fact, not aspiration. If v0.1.6 implementation
deviates from OQ-1..4, constitution must be updated before v0.1.7 ships.

**Authoring constraint:** Constitution author cites ratified decisions verbatim — no
editorialization, no new lease mechanics beyond OQ-1..4. Any constraint not in the
v0.1.6 implementation is forbidden. The §1 matrix is copy-paste from the roadmap; edits
are constitution violations.

**Test strategy:** No Python test changes. `dadaia specs doctor` memory-canon checks
serve as acceptance. Constitution diff reviewed by qa-engineer for verbatim compliance.

**In-workspace validation (operator):**
Operator reads the updated constitution and confirms: §1 matrix matches lived workflow;
the 9-agent roster is named; review-gate sequence (qa→commit, security→push,
code-review→PR) matches how gates actually run on this instance. `dadaia specs doctor`
passes memory-canon checks, including `quality-assurance.md` atom structure.

---

## Milestone v0.1.8 — Coordinator + sub-agent architecture + roster 15→9

**Objective:** Author all 9 core personas against the frozen v0.1.7 constitution. Each
persona declares its activity class, lease relationship, and gate role. Reduce roster
from 15 to 9 core. Frontend/design + devops become plugins. Coordinators deepened.

**Module-level change map:**

| File | Change |
|------|--------|
| `dadaia_workspace/public/agents/software-engineer.md` (NEW) | Generic implementer; MUTATING, PM subagent; TDD + SDD lifecycle wired |
| `dadaia_workspace/public/agents/software-engineer-python.md` | DELETE |
| `dadaia_workspace/public/agents/software-engineer-node.md` | DELETE |
| `dadaia_workspace/public/agents/backend-engineer.md` | DELETE |
| `dadaia_workspace/public/agents/researcher.md` | DELETE |
| `dadaia_workspace/public/agents/project-manager.md` | Deepen: model=`claude-opus-4-8`, lease-coordinator, grill-mandatory, dispatch logic, §1 position |
| `dadaia_workspace/public/agents/product-engineer.md` | Deepen: backlog-consumer explicit, memory guardian (DEFINITION+CLOSURE), §1 position |
| `dadaia_workspace/public/agents/project-auditor.md` | Deepen: ADDITIVE, peer, no-lease, §1 position |
| `dadaia_workspace/public/agents/ai-engineer.md` | Deepen: surface owner, MUTATING under PM lease during releases, own short MUTATING session ad-hoc, §1 position |
| `dadaia_workspace/public/agents/qa-engineer.md` | Sharpen: gate pre-commit, ADDITIVE evidence, §1 position |
| `dadaia_workspace/public/agents/security-reviewer.md` | Add §1 position (gate pre-push) |
| `dadaia_workspace/public/agents/code-reviewer.md` | Add §1 position (gate pre-PR) |
| `dadaia_workspace/public/agents/software-architect.md` | Strip dangling skill refs (`architect-code-audit`, `architect-design-patterns`) |
| `dadaia_workspace/public/agents/frontend-engineer.md` | Move to plugin stub; strip from core |
| `dadaia_workspace/public/agents/design-specialist.md` | Move to plugin stub |
| `dadaia_workspace/public/agents/devops-engineer.md` | Move to plugin stub; strip dangling skill refs |
| `dadaia_workspace/public/rules/plugin-scope.md` | Update named plugin set |
| `dadaia_workspace/public/skills/` | Remove 5 frontend/design skills + slop skill refs |
| `specs/bugs/agent-skill-surface-slop.md` | Annotate `adopted: v0.2.0` |
| `specs/bugs/semaphore-no-liveness-reclaim.md` | Annotate `superseded_by: v0.2.0/v0.1.6` |

**Dependency:** v0.1.7 must be committed. Personas cite the frozen constitution; if
constitution is uncommitted, personas cite an un-ratified document. Deployment ordering:
after this milestone renames `software-engineer-python` → `software-engineer`, the gate
fails-open for the new persona name until this milestone installs — fail-open is
acceptable (documented in SPEC §5).

**Test strategy:** No new Python unit tests for persona Markdown files. `dadaia public doctor`
exit-0 check is the acceptance gate. If any persona has a broken skill reference, doctor
flags it. After `dadaia public stage && install --force --target all`, all runtimes
(`.claude/`, `.agents/`, `.opencode/`, `.codex/`) reflect the 9-agent surface.

**In-workspace validation (operator):**
Operator runs a small end-to-end demand through PM: grill → backlog → SPEC definition →
implementation under one lease → review gates. Confirms no lock friction, no dangling
skill refs, and the coordinators navigate the full lifecycle from their personas without
operator narration. `dadaia public doctor` exits 0. 9 agents enumerable in all runtimes.

---

## Milestone v0.1.9 — Skills cleanup + workflow redesign + product/ tree

**Objective:** Delete the 7 stale workflows. Author `release-ship` + `audit-fanout`
(OD-1 resolution). Restructure `product/` memory tree into thematic subdirectories.
Prune skills 22→17 (5 frontend/design already removed in v0.1.8; remaining 0 stale).
Manifest + doctor reconcile on all runtimes.

**Module-level change map:**

| File | Change |
|------|--------|
| `dadaia_workspace/public/workflows/audit-cycle.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/code-review-fan-out.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/design-first-implementation.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/hotfix-release.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/spec-refinement.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/onboarding-new-repo.workflow.md` | DELETE |
| `dadaia_workspace/public/workflows/release-ship.workflow.md` (NEW) | Deploy gate sequence: merge → release-gate-approval → PyPI + tag |
| `dadaia_workspace/public/workflows/audit-fanout.workflow.md` (NEW) | Deterministic audit dispatch sequence |
| `dadaia_workspace/public/skills/` | Confirm exactly 17 skills; remove any remaining stale entries |
| `specs/memory/product/` | Restructure into thematic subdirs per OD-3 (`agents/`, `sdd/`, `panel/`, `platform/`, `distribution/`, `philosophy/`); update `index.md` wikilinks |
| `specs/memory/product/index.md` | Updated catalog, capability-map (Mermaid), wikilinks |

**Dependency:** v0.1.8 must be committed and roster must be final. No workflow can be
deleted before confirming no v0.1.8-authored persona references it (doctor D-OC-1 check
is the precondition gate for workflow deletions). `product/` tree restructure depends on
v0.1.7 `quality-assurance.md` existing (it enters the tree).

**Test strategy:** No new Python tests. Doctor D-OC-1 check (no dangling workflow
references in personas) must pass before deletions. `dadaia public stage && install
--force --target all && doctor` exits 0 on all runtimes. Memory tree: `dadaia specs
doctor` validates broken-image + wikilink checks post-restructure. 17-skill count
verified by doctor enumeration.

**In-workspace validation (operator):**
Operator inspects the reduced surface (9 agents / 17 skills / 2 new workflows). Browses
the `product/` tree and confirms it is navigable by a human. Runs a fresh-init parity
check (`dadaia init` on a temp dir) to confirm the default projection emits only the 9
core agents and not the plugin stubs. `dadaia public doctor` and `dadaia specs doctor`
both exit 0.

---

## Milestone v0.2.0 — Integration, drift-elimination, single deploy

**Objective:** Integrate all milestones on `feature/0.2.0`. Bump `pyproject` to `0.2.0`.
Dogfood the entire lifecycle end-to-end on this instance. Eliminate all drift.
Ship-trio approves. Single deploy: merge → PyPI + tag v0.2.0.

**Module-level change map:**

| File | Change |
|------|--------|
| `pyproject.toml` | Version bump to `0.2.0` |
| `dadaia_workspace/` | Integration validation: `pytest -p no:cacheprovider` full suite passes |
| `.claude/`, `.agents/`, `.opencode/`, `.codex/` | `dadaia public install --target all` + `dadaia public doctor` exit 0; no drift |
| `specs/memory/` | CLOSURE memory updates: `architecture.md`, affected `product/**` atoms |
| `specs/releases/v0.2.0/CLOSURE.md` | Closure with evidence triples |

**Dependency:** All milestones v0.1.6–v0.1.9 committed and operator-validated on
`feature/0.2.0`. No skip; the in-workspace validations are the per-milestone gates.

**Integration + drift-elimination approach:**
1. Run `dadaia public install --target all` and `dadaia public doctor` to confirm all
   four runtimes reflect the final 9-agent / 17-skill surface with no drift.
2. Run `dadaia specs doctor` to confirm memory canon, no orphan atoms, no broken links.
3. Run `pytest -p no:cacheprovider` full suite — must pass.
4. Dogfood: operator runs a complete demand through the lifecycle (PM intake → grill →
   backlog → SPEC → PLAN → TASKS → implement → qa gate → security gate → code-review gate
   → CLOSURE → archive) on the live instance with the new v0.2.0 surface.
5. Operator confirms zero lock friction throughout.
6. Ship-trio (qa-engineer + security-reviewer + code-reviewer) all APPROVE the final rc.
7. Single deploy: merge `feature/0.2.0` → `main` → tag `v0.2.0` → PyPI publish.

---

## Technical risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Gate-path migration (`*.semaphore.json` → `*.lock.json`) must be one atomic commit | HIGH | Single-commit rule; `lease.py` must exist before gate migration commit |
| v0.1.7 constitution author editorializes beyond OQ-1..4 | HIGH | Explicit constraint: cite verbatim; gate-review by qa confirms no new lease mechanics |
| v0.1.8 persona renames leave dangling refs in v0.1.9 workflow deletions | MEDIUM | Doctor D-OC-1 is a hard precondition gate before any v0.1.9 workflow deletion |
| v0.1.9 `product/` tree restructure breaks wikilinks | MEDIUM | `dadaia specs doctor` broken-link check after restructure; fix before gate |
| E2E two-process test flakiness | LOW | File-based rendezvous (not sleep); `tmp_path` only |
| `dadaia public install --force` on v0.2.0 clobbers locally-diverged projections | LOW | Doctor exit 0 is the acceptance gate; diverged projections are by-design replaced |

---

## Validation plan (per milestone)

| Milestone | Validation | Evidence |
|-----------|------------|---------|
| v0.1.6 | `pytest -p no:cacheprovider` suite green; gate ≤175 lines; ADDITIVE-while-MUTATING integration passes; TOCTOU blocked | commit SHA + `wc -l` |
| v0.1.6 | Operator: mutate→stale→steal cycle; doctor GC exit 0 | operator sign-off |
| v0.1.7 | `dadaia specs doctor` memory-canon checks pass; constitution §1 matrix verbatim | doctor output + handoff |
| v0.1.7 | Operator reads constitution; confirms it matches lived workflow | operator sign-off |
| v0.1.8 | `dadaia public doctor` exit 0; 9 agents enumerable all runtimes; doctor D-OC-1 no dangling refs | doctor output |
| v0.1.8 | Operator: E2E demand through PM, no lock friction | operator sign-off |
| v0.1.9 | Doctor exit 0; 7 stale workflows absent; exactly 17 skills; product/ tree valid | doctor output |
| v0.1.9 | Operator: fresh-init parity check | operator sign-off |
| v0.2.0 | Full pytest suite + doctor exit 0 + ship-trio APPROVE | handoff JSONs |
| v0.2.0 | Operator: full lifecycle dogfood, zero lock friction | operator sign-off → deploy |
