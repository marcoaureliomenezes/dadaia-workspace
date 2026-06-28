# PLAN: v0.1.36 alpha-1 - PI Layer-2 Release-Definition Hardening

**Status:** Aprovado
**Release ID:** v0.1.36
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

---

## Approach

1. Update the PI model truth surface: registry, discrete harness catalog, built-in PI
   profiles, and tests must use the live PI Codex model id `gpt-5.3-codex-spark`.
2. Harden `PiHeadlessAdapter` command construction so bare GPT ids are qualified as
   `openai-codex/<id>` and effort is forwarded through `--thinking`.
3. Fix release-definition `--step-model` routing by carrying label-specific model
   selections into each request as `resolved_model`, while preserving the existing
   default model-by-harness fallback.
4. Tighten release-definition create fragments so `spec_create`, `plan_create`, and
   `tasks_create` explicitly materialize canonical artifacts and report hash evidence.
5. Add a persisted active-worker marker around live release-definition worker calls so
   PI/Codex workflow state is observable while the adapter is still running.
6. Update bug records and validate with targeted unit/integration coverage, followed by a
   live PI smoke/release-definition run.

## Coverage

| Requirement | Workstream |
|---|---|
| R1 | PI adapter command hardening |
| R2 | Catalog/profile refresh |
| R3 | Release-definition step-label model routing |
| R4 | Create-fragment artifact contract |
| R5 | Bug notes and validation evidence |
| R6 | Active-worker lifecycle state marker |
