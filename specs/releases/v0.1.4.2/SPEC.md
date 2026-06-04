# SPEC: v0.1.4.2 — session-bind, codex-orchestration, and review-gate bug fix

**Status:** Aprovado
**Release ID:** v0.1.4.2
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
3. Development/review workflow gap — implementers, QA, security reviewers, and
   code reviewers do not share one strict lifecycle contract from SPEC agreement
   through final approval. This allows implementation to be treated as "done"
   before QA/security/code review have signed off, which is unacceptable for
   quality and privacy/security posture.

The release must make the product honest and mechanically consistent: context
resolution is session-bound everywhere outside archived history and explicit
legacy migration cleanup, Codex orchestration either truly spawns supported
subagents or is documented and reported as manual/reference-only, and the
development lifecycle has an enforceable review/QA gate before task closure,
push, PR, or release closure.

## 2. Versioning model

- Release folder: `v0.1.4.2`.
- `pyproject.toml` stays at `0.1.4` in this release. No package version bump is
  authorized here.
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

### BUG-WORKFLOW — implementation-review-qa-contract

Source: operator escalation on 2026-06-04.

Problem:

- SDD defines how approved tasks are implemented, but not a strict enough
  lifecycle for how implementers, `qa-engineer`, `security-reviewer`, and
  `code-reviewer` collaborate before and after implementation.
- Reviewers and QA are accountable for final approval, but they are not required
  to agree with task testability/security/review criteria before implementation
  starts.
- Implementers can treat their work as complete after local tests, even though
  the actual quality gate must be reviewer and QA approval.
- The process does not strongly prevent privacy leaks, secret leaks,
  consumer-specific public asset leakage, or security regressions before push,
  PR, or deploy.

Acceptance criteria:

- SPEC/PLAN/TASKS approval requires a **pre-implementation agreement gate**:
  the relevant implementer agent(s), `qa-engineer`, `code-reviewer`, and
  `security-reviewer` must review the planned tasks before implementation starts.
- Each TASKS.md item must explicitly state:
  - implementation scope and owning implementer;
  - unit/integration test obligations owned by the implementer;
  - E2E/validation obligations owned by `qa-engineer`;
  - security/privacy checks owned by `security-reviewer`;
  - code-review checks owned by `code-reviewer`;
  - the final approval evidence required before `[x]`.
- After implementation, the task remains **not done** until `qa-engineer`,
  `security-reviewer`, and `code-reviewer` each return an approving report or
  handoff sidecar. `design-specialist` is also required for visible UI changes.
- If any reviewer rejects, `project-manager` must route the issue back to the
  owning implementer. The same task remains active until fixes and re-review
  pass.
- Push, PR creation, merge, deploy, and task `[x]` are forbidden until the
  review/QA gate is green.
- The workflow must define project-manager obligations clearly enough that PM
  can conduct the entire development and validation loop without relying on
  informal operator memory.

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
- `specs/memory/product/agent-comms.md`
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

**AC-WORKFLOW-01** — Public workflows and project-manager playbooks define a
mandatory pre-implementation agreement gate before TASKS approval: implementer,
QA, code reviewer, and security reviewer must agree the task is implementable,
testable, reviewable, and security-checkable.

**AC-WORKFLOW-02** — Implementer personas and task protocol state that local
implementation completion is not task completion. A task reaches `[x]` only
after required QA, security, and code-review approvals are recorded.

**AC-WORKFLOW-03** — `project-manager` is explicitly responsible for routing the
implementation → review/QA → rework loop and for blocking push/PR/deploy/closure
when any reviewer rejects or approval evidence is missing.

**AC-WORKFLOW-04** — Security/privacy gates explicitly include secret scanning,
public-asset privacy leakage checks, auth/access-control review when relevant,
and validation that generated public assets contain no private project/customer
data.

**AC-CHAIN-01** — `dadaia public stage`, `dadaia public install --target all
--force`, `dadaia public doctor`, `dadaia specs doctor`, and unit tests exit 0.
