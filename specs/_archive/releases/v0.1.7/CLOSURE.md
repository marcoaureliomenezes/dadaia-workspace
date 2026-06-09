# CLOSURE — Release 0.1.7 "Audit Remediation + Unlock the Workflow"

**Status:** Aprovado
**Release ID:** 0.1.7 (minor over 0.1.6)
**Closed:** 2026-06-09
**Branch:** `feature/0.1.7` → squash-merged to `main` (#48). PyPI publish operator-gated (deferred to the cross-platform release).

## Summary

0.1.7 matured across four segments on a single `feature/0.1.7` branch:

- **alpha (T-017-01..20)** — deep-audit remediation: 14 findings fixed; `public_assets.py` split
  (2350→596 lines); net-new gate persona-fallback (later removed in rc-3) + SEC-01 PROTECTED
  `.dadaia/sessions` fix; preflight-absent coverage.
- **rc-2** — two independent re-audits PASS; `bug-registration-guardrail` rule across runtimes.
- **rc-3 "Unlock the Workflow" (T-017-21..28)** — removed the backlog-ownership persona gate (a
  *lock with no key* that blocked the legitimate owner in both Claude and Codex). New product law:
  **no workflow is ever lock-blocked; the single-session lease is the ONLY deterministic lock.**
  `specs/backlog/**` is now plain ADDITIVE.
- **rc-4 "Bug root-cause sweep" (T-017-29..36)** — root-caused and fixed all 8 open reported bugs,
  headlined by the CRITICAL `gate-cross-context-lock-contamination` (lease context now derived
  PATH-first from `repos/<slug>/…`, not first-ALIVE/env).

## Tasks completed

All 39 tasks `[x]` (T-017-01..36, incl. the reopened T-017-11 split and the rc-3/rc-4 additions).
T-017-11 module-split beyond `public_assets.py` deferred to 0.1.8.

| Segment | Tasks | Outcome |
|---|---|---|
| alpha | T-017-01..20 | 14 audit findings; god-module split; SEC-01 fix; preflight coverage. |
| rc-2 | re-audit | Two verification re-audits PASS; bug-registration-guardrail rule. |
| rc-3 | T-017-21..28 | Backlog persona gate deleted; lease is the sole lock; 3 gate tests flipped to ALLOW. |
| rc-4 | T-017-29..36 | All 8 reported bugs fixed `resolved_in: 0.1.7`. |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full pytest suite green | `pytest -p no:cacheprovider` | 2365 passed, 2 skipped, 1 xpassed |
| ruff format + lint clean | `ruff format --check . && ruff check .` | 424 files formatted; All checks passed |
| mypy --strict clean | `mypy --strict dadaia_workspace/` | no issues in 193 source files |
| public doctor exit 0 | `dadaia public doctor` | exit 0 — `[ok] public-privacy` |
| specs doctor 0 ERROR | `dadaia specs doctor` | 0 ERROR |
| PR #48 CI green | `gh pr view 48 --json statusCheckRollup` | all required checks SUCCESS |
| Ship-trio rc-4 unanimous APPROVE | review records in SPEC.md rc-4 section | qa + code-review + security APPROVE |

## Drifts

None outstanding. Deferred (tracked, not lost):
- `gate-fpath-not-canonicalized-before-classifier` (MEDIUM, no live bypass) — bug filed.
- `lease-shell-write-coverage-gap` (MEDIUM, ADR-3) — backlog candidate (lease mediates only agent
  file-tools, not Bash/CLI writes).
- `pre-push-gate-cannot-locate-workspace-venv` (MEDIUM) — bug filed during this close.
- T-017-11 further module splits → 0.1.8.

## Memory updates

`specs/memory/product/sdd/sdd-bug-backlog-governance.md` and `sdd-gate-v3.md` updated to record:
backlog ownership is a coordination convention (not a gate), and the single-session lease is the
only deterministic lock (RULE A2/D removed).

## Backlog returns

None. The cross-platform OS-compatibility initiative (FEAT-XPLAT-OS-COMPAT-01) proceeds as the
next release (0.1.8).

## Archive decision

Archived to `specs/_archive/releases/v0.1.7/`. ACTIVE freed and re-pointed to 0.1.8.
