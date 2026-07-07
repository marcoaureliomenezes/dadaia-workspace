# OQ-DECISIONS: v0.1.41 - Open bug root-cause sweep

**Status:** Aprovado
**Release ID:** v0.1.41
**Created:** 2026-06-29

## Decisions

### OQ-1 - Scope boundary

Only open `dadaia-workspace` bugs are in scope. Open bugs in other contexts remain in their
own project ledgers.

### OQ-2 - Active release handling

Do not change `specs/releases/ACTIVE.md` while `v0.1.40 alpha-1` is in implementation.
`v0.1.41` is a prepared next release, not the current active release.

### OQ-3 - Fake workflow output

The workflow-first requirement is satisfied by running `dadaia lifecycle release define`.
Because the fake harness only writes placeholders, the canonical artifacts are manually
refined from the inspected bug/root-cause set.

### OQ-5 - Newly observed cleanup bug

`context-release-ignores-persisted-bind-and-requires-dadaia_session_id-env` is included in
the persisted-bind workstream because it has the same root cause class as the specs-doctor
bind bugs and was observed while releasing the v0.1.41 implementation bind.

### OQ-4 - Panel CSP bug disposition

The panel CSP record is picked even though its body says the code fix already landed.
The release task is to verify the current behavior and close the stale bug, adding a guard
only if verification fails.
