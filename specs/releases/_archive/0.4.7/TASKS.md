# TASKS — Release: 0.4.7

**Status:** Approved
**Owner:** dd-software-engineer

## Candidate 12 — no model API in CI

- [x] **T-047-106 — The security-review job leaves CI; a scan refuses any model API in workflows.**
  Delete the `security-review` job and every `CLAUDE_API_KEY` reference from `.github/workflows/ci.yml`
  (and its header comment); delete `tests/contract/test_ci_security_review_job.py`; drop the job from
  `test_ci_preflight_ci_gating_parity.py`. Add the scan to `tests/contract/test_ci_workflow_hygiene.py`:
  no `uses: anthropics/*`, no `CLAUDE_API_KEY`/`ANTHROPIC_API_KEY` in any workflow.
  `RED:` the scan fails on today's `ci.yml`.
  `Write set:` `.github/workflows/ci.yml`, `tests/contract/{test_ci_security_review_job.py,test_ci_preflight_ci_gating_parity.py,test_ci_workflow_hygiene.py}`
  `blocked by:` — · `delivers:` FR1

- [x] **T-047-107 — Law and skills state the local security lens, not a CI job.**
  `public/data/AGENTS.md` §3, `dd-gitflow-default` `SKILL.md` and `CICD-AUTOMATION.md`, `tests/contract/README.md`:
  both PRs need CI green and a `dd-code-reviewer` APPROVED verdict (security lens) on the head; no CI job
  calls a model API. `CONTEXT.md` drops the verdict-file entry. Re-record behavior-map / CONTEXT-MAP hashes.
  `RED:` `test_behavior_map.py`, `test_context_map.py` after re-record; `git grep -n "security-review" -- dadaia_workspace` only generic senses.
  `Write set:` `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/skills/dd-gitflow-default/**`,
  `dadaia_workspace/public/entities/behavior-map.json`, `dadaia_workspace/public/data/CONTEXT-MAP.md`, `CONTEXT.md`, `tests/contract/README.md`
  `blocked by:` T-047-106 · `delivers:` FR2
