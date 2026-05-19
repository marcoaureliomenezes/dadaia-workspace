# SPEC: Game Agents Split

**Status:** Aprovado
**Version:** 1.0
**Context:** dadaia-workspace

## Problem

The monolithic `game-developer` agent covers game logic, map design, visual assets,
audio, and testing simultaneously. With `redacted-slug-v2` targeting Unreal Engine 5
(JSBSim + Cesium + Nanite + Lumen + photogrammetric pipeline), the agent is too shallow
in each domain to produce high-quality output.

## Solution

Split into three purpose-built agents, each a deep UE5 specialist with WebSearch
and trusted-source whitelists, integrated into game-exclusive workflows.

## Agents

| Agent | Model | Domain |
|---|---|---|
| `game-developer` | claude-sonnet-4-6 | Game logic: AI, physics, ballistics, mechanics, JSBSim |
| `game-designer` | claude-opus-4-7 | Design: maps, materials, audio, art direction, geospatial pipeline |
| `game-tester` | claude-opus-4-7 | Quality: UE5 Automation, Gauntlet, PIE screenshots, reports |

## New Skills (7)

| Skill | Agent |
|---|---|
| `game-unreal-developer` | game-developer |
| `game-flight-dynamics` | game-developer |
| `game-unreal-designer` | game-designer |
| `game-visual-design` | game-designer |
| `game-geospatial-pipeline` | game-designer |
| `game-audio-design` | game-designer |
| `game-testing-ue5` | game-tester |

Migrated: `game-map-architect` moves from game-developer → game-designer.

## New Workflows (3)

| Workflow | Trigger |
|---|---|
| `game-spec-definition` | New game or major evolution; replaces spec-refinement for game contexts |
| `game-dev-cycle` | Approved spec + open task in TASKS.md |
| `game-bugfix` | User-reported bug not caught by game-tester |

Updated: `tdd-cycle` removes `game-developer` from implementer list.

## New Rule (1)

`game-agents-coordination.md` — Decision Authority Matrix + anti-deadlock protocol
with `dadaia-grill-me` as tie-breaker.

## ADRs

- ADR-GAME-001: `redacted-slug-v2` in `repos/redacted-slug/redacted-slug-v2/`
- ADR-GAME-002: WebSearch for all 3 game agents with per-skill trusted source whitelist
- ADR-GAME-003: game-spec-definition replaces spec-refinement selectively for game contexts
- ADR-GAME-004: backend-engineer + frontend-engineer optional via `include_web_specialists=true`
- ADR-GAME-005: Decision Authority Matrix as always-active rule; conflicts trigger dadaia-grill-me

## Acceptance Criteria

- [ ] `dadaia public doctor` shows `[ok]` for all 13 new entries and 3 modified entries
- [ ] `game-designer` and `game-tester` agents load correctly in Claude Code
- [ ] `game-developer-scope.md` names all 3 game agents with their sub-domains
- [ ] `game-agents-coordination.md` rule is always active in game contexts
- [ ] `game-spec-definition` workflow validates cleanly via `dadaia public stage`
- [ ] `game-dev-cycle` workflow validates cleanly via `dadaia public stage`
- [ ] `game-bugfix` workflow validates cleanly via `dadaia public stage`
- [ ] `tdd-cycle` implementer list no longer includes `game-developer`
