# PLAN — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

## Design
- Deletion only: one CI job, one contract test, one secret reference, law lines. The only addition is the
  workflow scan test that measures P-33 (replaces `test_ci_security_review_job.py` one for one).
- Seam: `.github/workflows/*.yml` is the one place a model API could enter CI; the scan reads it as text.
- Bug surface: shrinks — the job failed closed on every PR and forced admin merges.

## Order of work
1. T-047-106: delete the job + its test, add the scan test; canonical QUALITY hunk + ADR 0025 land in the
   same commit (the PM stages).
2. T-047-107: law, skill and glossary text.

## Verification
- `pytest tests/contract/test_ci_workflow_hygiene.py` (scan) and the full suite; `dadaia doctor` clean;
  CI green with no security-review job on the PR.
