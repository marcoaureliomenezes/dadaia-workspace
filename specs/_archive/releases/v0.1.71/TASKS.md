# TASKS: Release v0.1.71

**Status:** Aprovado
**Release ID:** v0.1.71
**Owner:** product-engineer

> RED-first, executed-path, real-artifact fixtures. Reserve `[ ]` → `[-]` before writing,
> `[-]` → `[x]` after. Acceptance for every task includes a remote replay (T-5.1).

### T-1.1 — FR1 write-scope parser handles real consumer grammar `[-]`
- **Write set:** `dadaia_workspace/features/lifecycle/tasks_write_scope.py`,
  `tests/unit/features/lifecycle/test_tasks_write_scope.py`,
  `tests/fixtures/tasks/consumer-specs/releases/v0.2.0/TASKS.md`
- Done: real sample-consumer TASKS.md fixture with `[-] T-3.1` yields its 3 declared
  paths; internal `###`+bold-key grammar still parses; zero/many reserved → `()`.

```
[x] T-1.1
```

### T-2.1 — FR2 --context/--release-id filters on status + handoffs doctor `[ ]`
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`,
  `dadaia_workspace/container.py`,
  `dadaia_workspace/features/lifecycle/workflow_handoff_doctor.py`,
  `tests/unit/cli/test_lifecycle_status_runs_summary.py`,
  `tests/integration/cli/test_diagnostic_context_option.py`
- Done: both commands accept the options; filtered report covers only matching runs;
  absent filter = whole-workspace behavior preserved.

```
[x] T-2.1
```

### T-3.1 — FR3 no-arg context show reflects the bound session `[ ]`
- **Write set:** `dadaia_workspace/cli/commands/context.py`,
  `tests/integration/cli/test_context_show_reflects_bind.py`
- Done: no-arg show resolves to the ALIVE context with a live bound session (newest);
  falls back to first-ALIVE; named show unchanged.

```
[x] T-3.1
```

### T-4.1 — FR4 doctor exempts promote_to_evidence from unconsumed_required `[ ]`
- **Write set:** `dadaia_workspace/features/lifecycle/workflow_handoff_doctor.py`,
  `tests/unit/features/lifecycle/test_workflow_handoff_doctor.py`
- Done: terminal promote_to_evidence payload not flagged; delete_after_consumed still flags.

```
[x] T-4.1
```

### T-5.1 — Remote replay acceptance (all 4 reporters) `[ ]`
- **Write set:** none (acceptance evidence in CLOSURE)
- Done: on the operator's remote, feature branch installed, all four reporter commands
  pass against sample-consumer v0.2.0.

```
[x] T-5.1
```

## Task summary
| Task | FR | Status |
|------|----|--------|
| T-1.1 | FR1 | reserved |
| T-2.1 | FR2 | pending |
| T-3.1 | FR3 | pending |
| T-4.1 | FR4 | pending |
| T-5.1 | acceptance | pending |
