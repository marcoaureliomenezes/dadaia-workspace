# Closure: Release — orchestration-consolidation-v1

> **Status:** Aprovado
> **Release ID:** orchestration-consolidation-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-29

## Summary

This release completed the workflow→PM-playbook migration that `agents-r2-v1` left
half-done. Before this release the operator could not rely on the orchestration layer
for its most common routes: `project-manager.md` Step-4 stopped and escalated whenever
a workflow file was missing, and six of the thirteen routes in Step-3 had no file on
disk — they existed only as prose playbooks in `project-orchestration/SKILL.md`. The
orchestrator dead-ended on itself. Three independent registries (PM router, SKILL.md
inventory, SKILL.md playbook section) contradicted each other, and the backlog carried
a `dashboard-publication-workflow-v1` bullet for a file that already existed on disk.

The ruling that shaped this release — Decision C ("principled hybrid, file-iff-X") —
was validated by a 4-lens panel before any code was written. Under this ruling, a
coordination pattern earns an engine-backed `*.workflow.md` file only when it has a
multi-party `parallel_group` topology, a non-optional operator-approval gate sequence,
or enforced cross-surface named input contracts. Everything else becomes a PM Playbook.

What shipped: a two-tier PM router (7 engine-backed workflows via `dadaia orchestrate
run`; everything else a PM Playbook composed inline); three contradictory registries
collapsed to one source of truth; 5 patterns folded or added as playbooks under a
mandatory 7-field schema (Trigger / Entry / Input contract / Steps / Gate / Stop
conditions / Done when); a self-contradiction in `cross-cutting-feature.workflow.md`
fixed (YAML field `discovery.agent` and prose step-1 now both say `product-engineer`);
and a new bidirectional drift-gate invariant (`D-OC-1`) with unit tests that makes the
three-registry divergence structurally impossible to reintroduce. The operator's
interface is plain-language only — the PM grills, classifies, auto-reserves task_ids,
and either composes a playbook or calls `dadaia orchestrate run` with inputs it
populates itself.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-OCV-01 | Rewrite `project-manager.md` Step-3 + Step-4: two-tier router + operator UX contract | `2e02eef` |
| T-OCV-02 | Reconcile SKILL.md Workflow Inventory to 7 rows; remove duplicate spec-refinement entry; preserve scope=game content | `c90a2f1` |
| T-OCV-03 | Add 5 PM Playbook sections with mandatory 7-field schema; retrofit existing playbooks | `e1a924c` |
| T-OCV-04 | Fix `cross-cutting-feature.workflow.md` self-contradiction — YAML + prose both → `product-engineer` | `35946cd` |
| T-OCV-05a | Write D-OC-1 design note (parsing logic, rule statement, error format) as `D-OC-1-design-note.md` | `eab42cb` |
| T-OCV-05b | Backlog cleanup: delete stale `dashboard-publication-workflow-v1` bullet; move 3 workflow bullets to Histórico | `eab42cb` |
| T-OCV-06b | Implement bidirectional `D-OC-1` invariant in `dadaia_workspace/features/specs/doctor.py` | swept into closure commit |
| T-OCV-07 | Write unit test `tests/test_orchestration_registry.py` — 4 cases (all-correct, forward-missing-file, forward-missing-heading, reverse-orphan) | swept into closure commit |
| T-OCV-08 | Full propagation: pytest → stage → install → public doctor → git diff scope check | swept into closure commit |
| T-OCV-09 | Playbook round-trip acceptance (Tier-2 bug-fix-fastlane → software-engineer-python; no operator-supplied pattern name or task_id) | swept into closure commit |
| T-OCV-10 | Engine-backed round-trip acceptance (Tier-1 cross-cutting-feature; PM-derived `dadaia orchestrate run` call) | swept into closure commit |

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green | `poetry run pytest` | `1963 passed, 0 failed, 1 skipped, 1 xpassed, 89.47% cov in 993s` |
| specs doctor incl. bidirectional D-OC-1 | `poetry run dadaia specs doctor` | `[ok] 0 errors, 0 warnings` |
| D-OC-1 unit tests (4 cases) | `poetry run pytest tests/test_orchestration_registry.py` | `4 passed` (forward-missing-file, forward-missing-heading, reverse-orphan, all-correct) |
| public doctor (projection sync) | `poetry run dadaia public doctor` | `exit 0, 0 drift / 0 missing` |
| Public diff scope (AC-OC-13) | `git diff --stat 45f2cd9..HEAD -- dadaia_workspace/public/` | 3 files changed: `project-manager.md`, `project-orchestration/SKILL.md`, `cross-cutting-feature.workflow.md` |
| Lint and type checks | `ruff check` + `ruff format --check` + `mypy --strict` (touched files) | all green |
| Playbook round-trip AC-OC-16 | qa-engineer validation | PASS — `.dadaia/reports/dadaia-workspace/project-manager/2026-05-29T120000Z-T-OCV-09-intake.html` (Tier-2 bug-fix-fastlane → software-engineer-python; operator supplied no workflow name / no task_id) |
| Engine-backed round-trip AC-OC-17 | qa-engineer validation | PASS — `.dadaia/reports/dadaia-workspace/project-manager/2026-05-29T120100Z-T-OCV-10-dispatch.html` (Tier-1 cross-cutting-feature; PM-derived `dadaia orchestrate run`; operator supplied no workflow name) |

---

## Drifts

### plan-length-overflow

**Description:** The D-OC-1 design note (T-OCV-05a) was appended inline to PLAN.md as
originally planned, pushing PLAN.md to 471 lines — exceeding the 300-line limit enforced
by `SPEC-DOC-005`. For releases created on or after 2026-05-17 this is a hard error.
`dadaia specs doctor` flagged it immediately after the append.

**Resolution:** The design note was relocated to a sibling file
`specs/releases/orchestration-consolidation-v1/D-OC-1-design-note.md`. PLAN.md was
trimmed to 275 lines by removing the appended section. Doctor returned green.

**Memory updates:** None — this was a process artifact in the release directory, not a
product memory concern.

### implementer-turn-exhaustion

**Description:** Both `software-engineer-python` (T-OCV-06b/07) and `devops-engineer`
(T-OCV-08) exhausted their turn budget mid-task during the 16.5-minute full suite run,
before flipping task markers to `[x]` or summarising their work. The task list was left
with `[-]` markers and a few untracked loose ends (SPEC.md, test file, design note) when
each agent's session was interrupted.

**Resolution:** The orchestrator independently verified all success conditions (tests
green, ruff clean, mypy clean, doctors green) and closed the `[-]` markers to `[x]`.
The loose ends were consolidated in the closure commit to keep the working tree clean.

**Memory updates:** None.

### acceptance-subagent-mode

**Description:** The PM acceptance round-trips (T-OCV-09, T-OCV-10) ran with PM as a
sub-agent, which cannot nested-dispatch leaf agents under the single-entry-point rule.
This meant no live leaf execution occurred during the acceptance test — only PM's intake
and dispatch reports were produced.

**Resolution:** AC-OC-16 and AC-OC-17 explicitly validate the PM's intake/dispatch
reports (routing + derivation correctness), which is exactly what was produced and
qa-validated. Live leaf execution is out of scope for the acceptance criteria. This is
not a gap — the routing and derivation logic is what needed validation, not the leaf
agent's behaviour (which is covered by its own tests).

**Memory updates:** None.

---

## Memory updates

- `specs/memory/architecture.html` — updated agent-topology layer description: two-tier PM router (Tier-1: 7 engine-backed workflows via `dadaia orchestrate run`; Tier-2: PM Playbooks composed inline), D-OC-1 bidirectional drift gate added to doctor contracts table, operator plain-language interface and PM auto-reserves task_ids noted; playbook count updated to 13 PM playbooks (was 8); last-updated meta line updated.
- `specs/memory/product/agent-orchestration.html` — rewritten `#purpose` section to describe two-tier router; `#trigger` updated (7 workflows + 13 PM playbooks); `#dependencies` updated playbook count; last-updated meta updated.
- `specs/memory/product/specs-doctor.html` — updated check count from 11 to 12 (added D-OC-1 invariant); updated `#purpose` description to mention D-OC-1; updated `#flow` error code range; last-updated meta updated.
- `specs/memory/product/index.html` — `agent-orchestration` catalog entry updated to reflect two-tier router and 13 PM playbooks; last-updated meta updated.
- `specs/memory/product/agent-comms.html` — no change: this release did not touch the handoff contract, schema, CLI, or skill.
- `specs/memory/tech-stack.html` — no change: no new dependencies introduced.

---

## Backlog returns

No items returned to backlog. The three workflow-backlog candidates
(`data-pipeline-cycle-workflow-v1`, `ai-entity-refinement-workflow-v1`,
`ai-engineer-recursive-bootstrap-v1`) were resolved to PM Playbooks in T-OCV-05b and are
now annotated as closed in `specs/backlog/candidates.md ## Histórico`.

Optional future work (informal idea, not a candidate yet): a future release could
retrofit any remaining legacy playbooks in `project-orchestration/SKILL.md` that still
lack `**Input contract:**` or `**Done when:**` to the full 7-field schema, if the
mandatory-schema enforcement is extended to pre-existing playbooks via `D-OC-2` or
similar invariant.

---

## Archive decision

**MOVE** — release directory will be moved to
`specs/_archive/releases/orchestration-consolidation-v1/` via `git mv`. ACTIVE.md will
be updated to `release: none` after the move.
