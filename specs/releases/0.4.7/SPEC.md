# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-product-engineer
**Opened:** 2026-09-22
**Origin:** operator-demand

---

## 1. Problem and context

Candidate 12 — "no model API in CI". Operator ruling 2026-09-22: "não podemos ter job de CI com API do
Claude — retire". ADR 0016 (grill Q5 A) made the security verdict a required PR status check produced by
the official `anthropics/claude-code-security-review` Action, which needs a `CLAUDE_API_KEY` secret. The
secret was never added, so the job has failed closed on every PR since it landed, and the branch
ruleset's merges need `--admin`.

## 2. Objective

No CI job calls a model API; the security review is the `dd-code-reviewer` security lens, run by the
main thread before every PR, as it already is.

## 3. Scope (candidate 12)

### FR1 — the job and its secret leave CI
- `.github/workflows/ci.yml` loses the `security-review` job and every reference to `CLAUDE_API_KEY`.
- `tests/contract/test_ci_security_review_job.py` is deleted; `test_ci_preflight_ci_gating_parity.py`
  stops listing the job.
- A contract test refuses, in every `.github/workflows/*.yml`, a `uses:` of an `anthropics/*` action and
  any `CLAUDE_API_KEY`/`ANTHROPIC_API_KEY` reference — the measure of the new principle.

### FR2 — law and skills follow
- The root map template (`public/data/AGENTS.md` §3), `dd-gitflow-default` (`SKILL.md`,
  `CICD-AUTOMATION.md`) and every live citation state: both PRs need CI green and a `dd-code-reviewer`
  APPROVED verdict (security lens included) on the head; no CI job calls a model API.
- `CONTEXT.md` loses the dead verdict-file entry.

### FR3 — canonical memory (ADR 0025, same commit as FR1's code)
- `QUALITY.md` `## Gates`: the three `security-review` statements are deleted; `## Principles` gains
  `P-33 · We run no model API in CI` measured by the FR1 contract test, `ADR: 0025 (accepted)`.

## 4. Out of scope
- The branch ruleset's required checks (operator-owned in GitHub settings): the operator removes
  `Security review (...)`, `E2E panel (Playwright)` and `Security verdict gate (PR head sha)` there.

## 5. Decisions and constraints
- D1: ADR 0025 is operator-born, accepted at append, amending ADR 0016's verdict clause.
- D2: ratchets down only; the diff should delete more than it adds.

## 6. Traceability

| Requirement | Tasks |
|---|---|
| FR1 | T-047-106 |
| FR2 | T-047-107 |
| FR3 | T-047-106 (canonical hunk, PM-staged) |
