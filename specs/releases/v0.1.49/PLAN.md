# PLAN — v0.1.49 — Intake Integrity

**Status:** Aprovado

## Wave map

- **W0 — definition** (this document set): ACTIVE → v0.1.49 DEFINITION; SPEC/PLAN/TASKS
  authored; architecture + QA definition reviews; `Aprovado`; definition commit.
- **W1 — FR1 backlog tracking** (`.gitignore`, `git add specs/backlog`): pure
  repo-truth change, no Python. Commit message scope `intake`.
- **W2 — FR2 invariant derivation** (`features/backlog/subject_registry.py` +
  `tests/unit/test_backlog_subject_registry.py`, contract test if the CLI surface
  changes shape — it does not): TDD — regression tests first (py-docstring leak,
  tests/ leak, memory-doc keep), then drop the `source_root` leg.
- **W3 — FR3 allowlist extension** (`public/scripts/lint-memory-atoms.py` + unit tests
  + scaffold heading audit): TDD — merge-behavior tests + scaffold-coverage test
  first; then Group S + `.heading-allowlist` merge; then
  `public stage && install --target all && public doctor` (projection).
- **W4 — gates + ship**: local `ruff format --check && ruff check && mypy --strict &&
  pytest`; qa-engineer review (alpha gate) as review commit; security-reviewer APPROVE
  handoff carrying the pushed sha (push gate); push; watch CI to green; PR; merge.
- **W5 — closure** (CLOSURE phase): CLOSURE.md with evidence triples; bug `resolved`
  events ×2; consumed-backlog removal (`memory-heading-allowlist-extension` → durable
  copy `specs/_archive/v0.1.49/consumed-backlog/`); memory updates
  (`sdd-bug-backlog-governance`, `specs-doctor`); catalog regenerate + lint; archive
  release dir; ACTIVE → none.

## Write sets (disjoint per wave)

| Wave | Files |
|---|---|
| W1 | `.gitignore`, `specs/backlog/**` (index status only — no content edits) |
| W2 | `dadaia_workspace/features/backlog/subject_registry.py`, `tests/unit/test_backlog_subject_registry.py` |
| W3 | `dadaia_workspace/public/scripts/lint-memory-atoms.py`, `tests/unit/scripts/**`, projection targets via `dadaia public` |
| W5 | `specs/releases/v0.1.49/**`, `specs/_archive/**`, `specs/memory/**`, `specs/bugs/*.jsonl`, `specs/backlog/` (removal) |

W1 and W5 both touch `specs/backlog/` but in disjoint PHASES (W1 adds the tracked set
in IMPLEMENTATION; W5 removes exactly one consumed entry in CLOSURE) — sequential,
never concurrent, so no lease/marker contention.

## Test strategy

- W2: unit layer (registry is pure fs+parse); fixture trees under `tmp_path` with a
  fake `source_root` containing a `.py` docstring INV token and a `tests/` INV token;
  memory-doc INV token must resolve. No CLI runner needed.
- W3: unit layer for the merge function; one test enumerating the headings of the
  linted scaffold atoms (`public/scaffold/memory/*.md` minus the script's
  `_NON_ATOM_FILES` and `index.md`) against the shipped allowlist (fails on any
  future scaffold/allowlist drift; never pulls `AGENTS.md` governance headings into
  the allowlist).
- Full-suite + lint + mypy locally before push (pre-push gate runs them again).

## Rollback

Single feature branch `feature/v0.1.49`; every wave is one commit; revert = drop the
branch before merge. No state-file migrations, no schema changes.
