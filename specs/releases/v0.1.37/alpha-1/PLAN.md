# PLAN: v0.1.37 alpha-1 - PI Workflow Hardening

**Status:** Aprovado
**Release ID:** v0.1.37
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

---

## Approach

1. Add a workflow-worker recursion guard to lifecycle prompts and/or request policy so
   Layer-2 workers cannot validly solve a workflow step by invoking another `dadaia
   lifecycle` command.
2. Restrict review-step PI/headless tool profiles where possible, keeping shell access only
   for implementation/create steps that genuinely need it.
3. Introduce a prompt-size budget in lifecycle worker request assembly, with step-specific
   summarization for release-definition create steps. `spec_create` should rely on the
   release-scope handoff plus explicitly selected bug/backlog records, not the entire open
   catalog and historical handoff set.
4. Repair `lifecycle status` no-arg behavior so debugging stuck workflow runs is safe.
5. Repair `lifecycle bug report` default/fake writing so bug intake is trustworthy and
   preserves operator-provided fields.
6. Validate with focused tests covering each root cause, then run PI-relevant workflow
   checks. Prefer fake PI for deterministic recursion/guard tests and real PI only for a
   bounded smoke where it provides unique evidence.

## Commands

```bash
.dadaia/.venv/bin/python -m ruff check --no-cache <touched files>
.dadaia/.venv/bin/python -m mypy --strict <touched python files>
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_lifecycle_pipeline_cli.py \
  repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py \
  repos/dadaia-workspace/tests/integration/cli/test_lifecycle_bug_report_workflow.py \
  repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py -q
.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs
```

## Risk

The main risk is over-restricting worker tools and breaking legitimate create/implementation
steps. Keep the restriction step-aware: review workers should be narrow; create and
implementation workers may still need write/edit or shell capability, but recursive
workflow invocation should remain invalid everywhere.
