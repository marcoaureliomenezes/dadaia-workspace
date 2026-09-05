# PLAN — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer

---

## Design (codebase-design vocabulary)

The seam already exists: `core/release_state.py` is the one home of release-state
facts. Candidate 1 deepens that module (filename decider, candidate counter,
per-candidate phase cycle) instead of adding a sibling — callers keep a small
interface (`read`, `PHASES`, filename constant) over more behaviour. The segment
lane fails the deletion test (its behaviour concentrates into the rc-archive
verb) and is deleted, not layered over. `release rc-archive` is one deep CLI
verb: zero options, all validation and mechanics behind it.

## Order of work

1. TDD core: filename decider + legacy fallback (RED on legacy-only tree).
2. TDD canon/doctor: new entries, rename rule, one-live-release rule; retire
   segment entries/rules and their tests (staged deletions).
3. TDD scaffolder + CLI: new-shape `release new`, `rc-archive` verb; delete the
   segment scaffolding lane.
4. Migration commit: `_archive` renames + this release flips to `_RELEASE.json`
   + pyproject/CHANGELOG mint at birth.
5. Law/skills/behavior-map/CONTEXT.md rewrite.
6. Memory update, full preflight, candidate closure.

## Verification

- Full preflight (ruff, mypy --strict, import-linter, pytest) green.
- `dadaia specs doctor` 0 errors on this repo with the new shape live.
- `rc-archive` exercised on a fixture tree (unit) — the real first use happens
  at this candidate's own gate if the operator rules "continue".
