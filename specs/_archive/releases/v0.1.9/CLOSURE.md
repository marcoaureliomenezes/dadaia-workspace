# Closure: Release — v0.1.9 (segment alpha-1)

> **Status:** Aprovado
> **Release ID:** v0.1.9
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Closed:** 2026-06-09

## Summary

v0.1.9 restores spec/memory fidelity across the workspace: all 34 confirmed findings of
the 2026-06-09 project-auditor drift audit (overall 7.0 CONDITIONAL) are resolved. No
new user-facing behaviour shipped. Memory atoms now describe the product as it actually
is (real doctor check codes, Python-hook gate, hard-gated 3-OS CI, correct CLI/protocol
inventories, correct skill count), the archived 0.1.6 CLOSURE was backfilled to doctor
compliance, and the code layering law was completed: no `features/` module imports
`subprocess` directly anymore — all process execution flows through the new
`ProcessRunner` Protocol (`core/protocols/process_runner.py`) implemented by
`infrastructure/subprocess_runner.py`, enforced by the `features-no-subprocess`
import-linter contract. The AI surface reached persona parity (9/9 `[SCOPE ERROR]`
blocks, report-emission dedup to `workspace-protocol §4`, vestigial `opencode_model`
removed, `dev-server-registry` wired to software-engineer). During the release window
the agent model assignments were retiered (`claude-fable-5` for 5 deep-reasoning
leaves; `claude-opus-4-8` for the remainder), captured in tech-stack memory at closure.

## Tasks completed

All 18 tasks landed in the release commit `88b1044` ("feat(release): v0.1.9 —
Spec/Memory Fidelity (34-finding drift audit resolution)"); the model retier landed in
`8ccfa7a` ("Fable 5 retier"). Per-task SHAs were squashed into the release commit by
the coordinator; mapping below is release-level.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-MEM-01 | workspace-doctor.md LEASE→LOCK-NEW/INV-4/INV-5/SENTINEL-GC codes | `88b1044` |
| T-MEM-02 | architecture.md CLI/protocols/features coverage + bash-gate ref | `88b1044` |
| T-MEM-03 | sdd-gate-v3.md bash→Python hook + release_origin | `88b1044` |
| T-MEM-04 | release_origin: context-management, panel, workspace-init | `88b1044` |
| T-MEM-05 | cross-platform-portability.md hard-gated 3-OS CI section | `88b1044` |
| T-MEM-06 | specs-doctor.md check-ID enumeration (SPEC-DOC + TREE-5M) | `88b1044` |
| T-MEM-07 | tech-stack.md PM model + CLI commands | `88b1044` |
| T-MEM-08 | Skill count 17→18 in catalog.json + index.md | `88b1044` |
| T-SPEC-01 | constitution.md §7 phantom `researcher` removed | `88b1044` |
| T-SPEC-02 | quality-assurance.md stale deletion sentence removed | `88b1044` |
| T-SPEC-03 | 0.1.6 CLOSURE backfill (Summary/Validations/Drifts/Memory updates) | `88b1044` |
| T-CODE-01 | features subprocess → ProcessRunner Protocol + adapter + import-linter | `88b1044` |
| T-CODE-02 | container.py PLATFORM singleton replaces inline sys.platform | `88b1044` |
| T-AI-01 | dev-server-registry skill wired to software-engineer | `88b1044` |
| T-AI-02 | [SCOPE ERROR] block added to 5 personas (9/9 parity) | `88b1044` |
| T-AI-03 | ai-context-engineering I1 schema refresh | `88b1044` |
| T-AI-04 | Report-emission verbatim block dedup from persona bodies | `88b1044` |
| T-AI-05 | opencode_model vestigial key removed | `88b1044` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full pytest suite green (2510 passed) at implementation time | `pytest` | `88b1044` (coordinator-attested at commit time) |
| `dadaia specs doctor` 0 errors at implementation time | `dadaia specs doctor` | `88b1044` (coordinator-attested at commit time) |
| workspace-doctor.md carries real codes, no LEASE-1..4 | `rg "LEASE-[1-4]\|LOCK-NEW" specs/memory/product/platform/workspace-doctor.md` | ``LOCK-NEW (doctor.py:300), INV-4 (doctor.py:376), INV-5 (doctor.py:389), SENTINEL-GC e PTR-GC`` — LEASE-1..4 present only as explicit "não existem no código" disclaimer |
| No phantom `researcher` in constitution | `rg researcher specs/constitution.md` | ``No matches found`` |
| No direct `subprocess` import in `features/` | `rg "import subprocess" dadaia_workspace/features/` | only ``from dadaia_workspace.infrastructure.subprocess_runner import …`` (adapter import, ci_preflight/service.py:70) |
| ProcessRunner seam exists and is consumed via DI | `rg ProcessRunner dadaia_workspace/` | ``core/protocols/process_runner.py:24 class ProcessRunner(Protocol)``; consumed by features/import_, features/specs/doctor, features/ci_preflight, features/server_registry |
| import-linter forbids features→subprocess | `rg features-no-subprocess setup.cfg` | ``[importlinter:contract:features-no-subprocess] / type = forbidden`` |
| container.py uses PLATFORM singleton | `rg "PLATFORM\|sys.platform" dadaia_workspace/container.py` | ``from dadaia_workspace.core.platform import PLATFORM`` — no inline `sys.platform` comparison |
| [SCOPE ERROR] parity 9/9 personas | `rg -c "SCOPE ERROR" dadaia_workspace/public/agents/` | ``9 files, 9 occurrences`` |
| opencode_model vestigial key gone | `rg opencode_model dadaia_workspace/public/agents/` | ``No matches found`` |
| dev-server-registry wired | `rg dev-server-registry dadaia_workspace/public/agents/` | ``software-engineer.md:21: - dev-server-registry`` |
| Skill count recorded as 18 | `rg "18 skills" specs/memory/product/index.md` | ``index.md:30 … 9 agents / 18 skills / 2 workflows`` |
| specs-doctor.md check IDs match emissions | inspection of `specs/memory/product/sdd/specs-doctor.md` | atom lists SPEC-DOC 001,002,002L,003..009,012,016 + TREE-1..7+TREE-5M, no TREE-8 |

## Drifts

### report-emission-heading-retained

**Description:** AC-AI-04 states no persona body contains the verbatim "Report
emission" inline block. `project-manager.md:169` still carries a `## Report emission`
heading — but the ~72-line verbatim block was replaced by a 4-line pointer to
`workspace-protocol §4`, which is the dedup the finding demanded.

**Resolution:** Accepted — the duplication (the actual defect) is gone; the heading is
a pointer, consistent with the pattern used by other personas. Recorded for the
acceptance-wording mismatch.

**Memory updates:** none.

### residual-bash-gate-references-in-memory

**Description:** The TASKS final gate said "no `sdd-spec-gate.sh` in memory". Five
memory files still mentioned it. Three (sdd-gate-v3.md, architecture.md,
tech-stack.md) describe the bash scripts accurately as retained legacy fallback — the
scripts still exist in `dadaia_workspace/public/scripts/` — so those mentions are
correct current truth and were kept. Two (context-management.md:32,
spec-context-project.md:36) wrongly presented `sdd-spec-gate.sh` as the *current* gate.

**Resolution:** The two stale sentences were corrected at CLOSURE to the Python hook
(`python -m dadaia_workspace.hooks.sdd_gate`).

**Memory updates:** `specs/memory/product/platform/context-management.md`,
`specs/memory/product/philosophy/spec-context-project.md`.

### frontmatter-not-bumped-on-corrected-atoms

**Description:** T-MEM-01/T-MEM-06 corrected atom bodies but left
`last_updated`/`release_origin` stale (workspace-doctor.md at v0.2.0, specs-doctor.md
at v0.2.1), and `catalog.json` still carried the pre-fix tldr/summary for both atoms.

**Resolution:** Frontmatter bumped to v0.1.9 / 2026-06-09 at CLOSURE; the two
catalog.json entries refreshed by hand to mirror the atom frontmatter (PE has no shell
to run the catalog regenerator; coordinator should re-run it for canonical
`generated_at`).

**Memory updates:** `specs/memory/product/platform/workspace-doctor.md`,
`specs/memory/product/sdd/specs-doctor.md`, `specs/memory/product/catalog.json`.

### model-retier-fable-5

**Description:** During the release window, commit `8ccfa7a` retiered agent models:
`claude-fable-5` for project-auditor, product-engineer, ai-engineer, qa-engineer,
software-architect; `claude-opus-4-8` for software-engineer, security-reviewer,
code-reviewer (project-manager unchanged). tech-stack.md still showed the
pre-retier table (default `claude-sonnet-4-6`).

**Resolution:** tech-stack.md model-assignment table and intro updated at CLOSURE to
the verified frontmatter of `dadaia_workspace/public/agents/*.md`.

**Memory updates:** `specs/memory/tech-stack.md`.

### active-md-phase-drift

**Description:** `ACTIVE.md` remained at `phase: SPEC` throughout implementation
(flagged by audit); memory writes for T-MEM-* were performed under the DEFINITION-phase
authorization rather than a phase-accurate pointer.

**Resolution:** ACTIVE.md set to `phase: CLOSURE` before CLOSURE memory writes, then
repointed to v0.1.10 at archive time.

**Memory updates:** none (ACTIVE.md is not memory).

## Memory updates

Written during this CLOSURE phase:

- `specs/memory/tech-stack.md` — model retier (fable-5/opus-4-8 two-tier table); `release_origin: v0.1.9`.
- `specs/memory/architecture.md` — `core/protocols/` 21 files incl. `process_runner`; `subprocess_runner` adapter + `features-no-subprocess` contract documented; `release_origin: v0.1.9`.
- `specs/memory/product/platform/context-management.md` — gate reference corrected to Python hook; `release_origin: v0.1.9`.
- `specs/memory/product/philosophy/spec-context-project.md` — gate reference corrected to Python hook; `release_origin: v0.1.9`.
- `specs/memory/product/platform/workspace-doctor.md` — frontmatter bump only (body fixed in T-MEM-01).
- `specs/memory/product/sdd/specs-doctor.md` — frontmatter bump only (body fixed in T-MEM-06).
- `specs/memory/product/catalog.json` — workspace-doctor + specs-doctor entries refreshed; `generated_at` bumped.

Already written during DEFINITION under release tasks (T-MEM-01..08, T-SPEC-01..02):
workspace-doctor.md, architecture.md, sdd-gate-v3.md, context-management.md, panel.md,
workspace-init.md, cross-platform-portability.md, specs-doctor.md, tech-stack.md,
quality-assurance.md, index.md, catalog.json, constitution.md (§7).

Not updated, with reason:

- `specs/memory/product/index.md` — no change at CLOSURE: catalog order unchanged; skill count already corrected by T-MEM-08.
- `specs/memory/product/sdd/sdd-gate-v3.md` — no change at CLOSURE: bash scripts correctly described as retained fallback.

## Backlog returns

- None new from this release. `candidates.md` Priority-Index curation was routed to
  project-manager in the SPEC (backlog-ownership, ADDITIVE path). The 6 open bugs
  discovered around this release window are already folded into the v0.1.10 specs.

## Archive decision

**MOVE** — release directory `specs/releases/v0.1.9/` moves to
`specs/_archive/releases/v0.1.9/` (top-level target verified collision-free; the
nested legacy dirs under `specs/_archive/releases/v0.2.0/` are untouched).
product-engineer has no shell tool; the coordinator executes:

```bash
git mv specs/releases/v0.1.9 specs/_archive/releases/v0.1.9
```

ACTIVE.md repointed to `release: v0.1.10 / segment: alpha-1 / phase: DEFINITION`.
