# Job 3 — Windows by static rules: a configuration pin (FR6)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §1.

- **A pin, not a sweep.** The SPEC's "128 product `read_text`/`write_text` calls with no encoding" is a grep artifact: 127 are the kernel helpers `_platform.read_text`/`write_text` (already `encoding="utf-8"`), the 128th is `importlib.metadata`. `ruff --preview --select PLW1514` reports 0 hits in `dadaia_workspace/`, `tests/` and `scripts/`, and 1 in `evals/tasks/t2-block-list-bug/tests/test_grade.py:51`. AC6.2 therefore reduces to that one line.
- **Ruling superseded.** Operator Q6 "A: static rules, no new step" governs; it supersedes ADR 0265's "adds no guard, no lint rule and no gate" for the lint pin only. The rule rides `ruff check`, which `ci.py job` already runs: no step, job or gate is added.
- **Config.** `[tool.ruff.lint]` gains `preview = true`, `explicit-preview-rules = true` and `"PLW1514"` in `select` (the option pair keeps every other preview rule off; verify by running `ruff check` and seeing only the one rule is new). `.gitattributes` gains `text eol=lf` on `/tests` and `/scripts` (the tree has 0 CRLF files today: `git ls-files --eol` reports `i/lf w/lf` for all 939).
- **Revert-check.** Removing the `encoding` argument at `test_grade.py:51` turns `ruff check` red; AC6.3 evidence is `git check-attr eol` on one file of each tree.

**Gate law (rc-17).** The job's `verify:` is `python scripts/ci.py job` (median 1m52, measured; ruff runs in it). An implementer's definition of done is that run, plus `python scripts/ci.py lint` clean with the rule on, plus the own-diff self-check over `git diff <base>...HEAD`: no removed `assert` line, no added skip/xfail, and the sweep greps. No preflight, no full CI line; CI on push is the net.

**Sweep greps.** `git ls-files --eol tests scripts | grep -v 'w/lf'` prints nothing; `git check-attr eol tests/conftest.py scripts/ci.py` prints `eol: lf` twice; `grep -n 'read_text\|write_text\|open(' evals/tasks/t2-block-list-bug/tests/test_grade.py` shows `encoding=` on each.

Tasks: 1 (1 jr, 0 sr, 0 pe). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J3.T1 | jr | AC6.1, AC6.2, AC6.3 | `pyproject.toml`, `.gitattributes`, `evals/tasks/t2-block-list-bug/tests/test_grade.py` | three config words, one `encoding="utf-8"` at `test_grade.py:51`, two attribute words; no RED (the linter is the test) |
