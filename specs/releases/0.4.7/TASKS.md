# TASKS — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Candidate 9 — skills distribution, public presence, uvx alias

- [x] T-047-80 — FR1: the eight standalone skills conform to the Agent Skills spec.
  `public/entities/behavior-map.json` gains one top-level key `standalone_skills` (beside
  `schema_version`, `skill_md_line_ceiling`, `declared_overlaps`, `rows`) naming `dd-grill-me`,
  `dd-bug-resolution`, `dd-code-review`, `dd-test-stewardship`, `dd-codebase-design`,
  `dd-domain-modeling`, `dd-architecture-survey`, `dd-ai-eng-knowhow`. Each of those eight
  `SKILL.md` frontmatters gains a one-line `compatibility:` naming
  dadaia-workspace as the home of the full lifecycle (`pip install dadaia-workspace`); every
  body step that opens a scoped `AGENTS.md` is rephrased "inside a dadaia workspace, open …".
  V35 stays 18 dirs / 2880 lines — the frontmatter line is paid by deleting a redundant
  line inside the same skill, never in another.
  Seam: `standalone_skills` is the one data source for the set; no literal list in code or tests.
  RED: `tests/contract/test_standalone_skills.py` — for each name in `standalone_skills`, the
  frontmatter `name` equals the directory and matches `^[a-z0-9]+(-[a-z0-9]+)*$` (1–64, no
  leading/trailing/double hyphen), `description` is 1–1024 chars, `compatibility`
  (≤ 500) is present, `SKILL.md` is ≤ 500 lines, and no body line hard-requires a workspace
  path; the run fails today because `compatibility` is absent from all eight. Ruled at
  implementation: no `license:` line — MIT is carried by the repository LICENSE and by the
  marketplace manifests.
  `skills-ref validate <dir>` asserted per directory only when `shutil.which("skills-ref")`.
  Write set: `dadaia_workspace/public/entities/behavior-map.json`,
  `dadaia_workspace/public/skills/{dd-grill-me,dd-bug-resolution,dd-code-review,dd-test-stewardship,dd-codebase-design,dd-domain-modeling,dd-architecture-survey,dd-ai-eng-knowhow}/SKILL.md`,
  `tests/contract/test_standalone_skills.py`, `tests/contract/test_slop_ratchets.py`.

- [x] T-047-81 — FR2: the skills repository is built, not written.
  New `dadaia_workspace/public/scripts/build-skills-repo.py` — stdlib only, ≤ 150 lines, one
  `main(argv)`, the `lint-dadaia-cli-reachability.py` precedent, under `public/scripts/` and
  **not** under a skill (V36 untouched). `build-skills-repo.py <out>` renders: `skills/<name>/**`
  (every file of each skill in `standalone_skills`, byte-identical to its source),
  `README.md` derived from `[[public-asset-distribution]]` and `[[agentic-entities]]` with
  `<!-- derived-from: <slug> sha256:<12hex> -->` markers and the three install lines
  (`npx skills add`, Claude marketplace, Codex clone), `LICENSE` copied from the repo root,
  `.claude-plugin/marketplace.json` (`name: dadaia-skills`, `owner.name`, one plugin
  `dadaia-skills` with `source: "./"`, `skills: ["./skills/"]`, `description`, `version`,
  `license`, `repository`) and `.claude-plugin/plugin.json` (`name`, `description`, `version`,
  `author.name`), `version` read from `pyproject.toml`. Idempotent: a second run is byte-identical.
  Seam: the out-dir on argv — the output is never tracked in this repository and never read back.
  RED: `tests/contract/test_skills_repo_build.py` — building into `tmp_path` yields exactly the
  manifest set above, each `skills/<name>/**` equals its `public/skills` source file for file,
  both manifests carry the documented field set, and a second build leaves every mtime-independent
  byte identical; fails today because the script does not exist. `claude plugin validate <out>`
  asserted only when `shutil.which("claude")`.
  Write set: `dadaia_workspace/public/scripts/build-skills-repo.py`,
  `tests/contract/test_skills_repo_build.py`, `tests/contract/test_slop_ratchets.py`.

- [x] T-047-82 — FR2: CI publishes the built repository.
  `.github/workflows/release.yml` gains one job after the publish job (`needs:` it) that runs
  `python dadaia_workspace/public/scripts/build-skills-repo.py "$RUNNER_TEMP/skills-repo"` and
  pushes the result to `marcoaureliomenezes/dadaia-skills` `main` with the tag's version as the
  commit subject. Fail-closed: when `secrets.SKILLS_REPO_TOKEN` is empty the job emits exactly
  one `::error::` naming `SKILLS_REPO_TOKEN` and exits non-zero — the `security-review` precedent
  in `ci.yml`; no silent skip, no fallback token, `permissions:` minimal, the token used only in
  the remote URL and never echoed. No new verb enters (ADR 0018).
  Seam: the secret is the gate; the job is correct and red until D3 lands.
  RED: `tests/contract/test_ci_workflow_hygiene.py` — `release.yml` contains a job depending on
  publish that invokes `build-skills-repo.py`, names `SKILLS_REPO_TOKEN` in a guard emitting one
  `::error::`, and no workflow step interpolates the token outside the remote URL; fails today
  because the job is absent.
  Write set: `.github/workflows/release.yml`, `tests/contract/test_ci_workflow_hygiene.py`.

- [ ] T-047-83 — FR3: the four derived docs pages.
  `docs/index.md` (landing: the tagline once, links to the three pages and the skills repository),
  `docs/quickstart.md` (five minutes — install, `init <dir> --harness <name> --repo <url>`, bind,
  doctor, first backlog entry, first candidate; derived from `[[workspace-init]]`,
  `[[context-management]]`, `[[sdd-bug-backlog-governance]]`), `docs/positioning.md` ("your
  product repos never carry agent config; one law governs ten projects"; derived from
  `[[product-vision]]`, `[[spec-context-project]]`), `docs/bug-loop.md` (register → RED → fix →
  resolve; derived from `[[sdd-bug-backlog-governance]]`). Each page carries one
  `<!-- derived-from: <slug> sha256:<12hex> -->` marker per source atom, the hash being
  `sha256(atom bytes with \r\n→\n)[:12]`. No docs build toolchain enters the repository —
  GitHub Pages serves `/docs` on `main` (D3, operator).
  Seam: the `derived-from` marker — the one contract between an atom and a page.
  RED: `tests/contract/test_docs_derived_from_memory.py` — the covered set gains the four pages
  and every marker's hash matches the atom on disk; fails today because the pages are absent from
  the covered set.
  Write set: `docs/index.md`, `docs/quickstart.md`, `docs/positioning.md`, `docs/bug-loop.md`,
  `tests/contract/test_docs_derived_from_memory.py`.

- [ ] T-047-84 — FR3: the ledger article and the public wiring.
  `docs/bug-ledger-lessons.md` — the article: the closure-time counts from
  `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py stats` (514 records, 497 resolved,
  38 CRITICAL, 231 HIGH, stated as "at the 0.4.7 closure", never as a live figure) and the
  fix-chain lesson (an additive fix breeds the next bug; a deletion-shaped fix ends the family),
  derived from `[[QUALITY]]` and `[[sdd-bug-backlog-governance]]` under their markers. `README.md`
  gains a Documentation section linking `https://marcoaureliomenezes.github.io/dadaia-workspace/`
  and the skills repository (`npx skills add marcoaureliomenezes/dadaia-skills`); `llms.txt`
  lists the five new pages; `pyproject.toml` `[tool.poetry.urls]` gains
  `Documentation = "https://marcoaureliomenezes.github.io/dadaia-workspace/"`.
  Seam: the same `derived-from` marker; the article states no number a test must chase.
  RED: `tests/contract/test_docs_derived_from_memory.py` — the covered set gains
  `docs/bug-ledger-lessons.md` with both markers valid; extended to assert `llms.txt` lists every
  file under `docs/` and `README.md` links the Pages URL. Fails today on all three clauses.
  Write set: `docs/bug-ledger-lessons.md`, `README.md`, `llms.txt`, `pyproject.toml`,
  `tests/contract/test_docs_derived_from_memory.py`.

- [ ] T-047-85 — FR3: the `dadaia-workspace` console-script alias.
  `pyproject.toml` `[tool.poetry.scripts]` gains
  `dadaia-workspace = "dadaia_workspace.cli.main:_safe_app"` beside the existing `dadaia`, so
  `uvx dadaia-workspace init <dir> --harness <name> --repo <url>` resolves once 0.4.7 is on PyPI
  (review F9). A second *name*, never a second CLI: no new module, no new verb (ADR 0018).
  `docs/quickstart.md` shows the uvx line first and the `pip install dadaia-workspace` line
  second. `uv` is not installed on this machine and 0.4.7 is not published, so no live `uvx` run
  is claimed anywhere.
  Seam: the entry-point table — two names, one callable.
  RED: `tests/unit/cli/test_console_scripts.py` — parses `pyproject.toml`, asserts both
  `dadaia` and `dadaia-workspace` exist and that importing each target resolves to the *same*
  callable object (identity, not equality of strings); fails today because `dadaia-workspace` is
  absent from the table.
  Write set: `pyproject.toml`, `docs/quickstart.md`, `tests/unit/cli/test_console_scripts.py`.

- [ ] T-047-86 — FR4: closure.
  `CHANGELOG.md` gains a "Candidate 9" section (the skills distribution, the docs site, the
  alias); `specs/releases/0.4.7/_RELEASE.json` gains the closure `log` entry and its milestone
  via `RELEASE_PY phase`; the live instance is re-projected (`public stage` → `public install` →
  `public doctor` exit 0, `dadaia doctor --specs-dir repos/dadaia-workspace/specs` exit 0) so the
  eight re-frontmattered skills are the ones the instance runs; `.github/workflows/ci.yml` e2e
  jobs are left untouched (no init/install flag moved this candidate); dd-code-review dispatched;
  PR #260 updated and watched to green except the by-design red `security-review` (D1). The
  memory pass and the review verdict are the PM's.
  Seam: the live instance is the proof that the library change is real — never hand-edited.
  RED: `tests/contract/test_slop_ratchets.py` (V34/V35/V36 unchanged) plus the full
  `dadaia ci preflight`; the closure is refused while `dadaia doctor` exits non-zero.
  Write set: `CHANGELOG.md`, `specs/releases/0.4.7/_RELEASE.json`.
