# PLAN — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Design (codebase-design vocabulary)

Candidate 9 ships a *distribution*, not a feature. The library already holds the eight
standalone skills, the memory atoms and the LICENSE; what is missing is a renderer that turns
them into the shapes three ecosystems read (`skills/<name>/SKILL.md`, a Claude plugin
marketplace, a docs tree) and a CI step that pushes the result. The design risk is therefore
duplication, not complexity: a second copy of a skill, a second copy of an atom's prose, a
second entry point that means something different from the first.

- **One source, many renderings.** `public/skills/` is the only place a skill's bytes exist;
  `specs/memory/**` is the only place the prose exists. Every artifact this candidate adds is
  *derived*: the skills repository by `build-skills-repo.py`, the docs pages by the
  `derived-from` marker contract, the manifests' `version` by reading `pyproject.toml`. Nothing
  is hand-copied, so nothing can drift.
- **The build is a script, not a verb (ADR 0018).** `dadaia_workspace/public/scripts/build-skills-repo.py`
  follows the `lint-dadaia-cli-reachability.py` precedent exactly: stdlib only, `≤ 150` lines,
  one `main(argv)`, exercised from `tests/contract/`. It lives under `public/scripts/`, **not**
  under a skill — so V36 (36 files / 4191 lines for skill `scripts/`) is untouched by it; V35
  (18 dirs / 2880 lines under `public/skills`) is the ratchet FR1 must respect.
- **Seam placement (FR1).** The standalone set is *data*, not a list in code or in a test:
  `public/entities/behavior-map.json` gains one top-level key `standalone_skills` beside
  `declared_overlaps`. The contract test, the build script and any future audit all read that
  one key. Deletion test: delete the key and the eight names reappear in three places — it earns
  its keep.
- **Seam placement (FR2/CI).** The CI job's seam is the secret. `SKILLS_REPO_TOKEN` absent →
  one `::error::` naming the secret and a non-zero exit, exactly the `security-review` shape in
  `ci.yml`. No silent skip, no "best effort" push, no fallback token.
- **Seam placement (FR3).** The docs seam already exists: the `<!-- derived-from: <slug>
  sha256:<12hex> -->` marker (`sha256(atom bytes, \r\n→\n)[:12]`) and
  `tests/contract/test_docs_derived_from_memory.py`'s covered set. Five new pages join the
  covered set; no new mechanism, no docs build toolchain (GitHub Pages serves `/docs` raw).
- **Replace, don't layer (FR3 alias).** `dadaia-workspace = "…cli.main:_safe_app"` is a second
  *name* for the one callable, not a second CLI. The unit test asserts identity of the resolved
  callables, which is what stops it becoming a fork.
- **Deletion test on the touched surfaces.** `behavior-map.json` grows one key that removes a
  literal from two future readers; `pyproject.toml` grows two lines that remove an install
  instruction from the README; `release.yml` grows one job whose alternative is a manual
  operator act repeated per release. Nothing grows an existing *feature* module — no branch
  enters `features/**` or `infrastructure/**` in this candidate.

## Order of work (tracer bullets)

Each task leaves `dadaia ci preflight` green and the live instance re-projectable.

1. **T-047-80 (FR1)** — the tracer: the eight skills become spec-conformant and the
   `standalone_skills` key exists. Everything downstream reads that key.
2. **T-047-81 (FR2 build)** — the renderer, proven idempotent, against the now-valid skills.
3. **T-047-82 (FR2 CI)** — the publish job, fail-closed on the secret.
4. **T-047-83 (FR3 pages)** — the four derived pages and their markers.
5. **T-047-84 (FR3 article + wiring)** — the ledger article, README, `llms.txt`, the
   `Documentation` URL.
6. **T-047-85 (FR3 alias)** — the `dadaia-workspace` console script and the quickstart's uvx line.
7. **T-047-86 (FR4)** — CHANGELOG, `_RELEASE.json` log, live instance re-projected, closure.

80 precedes 81 because the build renders whatever the skills are; 83 precedes 84 because the
article's README/`llms.txt` wiring lists the pages 83 creates; 85 lands after 84 so the
quickstart is edited once.

## Verification

- `dadaia ci preflight` (`ruff format --check`, `ruff check`, `mypy --strict`, `pytest`) green
  before every push; every CI job watched to green except the by-design red `security-review`.
- Per-AC: AC1.1 `tests/contract/test_standalone_skills.py` + V35 unchanged in
  `tests/contract/test_slop_ratchets.py`; AC2.1 `tests/contract/test_skills_repo_build.py`
  (manifest set, per-skill byte equality with `public/skills`, second build changes nothing) and
  the `release.yml` pin in `tests/contract/test_ci_workflow_hygiene.py`; AC3.1
  `tests/contract/test_docs_derived_from_memory.py` covered set + `tests/unit/cli/test_console_scripts.py`
  + `dadaia doctor` exit 0 on the live instance; AC4.1 the CI run and the review verdict.
- **Binary availability (verified 2026-09-21 on this machine).** `skills-ref` **is on PyPI**
  (`pip index versions skills-ref` → 0.1.1, 0.1.0; `pip download --no-deps skills-ref` succeeds),
  so the CI contract job may `pip install skills-ref` and run `skills-ref validate <skill dir>`
  one directory at a time. It is **not installed locally**, and `claude` **is** on PATH while
  `uv`/`uvx` is **absent**. Consequence, binding on T-047-80/81: the contract tests implement the
  spec rules themselves (name charset/length/dir equality, description length, `SKILL.md`
  ≤ 500 lines, manifest field sets) and treat both binaries as an *extra* assertion guarded by
  `shutil.which`, skipping when absent. A green local run therefore never depends on a binary.

## Risks

**Bug history (standing rule).** The ledger's families touching this surface are
`public-install`/`projection` (the skill corpus is projected into four harness trees) and
`specs`/`docs` derivation. The recurring shape is *a second copy that drifts*: *public install
overwrites a consumer's hand-authored AGENTS.md*; *install-target doctor goldens stale after
skill additions*; *public install skips self-projection so the library repo's AGENTS.md drifts*.
Every one is a copy nobody re-derived. This candidate must not create a ninth copy of a skill:
the built repository is a build **output**, written to an out-dir passed on argv, never committed
into this repository and never read back as a source. If a reviewer finds skill bytes tracked
outside `public/skills/`, the build script was the wrong shape.

- **V35 is the hard ratchet (18 dirs / 2880 lines).** Adding `license:`/`compatibility:` to eight
  frontmatters is +16 lines. They are paid by deletion **inside the same skill** — a redundant
  line in that skill's body, not in a different one. Any task that cannot pay locally stops and
  reports rather than raising the ceiling. V32 (682) and the module ceiling (699/700) are not
  touched: no production module changes.
- **The 12 KB / 24 KB ratchet (V34)** applies to the live candidate trio; these documents are
  measured with `wc -c` before the definition commit.
- **Operator acts are blocking, not fixable (D3).** The `dadaia-skills` repository,
  `SKILLS_REPO_TOKEN` and GitHub Pages are the operator's. T-047-82 therefore ships a job that is
  *correct and red* until the secret exists — the same posture as `security-review` (D1). The
  README's `npx skills add marcoaureliomenezes/dadaia-skills` line and the Pages URL are written
  now and become true when D3 lands; the PM decides whether that is acceptable before T-047-84.
- **The uvx line is unverifiable here.** `uv` is not installed and 0.4.7 is not on PyPI, so
  `uvx dadaia-workspace init …` cannot be run end to end in this candidate. T-047-85 proves what
  is provable: both console-script entry points resolve to the same callable. The quickstart
  shows the uvx line first with the pip line beside it, so a reader is never stuck if uvx fails.
- **Two entry points, one CLI.** The risk of the alias is divergence — a future change adding a
  second `_safe_app`-like target. `tests/unit/cli/test_console_scripts.py` asserts *identity*, not
  merely that both resolve, which is what makes divergence fail.
- **Marker staleness.** A memory atom edited after a page is written silently invalidates its
  `sha256:<12hex>`; `test_docs_derived_from_memory.py` is the guard, and the closure task re-runs
  it after the PM's memory pass — if the pass edits `public-asset-distribution` or
  `sdd-bug-backlog-governance`, the markers in T-047-83/84's pages must be regenerated.
- **The ledger numbers age.** 514 records / 497 resolved / 38 CRITICAL / 231 HIGH are the
  closure-time counts; the article states them as "at the 0.4.7 closure", never as a live figure,
  so no test needs to pin a moving number.
