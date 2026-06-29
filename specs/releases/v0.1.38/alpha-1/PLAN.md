# PLAN: v0.1.38 alpha-1 - pi-agent-fourth-harness WS-PI-5

**Status:** Aprovado
**Release ID:** v0.1.38
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

---

## Work Plan

| Task | Work | Validation |
|------|------|------------|
| T1 | Verify the standalone `dadaia-pi-workspace` checkout is clean except for the deprecation `README.md`, and validate the README points to `dadaia-workspace` PI support. | `git status --short`; README inspection. |
| T2 | Run `dadaia context dead dadaia-pi-workspace --commit` to commit/push the pointer and remove the local checkout through the workspace lifecycle. | `dadaia context show dadaia-pi-workspace --json`; `test ! -e repos/dadaia-pi-workspace`. |
| T3 | Mark `pi-agent-fourth-harness` consumed/delivered for v0.1.38 and update the candidate index if needed. | `rg pi-agent-fourth-harness specs/backlog`; specs doctor. |
| T4 | Close the release with evidence, memory updates if required, final review handoff, and push. | Focused commands, full pre-push gate. |

## Validation Commands

```bash
.dadaia/.venv/bin/dadaia context show dadaia-pi-workspace --json
.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs
.dadaia/.venv/bin/dadaia public doctor
find repos/dadaia-workspace -type d \( -name .dadaia -o -name .venv -o -name .pytest_cache -o -name .mypy_cache -o -name .hypothesis -o -name .ruff_cache -o -name test-results -o -name playwright-report -o -name coverage \) -print
```
