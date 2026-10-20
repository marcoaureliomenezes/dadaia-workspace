# Job 1 — the §3a law gaps, the block-list reading, two CHANGELOG lines (FR1, FR10)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`; `S/` = `dadaia_workspace/public/skills/`. Design and evidence: PLAN §1, §1.1, §2. Law text only: no task here has a RED test, and every AC cites "none, law text" or the existing digest and copy pins.

- **Shape (T1).** `S/dd-gitflow-default/SKILL.md` §3a gains or widens rows; no existing row number moves, so the eight citing lines (`git grep -nE "shape[- ]?[0-9]+" -- dadaia_workspace/public docs README.md`: `data/worktrees-AGENTS.md:21`, `dd-bug-registration` :41, `dd-bug-resolution` :67 and :78, `dd-code-review` :41, `dd-release-definition` :63, `agents/dd-product-engineer.md:35`, `scaffold/releases/AGENTS.md:26`) stay true; new rows take numbers 12 and 13.
  - AC1.1 (L1): beside shape 3, the row for a fix that is itself a test change: a `test(<id>):` commit whose body carries the `fix(bugs): <id> — <cause>` line, the cited fix of the record.
  - AC1.2 (L2): shape 5 and shape 10 name the `pyproject.toml` version line and its commit `chore(release): rc-<N> is labelled <release>rc<N>`, in the `wt-rc` define tree.
  - AC1.3 (L3): row 12 is a code revert, git's own `Revert "<subject>"` with body `This reverts commit <sha>.`, in a task or hotfix tree. Row 13 is a format-only commit: shape 6's `style(<id>): …`, with no `fix(bugs)` or `refactor(bugs)` line, because a record's cited fix is the newest commit holding such a line.
  - AC1.4 (L4): the archive row of shape 4 lists `wt-main` job trees beside "any lane" and the `wt-rc`.
- **Public-text limits (T1, T2).** `tests/infrastructure/test_privacy_check.py` fails shipped text that names an ADR number (`ADR \d{4}`), a library path (`dadaia_workspace/`), or a one-stack tool (`ruff`, `poetry`, `mypy`, `gh pr`, `github.com`); say "a format-only commit". The words below are the law's, not the ADR's.
- **L5 wording, ruled by the main thread (T2).** Operator ruling of 2026-10-20: "Register, block-list fix on wt-rc (Recommended)". In `dadaia_workspace/public/scaffold/bugs/AGENTS.md` §2, block-list item (1) reads exactly: "(1) the work branch's `verify:` line is red, or merging the change would turn the work branch's CI red;". Nothing else on that line changes. The clause requires no remote or CI of a user's repo: with none, its second half never fires.
- **Digest procedure (T2).** `specs/bugs/AGENTS.md` is the byte-identical mirror (`diff` prints nothing). The new file's sha256 is appended to the `scaffold/bugs/AGENTS.md` array of `public/templates/shipped-hashes.json` (append-only: every old digest stays, so an unedited older copy still reads as shipped). `CANON_AT[13]` in `dadaia_workspace/core/specs_version.py` is re-pinned to the value `tests/core/test_specs_version.py::test_a_canon_change_bumps_the_stamp` computes and prints on failure; stamp 13 is unpublished (`git show v0.4.7:dadaia_workspace/core/specs_version.py` reads `CANONICAL_SPECS_VERSION = 7`; earlier re-pins of 13: `ff2cdd509`, `847cdee17`, `ee2104980`), so the re-pin is lawful and no stamp bump is made.
- **Consumers (pre-mortem answered in PLAN §2).** Item (1) of the block list is quoted by no other file: `README.md:122,126`, `docs/concepts.md:42`, `docs/bug-loop.md:4` and `docs/getting-started.md:170` say "a block-list bug" without the item text, so none changes and none is in `W:`.
- **CHANGELOG (T3).** `CHANGELOG.md:357` stops listing D1 (`CLAUDE_API_KEY`, removed) as open: the line keeps "D3–D6 from candidate 9 are unchanged and still open". `:389` stops listing the `dadaia-skills` repository and its token as pending: the sentence keeps Pages, the marketplace submission and the launch posts. Every heading stays as written (the file's preamble). The commit subject is `docs(J1.T3): …`.

**Gate law.** `verify:` is `python scripts/ci.py job`, unchanged. Definition of done: that run, the reviewer directories below, the own-diff self-check, the sweep greps; no preflight.

**Reviewer test directories** (`python scripts/impact.py <W: files>` at HEAD `84b5a7731`, collapsed; `git grep -n "dd-gitflow-default/SKILL.md" -- tests` adds `tests/core/test_gitflow.py`, which reads the §2a table by path and impact.py cannot see).
- T1: `tests/public/skills/dd_gitflow_default/scripts` (17 files), `tests/core/test_gitflow.py`.
- T2: impact.py prints 148 files in `tests/{cli,contract,core,e2e,features,fixtures,hooks,infrastructure,public}` and `tests/test_container.py` for `core/specs_version.py`, which `container.py` imports; the three data files print `unmapped`. The tests that read the changed bytes are `tests/core/test_specs_version.py`, `tests/features/specs`, `tests/features/migrate` and `tests/infrastructure/test_privacy_check.py`; the reviewer runs those four first and the printed reach after (PLAN §4, seam 3).
- T3: none (`CHANGELOG.md` is unmapped; `tests/contract/test_docs_derived_from_memory.py` excludes it).

**Sweep greps.** `diff dadaia_workspace/public/scaffold/bugs/AGENTS.md specs/bugs/AGENTS.md` prints nothing; `git grep -n "would turn the work branch's CI red" -- dadaia_workspace specs/bugs` prints two lines; `git grep -n "CLAUDE_API_KEY" -- CHANGELOG.md` prints no line that says "open" or "pending"; `git grep -nE "ADR [0-9]{4}|dadaia_workspace/" -- dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` prints nothing.

Tasks: 3 (1 sr, 2 jr). T1 and T3 share no path with T2; the three may run in parallel.

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J1.T1 | sr | AC1.1, AC1.2, AC1.3, AC1.4 | `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` | the four §3a edits above, wording by the engineer, each as a table row or a cell edit, none longer than its neighbours; owner tests: `tests/public/skills/dd_gitflow_default/scripts` and `tests/core/test_gitflow.py` stay green |
| J1.T2 | jr | AC1.5, AC1.6 | `dadaia_workspace/public/scaffold/bugs/AGENTS.md`, `specs/bugs/AGENTS.md`, `dadaia_workspace/public/templates/shipped-hashes.json`, `dadaia_workspace/core/specs_version.py` | block-list item (1) in the ruled words, the byte-identical mirror, the appended digest, the re-pinned `CANON_AT[13]`; owner `tests/core/test_specs_version.py` and the TREE-5 copy-drift tests in `tests/features/specs` |
| J1.T3 | jr | AC10.1 | `CHANGELOG.md` | the two pending lines corrected; headings untouched; no `[0.5.0]` section written |
