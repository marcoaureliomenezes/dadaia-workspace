# Closure: Release — v0.1.20

> **Status:** Aprovado
> **Release ID:** v0.1.20
> **Owner:** product-engineer
> **Closed:** 2026-06-25

## Summary

v0.1.20 closes the three residual polish items the v0.1.19 final zero-drift re-audit
flagged as "operator's call". All three are pure documentation/severity-word
corrections (zero behavior change), fixed so the operator's "no dead/stale code,
documentation and specs" mandate holds literally:

- **D1** — `specs/memory/product/sdd/specs-doctor.md` TREE-4 severity `ERROR` → `WARNING`
  (matches `doctor.py:1987` `Severity.WARNING`).
- **D2** — `doctor.py` `fix()` docstring corrected: it resolves TREE-4 only; TREE-3
  memory atoms are operator-authored `.md` (no Jinja/HTML generation), warn-only.
- **D3** — `container.py` `build_agent_runtime` docstring corrected: Codex and PI are
  live CLI-headless adapters; the Claude SDK adapter body is real (Ring-1 boundary,
  only the default `query_fn` transport deferred); OpenCode remains a documented stub.

## Tasks completed

| Task ID | Description | Commit |
|---------|-------------|--------|
| T-20-01 | Author SPEC/PLAN/TASKS | `<closure>` |
| T-20-02 | D1 specs-doctor.md TREE-4 severity ERROR→WARNING | `<closure>` |
| T-20-03 | D2 doctor.py fix() docstring | `<closure>` |
| T-20-04 | D3 container.py build_agent_runtime docstring | `<closure>` |
| T-20-05 | preflight + security APPROVE + CLOSURE + archive + gated push + CI green | `<closure>` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Format + lint + strict-type + full tests | `dadaia ci preflight` | 4/4 PASS (ruff format --check; ruff check; mypy --strict; pytest) |
| Memory atoms lint | `lint-memory-atoms.py` | 30 OK, 0 WARN, 0 ERROR |
| SDD structural health | `dadaia specs doctor` | exit 0 |
| Public projection + privacy | `dadaia public doctor` | exit 0; `[ok] public-privacy` |
| Security verdict (push gate) | security-reviewer APPROVE | keyed to the final pushed sha |
| GitHub Actions CI | CI for the closing tip | watched to green |

## Drifts

### residual-stale-docs-corrected

The v0.1.19 re-audit confirmed zero behavioral memory↔code drift but found one LOW
memory mislabel (TREE-4 severity word) and two INFO stale code docstrings (doctor.py
`fix()` TREE-3/Jinja claim; container.py "documented stub" for the now-real Claude SDK
adapter, predating PI). All three corrected here. No behavior, tests, or dependencies
changed. Post-fix: `specs doctor` exit 0, lint 30 OK, preflight 4/4.

## Memory updates

`specs/memory/product/sdd/specs-doctor.md` — TREE-4 severity corrected to WARNING (D1).
No other atom changed; no atom created or deleted; catalog frontmatter unaffected (no
regeneration needed). The auto-memory `project_pi_fourth_harness` atom already records
the v0.1.19/v0.1.20 fidelity arc.

## Notes

Polish release: no engine change, no new transport, no harness behavior change, no
dependency change. It makes the documentation/severity surface match the code exactly.
