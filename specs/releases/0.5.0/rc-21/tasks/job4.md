# Job 4 — the homepage names the project's page (FR7 AC7.1)

**Status:** Draft

Wave 1, waits on —. Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN §2, §3 (act A9 sets the GitHub side after the page is live). The edit must land before E (ADR 0269 (a)): the `gh repo edit` act is not a repo change and is not a task.

- **The edit (AC7.1).** `pyproject.toml:37` reads `Homepage = "https://marco-menezes.com/projetos/dadaia-workspace"`; the comment at `:34-35` says the homepage is that page instead of the PyPI project page and keeps the `Documentation` sentence. Nothing else in the file changes: `version` (line 3, `0.5.0rc21`) and every other url stay. The page route is the operator's: `/projetos/dadaia-workspace` (rc-21 grill, Q4: "/projetos/dadaia-workspace + amend 0273 (Recommended)").
- **Consumers.** `git grep -n "pypi.org/project" -- tests scripts dadaia_workspace` prints nothing, so no test or guard pins the old value; `scripts/guards/repo.py` reads `pyproject.toml` for the version label only. The PyPI-distribution atom is the PE's closure edit.

**Gate law.** `verify:` is `python scripts/ci.py job`, unchanged. Definition of done: that run (its `guards` step reads `pyproject.toml`), the own-diff self-check, the sweep grep; no preflight.

**Reviewer test directories.** `python scripts/impact.py pyproject.toml` prints `unmapped`: none beyond the job gate's guards. The reviewer runs `python scripts/guards/run.py`.

**Sweep grep.** `git grep -n "pypi.org/project" -- pyproject.toml` prints nothing; `git diff --numstat <base>...HEAD -- pyproject.toml` prints `2 2` at most.

Tasks: 1 (1 jr).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J4.T1 | jr | AC7.1 | `pyproject.toml` | `Homepage` and its two-line comment repointed; nothing else changes |
