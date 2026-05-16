# Game Agents Split — Design Doc

**Date:** 2026-05-16  
**Status:** Draft  
**Context:** dadaia-workspace / redacted-slug

---

## Context

The current `game-developer` agent is a monolithic implementer covering game logic, map design, visual assets, audio, and testing. As `redacted-slug-v2` targets Unreal Engine 5 with a photorealistic stack (JSBSim, Cesium, Nanite, Lumen, photogrammetric pipeline), this breadth makes the agent too shallow in each domain to produce high-quality output.

The goal is to split responsibilities into three purpose-built agents — `game-developer`, `game-designer`, and `game-tester` — each a deep specialist in its Unreal Engine domain, with active internet research capabilities, and integrated into three new game-exclusive workflows.

---

## Decision: Approach C — Layered Split

- Narrow `game-developer` to pure game logic.
- Create `game-designer` (design, assets, maps, audio) as a new agent.
- Create `game-tester` (UE5 automation, evidences, quality reports) as a new agent.
- Existing agents and workflows for non-game work are unchanged.
- `redacted-slug-trex` and existing `redacted-slug` remain functional (backward compatibility preserved).

---

## Section 1 — Agent Definitions

### `game-developer` (narrowed)

**Model:** claude-sonnet-4-6  
**Max turns:** 60  
**Tools:** Read, Write, Edit, Bash, Glob, Grep, WebFetch

**Exclusive domain:** game logic in `repos/redacted-slug/`

- Enemy AI: spawn patterns, behavior trees, difficulty scaling
- Player: input handling, movement, cooldowns, invincibility frames
- Ballistics: projectile trajectories, hitbox, damage calculation
- Game mechanics: lives, rounds, score, power-ups, game over, victory conditions
- UE5: C++ for performance-critical code (GameMode, GameState, PlayerController, Pawn, Components), Blueprints for gameplay scripting
- JSBSim: flight dynamics model integration (thrust, drag, lift, rudder, landing gear, ground effect, stall)
- Does NOT touch: visual assets, audio, terrain, materials, maps, tests

**Skills assigned:**
- `game-physics-engine` (existing)
- `game-platform-browser` (existing — backward compat)
- `game-platform-godot` (existing — ladder)
- `game-platform-unity` (existing — ladder)
- `game-platform-unreal` (existing — general ladder)
- `game-packaging-distribution` (existing)
- `game-unreal-developer` (new — deep UE5 logic + research protocol)
- `game-flight-dynamics` (new — JSBSim + aerodynamics)

---

### `game-designer` (new)

**Model:** claude-opus-4-7  
**Max turns:** 60  
**Tools:** Read, Write, Edit, Bash, Glob, Grep, WebFetch

**Exclusive domain:** design and static assets in `repos/redacted-slug/`

- Art direction: visual identity, color palette, aesthetic guides, design bible
- Level design: terrain layout, objectives positioning, combat zones
- Static assets via CLI/Python: heightfields, material instances, Houdini HDAs, Cesium config
- Lighting: Lumen setup, sky atmosphere, time-of-day, volumetric fog
- Audio: MetaSounds config, spatial audio, sound design specifications
- Geospatial pipeline: QGIS → GDAL/PDAL → RealityScan/Metashape → Cesium ion → Cesium for Unreal → UE5 Landscape/World Partition
- Active research: fetches map references and terrain data from safe public repositories (OSM, USGS, NASA EarthData, OpenTopography, Fab, Sketchfab CC)
- Does NOT touch: game logic, enemy AI, ballistics, flight physics, tests

**Skills assigned:**
- `game-map-architect` (migrated from game-developer)
- `game-unreal-designer` (new — deep UE5 design + map research protocol)
- `game-visual-design` (new — art direction, Nanite, Lumen, Megascans, post-process)
- `game-geospatial-pipeline` (new — QGIS, GDAL, Cesium, photogrammetry pipeline)
- `game-audio-design` (new — MetaSounds, spatial audio, public sound sources)

---

### `game-tester` (new)

**Model:** claude-opus-4-7  
**Max turns:** 40  
**Tools:** Read, Write, Edit, Bash, Glob, Grep, WebFetch

**Domain:** testing and quality validation in `repos/redacted-slug/`

- Defines acceptance criteria and test scenarios **before** implementation starts
- UE5 Functional Testing Framework: automated gameplay tests
- Gauntlet Automation Framework: performance and stress tests
- PIE screenshots: visual evidence of bugs and expected behaviors
- Quality reports: HTML with screenshots, logs, severity (Critical/High/Medium/Low), reproduction steps
- Bug reports classified and directed to game-developer (logic) or game-designer (design)
- Active research: Epic issue tracker, UE5 release notes, forums.unrealengine.com/c/development-discussion/testing-qa
- Does NOT write production code or game assets; writes only test scripts and reports

**Skills assigned:**
- `game-testing-ue5` (new — UE5 Automation, Gauntlet, PIE, report format, research protocol)

---

## Section 2 — Skill Architecture

### Existing skills — redistribution

| Skill | Previous owner | New owner | Action |
|---|---|---|---|
| `game-physics-engine` | game-developer | game-developer | kept |
| `game-platform-browser` | game-developer | game-developer | kept |
| `game-platform-godot` | game-developer | game-developer | kept |
| `game-platform-unity` | game-developer | game-developer | kept |
| `game-platform-unreal` | game-developer | game-developer | kept as general ladder |
| `game-map-architect` | game-developer | game-designer | migrated |
| `game-packaging-distribution` | game-developer | game-developer | kept |

### New skills (7)

#### `game-unreal-developer` → game-developer
Deep UE5 from the logic perspective: C++ Actor/Component/GameMode/GameState/PlayerController/Pawn lifecycle, UFUNCTION/UPROPERTY macros, Delegate system, Behavior Trees, EQS, Chaos Physics, Collision channels, NetRelevancy. Research protocol: Epic DevForum, forums.unrealengine.com, GitHub (UE5 examples/plugins), r/unrealengine, Stack Overflow — for gameplay patterns, version-specific bugs, reference implementations.

#### `game-flight-dynamics` → game-developer
JSBSim FDM integration with UE5: aerodynamic coefficients, propulsion models, landing gear, flight control system, autopilot basics, fixed-step simulation loop, ground effect, stall modeling, integration with Chaos Physics for collision events.

#### `game-unreal-designer` → game-designer
Deep UE5 from the design perspective: World Partition + Sublevels, Landscape sculpting/painting, PCG Framework (procedural vegetation, scatter, roads), Nanite mesh setup, Lumen configuration (sky light, HDRI, ray tracing budget), Megascans/Fab curation, Material Editor (layer blend, displacement, wetness, triplanar). **Map research protocol (critical):** active fetching from OpenStreetMap (ODbL — requires attribution), USGS EarthExplorer (DEM/terrain — public domain), NASA EarthData (satellite — public domain), OpenTopography (LiDAR — open access), Sketchfab (CC-licensed assets), ArtStation (visual references). Security rule: verify license before using any data; never use Google Maps/Earth/StreetView for 3D reconstruction.

#### `game-visual-design` → game-designer
Art direction protocol: design bible format, visual identity, color palette, aesthetic pillars, moodboard (textual + URL references), post-process volume (bloom, DoF, chromatic aberration, tone mapping, vignette), sky atmosphere, volumetric fog, time-of-day system, cinematic camera rigs for trailers/screenshots.

#### `game-geospatial-pipeline` → game-designer
End-to-end pipeline: QGIS (CRS validation, data inspection, raster/vector prep) → GDAL/PDAL (reprojection, mosaic, DEM processing, LiDAR classification) → RealityScan/Metashape (photogrammetry reconstruction, GCP setup, 3D Tiles export) → Cesium ion (upload, tiling, streaming) → Cesium for Unreal (globe setup, georeferencing, sublevel streaming) → UE5 Landscape import. Fidelity strategy: regional (heightfield), urban hotspots (3D Tiles), landmarks (local Nanite mesh). Legal: OSM ODbL attribution required; no Google data for reconstruction.

#### `game-audio-design` → game-designer
MetaSounds UE5: node graph fundamentals, Modulators, triggers, MetaSound Sources. Attenuation Shapes, Reverb Submix chains. Sound design specifications: jet turbines (frequency layering, Doppler shift), afterburner (harmonic distortion), wind (velocity-scaled), explosions (layered ADSR), cockpit ambience. Safe public sources: Freesound.org (CC0/CC-BY), ZapSplat free tier, BBC Sound Effects Library (verify license per use case).

#### `game-testing-ue5` → game-tester
UE5 Automation Testing Framework: FunctionalTest actor setup, `RunTests` CLI flags, test spec format. Gauntlet Automation Framework: perf capture, stat dumps, GPU timing. PIE screenshot automation: `TakeAutomationScreenshot`, screenshot comparison, diff thresholds. Report format: HTML with embedded screenshots, severity matrix (Critical/High/Medium/Low), reproduction steps, environment info (UE5 version, platform, changelist). Research protocol: Epic issue tracker (issues.unrealengine.com), UE5 release notes (version-specific breaking changes), forums.unrealengine.com/c/development-discussion/testing-qa, r/unrealengine — run before each test session to check known issues.

---

## Section 3 — Workflows

### `game-spec-definition.workflow.md` (new)

**Trigger:** new game or major evolution (e.g., redacted-slug-v2).

**Stages:**

| Stage | Agent | Needs | Parallel group | Output |
|---|---|---|---|---|
| `discovery` | product-engineer | — | — | Discovery report + open questions resolved via dadaia-grill-me |
| `arch-review` | software-architect | discovery [gate] | specialists | Architecture feasibility, patterns, tech decisions |
| `devops-review` | devops-engineer | discovery [gate] | specialists | UE5 build pipeline, CI/CD, deploy strategy |
| `gameplay-analysis` | game-developer | discovery [gate] | specialists | Mechanic viability, JSBSim feasibility, AI scope |
| `design-analysis` | game-designer | discovery [gate] | specialists | Map feasibility, asset pipeline, visual direction, research findings |
| `qa-criteria` | game-tester | discovery [gate] | specialists | Initial acceptance criteria, known UE5 risks for this scope |
| `synthesis` | product-engineer | specialists [gate] | — | SPEC.md draft → promotes to "Em revisão" after operator approval |

`arch-review`, `devops-review`, `gameplay-analysis`, `design-analysis`, `qa-criteria` run in parallel after gate.

---

### `game-dev-cycle.workflow.md` (new — exclusive for games)

**Trigger:** SPEC.md `Status: Aprovado` + TASKS.md task in OPEN state.

**Stages:**

| Stage | Agent | Needs | Output |
|---|---|---|---|
| `acceptance-criteria` | game-tester | approved spec | Test scenarios, expected behaviors, red test specs |
| `design-impl` | game-designer | acceptance-criteria [gate] | Static assets: terrain, materials, Lumen, audio, map layout |
| `logic-impl` | game-developer | design-impl [gate] | Game logic: AI, movement, ballistics, mechanics, JSBSim |
| `validation` | game-tester | logic-impl [gate] | UE5 Automation + Gauntlet + PIE screenshots → HTML quality report |

On validation failure: route to `game-designer` (design bugs) or `game-developer` (logic bugs) → re-validate.

---

### `game-bugfix.workflow.md` (new — fast-track)

**Trigger:** user-reported bug not caught by game-tester.

**Stages:**

| Stage | Agent | Needs | Output |
|---|---|---|---|
| `reproduce` | game-tester | bug report | Evidence (screenshots, logs), bug classification (design vs logic) |
| `fix` | game-designer OR game-developer | reproduce [gate] | Fix applied, test updated |
| `regression` | game-tester | fix [gate] | Regression suite result, test suite updated to prevent recurrence |

---

### `tdd-cycle.workflow.md` (update)

Remove `game-developer` from the parameterized implementer list. Game agents use `game-dev-cycle` exclusively.

```
Before: implementer_agent = frontend-engineer | backend-engineer | software-engineer | game-developer
After:  implementer_agent = frontend-engineer | backend-engineer | software-engineer
```

---

## Section 4 — Scope Rule Update

### `game-developer-scope.md` (updated)

Three agents share exclusive ownership of `repos/redacted-slug/`. Each has a distinct sub-domain:

| Agent | Sub-domain | Writes |
|---|---|---|
| game-developer | Logic | C++, Blueprints (gameplay), test fixtures |
| game-designer | Design | Python/CLI scripts, config files, asset specs, HDA |
| game-tester | Testing | Test scripts, quality reports (HTML) |

All other agents (product-engineer, software-architect, qa-engineer, software-engineer, devops-engineer, frontend-engineer, backend-engineer) may READ game files for context but NEVER write to `repos/redacted-slug/`.

Cross-domain rule: if a bug spans logic AND design, `game-tester` classifies it and directs each fix to the correct agent independently.

---

## Section 5 — Manifest Implications

**New entries (12):**
- 2 agents: `game-designer`, `game-tester`
- 7 skills: `game-unreal-developer`, `game-flight-dynamics`, `game-unreal-designer`, `game-visual-design`, `game-geospatial-pipeline`, `game-audio-design`, `game-testing-ue5`
- 3 workflows: `game-spec-definition`, `game-dev-cycle`, `game-bugfix`

**Modified entries (3):**
- 1 agent: `game-developer` (narrowed)
- 1 rule: `game-developer-scope` (updated)
- 1 workflow: `tdd-cycle` (implementer list)

**CLI after all changes:**
```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

---

## Implementation Prerequisites (SDD)

Before any file in `dadaia_workspace/public/` is created or modified, the following must reach `Status: Aprovado`:

- `repos/dadaia-workspace/specs/features/game-agents-split/SPEC.md`
- `repos/dadaia-workspace/specs/features/game-agents-split/PLAN.md`
- `repos/dadaia-workspace/specs/features/game-agents-split/TASKS.md`

Tasks tracked in main `specs/TASKS.md` under Fase 11 (T145–T165).
