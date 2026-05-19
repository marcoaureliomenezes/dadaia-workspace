# Closure: Release — agents-r1-v1

> **Status:** Aprovado
> **Release ID:** agents-r1-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-18
> **Branch:** `release/agents-r1-v1` (cut from `main` at `427ab86`, post `panel-r3-v1` archive)

## Summary

Refactored the dadaia-workspace agent topology from a flat 10-agent / 12-workflow set with a
single overloaded `product-engineer` orchestrator into an explicit **3-tier dispatcher
architecture**: 2 orchestrators (`project-manager`, `project-auditor`, Opus 4.7 with `Agent`
tool) at Tier 1; 1 curator (`product-engineer`, slimmed to spec-author leaf with `Agent`
tool removed) at Tier 2; and 13 leaf specialists (Tier 3) including 4 new
(`code-reviewer`, `researcher`, `security-reviewer`, `design-specialist`, all Sonnet 4.6
without `Agent` tool) plus the 9 existing implementers (`Agent` stripped from 8 of them).

Five new skills, three new rules, six refactored workflows (PE → PM orchestrator swap),
and three new workflows (`audit-cycle`, `code-review-fan-out`, `design-validation`)
shipped alongside. The reader gained a declarative `paths` field (enforcement deferred to
`agents-r2-v1`). Ten panel test files were updated for the 16-agent + 15-workflow
topology; 636 unit tests pass. Production source outside `dadaia_workspace/features/agents/reader.py`
remains untouched.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| AGT-01..AGT-08 | P1 foundations: 3 new rules, 3 rule updates, grill-me preamble, 5 skill stubs | `260bb6f` |
| AGT-09..AGT-14 | P2 6 new agents (project-manager, project-auditor, code-reviewer, researcher, security-reviewer, design-specialist) | `2961bbc` |
| AGT-15..AGT-17 | P2 slim PE/FE + strip `Agent` tool from 8 leaf agents (4 implementers in this commit; 4 game agents covered by AGT-17 frontmatter sweep) | `d35bf5d` |
| AGT-18..AGT-22 | P3 5 skill bodies (project-orchestration, architecture-code-review, security-audit-protocol, drift-detection, ux-ui-review) | `977abec` |
| AGT-23..AGT-28 | P4 refactor 6 existing workflows (PE → PM swap) | `30da523` |
| AGT-29..AGT-31 | P5 3 new workflows (audit-cycle, code-review-fan-out, design-validation) | `30da523` |
| AGT-32, AGT-33 | P6 reader `paths` field + 10 panel test updates | `493f464` |
| AGT-34 | P7 consumer-repo `dadaia public doctor` sweep | `2f4312c` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| All 16 agents load via `MarkdownAgentStore` and panel renders 16 cards | `dadaia panel` smoke check (operator verified) | Operator OK: "16 agents (was 10) + 15 workflows (was 12)" (DoD §13) |
| `Agent` tool restricted to PM + auditor only | `grep -nE '^\s*-?\s*Agent\b' dadaia_workspace/public/agents/*.md` | Returns only `project-manager.md` and `project-auditor.md` (C5) |
| All 15 workflows load + `audit-cycle` DAG renders 4-way parallel | `dadaia public doctor` | 305 ok / 0 err / 0 drift |
| Reader `paths` field declarative | `pytest -q tests/unit/features/agents/test_reader.py` | green (commit `493f464`) |
| Full unit suite green for new topology | `pytest -q tests/` | 636 passed (P6 evidence) |
| SDD structural invariants | `dadaia specs doctor` | `[ok] 0 errors, 0 warnings` |
| Canonical → projection chain consistent | `dadaia public stage && dadaia public install --target all && dadaia public doctor` | `[ok]` 305/305 (commit `30da523` and re-run at P7) |
| Consumer-repo projections in sync | `dadaia public doctor` in every consumer repo (P7 sweep) | All `[ok]` or documented `[not-applicable]` (Codex workflows) — commit `2f4312c` |
| Branch cut point preserved | `git log --oneline 427ab86..HEAD` | 12 commits since cut; HEAD = `2f4312c` |

## Drifts

None. P0..P7 executed exactly per PLAN.md phase plan; no deviations required. AGT-17's
single-task strip of `Agent` from 8 leaf implementers was committed together with the
PE/FE slim (AGT-15/16) in `d35bf5d` instead of as a separate commit — this is a commit
granularity choice, not a content drift, and matches the AGT-17 parallel-safe note in
TASKS.md.

## Memory updates

- `specs/memory/architecture.html` — `<section id="layers">` updated to note the 3-tier
  agent topology (Tier 1 orchestrators with `Agent` tool, Tier 2 curator, Tier 3 leaf
  specialists); `<section id="runtime-state">` `.dadaia/reports/<context>/<agent>/` note
  now reflects 16 agent directory names.
- `specs/memory/product/index.html` — `<section id="users">` agent count bumped from
  "10+" to 16; `<section id="catalog">` `agent-orchestration` entry description updated
  to "16 agents, 3-tier dispatcher + 15 workflows pré-instalados"; `<section id="capability-map">`
  Mermaid `WF[11 workflows]` updated to `WF[15 workflows]`.
- `specs/memory/product/agent-orchestration.html` — atomic re-render reflecting new
  topology: purpose mentions 3-tier dispatcher; flow lists 15 workflows; sequence diagram
  shows PM (orchestrator) dispatching specialists with PE as leaf for spec write;
  dependencies updated.
- `specs/memory/tech-stack.html` — **no change**: release did not touch dependencies.

## Backlog returns

- `backlog/candidates.md` ← Promote `paths` field from declarative to gate-enforced
  (target release: `agents-r2-v1`).
- `backlog/candidates.md` ← Sub-agent promotion of `dadaia-grill-me` (target release:
  `agents-r2-v1`).
- `backlog/candidates.md` ← Tighten PE line budget below 280 and FE below 230 after
  this release stabilizes (current ship is at the budget ceiling, not below it; verify
  with `wc -l` and trim non-essential sections).

(`specs/backlog/ideas.md` deliberately untouched — operator working memory.)

## Archive decision

**MOVE** — release directory moved to `specs/_archive/releases/agents-r1-v1/` via
`git mv`. `specs/releases/ACTIVE.md` updated to `release: none / phase: none`.
