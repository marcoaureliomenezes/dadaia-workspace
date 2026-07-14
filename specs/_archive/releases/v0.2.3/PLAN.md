# PLAN: v0.2.3 - Four-workflow consolidation

**Status:** Aprovado

## Approach

1. Collapse the governed catalog and CLI execution paths to four names.
2. Merge research and bug-intake responsibilities into backlog definition.
3. Merge implementation, retry, all reviews, and closure into one linear engine
   with bounded correction rounds.
4. Keep audit as the independent final verification/disposition workflow.
5. Reduce the handoff registry to schemas used by the four workflows and enforce
   one producer payload per attempted model step.
6. Update panel workflow cards, model policy, public guidance, and current memory.
7. Add the Games tab and its isolated Snake/Tetris implementation.
8. Execute four real phantom lifecycle journeys, alternating Codex and PI.

## Design constraints

- Python owns sequence and transitions; workers never approve themselves.
- Review steps remain additive and may not write production files.
- A correction round returns to implementation with the exact rejected review
  payload; no latest-file or implicit handoff lookup is allowed.
- Workflow command help must expose four execution commands clearly.
- Utility commands remain available under diagnostic namespaces without entering
  the governed catalog.
- No generated projections or runtime state may enter the repository.

## Verification

- Targeted workflow and handoff tests after every structural slice.
- Full unit/integration suite after consolidation.
- CLI help/catalog assertion: exactly four governed workflows.
- Real Codex and PI Layer-2 runs with persisted run/step evidence.
- Handoff doctor clean after every phantom release.
- Playwright screenshots and interaction checks for Games.
