# Closure: Release — v0.1.5

> **Status:** Aprovado
> **Release ID:** v0.1.5
> **Owner:** product-engineer
> **Closed:** 2026-06-05

## Summary

Release v0.1.5 delivers the complete governance layer for how bugs and backlog items
become releases in the dadaia-workspace SDD lifecycle, together with the structural
engine (scaffolder, ACTIVE.md schema v2, gate path-resolution, doctor checks, CLI)
that makes the `alpha-N/rc-N` maturity model operational. The release also ships a
mandatory pre-push CI gate that blocks pushes when any locally-runnable CI check fails.

Five ADRs (ADR-1..5) formally record the decisions: the alpha/rc nested model that
eliminates the 4-segment collision class, hotfix unification under the same model,
the feature/{version} branch + review cadence (alpha=qa-only-commit, rc=ship-trio-or-
iterate), the bug/backlog governance rules (pick, bug-always-solved, subsumption,
sanitize, mandatory grill), and the in-scope fold of the engine into v0.1.5.

Governance surfaces delivered: skill `dadaia-release-definition`, rule
`release-governance.md`, persona edits to `product-engineer.md` and
`project-manager.md`, `project-orchestration` contract rewrite, and the
`dadaia-grill-me` mandatory-trigger note. All lib-originated assets propagated via
`dadaia public stage && install --force`.

**Deployment is explicitly deferred.** This release is authored and ready on
`feature/0.1.5` but has not been pushed, merged, or published as a wheel. Two
backlog items must land first:
- `FEAT-SESSION-SEMAPHORE-01` — session semaphore (deploy-blocker)
- `FEAT-DADAIA-AGENTS-01` — agent dispatch improvements

No merge, no PR, no push, no PyPI upload may occur for v0.1.5 until both items are
resolved. See `specs/backlog/candidates.md` for tracking.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-ADR-01 | Author ADR-1..4 (alpha/rc model, hotfix unification, cadence, bug/backlog) | inline in SPEC.md §8 |
| T-GOV-01 | New skill `dadaia-release-definition` | `dadaia_workspace/public/skills/dadaia-release-definition/SKILL.md` |
| T-GOV-02 | Persona edits: product-engineer + project-manager | `dadaia_workspace/public/agents/{product-engineer,project-manager}.md` |
| T-GOV-03 | Rewrite `project-orchestration` review contract + playbook | `dadaia_workspace/public/skills/project-orchestration/SKILL.md` |
| T-GOV-04 | `dadaia-grill-me` mandatory-at-release-definition trigger | `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md` |
| T-GOV-05 | Always-on rule `release-governance` | `dadaia_workspace/public/rules/release-governance.md` |
| T-GATE-01 | Mandatory pre-push CI gate | `dadaia_workspace/public/scripts/pre-push-ci-gate.sh` |
| T-SANI-01 | Sanitize stale bugs/backlog + v0.1.3 draft | `specs/releases/v0.1.3/*`, `specs/backlog/*`, `specs/bugs/*` |
| T-PROP-01 | Propagate + verify projections + full suite green | projections under `.claude/`, `.codex/`, `.agents/`, `.opencode/` |
| T-ENG-01 | ACTIVE.md schema v2 (`segment:` field) + readers | `dadaia_workspace/features/specs/doctor.py` |
| T-ENG-02 | Scaffolder for `alpha-N`/`rc-N` segments | `dadaia_workspace/features/specs/scaffolder.py` |
| T-ENG-03 | CLI `dadaia specs release open` + `segment open` | `dadaia_workspace/cli/commands/specs.py` |
| T-ENG-04 | Gate path-resolution to active segment | `dadaia_workspace/public/scripts/sdd-spec-gate.sh` |
| T-ENG-05 | Doctor: segment-aware checks | `dadaia_workspace/features/specs/doctor.py` |
| T-ENG-06 | `.gitignore` tracks segment files | `.gitignore` |
| T-ENG-07 | Hotfix reconciliation (ADR-2) | `dadaia_workspace/cli/commands/specs.py`, `dadaia_workspace/features/specs/scaffolder.py` |
| T-ENG-08 | CI `feature/{version}` branch trigger | `.github/workflows/ci.yml` |
| T-ENG-09 | Skill docs updated for segments | `dadaia_workspace/public/skills/{dadaia-workspace-spec-navigator,dadaia-release-closure,dadaia-task-manager,dadaia-workspace-spec-reviewer}/SKILL.md` |
| T-MEM-01 | CLOSURE memory atoms | `specs/memory/product/{sdd-bug-backlog-governance,sdd-hotfix-track}.md`, `specs/memory/product/index.md` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| `dadaia-release-definition` skill exists and is discoverable | `ls dadaia_workspace/public/skills/dadaia-release-definition/SKILL.md` | `dadaia_workspace/public/skills/dadaia-release-definition/SKILL.md` exists |
| `release-governance.md` rule exists and projects to `.claude/rules/` | `cat .claude/rules/release-governance.md` | `.claude/rules/release-governance.md` present with mandatory grill + bug-always-solved content |
| `product-engineer.md` + `project-manager.md` persona edits propagated | `cat dadaia_workspace/public/agents/product-engineer.md \| grep release-definition` | release-definition responsibility present in both personas |
| `project-orchestration` skill reflects alpha/rc cadence | `grep -n 'alpha-N\|rc-N\|feature/{version}' dadaia_workspace/public/skills/project-orchestration/SKILL.md` | all three terms found |
| `dadaia-grill-me` skill lists release-definition as mandatory trigger | `grep -n 'release-definition\|mandatory' dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md` | mandatory trigger section present |
| Pre-push CI gate blocks on failure | `bash dadaia_workspace/public/scripts/pre-push-ci-gate.sh` (with deliberate ruff violation) | non-zero exit returned; push blocked |
| Pre-push gate runs ruff+mypy+pytest suite | `cat dadaia_workspace/public/scripts/pre-push-ci-gate.sh \| grep -E 'ruff\|mypy\|pytest'` | all four commands present |
| ACTIVE.md schema v2 segment reader parses both flat and segmented | `python -m pytest tests/unit/specs/ -k segment -p no:cacheprovider` | tests pass (T-ENG-01 acceptance) |
| Scaffolder creates `alpha-N`/`rc-N` segment dirs | `python -m pytest tests/unit/specs/ -k scaffold -p no:cacheprovider` | tests pass (T-ENG-02 acceptance) |
| Gate resolves active segment's TASKS.md | `python -m pytest tests/integration/gate/ -p no:cacheprovider` | tests pass (T-ENG-04 acceptance) |
| Doctor segment-aware SPEC-DOC-004 passes | `python -m pytest tests/unit/specs/ -k doctor -p no:cacheprovider` | tests pass (T-ENG-05 acceptance) |
| `dadaia public doctor` exit 0 | `dadaia public doctor` | exit 0 (T-PROP-01 acceptance) |
| `dadaia specs doctor` 0 ERROR | `.dadaia/.venv/bin/dadaia specs doctor` | 0 ERROR confirmed (T-MEM-01 acceptance) |
| Full CI-equivalent suite green | `ruff format --check . && ruff check . && mypy --strict dadaia_workspace/ && pytest -p no:cacheprovider` | all pass (T-PROP-01 acceptance) |
| ADR-1..5 authored and Aprovado | `grep 'ADR-' specs/releases/v0.1.5/SPEC.md` | ADR-1..5 present in SPEC.md §8 (Aprovado) |
| Memory atom `sdd-bug-backlog-governance.md` created | `cat specs/memory/product/sdd-bug-backlog-governance.md` | atom present with all required sections |
| Memory atom `sdd-hotfix-track.md` annotated as superseded | `grep superseded specs/memory/product/sdd-hotfix-track.md` | superseded note + link to sdd-bug-backlog-governance present |

## Drifts

### adr-location-deferred

**Description:** ADR-1..4 were authored inline in `SPEC.md §8` rather than in a
dedicated `specs/releases/v0.1.5/adr/` subdirectory. The SPEC itself noted that the
`.gitignore` tracks only SPEC/PLAN/TASKS/CLOSURE per release dir and that a dedicated
ADR directory is an SDD-structure change deferred to v0.1.6.

**Resolution:** ADRs live inline in SPEC.md. ADR-5 was also added inline when the
engine was folded into v0.1.5. No drift from stated intent — this was the planned
approach. Next release should evaluate whether a dedicated `adr/` directory should be
added.

**Memory updates:** None required — memory atoms reference the SPEC directly.

### engine-folded-from-v016

**Description:** The ADR-1/ADR-2 "engine" (scaffolder, schema v2, gate path-resolution,
doctor, CLI) was originally deferred to v0.1.6. Per operator decision 2026-06-05 and
ADR-5, it was folded into v0.1.5.

**Resolution:** T-ENG-01..09 delivered the full engine. SPEC.md §4 ("Out of scope")
and §5 ("Bootstrapping note") were superseded by ADR-5. The release grew from
"govern now" to "govern + build the engine". No architectural change — purely scope
expansion within the same unmerged branch.

**Memory updates:** `specs/memory/product/sdd-bug-backlog-governance.md` covers the
engine deliverables (segment model, ACTIVE.md schema v2, scaffolder CLI surface,
doctor checks, pre-push gate).

### no-sdd-release-lifecycle-atom

**Description:** T-MEM-01 acceptance says to locate the existing "release-lifecycle"
atom and update it for the alpha-N/rc-N segment model. No standalone
`sdd-release-lifecycle.md` atom exists in `specs/memory/product/`. The catalog
shows `sdd-hotfix-track` (superseded) and `agent-sdd-alignment` (agent behavior, not
lifecycle documentation). The memory context note (`project_sdd_release_lifecycle.md`)
references this concept but no product atom was ever created for it.

**Resolution:** The lifecycle governance is fully captured in the new
`sdd-bug-backlog-governance.md` atom, which covers: bug/backlog→release,
alpha-N/rc-N model, review cadence, branch model, pre-push gate, and hotfix
unification. A separate `sdd-release-lifecycle.md` atom is **not created** per
T-MEM-01 acceptance ("If no such atom exists, note that in your handoff — do not
invent one outside acceptance"). If a dedicated lifecycle overview atom is desired,
add it to `specs/backlog/candidates.md` for the next release.

**Memory updates:** No `sdd-release-lifecycle.md` created. Lifecycle content lives
in `sdd-bug-backlog-governance.md`.

## Memory updates

- `specs/memory/product/sdd-bug-backlog-governance.md` — **NEW ATOM**: captures the
  v0.1.5 bug/backlog→release governance, alpha-N/rc-N segment model (ADR-1/ADR-5),
  review cadence (ADR-3), hotfix unification (ADR-2), and pre-push CI gate (T-GATE-01).
  All required sections present (Propósito, Fluxo de uso, Trigger típico, Diferencial,
  Estado runtime tocado, Dependências). Wikilinks to [[sdd-gate-v3]], [[specs-doctor]],
  [[public-asset-distribution]], [[sdd-hotfix-track]], [[agent-sdd-alignment]].

- `specs/memory/product/sdd-hotfix-track.md` — **ANNOTATED SUPERSEDED**: added
  `superseded_by: sdd-bug-backlog-governance` frontmatter field, `superseded_reason`,
  `superseded` tag, and a visible `> **SUPERSEDED**` notice at the top of the body.
  Atom retained (not deleted) per the "never delete" rule of bug/backlog governance.

- `specs/memory/product/index.md` — **CATALOG UPDATED**: added row for new
  `sdd-bug-backlog-governance` atom; updated `sdd-hotfix-track` row to note superseded.

- `specs/memory/architecture.md` — no change: release did not modify architecture
  layer rules or agent topology.

- `specs/memory/tech-stack.md` — no change: release did not add or remove approved
  technologies.

## Backlog returns

- `backlog/candidates.md` ← `FEAT-SESSION-SEMAPHORE-01` (session semaphore — deploy
  blocker for v0.1.5 ship gate; already tracked)
- `backlog/candidates.md` ← `FEAT-DADAIA-AGENTS-01` (agent dispatch improvements —
  second deploy-blocker for v0.1.5 ship gate; already tracked)
- `backlog/ideas.md` ← consider a dedicated `sdd-release-lifecycle.md` memory atom
  as a standalone overview of the complete lifecycle (currently covered inline in
  `sdd-bug-backlog-governance.md`; a separate atom would serve as an entry-point
  for new operators)
- `backlog/ideas.md` ← consider a dedicated `adr/` subdirectory under
  `specs/releases/<ver>/` for cleaner ADR organization (currently ADRs are inline
  in SPEC.md §8; the structure change is a v0.1.6+ decision)

## Archive decision

**DEFERRED** — The release directory remains in `specs/releases/v0.1.5/`. Archiving
(`git mv specs/releases/v0.1.5 specs/_archive/releases/v0.1.5`) and updating
`ACTIVE.md` to point to the next release are **blocked** by the two deploy-blocker
backlog items (`FEAT-SESSION-SEMAPHORE-01` + `FEAT-DADAIA-AGENTS-01`).

Branch `feature/0.1.5` remains unmerged and unpushed until both items are resolved
and the operator elects to ship. When ship gate opens: spawn qa-engineer + code-reviewer
+ security-reviewer, all APPROVE, push + open PR → merge → archive.
