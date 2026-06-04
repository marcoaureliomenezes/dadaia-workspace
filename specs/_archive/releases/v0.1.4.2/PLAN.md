# PLAN: v0.1.4.2 — session-bind, codex-orchestration, and review-gate bug fix

**Status:** Aprovado
**Release ID:** v0.1.4.2
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Strategy

Fix the reported bugs as one patch release because they share the same product
truth problem: runtime behavior and projected instructions must not overclaim
what the system actually does. The release also codifies the strict development
quality gate: implementation is only complete after QA, security, and code review
approval.

The default Codex orchestration decision is manual/reference-only unless a
supported runtime integration point is found during T-BUG-04. The release should
not invent subprocess-based spawning that Codex cannot support.

## 2. Layers affected

| Layer | What changes |
|-------|--------------|
| `dadaia_workspace/cli/commands/` | Context help and specs/memory/orchestration command guidance |
| `dadaia_workspace/features/spec_context/` | Session-bound context resolution surfaces if needed |
| `dadaia_workspace/features/specs/` | Doctor context resolution and message text |
| `dadaia_workspace/core/` | Remove or quarantine primary-context protocols if unused |
| `dadaia_workspace/infrastructure/` | Remove/quarantine primary-context stores; fix Codex dispatcher capabilities |
| `dadaia_workspace/public/` | Agent/skill/rule/data wording and gate script terminology |
| `dadaia_workspace/public/workflows/` | Pre-implementation agreement and post-implementation review/QA workflow gates |
| `specs/memory/` | Closure-only product truth updates |
| `tests/` | Regression coverage for both bugs |

## 3. Execution order

```
T-BUG-01 → T-BUG-02 → T-BUG-03
                  ↘
                    T-BUG-04 → T-BUG-05
T-BUG-06 → T-BUG-07 → T-BUG-08
all implementation tasks → T-BUG-09 → T-BUG-10
```

## 4. Technical risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Legacy migration cleanup still needs primary strings | Medium | Allow only explicit deletion/migration code and assert exceptions in tests |
| Doctor context resolution touches several CLI paths | Medium | Add focused CLI tests before broad text cleanup |
| Codex real spawning is unsupported | High | Prefer manual/reference-only mode and make capabilities truthful |
| Public projection drift after text changes | Medium | Run the full asset chain in T-BUG-07 |
| Review gate becomes prose-only | High | Update workflows, agent personas, task-manager skill, and tests so the contract is machine-checkable where practical |
| Reviewers approve late but never saw task testability | High | Add a pre-implementation agreement gate before TASKS approval and require reviewer evidence references |

## 5. Implementation notes

### Session-bound context cleanup

Treat `DADAIA_CONTEXT` and `DADAIA_SESSION_ID` as the active runtime contract.
Commands that need specs must resolve from the bound session/context or accept an
explicit `--specs-dir`. Error messages must mention `dadaia context bind`, not
removed verbs.

`primary_context` strings are allowed only in migration/deletion code paths and
tests that prove legacy files are removed or ignored.

### Codex orchestration

Use manual/reference-only Codex orchestration unless a supported Codex runtime
API exists in the local tool surface. For manual mode:

- `CodexAgentDispatcher.dispatch()` may continue writing invocation files.
- `dispatch_parallel()` must not claim parallel runtime execution.
- Capabilities and projected text must describe manual handoff behavior.
- Public doctor may report Codex workflows/orchestration as reference-only or
  partial, not green parity.

### Implementation-review QA contract

The release must introduce a single strict lifecycle that applies to feature,
bug-fix, hotfix, and cross-cutting implementation work:

1. **Spec agreement gate.** Before TASKS are approved, `project-manager` routes
   the draft task plan to the owning implementer(s), `qa-engineer`,
   `code-reviewer`, and `security-reviewer`. For visible UI work,
   `design-specialist` is included. Each reviewer must confirm the task has
   clear implementation scope, test obligations, review criteria, and security
   checks. Rejection sends the task back to `product-engineer` for spec repair.
2. **Implementation stage.** Implementers reserve the task, implement code, and
   write unit/integration tests in their scope. They emit an
   implementation-complete report, but do not mark the task `[x]`.
3. **Validation fan-out.** `qa-engineer`, `security-reviewer`, and
   `code-reviewer` review the exact implementation diff/commit. QA owns E2E and
   acceptance validation. Security owns secrets/privacy/auth/access-control and
   public asset leakage checks. Code review owns maintainability, architecture,
   test adequacy, and regression risk.
4. **Rework loop.** Any rejection keeps the task open and routes findings back
   to the implementer. The same validation fan-out repeats after fixes.
5. **Done gate.** `project-manager` or `product-engineer` may close the task only
   after all required reviewers approve and evidence paths are recorded. Push,
   PR creation, merge, deploy, and release closure are blocked before this gate.

The contract should be encoded in:

- `project-orchestration` skill and `project-manager` persona;
- `dadaia-task-manager` skill;
- implementer personas (`software-engineer-python`, `software-engineer-node`,
  `frontend-engineer`, `backend-engineer`, `ai-engineer`, `devops-engineer`);
- reviewer personas (`qa-engineer`, `security-reviewer`, `code-reviewer`);
- workflows (`spec-refinement`, `hotfix-release`, `cross-cutting-feature`,
  `code-review-fan-out`, and any implementation workflow/playbook docs);
- tests that assert the gate text and required evidence fields exist.

## 6. Validation plan

Run these commands before closure:

```bash
rg -n "primary_context|is_primary|context promote|context activate" \
  dadaia_workspace/public dadaia_workspace/cli dadaia_workspace/core \
  dadaia_workspace/infrastructure specs/memory

rg -n "Agent tool|supports_parallel|CodexAgentDispatcher|manual/reference-only" \
  dadaia_workspace/public dadaia_workspace/infrastructure specs/memory

rg -n "pre-implementation agreement|implementation-complete|review/QA gate|security-reviewer|code-reviewer|qa-engineer" \
  dadaia_workspace/public/agents dadaia_workspace/public/skills \
  dadaia_workspace/public/workflows specs/memory

source /home/marco/workspace/dadaia/.dadaia/.venv/bin/activate
poetry run pytest -q -p no:cacheprovider -m "unit and not slow" tests/unit
poetry run pytest -q -p no:cacheprovider tests/unit/features/specs/

DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=<session> DADAIA_MODE=SPEC \
  .dadaia/.venv/bin/dadaia public stage
DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=<session> DADAIA_MODE=SPEC \
  .dadaia/.venv/bin/dadaia public install --target all --force
DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=<session> DADAIA_MODE=SPEC \
  .dadaia/.venv/bin/dadaia public doctor
DADAIA_CONTEXT=dadaia-workspace DADAIA_SESSION_ID=<session> DADAIA_MODE=SPEC \
  .dadaia/.venv/bin/dadaia specs doctor
```
