# TASKS: v0.1.4.2 — session-bind, codex-orchestration, and review-gate bug fix

**Status:** Aprovado
**Release ID:** v0.1.4.2
**Owner:** product-engineer
**Created:** 2026-06-04

---

## Execution order

Maximum one `[-]` at a time unless disjoint write sets are declared.

```
T-BUG-01 → T-BUG-02 → T-BUG-03
                  ↘
                    T-BUG-04 → T-BUG-05
T-BUG-06 → T-BUG-07 → T-BUG-08
all implementation tasks → T-BUG-09 → T-BUG-10
```

---

## Tasks

### T-BUG-01 — Define allowed legacy primary-context exceptions

- **Status:** [x]
- **Owner:** software-architect
- **Target files:** `dadaia_workspace/**`, `tests/**`
- **Preconditions:** none
- **Done criterion:** A documented exception list exists in tests or helper code
  for legacy primary-context deletion/migration only; all other hits are treated
  as failures.

Audit every active hit for `primary_context`, `is_primary`,
`context promote`, and `context activate`. Classify each hit as delete, rename,
or explicit legacy migration exception.

---

### T-BUG-02 — Remove session-bind primary residue from CLI/source

- **Status:** [x]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/cli/**`, `dadaia_workspace/core/**`,
  `dadaia_workspace/features/**`, `dadaia_workspace/infrastructure/**`
- **Preconditions:** T-BUG-01 done
- **Done criterion:** CLI commands resolve context from session-bound state or
  explicit flags and never tell operators to use removed activate/promote flows.

Fix specs doctor, memory, migrate, newartifacts, orchestrate, gate helpers, and
any source-level primary-context residue.

Evidence:
- `rg -n "primary_context|is_primary|context promote|context activate|PRIMARY_|JsonPrimaryContextStore|PrimaryContextStore|primary_store" dadaia_workspace/cli dadaia_workspace/core dadaia_workspace/features dadaia_workspace/infrastructure` reports only explicit migration/import cleanup paths.
- `python -m pytest -q -p no:cacheprovider tests/contract/test_session_bound_context_residue.py tests/unit/test_spec_context_service.py tests/unit/features/spec_context/test_service.py tests/unit/test_spec_context_doctor.py tests/unit/test_spec_context_locking.py tests/unit/test_spec_context_lock_reclaim.py tests/unit/features/panel/test_api_contract.py tests/contract/cli/test_cli_memory_catalog.py tests/integration/test_cli_orchestrate.py tests/unit/infrastructure/test_public_assets.py` → 287 passed.

---

### T-BUG-03 — Remove session-bind primary residue from public assets and memory

- **Status:** [x]
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/**`, `specs/memory/**`
- **Preconditions:** T-BUG-01 done
- **Done criterion:** Generated agent/rule/skill/data wording consistently uses
  `dadaia context bind`; no active memory atom describes global primary context
  as current behavior.

Update public source only; generated projections are handled in T-BUG-07.

Evidence:
- `rg -n "primary_context|is_primary|context promote|context activate|PRIMARY_" dadaia_workspace/public specs/memory` returns no hits.
- `python -m pytest -q -p no:cacheprovider tests/contract/test_session_bound_context_residue.py tests/integration/features/spec_artifacts/test_memory.py tests/unit/infrastructure/test_public_assets.py` → 201 passed.
- `bash -n dadaia_workspace/public/scripts/sdd-spec-gate.sh` passed.

---

### T-BUG-04 — Make Codex dispatcher capabilities truthful

- **Status:** [x]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/infrastructure/codex_agent_dispatcher.py`,
  `dadaia_workspace/features/orchestration/**`, relevant tests
- **Preconditions:** T-BUG-01 done
- **Done criterion:** Codex dispatcher capabilities and dispatch results state
  manual/reference-only behavior unless real supported spawning is implemented.

Prefer manual/reference-only mode. Do not claim parallel execution for a loop
that writes handoff files sequentially.

Evidence:
- `rg -n "Codex.*best-effort|best-effort.*Codex|supports_parallel.*True|parallel \\(best-effort\\)|Codex supports best-effort|mode=DispatcherMode.CODEX|DispatcherMode.CODEX, True" dadaia_workspace tests` reports only Claude's native `supports_parallel=True`.
- `python -m pytest -q -p no:cacheprovider tests/unit/features/agents/test_codex_dispatcher_parallel.py tests/unit/features/agents/test_codex_dispatcher_unsupported.py tests/unit/features/agents/test_codex_dispatcher_sequential.py tests/unit/test_orchestration_runtime.py tests/unit/test_orchestration_runner.py tests/unit/test_orchestration_service.py` → 59 passed.

---

### T-BUG-05 — Align Codex-facing orchestration wording

- **Status:** [x]
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/agents/**`,
  `dadaia_workspace/public/workflows/**`, `specs/memory/product/agent-orchestration.md`
- **Preconditions:** T-BUG-04 done
- **Done criterion:** Codex-facing text no longer promises spawned subagents or
  runtime parallelism when the CLI only emits manual handoffs.

Use explicit language such as manual handoff, reference-only workflow, or
host-conversation subagent tool when available.

Evidence:
- `rg -n "best-effort|deferred multi-agent|fake literal|parallel stages may be dispatched in parallel|run in parallel|runs them in parallel|builds in parallel|work in parallel|race ahead in parallel" dadaia_workspace/public/agents dadaia_workspace/public/workflows specs/memory/product/agent-orchestration.md` has no Codex-facing runtime-concurrency promises.
- `python -m pytest -q -p no:cacheprovider tests/unit/test_workflow_schema.py tests/unit/features/workflows/test_service.py tests/integration/panel/test_api_workflows.py` → 47 passed.

---

### T-BUG-06 — Add regression tests for both bugs

- **Status:** [x]
- **Owner:** qa-engineer
- **Target files:** `tests/**`
- **Preconditions:** T-BUG-02 through T-BUG-05 done
- **Done criterion:** Tests fail on the reported bugs and pass after the fixes:
  no stale primary-context active hits, current context-bind guidance, and
truthful Codex dispatcher/manual orchestration output.

Evidence:
- `python -m pytest -q -p no:cacheprovider tests/contract/test_session_bound_context_residue.py tests/contract/test_codex_reference_only_wording.py tests/unit/features/agents/test_codex_dispatcher_parallel.py tests/unit/features/agents/test_codex_dispatcher_unsupported.py tests/unit/features/agents/test_codex_dispatcher_sequential.py tests/unit/test_orchestration_runtime.py tests/unit/test_workflow_schema.py tests/unit/features/workflows/test_service.py` → 71 passed.

---

### T-BUG-07 — Define strict implementation-review QA contract

- **Status:** [x]
- **Owner:** product-engineer
- **Target files:** `dadaia_workspace/public/skills/project-orchestration/SKILL.md`,
  `dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md`,
  `dadaia_workspace/public/agents/project-manager.md`,
  `dadaia_workspace/public/workflows/**`
- **Preconditions:** none
- **Done criterion:** Public workflow/playbook docs define the full lifecycle:
  pre-implementation agreement, implementation-complete handoff, review/QA
  fan-out, rework loop, and done gate. They explicitly forbid push, PR, merge,
  deploy, release closure, and `[x]` task closure before green QA/security/code
  review approval.

The contract must state that before TASKS approval, the owning implementer(s),
`qa-engineer`, `code-reviewer`, and `security-reviewer` agree with each task's
implementation scope, test plan, E2E/validation plan, review criteria, and
security/privacy checks. UI tasks also require `design-specialist` agreement.

Evidence:
- `python -m pytest -q -p no:cacheprovider tests/unit/test_workflow_schema.py tests/unit/features/workflows/test_service.py tests/integration/panel/test_api_workflows.py` → 47 passed.
- Public orchestration docs now define pre-implementation agreement, implementation-complete handoff, review/QA fan-out, rework loop, and done gate before `[x]`, push, PR, merge, deploy, CLOSURE, or memory updates.

---

### T-BUG-08 — Align implementer and reviewer personas with the gate

- **Status:** [x]
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/agents/software-engineer-python.md`,
  `dadaia_workspace/public/agents/software-engineer-node.md`,
  `dadaia_workspace/public/agents/frontend-engineer.md`,
  `dadaia_workspace/public/agents/backend-engineer.md`,
  `dadaia_workspace/public/agents/ai-engineer.md`,
  `dadaia_workspace/public/agents/devops-engineer.md`,
  `dadaia_workspace/public/agents/qa-engineer.md`,
  `dadaia_workspace/public/agents/security-reviewer.md`,
  `dadaia_workspace/public/agents/code-reviewer.md`
- **Preconditions:** T-BUG-07 done
- **Done criterion:** Implementer personas say implementation completion is a
  handoff, not task completion; reviewer personas define approve/reject output
  contracts; all require evidence paths and rerun after rework.

Include explicit security/privacy leakage checks for public assets, secrets,
auth/access control, dependency additions, generated files, and consumer-specific
data.

Evidence:
- `python -m pytest -q -p no:cacheprovider tests/contract/test_source_repo_hygiene.py tests/contract/test_codex_reference_only_wording.py` → 5 passed.
- Target implementer personas now state implementation-complete handoff, not DONE; reviewer personas define `APPROVE`/`REQUEST_CHANGES`, evidence paths, rerun-after-rework, and security/privacy leakage checks.

---

### T-BUG-09 — Add regression tests for workflow gate contract

- **Status:** [x]
- **Owner:** qa-engineer
- **Target files:** `tests/**`
- **Preconditions:** T-BUG-07 and T-BUG-08 done
- **Done criterion:** Tests assert public workflows/skills/personas contain the
  required pre-implementation agreement gate, post-implementation review/QA gate,
  rework loop, approval evidence, and no-push/PR/deploy-before-approval wording.

Evidence:
- `python -m pytest -q -p no:cacheprovider tests/contract/test_workflow_review_gate_contract.py tests/contract/test_source_repo_hygiene.py tests/contract/test_codex_reference_only_wording.py` → 11 passed.

---

### T-BUG-10 — Propagate assets and verify release

- **Status:** [x]
- **Owner:** devops-engineer
- **Target files:** `.dadaia/agentic/`, `.claude/`, `.codex/`, `.opencode/`,
  `.agents/` (generated projections)
- **Preconditions:** T-BUG-01 through T-BUG-09 all `[x]`
- **Done criterion:** Full validation plan from PLAN §6 exits 0, public doctor
  has no drift, specs doctor has no errors, and no forbidden cache/state dirs
  exist in the repo.

Evidence:
- `rg -n "primary_context|is_primary|context promote|context activate" dadaia_workspace/public dadaia_workspace/cli dadaia_workspace/core dadaia_workspace/infrastructure specs/memory` reports only explicit migration/import cleanup paths.
- `rg -n "Agent tool|supports_parallel|CodexAgentDispatcher|manual/reference-only" dadaia_workspace/public dadaia_workspace/infrastructure specs/memory` confirms truthful dispatcher capability and reference-only/manual wording.
- `rg -n "pre-implementation agreement|implementation-complete|review/QA gate|security-reviewer|code-reviewer|qa-engineer" dadaia_workspace/public/agents dadaia_workspace/public/skills dadaia_workspace/public/workflows specs/memory` confirms the review/QA gate contract surfaces.
- `.dadaia/.venv/bin/dadaia public stage` staged 12 asset groups.
- `.dadaia/.venv/bin/dadaia public install --target all --force` processed 176 workspace-root assets.
- `.dadaia/.venv/bin/dadaia public doctor` exited 0 with `[ok] public-privacy`, expected Codex `[reference-only]` workflow entries, and no drift failures.
- `.dadaia/.venv/bin/dadaia specs doctor` exited 0 errors with 5 existing warnings.
- `.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider -m "unit and not slow" tests/unit` → 1543 passed, 1 xpassed.
- `.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/features/specs/` → 96 passed.
- Forbidden repo artifact scan for `.dadaia`, `.venv`, pytest/mypy/ruff caches, coverage, Playwright reports, test-results, and `__pycache__` returned no paths after cleanup.
