# TASKS: v0.1.9 — Skills cleanup + workflow redesign + memory tree + surface cleanup

**Status:** Aprovado
**Release ID:** v0.1.9
**Owner:** product-engineer
**Created:** 2026-06-06
**Parent program:** v0.2.0

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Maximum one `[-]` per owner at a time unless disjoint write sets are declared.
All tasks start `[ ]` OPEN.

**Parallel note:** T-019-05 and T-019-06 have fully disjoint write sets
(`dadaia_workspace/public/skills/**` vs `specs/memory/product/**`) and may run
concurrently once T-019-04 is DONE, with the constraint that each owner keeps
at most one `[-]` in their own write set.

---

## T-019-01 — D-OC-1 audit: confirm zero stale workflow refs in all personas and project-orchestration

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:** None — read-only audit. Any strips required are tracked here as findings and executed in T-019-02.
- **Preconditions:** T-018-09 DONE (v0.1.8 committed and operator-validated; all 9 v0.1.8 personas are the final surface).
- **Context note:** `project-orchestration` (the PM-loaded skill) was not rebuilt in v0.1.8 and remains at the pre-v0.1.9 stale state (15-agent topology, 7-workflow inventory). T-019-01 audits its current stale state; T-019-02 rebuilds it. This is the expected starting condition, not a surprise finding.
- **Done criteria:**
  - Read every file in `dadaia_workspace/public/agents/*.md` (all 9 core personas) and `dadaia_workspace/public/skills/project-orchestration/SKILL.md`.
  - For each file, record any reference to the 7 stale workflow slugs: `audit-cycle`, `code-review-fan-out`, `cross-cutting-feature`, `design-first-implementation`, `hotfix-release`, `spec-refinement`, `onboarding-new-repo`.
  - Produce a findings list: for each file, list (a) whether a stale reference was found, (b) the line(s) containing the reference, (c) proposed strip action.
  - Also flag any reference to deleted persona names: `software-engineer-python`, `software-engineer-node`, `backend-engineer`, `researcher` (outside plugin-scope notes).
  - D-OC-1 finding: if zero stale refs found, commit `chore(audit): D-OC-1 clean — no stale workflow refs (T-019-01)`. If refs found, do NOT commit yet — proceed to T-019-02.
- **Commit convention:** `chore(audit): D-OC-1 audit — found N stale refs, proceeding to strip (T-019-01)` (or `D-OC-1 clean` if zero found).

---

## T-019-02 — Strip stale workflow refs from project-orchestration and any residual personas

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `dadaia_workspace/public/skills/project-orchestration/SKILL.md`
  - Any `dadaia_workspace/public/agents/*.md` files where stale refs were found in T-019-01 (zero files if D-OC-1 was clean)
- **Preconditions:** T-019-01 DONE (findings list available).
- **Done criteria:**
  - `project-orchestration/SKILL.md` Workflow Inventory table: remove all 7 stale workflow rows. Replace with a note: "Workflows: see `public/workflows/` — exactly 2 workflows in the default installation."
  - `project-orchestration/SKILL.md` Agent Inventory table: if it still lists 15 agents (stale from v0.1.8 delay), update to list exactly 9 core agents matching the v0.1.7 roster. Roles must match SPEC §2 of the v0.1.7 constitution.
  - `project-orchestration/SKILL.md` Decision Authority table: remove rows for `software-engineer-python`, `software-engineer-node`, `backend-engineer`, `frontend-engineer` (as peer authority), `design-specialist` (as peer authority), `devops-engineer` (as peer). Rows for the 9 core agents remain.
  - `project-orchestration/SKILL.md` Generic Playbooks: remove `design-validation` playbook (references deleted agents). Keep all others; update any playbook that mentions a deleted agent.
  - Any persona file flagged in T-019-01: strip the specific references identified in the findings list.
  - After edits: re-run the D-OC-1 audit (grep the changed files) — zero stale refs must remain.
  - `dadaia public stage` exits 0 after this task.
- **Commit convention:** `refactor(skills): strip stale workflow+agent refs from project-orchestration (T-019-02)`

---

## T-019-03 — Delete 7 stale workflow files

- **Status:** [x] (pulled forward in v0.1.8 — workflows blocked staging)
- **Owner:** ai-engineer
- **Write-set:**
  - `dadaia_workspace/public/workflows/audit-cycle.workflow.md` (DELETE)
  - `dadaia_workspace/public/workflows/code-review-fan-out.workflow.md` (DELETE)
  - `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md` (DELETE)
  - `dadaia_workspace/public/workflows/design-first-implementation.workflow.md` (DELETE)
  - `dadaia_workspace/public/workflows/hotfix-release.workflow.md` (DELETE)
  - `dadaia_workspace/public/workflows/spec-refinement.workflow.md` (DELETE)
  - `dadaia_workspace/public/workflows/onboarding-new-repo.workflow.md` (DELETE)
- **Preconditions:** T-019-02 DONE (D-OC-1 clean — no persona or skill references the 7 workflow slugs before deletion).
- **Done criteria:**
  - All 7 files deleted from `dadaia_workspace/public/workflows/`.
  - `dadaia public stage` exits 0 (manifest accepts the deletions with no error).
  - `ls dadaia_workspace/public/workflows/` shows 0 files (empty directory before new files added in T-019-04).
- **Commit convention:** `refactor(workflows): delete 7 stale workflows (T-019-03)`

---

## T-019-04 — Author `release-ship.workflow.md` + `audit-fanout.workflow.md`

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `dadaia_workspace/public/workflows/release-ship.workflow.md` (NEW)
  - `dadaia_workspace/public/workflows/audit-fanout.workflow.md` (NEW)
- **Preconditions:** T-019-03 DONE.
- **Done criteria:**

  **`release-ship.workflow.md`:**
  - Frontmatter: `name: release-ship`, `trigger: operator-elects-to-ship`, `owner: project-manager`, `activity_class: MUTATING`, `lifecycle_phase: Closure`.
  - Steps section lists the deterministic deploy gate sequence in order:
    1. Precondition: all ship-trio handoffs (`qa`, `security`, `code-review`) present with `verdict: APPROVED`.
    2. Precondition: `pytest -p no:cacheprovider` passes on the rc commit.
    3. `dadaia ci preflight` (ruff format, ruff check, mypy --strict, pytest) exits 0.
    4. Merge `feature/<version>` → `main` (no fast-forward preferred; preserve history).
    5. Tag: `git tag v<M>.<m>.<p> <merge-commit-sha>`.
    6. PyPI publish: `poetry publish --build`.
    7. Smoke test: `pip install dadaia==<version>` in a clean venv; `dadaia --version` matches.
  - Judgment-delegation section: if any precondition fails, workflow terminates and delegates to PM with specific failure detail.
  - Does NOT contain judgment calls about whether to ship (that decision lives in PM's persona).
  - Cites v0.1.7 constitution §1 matrix: MUTATING class, Closure phase.

  **`audit-fanout.workflow.md`:**
  - Frontmatter: `name: audit-fanout`, `trigger: operator-requests-audit or CLOSURE`, `owner: project-manager`, `activity_class: ADDITIVE`, `lifecycle_phase: Research/Audit`.
  - Steps section lists the deterministic audit dispatch sequence:
    1. project-auditor bootstraps memory: reads `specs/memory/architecture.md`, `product/index.md`, and target feature atoms.
    2. Runs `dadaia public doctor` + `dadaia specs doctor`; any non-zero exit is an immediate finding.
    3. Runs drift-detection protocol (per `drift-detection` skill) for in-scope features.
    4. Emits findings handoff JSON to `.dadaia/handoff/<context>/`.
    5. PM reads handoff; decides whether to open backlog items or an immediate release.
  - No judgment calls embedded. PM decides after step 5.
  - Cites v0.1.7 constitution §1 matrix: ADDITIVE class, Research phase.

  **Shared:**
  - Each workflow file must contain an explicit honesty note: "This is a dispatch-reference
    document. Claude Code and Codex do not auto-load `.claude/workflows/` files at runtime;
    this file is used only when PM explicitly loads it as context."
  - `release-ship.workflow.md` must NOT encode the ship decision; it covers only the
    deterministic sequence AFTER PM has decided to ship. Judgment forks terminate and
    delegate to PM.
  - `audit-fanout.workflow.md` must CITE the `drift-detection` skill (by name reference)
    rather than restating the drift-detection procedure inline.
  - D-OC-1 re-check after adding new files: `dadaia public doctor` must show the 2 new workflows and no dangling refs.
  - `dadaia public stage` exits 0.
- **Commit convention:** `feat(workflows): release-ship + audit-fanout lifecycle workflows (T-019-04)`

---

## T-019-05 — Skills text-review: 17 skills — strip dead refs, verify phase mapping, trim slop

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:** `dadaia_workspace/public/skills/` — edits to surviving 17 skill SKILL.md files; also DELETE the 5 frontend/design skill directories.
- **Preconditions:** T-019-04 DONE. (Disjoint write set from T-019-06; may run concurrently with T-019-06 after T-019-04 is DONE.)
- **Done criteria:**

  **Deletions (5 frontend/design skills):**
  - `dadaia_workspace/public/skills/frontend-design/` — directory and SKILL.md deleted.
  - `dadaia_workspace/public/skills/frontend-implementation-quality/` — deleted.
  - `dadaia_workspace/public/skills/design-reference-research/` — deleted.
  - `dadaia_workspace/public/skills/design-report-quality-gate/` — deleted.
  - `dadaia_workspace/public/skills/ux-ui-review/` — deleted.
  - `dadaia public stage` exits 0 after deletions (no manifest error for deleted skills).

  **Text-review pass (17 remaining skills):** For each skill, the following criteria
  are verified and corrected where needed. ai-engineer attests to each criterion in
  the commit message for the group:

  1. **`project-orchestration`** — already handled in T-019-02. In this task, verify
     the post-T-019-02 version satisfies all 6 review criteria from SPEC §2.2. No
     further edit expected if T-019-02 was complete, but the attestation is recorded here.

  2. **`dadaia-workspace-doctor`** — Fix: rename `product-auditor-agent` to
     `project-auditor` throughout. Update Phase 3 report path format to match current
     `.dadaia/reports/<context>/<agent>/` convention. Verify no HTML-memory refs.

  3. **`dadaia-workspace-manager`** — Verify lock primitives section reflects v0.1.6
     model (`dadaia lock steal`). Remove any reference to semaphore acquisition on
     `context bind`. Update Doctor Invariants table if it contains LOCK rows referencing
     semaphore-era fields.

  4. **`drift-detection`** — Replace all references to "atomic HTML files" with
     "Markdown atoms" (`*.md`). Verify the Memory Atom Inventory table lists `*.md`
     paths, not `*.html`. Verify no reference to `evidence/` subtree.

  5. **`dadaia-release-definition`** — **EDIT required** (determined pre-task): `dadaia
     backlog list` and `dadaia bug list` do NOT exist in the CLI (`dadaia_workspace/cli/
     commands/newartifacts.py` only ships `backlog new` and `bug new`). Replace both
     CLI command references in the skill with: "read `specs/bugs/*.md` directly" and
     "read `specs/backlog/*.md` directly". No runtime verification needed — the answer
     is determined from source inspection.

  6. **`dadaia-step0-memory-bootstrap`** — Verify all memory path references are `.md`,
     no `.html`. Verify `catalog.json` reference is current. No stale `ctx-inject.sh`
     path references.

  7. **`dadaia-workspace-spec-navigator`** — Verify no reference to `evidence/` subtree.
     Verify legacy-feature compat note (`SDD_LEGACY_FEATURES=1`) reflects current gate
     behavior. Strip references to `standby`, `is_selected`, `select` (v1 context fields).

  8. **`dadaia-workspace-spec-reviewer`** — Verify no reference to `evidence/` subtree.
     Verify review criteria cover `specs/memory/` as Markdown (not HTML). Confirm
     broken-image check references `.dadaia/reports/` not `evidence/`.

  9. **`dadaia-handoff-emitter`** — Confirm `schema_version: "handoff-v1.1"` is the only
     cited version. No earlier version references. No `evidence/` path references.

  10. **`dadaia-grill-me`** — Verify report path format: `.dadaia/reports/<context-name>/
      product-engineer/<YYYY-MM-DDTHHMMSSZ>-refine-specs.html`. Verify no stale agent names
      in problem templates.

  11. **`dadaia-release-closure`** — Verify phase restriction language: PE may write memory
      in DEFINITION + CLOSURE (both), not CLOSURE-only (v0.1.7 update). Update if stale.

  12. **`dadaia-task-manager`** — Verify `SDD_LEGACY_FEATURES=1` and legacy paths note
      reflects current gate behavior. Confirm Segments note (ADR-1/ADR-5) is present.

  13. **`harness-primitives`** — Scan for any workspace-private names (IPs, hostnames,
      project slugs). Verify `dadaia projection` reference is current. No platform-specific
      leak.

  14. **`ai-harness-claude-code`** — Restricted-scope skill (ai-engineer only). Verify
      `harness-skill-scope` rule citation is present or implied. Verify phase mapping:
      "ai-engineer / harness literacy" declared in description or opening section.

  15. **`ai-harness-codex`** — Same checks as `ai-harness-claude-code`.

  16. **`ai-context-engineering`** — Same checks. Verify no reference to deprecated
      context engineering concepts post-v0.1.7 constitution.

  17. **`dev-server-registry`** — Verify port range (3000–3999) is still accurate. Verify
      `dadaia server dashboard` URL (4999) is consistent with panel memory atom. No stale CLI flags.

  **Attestation:** ai-engineer records in the commit message which criteria were clean
  and which required edits, for each skill (a table in the extended commit message is acceptable).

  **Count verification:** after deletions and reviews, `ls dadaia_workspace/public/skills/ | wc -l`
  must equal 17 (one directory per skill). `dadaia public stage` exits 0.

- **Commit convention:** `refactor(skills): text-review pass — 17 skills clean, 5 deleted (T-019-05)`

---

## T-019-06 — `product/` memory tree restructure + `index.md` rebuild

- **Status:** [x]
- **Owner:** product-engineer (with project-auditor placement review)
- **Write-set:**
  - `specs/memory/product/` — create 6 subdirectory directories, `git mv` 24 atoms into them (+ archive `test-suite-architecture.md`), update `index.md`.
- **Preconditions:** T-019-04 DONE; `specs/memory/product/quality-assurance.md` exists (created in T-017-02); T-018-09 DONE (roster final). (Disjoint write set from T-019-05; may run concurrently after T-019-04.)
- **Done criteria:**

  **Subdirectory creation:**
  - `specs/memory/product/agents/` created.
  - `specs/memory/product/sdd/` created.
  - `specs/memory/product/panel/` created.
  - `specs/memory/product/platform/` created.
  - `specs/memory/product/distribution/` created.
  - `specs/memory/product/philosophy/` created.

  **Atom placement (provisional by PE; confirmed or adjusted by project-auditor):**

  Total atoms placed: **24** (agents:8 + sdd:5 + panel:2 + platform:6 + distribution:2 +
  philosophy:1 = 24). This matches the §4.1 arithmetic exactly.

  - `agents/` (8): `agent-sdd-alignment.md`, `agent-orchestration.md`, `agent-monitoring.md`,
    `agent-comms.md`, `harness-primitives.md`, `ai-harness-claude-code.md`, `ai-harness-codex.md`,
    `ai-context-engineering.md`.
  - `sdd/` (5): `sdd-gate-v3.md`, `sdd-bug-backlog-governance.md`, `sdd-hotfix-track.md`,
    `specs-doctor.md`, `quality-assurance.md`.
  - `panel/` (2): `panel.md`, `brand-identity.md`.
  - `platform/` (6): `context-management.md`, `workspace-init.md`, `workspace-doctor.md`,
    `workspace-portability.md`, `server-registry.md`, `multi-platform-parity.md`.
  - `distribution/` (2): `public-asset-distribution.md`, `academy.md`.
  - `philosophy/` (1): `repos-catalog.md`.

  **`agent-sdd-alignment.md`** appears in `agents/` ONLY. It must NOT appear in any
  other group. project-auditor may confirm or move it but may not duplicate it.

  **`test-suite-architecture.md` handling:** this atom is physically present at the flat
  root. It must be handled in this task via `git mv specs/memory/product/test-suite-architecture.md
  specs/_archive/legacy-memory/<YYYYMMDD>/test-suite-architecture.md`. It is NOT added to
  any subdir catalog. AC-9 is satisfied when no flat atom (other than `index.md`) remains.

  **`philosophy/` single-atom criterion:** project-auditor must include in the placement
  handoff an explicit justification for `repos-catalog.md` remaining as a single atom in
  its own group. If no justification is provided, auditor must propose merging it into
  the nearest group (likely `platform/` or `agents/`). PE adjusts before commit.

  - `product/` root (besides `index.md`): no files after `test-suite-architecture.md` is archived.

  **project-auditor placement review:**
  - project-auditor reads each atom title and `## Propósito` section.
  - Flags any atom whose placement is ambiguous or wrong.
  - PE adjusts placement per auditor finding before committing.
  - Auditor emits a handoff with confirmed placement list: `.dadaia/handoff/dadaia-workspace/<UTC>-project-auditor-memory-tree-placement.handoff.json`.

  **`index.md` rebuild:**
  - `## Vision` section: 2–3 sentences, atomic, no changelog.
  - `## Users` section: who operates a dadaia workspace.
  - `## Catalog` section: ordered `<ol class="catalog">` listing all 24 production features
    (per §4.1 arithmetic; `test-suite-architecture.md` excluded as archived),
    grouped by thematic subdir, each item a relative Markdown link
    (e.g. `[Context management](platform/context-management.md)`).
  - `## Capability map` section: fenced Mermaid `flowchart LR` showing the 6 thematic
    groups as nodes and their key inter-group dependencies as edges.
  - `## Limits` section: explicit non-goals (what dadaia-workspace is not: not an AI model
    provider, not a CI/CD system, not a cloud service).
  - No `Changelog`, `History`, `Histórico`, or `Versions` section.
  - Old flat-file-era `index.md` content (auto-generated table) is replaced.

  **Post-move validation:**
  - `dadaia specs doctor` exits 0: no broken wikilinks, no broken image refs, all 24
    placed atoms have the 6 required feature sections (`Propósito`, `Fluxo de uso`,
    `Trigger típico`, `Diferencial`, `Estado runtime tocado`, `Dependências`), memory
    atomicity rules pass. Doctor must recurse into subdirs for atom-structure checks
    (ai-engineer verifies glob depth before accepting T-019-06).
  - `find specs/memory/product -maxdepth 1 -name "*.md" | grep -v index.md` returns
    nothing (no flat-root atoms remain; `test-suite-architecture.md` was archived).

- **Commit convention:** `feat(memory): product/ tree restructure — 6 groups + index wikilinks (T-019-06)`

---

## T-019-07 — Final propagation: `dadaia public stage && install --force --target all` + doctor exit 0

- **Status:** [x]
- **Owner:** ai-engineer
- **Write-set:**
  - `.dadaia/agentic/` (manifest rebuilt)
  - `.claude/agents/`, `.claude/skills/`, `.claude/workflows/`, `.claude/rules/` (projections)
  - `.agents/skills/` (projection)
  - `.opencode/agents/` (projection)
  - `.codex/` (projection)
- **Preconditions:** T-019-05 DONE AND T-019-06 DONE (both skills review and memory tree complete before propagation).
- **Done criteria:**
  - `dadaia public stage` exits 0. Manifest correctly reflects 17 skills (5 deleted) and 2 workflows (7 deleted, 2 added).
  - `dadaia public install --force --target all` exits 0. The `--force` flag is used here because the 7 workflow deletions and 5 skill deletions create projected files that must be removed from runtimes (plain `install` only updates hash-mismatches; `--force` also removes deleted-source projections).
  - `dadaia public doctor` exits 0 on all runtimes:
    - `.claude/agents/`: exactly 9 agent `.md` files.
    - `.claude/skills/` or `.agents/skills/`: exactly 17 skill directories.
    - Workflows (if projected): exactly 2 workflow files.
    - No orphan skill, workflow, or agent detected by doctor.
    - No `[drift]` or `[missing]` entries; only `[ok]` or `[not-applicable]`.
  - `dadaia specs doctor` exits 0:
    - Memory canon checks pass.
    - No broken wikilinks in `specs/memory/product/` (including subdirs).
    - No broken image references in any memory Markdown.
    - All 24 placed atoms under `specs/memory/product/**/*.md` have the 6 required sections.
    - `index.md` has all 4 required top-level sections.
    - No flat-root atoms (other than `index.md`); `test-suite-architecture.md` confirmed absent.
  - Exact counts captured in handoff or commit message:
    - Skills: 17.
    - Workflows: 2.
    - Agents: 9.
    - Product atoms placed: 24 (agents:8 / sdd:5 / panel:2 / platform:6 / distribution:2 / philosophy:1).
- **Commit convention:** `chore(public): v0.1.9 final propagation — 9 agents / 17 skills / 2 workflows, doctor exit 0 (T-019-07)`

---

## T-019-08 — qa-engineer gate (pre-commit)

- **Status:** [x]
- **Owner:** qa-engineer
- **Write-set:** `.dadaia/handoff/dadaia-workspace/` (ADDITIVE — evidence only)
- **Preconditions:** T-019-07 DONE.
- **Done criteria:**
  - qa-engineer reads `dadaia public doctor` output from T-019-07 and confirms:
    - 7 stale workflows absent from all runtimes.
    - Exactly 2 new workflows present.
    - Exactly 17 skills; 5 frontend/design skills absent.
    - Exactly 9 agents; no deleted persona names.
    - `dadaia public doctor` exit 0 output evidence attached.
  - qa-engineer reads `dadaia specs doctor` output and confirms:
    - `product/` tree has all 6 subdirs; no flat-root atoms (besides `index.md`); `test-suite-architecture.md` absent from flat root.
    - `index.md` has Vision, Users, Catalog, Capability map, Limits sections.
    - No broken wikilinks or image refs.
    - All 24 placed atoms (agents:8 / sdd:5 / panel:2 / platform:6 / distribution:2 / philosophy:1) have the 6 required feature sections.
  - qa-engineer reads `project-orchestration/SKILL.md` and confirms:
    - Agent inventory: exactly 9 agents.
    - Workflow inventory: exactly 2 workflows (`release-ship`, `audit-fanout`).
    - No reference to deleted persona names (`software-engineer-python`, `backend-engineer`, etc.).
    - Decision Authority table: no rows for deleted agents.
  - qa-engineer spot-checks 5 of the 17 skills for dead-ref compliance (random selection from different priority tiers).
  - If any finding is BLOCKING: qa-engineer returns `REQUEST_CHANGES` verdict; relevant task re-opened; qa re-runs after fix.
  - Handoff JSON emitted: `<UTC>-qa-engineer-T-019-08-qa-gate.handoff.json`.
  - APPROVE verdict → commit allowed.
- **Commit convention:** `chore(gate): v0.1.9 qa-engineer approval (T-019-08)`

---

## T-019-09 — Operator in-workspace validation + push to `feature/0.2.0`

- **Status:** [x]
- **Owner:** project-manager (coordinates); operator signs off
- **Write-set:** `.dadaia/handoff/dadaia-workspace/` (ADDITIVE — operator sign-off record)
- **Preconditions:** T-019-08 DONE (qa APPROVE handoff present).
- **Done criteria:**
  - Operator inspects the reduced surface interactively:
    - Browses `.claude/agents/` — confirms 9 `.md` files, no plugin stubs in core.
    - Browses `.claude/skills/` (or `.agents/skills/`) — confirms 17 skill directories; names match the expected list.
    - Browses `specs/memory/product/` — confirms 6 thematic subdirs, `index.md` at root, no flat atoms.
    - Reads `specs/memory/product/index.md` — confirms it is navigable and the Mermaid capability-map renders without syntax errors.
  - Operator runs fresh-init parity check:
    ```
    mkdir /tmp/dadaia-parity-test && cd /tmp/dadaia-parity-test && dadaia init
    ls .claude/agents/ | wc -l   # must equal 9
    ls .claude/skills/ | wc -l   # must equal 17 (or equivalent runtime path)
    ```
  - Default projection emits only 9 core agents; no `frontend-engineer.md`, `design-specialist.md`, `devops-engineer.md` in core projection.
  - Operator sign-off recorded. Push to `feature/0.2.0` branch allowed.
  - Operator sign-off handoff or commit note emitted.
- **Commit convention:** `chore(gate): v0.1.9 operator sign-off (T-019-09)`

---

## Task dependency graph

```
T-019-01 (D-OC-1 audit)
  │
  ▼
T-019-02 (strip refs)
  │
  ▼
T-019-03 (delete 7 workflows)
  │
  ▼
T-019-04 (author 2 new workflows)
  │
  ├──────────────────────┐
  ▼                      ▼
T-019-05 (skills review) T-019-06 (memory tree)
  │                      │
  └──────────┬───────────┘
             ▼
        T-019-07 (propagation)
             │
             ▼
        T-019-08 (qa gate)
             │
             ▼
        T-019-09 (operator sign-off + push)
```

---

## Summary

| Task | Owner | Write-set summary | Preconditions |
|---|---|---|---|
| T-019-01 | ai-engineer | Read-only audit | T-018-09 DONE |
| T-019-02 | ai-engineer | `project-orchestration` + flagged personas | T-019-01 DONE |
| T-019-03 | ai-engineer | Delete 7 workflow files | T-019-02 DONE |
| T-019-04 | ai-engineer | Create 2 workflow files | T-019-03 DONE |
| T-019-05 | ai-engineer | 17 skills: review + 5 deletions | T-019-04 DONE |
| T-019-06 | product-engineer (+ project-auditor review) | `specs/memory/product/` restructure | T-019-04 DONE |
| T-019-07 | ai-engineer | All runtimes (manifest + projections) | T-019-05 AND T-019-06 DONE |
| T-019-08 | qa-engineer | `.dadaia/handoff/` ADDITIVE only | T-019-07 DONE |
| T-019-09 | project-manager / operator | `.dadaia/handoff/` ADDITIVE only | T-019-08 DONE |

**Total: 9 tasks.**
