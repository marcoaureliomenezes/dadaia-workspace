---
title: session-bind-primary-residue
severity: Critical
opened: 2026-06-04
session_id: sess_6bf8281d
status: Closed
closed: 2026-06-04
closed_by_release: v0.1.4.2
---

# Bug: session-bind-primary-residue

## Description

The v2 context model is session-bound only, but shipped source, public agent
assets, CLI help text, memory atoms, and generated root rules still contain
the retired global primary-context model.

This is not only stale wording. It causes agents and tools to prefer
`primary_context.json`, `is_primary`, `context promote`, or fallback "first
ALIVE" resolution even though the product truth says each agent session must
bind context explicitly with `dadaia context bind`.

Impact:

- Hooks and gates can resolve the wrong context when `DADAIA_CONTEXT` is not
  inherited by the runtime.
- Agents receive contradictory instructions: session bind is required, but
  projected skills still describe global primary context.
- Specs doctor and related commands can fail or ask operators to run removed
  verbs such as `activate`.
- The codebase cannot honestly claim v2 context semantics while primary
  fallback paths remain executable.

## Steps to reproduce

1. From the workspace root, run:
   `rg -n "primary_context|PRIMARY_|is_primary|context promote|context activate" repos/dadaia-workspace/dadaia_workspace repos/dadaia-workspace/specs`
2. Observe live source hits in:
   - `dadaia_workspace/infrastructure/json_primary_context_store.py`
   - `dadaia_workspace/core/protocols/primary_context_store.py`
   - `dadaia_workspace/cli/commands/{specs,memory,migrate,newartifacts,orchestrate}.py`
   - `dadaia_workspace/public/scripts/sdd-spec-gate.sh`
   - `dadaia_workspace/public/skills/dadaia-workspace-manager/SKILL.md`
   - `dadaia_workspace/public/data/AGENTS.md`
   - memory atoms under `specs/memory/**`
3. Expected: v2 source and generated assets resolve context only from the
   current bound session (`DADAIA_CONTEXT` / `DADAIA_SESSION_ID` plus session
   state) and never mention or execute a global primary context.
4. Actual: multiple shipped paths still mention and/or execute primary-context
   logic.

## Environment

- dadaia version: `0.1.4` from `pyproject.toml`
- active release: `v0.1.4.1` / `IMPLEMENTATION`
- OS: Ubuntu Linux 24.04 family, kernel `6.17.0-29-generic`
- Python: `3.12.3`

## Root cause hypothesis

The v2 migration removed `primary_context.json` as product truth, but the
cleanup was partial and mixed two incompatible transition strategies:

- old primary-context store/protocol classes were left in source;
- public assets and skills were not fully regenerated from v2 semantics;
- some gate/spec tasks marked primary cleanup done while their acceptance
  criteria still allowed fallback global context resolution;
- memory atoms were updated inconsistently, leaving session-bind truth and
  primary-context references side by side.

## Acceptance criteria for fix

- `rg -n "primary_context|is_primary|context promote|context activate" dadaia_workspace/public dadaia_workspace/cli dadaia_workspace/core dadaia_workspace/infrastructure specs/memory`
  returns zero matches except archived release history and explicit migration
  code that only deletes legacy state.
- `sdd-spec-gate.sh` no longer uses `PRIMARY_*` identifiers or first-ALIVE
  fallback semantics; names reflect session-bound context.
- `dadaia specs doctor`, `dadaia memory`, `dadaia migrate`, `dadaia newartifacts`,
  and `dadaia orchestrate` do not ask for removed `activate`/`promote` flows.
- Generated `AGENTS.md`, Codex skills, Claude skills, and OpenCode assets all
  describe session bind as the only active context mechanism.

## Resolution

Resolved by archived release `specs/_archive/releases/v0.1.4.2/`.

Evidence is recorded in `specs/_archive/releases/v0.1.4.2/CLOSURE.md`:

- `T-BUG-01` classified the only allowed legacy primary-context exceptions.
- `T-BUG-02` removed source-level session-bind primary residue.
- `T-BUG-03` removed public asset and memory residue.
- `T-BUG-06` added regression coverage.
- `T-BUG-10` propagated generated assets and verified the release.

The closure validation records the residue scan result: active source and memory
hits are limited to explicit migration cleanup code that deletes retired legacy
state.
