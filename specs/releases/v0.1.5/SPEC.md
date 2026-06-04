# SPEC: v0.1.5 — session-bind and codex-orchestration bug fix

**Status:** Aprovado
**Release ID:** v0.1.5
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Objective

Fix the two critical bugs currently reported under `specs/bugs/`:

1. `session-bind-primary-residue` — the codebase and projected assets still
   contain retired global primary-context semantics even though the active model
   is session-bound via `dadaia context bind`.
2. `codex-agent-orchestration-mismatch` — Codex orchestration claims real
   parallel/subagent dispatch even though the implemented dispatcher writes
   manual handoff invocation files.

The release must make the product honest and mechanically consistent: context
resolution is session-bound everywhere outside archived history and explicit
legacy migration cleanup, and Codex orchestration either truly spawns supported
subagents or is documented and reported as manual/reference-only.

## 2. Versioning model

- Release folder: `v0.1.5`.
- `pyproject.toml` may be bumped from `0.1.4` to `0.1.5` only if the operator
  chooses to publish this release.
- No branch creation is required; work continues on the current branch.

## 3. Source bugs

### BUG-CTX — session-bind-primary-residue

Source: `specs/bugs/session-bind-primary-residue.md`

Acceptance criteria:

- `rg -n "primary_context|is_primary|context promote|context activate" dadaia_workspace/public dadaia_workspace/cli dadaia_workspace/core dadaia_workspace/infrastructure specs/memory`
  returns zero matches except explicit migration code that only deletes legacy
  state. Archived release history is excluded from this check.
- `sdd-spec-gate.sh` no longer uses `PRIMARY_*` identifiers or first-ALIVE
  fallback semantics; variable names and behavior reflect session-bound context.
- `dadaia specs doctor`, `dadaia memory`, `dadaia migrate`,
  `dadaia newartifacts`, and `dadaia orchestrate` do not ask operators to run
  removed `activate` or `promote` flows.
- Generated `AGENTS.md`, Codex skills, Claude skills, and OpenCode assets all
  describe `dadaia context bind` as the active context mechanism.

### BUG-CODEX — codex-agent-orchestration-mismatch

Source: `specs/bugs/codex-agent-orchestration-mismatch.md`

Acceptance criteria:

- The implementation chooses one honest Codex mode:
  - real subagent spawning through a supported integration point, or
  - manual/reference-only Codex orchestration.
- If manual/reference-only is chosen, `CodexAgentDispatcher.capabilities()` must
  not advertise true parallel execution. It must either set
  `supports_parallel=False` or expose a distinct partial/manual capability.
- Codex-facing invocation text, project-manager wording, orchestration memory,
  and public doctor/runtime parity output must not imply that the CLI can spawn
  Codex subagents.
- Regression tests prove the generated Codex orchestration output and reported
  capabilities match the chosen behavior.

## 4. Constraints

- Do not create another branch.
- Do not edit archived release history except through `git mv` during release
  archival.
- Do not remove legacy migration code whose only purpose is deleting or
  detecting retired primary-context state; make that exception explicit in code
  comments/tests.
- Keep generated runtime projections managed only through
  `dadaia public stage` and `dadaia public install --target all --force`.

## 5. Memory files affected at closure

- `specs/memory/product/context-management.md`
- `specs/memory/product/sdd-gate-v3.md`
- `specs/memory/product/agent-orchestration.md`
- `specs/memory/architecture.md`
- `specs/memory/tech-stack.md` only if dependencies or runtime support change.

## 6. Acceptance criteria

**AC-CTX-01** — No active source, public asset, CLI help, or memory atom refers
to global primary-context operation or removed context verbs, except explicit
legacy deletion/migration code.

**AC-CTX-02** — `dadaia specs doctor` resolves the bound context or provides
current `context bind` guidance; it never says `context activate`.

**AC-CTX-03** — SDD gate terminology and behavior are session-bound, with no
`PRIMARY_*` identifiers or first-ALIVE fallback.

**AC-CODEX-01** — Codex dispatcher capabilities match reality.

**AC-CODEX-02** — Codex-facing persona/orchestration text does not overclaim
agent spawning or parallel execution.

**AC-CODEX-03** — Tests cover both bug fixes.

**AC-CHAIN-01** — `dadaia public stage`, `dadaia public install --target all
--force`, `dadaia public doctor`, `dadaia specs doctor`, and unit tests exit 0.
