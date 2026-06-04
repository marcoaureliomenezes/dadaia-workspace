# TASKS: v0.1.5 — session-bind and codex-orchestration bug fix

**Status:** Aprovado
**Release ID:** v0.1.5
**Owner:** product-engineer
**Created:** 2026-06-04

---

## Execution order

Maximum one `[-]` at a time unless disjoint write sets are declared.

```
T-BUG-01 → T-BUG-02 → T-BUG-03
                  ↘
                    T-BUG-04 → T-BUG-05 → T-BUG-06 → T-BUG-07
```

---

## Tasks

### T-BUG-01 — Define allowed legacy primary-context exceptions

- **Status:** [ ]
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

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/cli/**`, `dadaia_workspace/core/**`,
  `dadaia_workspace/features/**`, `dadaia_workspace/infrastructure/**`
- **Preconditions:** T-BUG-01 done
- **Done criterion:** CLI commands resolve context from session-bound state or
  explicit flags and never tell operators to use removed activate/promote flows.

Fix specs doctor, memory, migrate, newartifacts, orchestrate, gate helpers, and
any source-level primary-context residue.

---

### T-BUG-03 — Remove session-bind primary residue from public assets and memory

- **Status:** [ ]
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/**`, `specs/memory/**`
- **Preconditions:** T-BUG-01 done
- **Done criterion:** Generated agent/rule/skill/data wording consistently uses
  `dadaia context bind`; no active memory atom describes global primary context
  as current behavior.

Update public source only; generated projections are handled in T-BUG-07.

---

### T-BUG-04 — Make Codex dispatcher capabilities truthful

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/infrastructure/codex_agent_dispatcher.py`,
  `dadaia_workspace/features/orchestration/**`, relevant tests
- **Preconditions:** T-BUG-01 done
- **Done criterion:** Codex dispatcher capabilities and dispatch results state
  manual/reference-only behavior unless real supported spawning is implemented.

Prefer manual/reference-only mode. Do not claim parallel execution for a loop
that writes handoff files sequentially.

---

### T-BUG-05 — Align Codex-facing orchestration wording

- **Status:** [ ]
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/agents/**`,
  `dadaia_workspace/public/workflows/**`, `specs/memory/product/agent-orchestration.md`
- **Preconditions:** T-BUG-04 done
- **Done criterion:** Codex-facing text no longer promises spawned subagents or
  runtime parallelism when the CLI only emits manual handoffs.

Use explicit language such as manual handoff, reference-only workflow, or
host-conversation subagent tool when available.

---

### T-BUG-06 — Add regression tests for both bugs

- **Status:** [ ]
- **Owner:** qa-engineer
- **Target files:** `tests/**`
- **Preconditions:** T-BUG-02 through T-BUG-05 done
- **Done criterion:** Tests fail on the reported bugs and pass after the fixes:
  no stale primary-context active hits, current context-bind guidance, and
  truthful Codex dispatcher/manual orchestration output.

---

### T-BUG-07 — Propagate assets and verify release

- **Status:** [ ]
- **Owner:** devops-engineer
- **Target files:** `.dadaia/agentic/`, `.claude/`, `.codex/`, `.opencode/`,
  `.agents/` (generated projections)
- **Preconditions:** T-BUG-01 through T-BUG-06 all `[x]`
- **Done criterion:** Full validation plan from PLAN §6 exits 0, public doctor
  has no drift, specs doctor has no errors, and no forbidden cache/state dirs
  exist in the repo.
