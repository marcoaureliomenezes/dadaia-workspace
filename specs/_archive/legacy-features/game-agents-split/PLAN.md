# PLAN: Game Agents Split

**Status:** Aprovado
**Reference:** `docs/superpowers/plans/2026-05-16-game-agents-split.md`

## Approach

Content-creation plan. All artifacts are Markdown + YAML files in
`dadaia_workspace/public/`. Propagated to all runtimes via dadaia CLI after
all files are written.

## Execution Order

1. Rules: game-agents-coordination (new), game-developer-scope (update)
2. Agents: game-developer (update), game-designer (new), game-tester (new)
3. Skills: 7 new files (game-unreal-developer through game-testing-ue5)
4. Workflows: 3 new (game-spec-definition, game-dev-cycle, game-bugfix) + tdd-cycle update
5. Propagation: dadaia public stage && install --target all && doctor
